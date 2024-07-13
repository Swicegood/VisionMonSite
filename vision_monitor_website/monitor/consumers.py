import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from redis.asyncio import Redis
import os

REDIS_HOST = os.getenv('REDIS_HOST', '192.168.0.71')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_MESSAGE_CHANNEL = 'llm_messages'
REDIS_STATE_CHANNEL = 'state_processing'
REDIS_STATE_RESULT_CHANNEL = 'state_result'

class LLMOutputConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("llm_output", self.channel_name)
        await self.accept()
        self.redis = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        asyncio.create_task(self.listen_for_redis_messages())

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("llm_output", self.channel_name)
        await self.redis.close()

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        
        await self.channel_layer.group_send(
            "llm_output",
            {
                "type": "send_message",
                "message": message
            }
        )

    async def send_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))

    async def request_state_processing(self):
        await self.redis.rpush(REDIS_STATE_CHANNEL, "process")

    async def listen_for_redis_messages(self):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(REDIS_MESSAGE_CHANNEL, REDIS_STATE_RESULT_CHANNEL)
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    await self.send(text_data=message['data'])
        except Exception as e:
            print(f"Error listening for Redis messages: {str(e)}")
        finally:
            await pubsub.unsubscribe(REDIS_MESSAGE_CHANNEL, REDIS_STATE_RESULT_CHANNEL)