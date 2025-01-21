import requests
import logging
import json
from requests.exceptions import RequestException
from .config import DISCORD_WEBHOOK_URL
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MiB in bytes

def send_discord_message(image_paths, message, ttime, title):
    files = []
    attachments = []
    total_size = 0

    for i, (path, camera_name) in enumerate(image_paths):
        with open(path, "rb") as img_file:
            file_content = img_file.read()
            file_size = len(file_content)
            
            if total_size + file_size > MAX_FILE_SIZE:
                logger.warning(f"Skipping file {camera_name} as it would exceed the 25 MiB limit")
                continue
            
            total_size += file_size
            files.append(("files[" + str(i) + "]", (camera_name + ".jpg", file_content, "image/jpeg")))
            attachments.append({
                "id": i,
                "description": f"Image from {camera_name}",
                "filename": camera_name + ".jpg"
            })

    embeds = [{
        "title": "Security Alert",
        "description": ttime,
        "fields": [{"name": "Message", "value": message}]
    }]

    for i, (_, camera_name) in enumerate(image_paths[:len(files)]):
        embeds.append({
            "title": camera_name,
            "image": {"url": f"attachment://{camera_name}.jpg"}
        })

    payload = {
        "username": title,
        "embeds": embeds,
        "attachments": attachments
    }

    data = {
        "payload_json": json.dumps(payload)
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, data=data, files=files)
        response.raise_for_status()
        
        logger.info(f"Discord API response status code: {response.status_code}")
        logger.debug(f"Discord API response content: {response.text}")
        
        return True
    except RequestException as e:
        logger.error(f"Request to Discord API failed: {str(e)}")
        if hasattr(e.response, 'text'):
            logger.error(f"Response content: {e.response.text}")
        return False

def send_discord(image_paths, message, ttime, title):
    try:
        return send_discord_message(image_paths, message, ttime, title)
    except Exception as e:
        logger.exception("Unexpected error in send_discord")
        return False