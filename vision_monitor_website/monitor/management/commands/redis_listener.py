import asyncio
import json
import logging
from django.core.management.base import BaseCommand
from channels.layers import get_channel_layer
import redis
import os
from django.conf import settings
from asgiref.sync import sync_to_async
import psycopg2
from django.utils import timezone
from django.urls import reverse
from django.http import HttpRequest
from monitor.notifications import process_scheduled_alerts

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
        
        asyncio.run(self.run_listener_and_processor())

    async def run_listener_and_processor(self):
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        channel_layer = get_channel_layer()

        # Create tasks for both Redis listening and processing scheduled alerts
        listener_task = asyncio.create_task(self.listen_to_redis(redis_client, channel_layer))
        alerts_task = asyncio.create_task(process_scheduled_alerts(redis_client))

        # Wait for both tasks to complete (which they never should)
        await asyncio.gather(listener_task, alerts_task)

    async def listen_to_redis(self, redis_client, channel_layer):
        pubsub = redis_client.pubsub()
        pubsub.subscribe(REDIS_MESSAGE_CHANNEL, REDIS_STATE_RESULT_CHANNEL)

        logger.info(f"Subscribed to Redis channels: {REDIS_MESSAGE_CHANNEL}, {REDIS_STATE_RESULT_CHANNEL}")

        try:
            while True:
                try:
                    message = await sync_to_async(pubsub.get_message)(ignore_subscribe_messages=True, timeout=1.0)
                    if message:
                        channel = message['channel'].decode('utf-8')
                        data = message['data'].decode('utf-8')
                        logger.info(f"Received message from Redis channel {channel}: {data}")

                        if channel == REDIS_STATE_RESULT_CHANNEL:
                            # Store raw message in the database
                            await self.store_state_result(data)
                            # Trigger notification with raw message
                            await self.trigger_notification(data)

                        # Forward the message to the WebSocket group
                        await channel_layer.group_send(
                            "llm_output",
                            {
                                "type": "send_message",
                                "message": json.dumps({
                                    "channel": channel,
                                    "message": data
                                })
                            }
                        )
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                
                await asyncio.sleep(0.1)  # Small delay to prevent CPU overuse

        except asyncio.CancelledError:
            logger.info("Redis listener cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in Redis listener: {str(e)}")
        finally:
            pubsub.unsubscribe()
            redis_client.close()
            logger.info("Redis connection closed")

    @sync_to_async
    def store_state_result(self, raw_message):
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

    @sync_to_async
    def trigger_notification(self, raw_message):
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