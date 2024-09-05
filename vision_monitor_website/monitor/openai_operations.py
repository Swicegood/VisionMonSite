import logging
import os
import json
import asyncio
import aiocron
from django.utils import timezone
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from openai import AsyncOpenAI
import threading

from .db_operations import fetch_daily_descriptions

SMTP_SERVER = os.getenv('SMTP_SERVER', '192.168.0.71')
SMTP_PORT = int(os.getenv('SMTP_PORT', 25))
SMTP_FROM = os.getenv('SMTP_FROM',"jguru108@gmail.com")
SMTP_TO = os.getenv('SMTP_TO', "jguru108@gmail.com")
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = SMTP_FROM
    msg['To'] = SMTP_TO
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.send_message(msg)
        logger.info(f"Email sent successfully to {SMTP_TO}")
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")

async def generate_daily_summary():
    try:
        # Fetch all descriptions from the last 24 hours
        daily_descriptions = await fetch_daily_descriptions()
        
        if not daily_descriptions:
            logger.warning("No descriptions found for the last 24 hours.")
            return
        
        # Prepare the prompt for OpenAI
        prompt = f"""Create a concise summary of the day's activities at the temple based on the following camera descriptions. 
        Focus on key events of people, unusual occurrences, and overall patterns of human activity.
        You will have to weed through much irrelavant descriptive text about the spaces and objects in the temple to find the human activities. 
        Organize the summary by different areas of the temple if possible.

        Camera Descriptions:
        {json.dumps(daily_descriptions, indent=2)}

        Please provide a summary in about 300-500 words."""

        # Call OpenAI API
        response = await client.chat.completions.create(
            model="gpt-4o-2024-05-13",
            messages=[
                {"role": "system", "content": "You are an AI assistant tasked with summarizing daily activities at a temple."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=700
        )

        summary = response.choices[0].message.content.strip()

        # Send email
        subject = f"Temple Activity Summary for {timezone.now().strftime('%Y-%m-%d')}"
        send_email(subject, summary)

    except Exception as e:
        logger.error(f"Error generating or sending daily summary: {str(e)}")

async def start_scheduled_tasks():
    # Schedule the daily summary task
    cron = aiocron.crontab('0 20,0 * * *', func=generate_daily_summary)
    
    while True:
        await asyncio.sleep(3600)  # Sleep for an hour

def run_scheduler_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(start_scheduled_tasks())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()

# This function should be called when your application starts
def run_scheduler():
    scheduler_thread = threading.Thread(target=run_scheduler_in_thread)
    scheduler_thread.start()
    return scheduler_thread