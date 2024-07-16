import discord
from discord import Webhook
import aiohttp
import logging
import requests
from requests.exceptions import RequestException

url = 'https://discord.com/api/webhooks/828356057680183377/VJLxRe7a0zzCmy6Q7LNVEy2qMD99yJLRARJ7RkYys5UQcY0yaO3HJFXbeM0Pox0FPMiA'

logger = logging.getLogger(__name__)

async def send_discord_async(file, message, ttime):
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(url, session=session)
        e = discord.Embed(description=ttime)
        
        if file:
            with open(file, "rb") as f:
                my_file = discord.File(f)
            await webhook.send(message, username='Radha-Golokananda', file=my_file, embed=e)
        elif message:
            await webhook.send(message, username='Radha-Golokananda', embed=e)
        else:
            return False

def send_discord_sync(file, message, ttime):
    data = {
        "content": message,
        "username": "Radha-Golokananda",
        "embeds": [{"description": ttime}]  # This is already correct, but let's keep it for clarity
    }
    
    files = None
    if file:
        try:
            files = {"file": open(file, "rb")}
        except IOError as e:
            logger.error(f"Failed to open image file: {str(e)}")
            return False

    try:
        response = requests.post(url, json=data, files=files)
        logger.info(f"Discord API response status code: {response.status_code}")
        logger.info(f"Discord API response content: {response.text}")
        
        if response.status_code != 204:
            logger.error(f"Discord API returned non-204 status code: {response.status_code}")
            logger.error(f"Response content: {response.text}")
        
        return response.status_code == 204
    except RequestException as e:
        logger.error(f"Request to Discord API failed: {str(e)}")
        return False
    finally:
        if files:
            files["file"].close()

def send_discord(file, message, ttime):
    try:
        return send_discord_sync(file, message, ttime)
    except Exception as e:
        logger.exception("Unexpected error in send_discord")
        return False

# Example usage:
# send_discord("path/to/file.jpg", "Test message", "2023-05-20 10:00:00")