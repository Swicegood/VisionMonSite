import threading
import json
import logging
import time
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
from monitor.notifications import process_scheduled_alerts_sync, notify

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv('REDIS_HOST', '192.168.0.71')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_MESSAGE_CHANNEL = 'llm_messages'
REDIS_STATE_CHANNEL = 'state_processing'
REDIS_STATE_RESULT_CHANNEL = 'state_result'
REDIS_RECONNECT_DELAY = 5  # seconds

class Command(BaseCommand):
    help = 'Runs a Redis listener and processes scheduled alerts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as a daemon process',
        )

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger(__name__)
        if options['daemon']:
            logger.info('Starting Redis listener and scheduled alerts processor in daemon mode...')
        else:
            logger.info('Starting Redis listener and scheduled alerts processor...')
        
        self.run_listener_and_processor()

    def run_listener_and_processor(self):
        channel_layer = get_channel_layer()

        listener_thread = threading.Thread(target=self.listen_to_redis_sync, args=(channel_layer,))
        listener_thread.start()

        alerts_thread = threading.Thread(target=self.run_scheduled_alerts_processor)
        alerts_thread.start()

        listener_thread.join()
        alerts_thread.join()

    def get_redis_connection(self):
        while True:
            try:
                redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
                redis_client.ping()  # Test the connection
                return redis_client
            except redis.ConnectionError:
                logger.error(f"Failed to connect to Redis. Retrying in {REDIS_RECONNECT_DELAY} seconds...")
                time.sleep(REDIS_RECONNECT_DELAY)

    def listen_to_redis_sync(self, channel_layer):
        while True:
            try:
                redis_client = self.get_redis_connection()
                pubsub = redis_client.pubsub()
                pubsub.subscribe(REDIS_MESSAGE_CHANNEL, REDIS_STATE_RESULT_CHANNEL)

                logger.info(f"Subscribed to Redis channels: {REDIS_MESSAGE_CHANNEL}, {REDIS_STATE_RESULT_CHANNEL}")

                for message in pubsub.listen():
                    logger.debug(f"Received from pubsub: {message}")
                    
                    if message['type'] == 'message':
                        channel = message['channel'].decode('utf-8')
                        data = message['data']
                        if isinstance(data, bytes):
                            data = data.decode('utf-8')
                        logger.info(f"Received message from Redis channel {channel}: {data}")

                        if channel == REDIS_STATE_RESULT_CHANNEL:
                            self.store_state_result_sync(data)
                            self.trigger_notification_sync(data)

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

            except redis.ConnectionError:
                logger.error("Lost connection to Redis. Attempting to reconnect...")
                time.sleep(REDIS_RECONNECT_DELAY)
            except Exception as e:
                logger.error(f"Unexpected error in Redis listener: {str(e)}", exc_info=True)
                time.sleep(REDIS_RECONNECT_DELAY)
            finally:
                try:
                    pubsub.unsubscribe()
                    redis_client.close()
                except:
                    pass
                logger.info("Redis connection closed")

    def run_scheduled_alerts_processor(self):
        while True:
            try:
                redis_client = self.get_redis_connection()
                process_scheduled_alerts_sync(redis_client)
            except Exception as e:
                logger.error(f"Error in scheduled alerts processor: {str(e)}", exc_info=True)
                time.sleep(REDIS_RECONNECT_DELAY)

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
            conn = psycopg2.connect(
                host=settings.DATABASES['default']['HOST'],
                database=settings.DATABASES['default']['NAME'],
                user=settings.DATABASES['default']['USER'],
                password=settings.DATABASES['default']['PASSWORD'],
                port=settings.DATABASES['default']['PORT'],
            )
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM state_result
                    WHERE timestamp >= %s
                """, (timezone.now() - timezone.timedelta(hours=1),))
                count = cursor.fetchone()[0]

            if count >= 15:
                request = HttpRequest()
                request.META['SERVER_NAME'] = 'example.com'
                request.META['SERVER_PORT'] = '8000'

                notify(request, raw_message)
                logger.info(f"Triggered notification with raw message")
            else:
                logger.info(f"Skipped notification. Only {count} state results in the last hour.")
        except Exception as e:
            logger.error(f"Error in trigger_notification_sync: {str(e)}")
        finally:
            if conn:
                conn.close()