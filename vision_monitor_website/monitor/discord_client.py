import requests
import logging

logger = logging.getLogger(__name__)

url = 'https://discord.com/api/webhooks/828356057680183377/VJLxRe7a0zzCmy6Q7LNVEy2qMD99yJLRARJ7RkYys5UQcY0yaO3HJFXbeM0Pox0FPMiA'

def send_discord_sync(image_paths, message, ttime):
    embeds = [{"description": ttime}]
    
    files = []
    for i, (path, camera_name) in enumerate(image_paths):
        files.append(("file" + str(i), (f"{camera_name}.jpg", open(path, "rb"), "image/jpeg")))
        embeds.append({
            "title": camera_name,
            "image": {"url": f"attachment://{camera_name}.jpg"}
        })

    data = {
        "content": message,
        "username": "Radha-Golokananda",
        "embeds": embeds
    }

    try:
        response = requests.post(url, json=data, files=files)
        logger.info(f"Discord API response status code: {response.status_code}")
        logger.info(f"Discord API response content: {response.text}")
        
        if response.status_code != 204:
            logger.error(f"Discord API returned non-204 status code: {response.status_code}")
            logger.error(f"Response content: {response.text}")
        
        return response.status_code == 204
    except requests.RequestException as e:
        logger.error(f"Request to Discord API failed: {str(e)}")
        return False
    finally:
        for _, file in files:
            file[1].close()

def send_discord(image_paths, message, ttime):
    try:
        return send_discord_sync(image_paths, message, ttime)
    except Exception as e:
        logger.exception("Unexpected error in send_discord")
        return False