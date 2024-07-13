import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
import os
import aioredis
from django.conf import settings

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', '192.168.0.71')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_STATE_CHANNEL = 'state_processing'
REDIS_STATE_RESULT_CHANNEL = 'state_result'

class LLMOutputConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("llm_output", self.channel_name)
        await self.accept()
        self.redis = await aioredis.create_redis_pool(f'redis://{REDIS_HOST}:{REDIS_PORT}')
        asyncio.create_task(self.listen_for_state_results())

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("llm_output", self.channel_name)
        self.redis.close()
        await self.redis.wait_closed()

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

    async def listen_for_state_results(self):
        channel = self.redis.pubsub()
        await channel.subscribe(REDIS_STATE_RESULT_CHANNEL)
        try:
            async for message in channel.listen():
                if message['type'] == 'message':
                    state_data = json.loads(message['data'])
                    await self.send(text_data=json.dumps(state_data))
        except Exception as e:
            print(f"Error listening for state results: {str(e)}")
        finally:
            await channel.unsubscribe(REDIS_STATE_RESULT_CHANNEL)

    async def send_states(self, event):
        facility_state = event['facility_state']
        camera_states = event['camera_states']
        await self.send(text_data=json.dumps({
            'facility_state': facility_state,
            'camera_states': camera_states
        }))