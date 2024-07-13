import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from openai import OpenAI
import os

client = OpenAI(base_url=os.getenv('OPENAI_BASE_URL', 'http://192.168.0.199:1337/v1'), api_key=os.getenv('OPENAI_API_KEY', 'lm-studio'))

TOTAL_CAMERAS = 16  # Update this to match the total number of cameras

class LLMOutputConsumer(AsyncWebsocketConsumer):
    camera_descriptions = {}
    
    async def connect(self):
        await self.channel_layer.group_add("llm_output", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("llm_output", self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        
        # Parse the message to extract camera info and description
        parts = message.split(' ', 3)
        if len(parts) == 4:
            camera_name, camera_index, timestamp, description = parts
            self.camera_descriptions[camera_name] = description

            # Check if we have descriptions for all cameras
            if len(self.camera_descriptions) == TOTAL_CAMERAS:
                facility_state = await self.process_facility_state()
                await self.channel_layer.group_send(
                    "llm_output",
                    {
                        "type": "send_facility_state",
                        "state": facility_state
                    }
                )
                # Clear the descriptions for the next round
                self.camera_descriptions.clear()
        
        await self.channel_layer.group_send(
            "llm_output",
            {
                "type": "send_message",
                "message": message
            }
        )

    @sync_to_async
    def process_facility_state(self):
        all_descriptions = " ".join(self.camera_descriptions.values())
        prompt = f"""Please read all the following descriptions of different parts of a facility and decide the state of the facility. Output one or more of the following: "busy", "off-hours", "festival happening", "night-time", "quiet" or "meal time". Please output only those words and give your justification for choosing each.

Descriptions: {all_descriptions}"""

        try:
            response = client.chat.completions.create(
                model="not used",
                messages=[
                    {"role": "system", "content": "You are an AI tasked with determining the overall state of a facility based on security camera descriptions."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error processing facility state: {str(e)}"

    async def send_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))

    async def send_facility_state(self, event):
        state = event['state']
        await self.send(text_data=json.dumps({
            'facility_state': state
        }))