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
from functools import wraps
import aiohttp

from .db_operations import fetch_daily_descriptions

SMTP_SERVER = os.getenv('SMTP_SERVER', '192.168.0.71')
SMTP_PORT = int(os.getenv('SMTP_PORT', 25))
SMTP_FROM = os.getenv('SMTP_FROM',"jguru108@gmail.com")
SMTP_TO = os.getenv('SMTP_TO', "jguru108@gmail.com")
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
DEBUG = os.getenv('DEBUG', False)

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

def async_retry(max_retries=3, base_delay=1, max_delay=60):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return await asyncio.wait_for(func(*args, **kwargs), timeout=60)  # Increased timeout to 60 seconds
                except asyncio.TimeoutError:
                    logger.warning(f"Function {func.__name__} timed out. Retrying...")
                except Exception as e:
                    logger.error(f"Error in {func.__name__}: {str(e)}")
                
                retries += 1
                if retries < max_retries:
                    delay = min(base_delay * (2 ** (retries - 1)), max_delay)
                    logger.info(f"Retrying {func.__name__} in {delay} seconds...")
                    await asyncio.sleep(delay)
            
            logger.error(f"Max retries reached for {func.__name__}")
            raise Exception(f"Max retries reached for {func.__name__}")
        return wrapper
    return decorator


@async_retry(max_retries=3, base_delay=1, max_delay=60)
async def call_openai_api(prompt):
    logger.debug("Calling OpenAI API")
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",  # Changed to a definitely available model
            messages=[
                {"role": "system", "content": "You are an AI assistant tasked with summarizing daily activities at a temple."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=700
        )
        logger.debug("OpenAI API call successful")
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI API call failed: {str(e)}")
        raise

@async_retry(max_retries=3, base_delay=1, max_delay=60)
async def send_email(subject, body):
    # Implement your email sending logic here
    # This is a placeholder
    logger.info(f"Sending email: {subject}")
    logger.debug(f"Email body: {body}")

@async_retry(max_retries=3, base_delay=2, max_delay=120)
async def generate_daily_summary():
    try:
        logger.debug("Starting daily summary generation")
        daily_descriptions = await fetch_daily_descriptions()
        
        if not daily_descriptions:
            logger.warning("No descriptions found for the last 24 hours.")
            return
        
        prompt = f"""Create a concise summary of the day's activities at the temple based on the following camera descriptions. 
        Focus on key events of people, unusual occurrences, and overall patterns of human activity.
        You will have to weed through much irrelavant descriptive text about the spaces and objects in the temple to find the human activities. 
        Organize the summary by different areas of the temple if possible. 
        Camera Descriptions:
        {json.dumps(daily_descriptions, indent=2)}
        Please provide a summary in about 300-500 words."""
        
        summary = await call_openai_api(prompt)
        
        subject = f"Temple Activity Summary for {timezone.now().strftime('%Y-%m-%d')}"
        await send_email(subject, summary)
        
        logger.info("Daily summary generated and sent successfully.")
    except Exception as e:
        logger.error(f"Error generating or sending daily summary: {str(e)}")
        raise

async def test_openai_connection():
    logger.debug("Testing OpenAI connection")
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": "Hello, how are you?"}]
            }
        ) as response:
            if response.status == 200:
                logger.info("OpenAI connection test successful")
                return await response.json()
            else:
                logger.error(f"OpenAI connection test failed: {response.status}")
                return await response.text()
            
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
    if DEBUG:
        try:
            # First, test the OpenAI connection
            test_result = asyncio.run(test_openai_connection())
            logger.debug(f"OpenAI test result: {test_result}")

            # If the test is successful, proceed with generating the daily summary
            if isinstance(test_result, dict) and 'choices' in test_result:
                asyncio.run(generate_daily_summary())
            else:
                logger.error("OpenAI connection test failed, not proceeding with summary generation")
        except Exception as e:
            logger.error(f"Failed to generate daily summary: {str(e)}")
    scheduler_thread = threading.Thread(target=run_scheduler_in_thread)
    scheduler_thread.start()
    return scheduler_thread

if __name__ == '__main__':
    generate_daily_summary