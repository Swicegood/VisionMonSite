import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LLMOutputConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("llm_output", self.channel_name)
        await self.accept()
        logger.info("WebSocket connection established")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("llm_output", self.channel_name)
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

    async def send_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))
        logger.debug(f"Sent message to WebSocket: {message}")