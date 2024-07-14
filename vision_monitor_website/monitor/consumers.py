import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import aioredis
import os

# Configure logging
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
        asyncio.create_task(self.listen_for_redis_messages())
        logger.info("WebSocket connection established and Redis listener started")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("llm_output", self.channel_name)
        self.redis.close()
        await self.redis.wait_closed()
        logger.info(f"WebSocket disconnected with code {close_code}")

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
        await self.redis.rpush(REDIS_STATE_CHANNEL, "process")
        logger.info("Requested state processing via Redis")

    async def listen_for_redis_messages(self):
        logger.info(f"Starting to listen for Redis messages on channels: {REDIS_MESSAGE_CHANNEL}, {REDIS_STATE_RESULT_CHANNEL}")
        channel = await self.redis.subscribe(REDIS_MESSAGE_CHANNEL, REDIS_STATE_RESULT_CHANNEL)
        try:
            while await channel[0].wait_message():
                msg = await channel[0].get(encoding='utf-8')
                if msg:
                    logger.debug(f"Received message from Redis: {msg}")
                    if REDIS_STATE_RESULT_CHANNEL in channel[0].name.decode():
                        logger.info(f"Received state result: {msg}")
                    await self.send(text_data=msg)
                    logger.debug(f"Sent Redis message to WebSocket: {msg}")
        except Exception as e:
            logger.error(f"Error listening for Redis messages: {str(e)}")
        finally:
            await self.redis.unsubscribe(REDIS_MESSAGE_CHANNEL, REDIS_STATE_RESULT_CHANNEL)
            logger.info("Unsubscribed from Redis channels")