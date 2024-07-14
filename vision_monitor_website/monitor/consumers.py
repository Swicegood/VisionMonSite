import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import redis
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
        self.redis_client = None
        self.redis_listener = None
        self.background_task = None
        await self.connect_redis()
        self.background_task = asyncio.create_task(self.background_processor())
        self.redis_listener = asyncio.create_task(self.listen_for_redis_messages())
        asyncio.create_task(self.check_task_status())
        logger.info("WebSocket connection established, background task and Redis listener started")

    async def disconnect(self, close_code):
        logger.info(f"Disconnecting WebSocket with code {close_code}")
        await self.channel_layer.group_discard("llm_output", self.channel_name)
        
        if self.redis_listener:
            self.redis_listener.cancel()
        
        if self.background_task:
            self.background_task.cancel()
        
        if self.redis_client:
            self.redis_client.close()
        
        logger.info("WebSocket disconnected and cleanup completed")

    async def connect_redis(self):
        while True:
            try:
                pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT)
                self.redis_client = redis.Redis(connection_pool=pool)
                logger.info("Connected to Redis")
                return
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {str(e)}")
                await asyncio.sleep(5)

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

    @sync_to_async
    def request_state_processing(self):
        try:
            self.redis_client.rpush(REDIS_STATE_CHANNEL, "process")
            logger.info("Requested state processing via Redis")
        except Exception as e:
            logger.error(f"Error requesting state processing: {str(e)}")

    async def listen_for_redis_messages(self):
        logger.info(f"Starting to listen for Redis messages on channels: {REDIS_MESSAGE_CHANNEL}, {REDIS_STATE_RESULT_CHANNEL}")
        try:
            pubsub = self.redis_client.pubsub()
            pubsub.subscribe(REDIS_MESSAGE_CHANNEL, REDIS_STATE_RESULT_CHANNEL)
            logger.info(f"Subscribed to Redis channels: {REDIS_MESSAGE_CHANNEL}, {REDIS_STATE_RESULT_CHANNEL}")
            
            while True:
                try:
                    message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message:
                        logger.info(f"Received message from Redis: {message}")
                        channel = message['channel'].decode('utf-8')
                        data = message['data'].decode('utf-8')
                        if channel == REDIS_STATE_RESULT_CHANNEL:
                            logger.info(f"Received state result: {data}")
                        await self.send(text_data=json.dumps({'channel': channel, 'message': data}))
                        logger.debug(f"Sent Redis message to WebSocket: {data}")
                    else:
                        logger.debug("No message received from Redis")
                except Exception as e:
                    logger.warning(f"Error receiving message from Redis: {str(e)}")
                    await asyncio.sleep(1)  # Wait before trying again

        except asyncio.CancelledError:
            logger.info("Redis listener task cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in Redis listener: {str(e)}")
        finally:
            try:
                pubsub.unsubscribe(REDIS_MESSAGE_CHANNEL, REDIS_STATE_RESULT_CHANNEL)
                logger.info("Unsubscribed from Redis channels")
            except Exception as e:
                logger.error(f"Error unsubscribing from Redis channels: {str(e)}")

    async def background_processor(self):
        logger.info("Background processor started")
        while True:
            try:
                if not self.redis_client:
                    logger.info("Redis client not found, connecting...")
                    await self.connect_redis()

                # Check for messages in Redis
                logger.debug("Checking for messages in Redis...")
                message = await sync_to_async(self.redis_client.lpop)(REDIS_MESSAGE_CHANNEL)
                if message:
                    logger.info(f"Message found in {REDIS_MESSAGE_CHANNEL}: {message}")
                    await self.process_message(message.decode('utf-8'))
                else:
                    logger.debug(f"No message found in {REDIS_MESSAGE_CHANNEL}")

                # Check if state processing is needed
                state_request = await sync_to_async(self.redis_client.lpop)(REDIS_STATE_CHANNEL)
                if state_request:
                    logger.info(f"State processing request found in {REDIS_STATE_CHANNEL}")
                    await self.request_state_processing()
                else:
                    logger.debug(f"No state processing request found in {REDIS_STATE_CHANNEL}")

                # Check active subscriptions
                channels = await sync_to_async(self.redis_client.pubsub_channels)()
                logger.debug(f"Active subscriptions: {channels}")

                # Short sleep to prevent CPU overuse
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in background processor: {str(e)}")
                await asyncio.sleep(5)

    async def process_message(self, message):
        try:
            # Process the message here
            logger.info(f"Processing message: {message}")
            # You can add your message processing logic here
            
            # Send the processed message to the WebSocket
            await self.send(text_data=json.dumps({
                'message': f"Processed: {message}"
            }))
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")

    async def check_task_status(self):
        while True:
            logger.info(f"Background task status: {'Running' if self.background_task and not self.background_task.done() else 'Not running'}")
            logger.info(f"Redis listener status: {'Running' if self.redis_listener and not self.redis_listener.done() else 'Not running'}")
            await asyncio.sleep(60)  # Check every minute

    @sync_to_async
    def debug_redis_pubsub(self):
        try:
            result = self.redis_client.pubsub_channels()
            logger.debug(f"Active Redis PubSub channels: {result}")
            return result
        except Exception as e:
            logger.error(f"Error checking Redis PubSub channels: {str(e)}")
            return None