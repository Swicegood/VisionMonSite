import threading
import json
import logging
from django.core.management.base import BaseCommand
from channels.layers import get_channel_layer
import redis
import os
from django.conf import settings
from asgiref.sync import async_to_sync
import psycopg2
from django.utils import timezone
from django.urls import reverse
from django.http import HttpRequest
from monitor.notifications import process_scheduled_alerts_sync  # Updated import

logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv('REDIS_HOST', '192.168.0.71')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_MESSAGE_CHANNEL = 'llm_messages'
REDIS_STATE_CHANNEL = 'state_processing'
REDIS_STATE_RESULT_CHANNEL = 'state_result'

class Command(BaseCommand):
    help = 'Runs a Redis listener and processes scheduled alerts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as a daemon process',
        )

    def handle(self, *args, **options):
        if options['daemon']:
            self.stdout.write('Starting Redis listener and scheduled alerts processor in daemon mode...')
            # Implement daemon logic here if needed
        else:
            self.stdout.write('Starting Redis listener and scheduled alerts processor...')
        
        self.run_listener_and_processor()

    def run_listener_and_processor(self):
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        channel_layer = get_channel_layer()

        # Create and start the Redis listener thread
        listener_thread = threading.Thread(target=self.listen_to_redis_sync, args=(redis_client, channel_layer))
        listener_thread.start()

        # Create and start the scheduled alerts processor thread
        alerts_thread = threading.Thread(target=self.run_scheduled_alerts_processor, args=(redis_client,))
        alerts_thread.start()

        # Wait for both threads to complete (which they never should)
        listener_thread.join()
        alerts_thread.join()

    def listen_to_redis_sync(self, redis_client, channel_layer):
        pubsub = redis_client.pubsub()
        pubsub.subscribe(REDIS_MESSAGE_CHANNEL, REDIS_STATE_RESULT_CHANNEL)

        logger.info(f"Subscribed to Redis channels: {REDIS_MESSAGE_CHANNEL}, {REDIS_STATE_RESULT_CHANNEL}")

        try:
            for message in pubsub.listen():
                logger.debug(f"Received from pubsub: {message}")
                
                if message['type'] == 'message':
                    channel = message['channel'].decode('utf-8')
                    data = message['data']
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    logger.info(f"Received message from Redis channel {channel}: {data}")

                    if channel == REDIS_STATE_RESULT_CHANNEL:
                        # Store raw message in the database
                        self.store_state_result_sync(data)
                        # Trigger notification with raw message
                        self.trigger_notification_sync(data)

                    # Forward the message to the WebSocket group
                    async_to_sync(channel_layer.group_send)(
                        "llm_output",
                        {
                            "type": "send_message",
                            "message": json.dumps({
                                "channel": channel,
                                "message": data
                            })
                        }
                    )

        except KeyboardInterrupt:
            logger.info("Redis listener stopped")
        except Exception as e:
            logger.error(f"Unexpected error in Redis listener: {str(e)}", exc_info=True)
        finally:
            pubsub.unsubscribe()
            redis_client.close()
            logger.info("Redis connection closed")

    def run_scheduled_alerts_processor(self, redis_client):
        try:
            process_scheduled_alerts_sync(redis_client)
        except Exception as e:
            logger.error(f"Error in scheduled alerts processor: {str(e)}", exc_info=True)

    def store_state_result_sync(self, raw_message):
        try:
            conn = psycopg2.connect(
                host=settings.DATABASES['default']['HOST'],
                database=settings.DATABASES['default']['NAME'],
                user=settings.DATABASES['default']['USER'],
                password=settings.DATABASES['default']['PASSWORD'],
                port=settings.DATABASES['default']['PORT'],
            )
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO state_result (raw_message, timestamp)
                    VALUES (%s, %s)
                """, (raw_message, timezone.now()))
            conn.commit()
            logger.info(f"Stored raw message in database")
        except Exception as e:
            logger.error(f"Error storing raw message in database: {str(e)}")
        finally:
            if conn:
                conn.close()

    def trigger_notification_sync(self, raw_message):
        try:
            # Create a mock request object
            request = HttpRequest()
            request.META['SERVER_NAME'] = 'example.com'  # Use a default domain or get it from settings
            request.META['SERVER_PORT'] = '8000'  # Adjust if your port is different

            # Import here to avoid circular import
            from monitor.notifications import notify

            # Call the notify function with raw message
            notify(request, raw_message)
            logger.info(f"Triggered notification with raw message")
        except Exception as e:
            logger.error(f"Error triggering notification: {str(e)}")