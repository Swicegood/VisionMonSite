# monitor/scheduled_tasks.py
import asyncio
import json
import base64
from datetime import datetime, time
from django.utils import timezone
from .db_operations import get_latest_frame
from .redis_operations import connect_redis
from .config import ALERT_QUEUE
import logging

logger = logging.getLogger(__name__)

# Helper function to check if current time is within a specified range
def is_time_in_range(start, end, current):
    return start <= current <= end if start <= end else start <= current or current <= end

# Helper function to check if current day is in specified days
def is_day_match(current_day, days):
    return current_day in days

def check_no_shows():
    redis_client = connect_redis()
    
    # Define the time periods and cameras with cron-like notation
    # Format: "camera_id": [("start_time", "end_time", [days_of_week])]
    # Days of week: 0 = Monday, 1 = Tuesday, ..., 6 = Sunday
    no_show_checks = {
        "sHlS7ewuGDEd2ef4": [
            ("11:55", "12:00", range(7)),  # Every day
            ("15:45", "15:55", range(0, 6)),  # Monday to Saturday
            ("18:40", "18:45", range(0, 6)),  # Monday to Saturday
            ("15:02", "15:59", range(0, 6))   # Monday to Saturday
        ],
        "g8rHNVCflWO1ptKN": [
            ("03:30", "04:00", range(7)),  # Every day
            ("10:30", "11:10", range(7)),  # Every day
            ("16:30", "16:45", range(7)),  # Every day
            ("18:00", "18:25", range(7))   # Every day
        ]
    }

    current_time = timezone.now()
    current_time_only = current_time.time()
    current_day = current_time.weekday()

    logger.info(f"Starting no-show checks at {current_time}")

    for camera_id, time_periods in no_show_checks.items():
        logger.info(f"Checking camera {camera_id}")
        for start_time, end_time, days in time_periods:
            start = datetime.strptime(start_time, "%H:%M").time()
            end = datetime.strptime(end_time, "%H:%M").time()

            if is_time_in_range(start, end, current_time_only) and is_day_match(current_day, days):
                logger.info(f"Time period match for camera {camera_id}: {start_time}-{end_time}")
                # Check if we have a webhook hit in Redis
                last_hit = redis_client.get(f"webhook:{camera_id}")
                if not last_hit:
                    logger.info(f"No webhook hit found for camera {camera_id}")
                    # No webhook hit during this period, create an alert
                    frame = get_latest_frame(camera_id)
                    if frame:
                        frame_base64 = base64.b64encode(frame).decode('utf-8')
                        alert_data = {
                            'camera_id': camera_id,
                            'check_time': f"{start_time}-{end_time}",
                            'message': f"No person detected for camera {camera_id} between {start_time} and {end_time}",
                            'frame': frame_base64
                        }
                        redis_client.rpush(ALERT_QUEUE, json.dumps(alert_data))
                        logger.info(f"No-show alert created for camera {camera_id}")
                    else:
                        logger.warning(f"Failed to get latest frame for camera {camera_id}")
                else:
                    logger.info(f"Webhook hit found for camera {camera_id}, no alert needed")
            else:
                logger.info(f"No time period match for camera {camera_id}: {start_time}-{end_time}")

    redis_client.close()
    logger.info("Completed no-show checks")

async def run_no_show_checks():
    while True:
        try:
            check_no_shows()
        except Exception as e:
            logger.error(f"Error in no-show checks: {str(e)}")
        await asyncio.sleep(60)  # Check every minute