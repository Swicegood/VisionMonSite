import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from openai import OpenAI
import os
from datetime import datetime, timedelta
from django.db import connection
from django.conf import settings

client = OpenAI(base_url=os.getenv('OPENAI_BASE_URL', 'http://192.168.0.199:1337/v1'), api_key=os.getenv('OPENAI_API_KEY', 'lm-studio'))

TOTAL_CAMERAS = 16

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
        
        parts = message.split(' ', 3)
        if len(parts) == 4:
            camera_name, camera_index, timestamp, description = parts
            self.camera_descriptions[camera_name] = description

            if len(self.camera_descriptions) == TOTAL_CAMERAS:
                facility_state = await self.process_facility_state()
                camera_states = await self.process_camera_states()
                await self.channel_layer.group_send(
                    "llm_output",
                    {
                        "type": "send_states",
                        "facility_state": facility_state,
                        "camera_states": camera_states
                    }
                )
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

    @sync_to_async
    def process_camera_states(self):
        camera_states = {}
        one_hour_ago = datetime.now() - timedelta(hours=1)

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT camera_id, GROUP_CONCAT(llm_description SEPARATOR ' ') as aggregate_description
                FROM frame_analysis
                WHERE timestamp > %s
                GROUP BY camera_id
            """, [one_hour_ago])
            results = cursor.fetchall()

        for camera_id, aggregate_description in results:
            prompt = f"""Please read the following aggregate description of a camera's view over the last hour and decide the state of this part of the facility. Output one or more of the following: "busy", "off-hours", "festival happening", "night-time", "quiet" or "meal time". Please output only those words and give your justification for choosing each.

Aggregate Description: {aggregate_description}"""

            try:
                response = client.chat.completions.create(
                    model="not used",
                    messages=[
                        {"role": "system", "content": "You are an AI tasked with determining the state of a specific area in a facility based on aggregated security camera descriptions."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200
                )
                camera_states[camera_id] = response.choices[0].message.content
            except Exception as e:
                camera_states[camera_id] = f"Error processing camera state: {str(e)}"
        
        return camera_states

    async def send_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))

    async def send_states(self, event):
        facility_state = event['facility_state']
        camera_states = event['camera_states']
        await self.send(text_data=json.dumps({
            'facility_state': facility_state,
            'camera_states': camera_states
        }))