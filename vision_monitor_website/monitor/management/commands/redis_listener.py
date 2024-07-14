import asyncio
import json
import logging
from django.core.management.base import BaseCommand
from channels.layers import get_channel_layer
import redis
import os
from django.conf import settings
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv('REDIS_HOST', '192.168.0.71')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_MESSAGE_CHANNEL = 'llm_messages'
REDIS_STATE_CHANNEL = 'state_processing'
REDIS_STATE_RESULT_CHANNEL = 'state_result'

class Command(BaseCommand):
    help = 'Runs a Redis listener'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as a daemon process',
        )

    def handle(self, *args, **options):
        if options['daemon']:
            self.stdout.write('Starting Redis listener in daemon mode...')
            # Implement daemon logic here if needed
        else:
            self.stdout.write('Starting Redis listener...')
        
        asyncio.run(self.listen_to_redis())

    async def listen_to_redis(self):
        redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        pubsub = redis_client.pubsub()
        pubsub.subscribe(REDIS_MESSAGE_CHANNEL, REDIS_STATE_RESULT_CHANNEL)
        channel_layer = get_channel_layer()

        logger.info(f"Subscribed to Redis channels: {REDIS_MESSAGE_CHANNEL}, {REDIS_STATE_RESULT_CHANNEL}")

        try:
            while True:
                try:
                    message = await sync_to_async(pubsub.get_message)(ignore_subscribe_messages=True, timeout=1.0)
                    if message:
                        channel = message['channel'].decode('utf-8')
                        data = message['data'].decode('utf-8')
                        logger.info(f"Received message from Redis channel {channel}: {data}")

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