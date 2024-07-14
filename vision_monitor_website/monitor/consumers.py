import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import aioredis
import os

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv('REDIS_HOST', '192.168.0.71')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_MESSAGE_CHANNEL = 'llm_messages'
REDIS_STATE_CHANNEL = 'state_processing'
REDIS_STATE_RESULT_CHANNEL = 'state_result'

class LLMOutputConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("llm_output", self.channel_name)
        await self.accept()
        self.redis = await aioredis.create_redis_pool(f'redis://{REDIS_HOST}:{REDIS_PORT}')
        logger.debug(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        self.redis_listener = asyncio.create_task(self.listen_for_redis_messages())
        logger.info("WebSocket connection established and Redis listener started")

    async def disconnect(self, close_code):
        logger.info(f"Disconnecting WebSocket with code {close_code}")
        await self.channel_layer.group_discard("llm_output", self.channel_name)
        
        if hasattr(self, 'redis_listener'):
            self.redis_listener.cancel()
        
        if hasattr(self, 'redis'):
            self.redis.close()
            await self.redis.wait_closed()
        
        logger.info("WebSocket disconnected and cleanup completed")

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        logger.debug(f"Received message from WebSocket: {message}")
        
        await self.channel_layer.group_send(
            "llm_output",
            {
                "type": "send_message",
                "message": message
            }
        )
        logger.debug(f"Sent message to channel layer group: {message}")

    async def send_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))
        logger.debug(f"Sent message to WebSocket: {message}")

    async def request_state_processing(self):
        try:
            await self.redis.rpush(REDIS_STATE_CHANNEL, "process")
            logger.info("Requested state processing via Redis")
        except Exception as e:
            logger.error(f"Error requesting state processing: {str(e)}")

    async def check_redis_connection(self):
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False

    async def listen_for_redis_messages(self):
        logger.info(f"Starting to listen for Redis messages on channels: {REDIS_MESSAGE_CHANNEL}, {REDIS_STATE_RESULT_CHANNEL}")
        try:
            channels = await self.redis.subscribe(REDIS_MESSAGE_CHANNEL, REDIS_STATE_RESULT_CHANNEL)
            logger.info(f"Subscribed to Redis channels: {[ch.name.decode() for ch in channels]}")
            
            while True:
                try:
                    # Check if Redis connection is still alive
                    if not await self.check_redis_connection():
                        logger.warning("Redis connection lost. Attempting to reconnect...")
                        self.redis = await aioredis.create_redis_pool(f'redis://{REDIS_HOST}:{REDIS_PORT}')
                        channels = await self.redis.subscribe(REDIS_MESSAGE_CHANNEL, REDIS_STATE_RESULT_CHANNEL)
                        logger.info("Reconnected to Redis and resubscribed to channels")

                    # Wait for message with a timeout
                    message = await asyncio.wait_for(channels[0].get(), timeout=5.0)
                    if message:
                        msg = message.decode('utf-8')
                        logger.debug(f"Received message from Redis: {msg}")
                        channel_name = channels[0].name.decode()
                        if channel_name == REDIS_STATE_RESULT_CHANNEL:
                            logger.info(f"Received state result: {msg}")
                        await self.send(text_data=msg)
                        logger.debug(f"Sent Redis message to WebSocket: {msg}")
                except asyncio.TimeoutError:
                    logger.debug("No message received in the last 5 seconds")
                except Exception as e:
                    logger.warning(f"Error receiving message from Redis: {str(e)}")
                    await asyncio.sleep(1)  # Wait before trying again

        except asyncio.CancelledError:
            logger.info("Redis listener task cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in Redis listener: {str(e)}")
        finally:
            try:
                await self.redis.unsubscribe(REDIS_MESSAGE_CHANNEL, REDIS_STATE_RESULT_CHANNEL)
                logger.info("Unsubscribed from Redis channels")
            except Exception as e:
                logger.error(f"Error unsubscribing from Redis channels: {str(e)}")

    @sync_to_async
    def debug_redis_pubsub(self):
        try:
            result = self.redis.pubsub_channels()
            logger.debug(f"Active Redis PubSub channels: {result}")
            return result
        except Exception as e:
            logger.error(f"Error checking Redis PubSub channels: {str(e)}")
            return None