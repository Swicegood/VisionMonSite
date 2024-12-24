import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

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
        message_type = text_data_json.get('type', 'default')
        message = text_data_json.get('message', '')
        
        logger.debug(f"Received message of type '{message_type}' from WebSocket: {message}")
        
        # Broadcast message to all connected clients
        await self.channel_layer.group_send(
            "llm_output",
            {
                "type": "send_message",
                "message_type": message_type,
                "message": message
            }
        )

    async def send_message(self, event):
        message_type = event.get('message_type', 'default')
        message = event['message']

        # Structure the outgoing message
        outgoing_message = {
            'type': message_type,
            'message': message
        }

        await self.send(text_data=json.dumps(outgoing_message))
        logger.debug(f"Sent message of type '{message_type}' to WebSocket: {message}")