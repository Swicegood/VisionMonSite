# monitor/scheduled_tasks.py
import asyncio
import json
import base64
from datetime import datetime, time, timedelta
from django.utils import timezone
from .db_operations import get_latest_frame
from .redis_operations import connect_redis
from .config import ALERT_QUEUE
import pytz
import logging
from django.db import connection
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

def convert_to_utc(t, tz_name='America/New_York'):
    """Convert a time to UTC."""
    local_tz = pytz.timezone(tz_name)
    today = datetime.now(local_tz).date()
    local_dt = local_tz.localize(datetime.combine(today, t))
    return local_dt.astimezone(pytz.UTC).time()

# Helper function to check if current time is within a specified range
def is_time_in_range(start, end, current):
    if start <= end:
        return start <= current <= end
    else:  # Crosses midnight
        return start <= current or current <= end

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
            ("11:52", "12:00", range(7)),
            ("15:45", "15:55", range(0, 6)),
            ("18:40", "18:45", range(0, 6))
        ],
        "g8rHNVCflWO1ptKN": [
            ("03:33", "04:00", range(7)),
            ("10:30", "11:10", range(0, 6)),
            ("15:30", "15:45", range(7)),
            ("18:15", "18:25", range(7))
        ]
    }

    current_time_utc = timezone.now()
    current_time_only_utc = current_time_utc.time()
    current_day_utc = current_time_utc.weekday()

    logger.info(f"Starting no-show checks at UTC: {current_time_utc}")

    for camera_id, time_periods in no_show_checks.items():
        logger.info(f"Checking camera {camera_id}")
        for start_time_str, end_time_str, days in time_periods:
            start_time_local = datetime.strptime(start_time_str, "%H:%M").time()
            end_time_local = datetime.strptime(end_time_str, "%H:%M").time()
            
            # Convert local times to UTC
            start_time_utc = convert_to_utc(start_time_local)
            end_time_utc = convert_to_utc(end_time_local)

            if is_time_in_range(start_time_utc, end_time_utc, current_time_only_utc) and current_day_utc in days:
                logger.info(f"Time period match for camera {camera_id}: {start_time_str}-{end_time_str} local ({start_time_utc}-{end_time_utc} UTC). Current UTC time: {current_time_only_utc}")
                # Rest of your check logic here
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
                            'check_time': f"{start_time_str}-{end_time_str} local",
                            'message': f"No person detected for camera {camera_id} between {start_time_str}-{end_time_str} local time",
                            'frame': frame_base64
                        }
                        redis_client.rpush(ALERT_QUEUE, json.dumps(alert_data))
                        logger.info(f"No-show alert created for camera {camera_id}")
                    else:
                        logger.warning(f"Failed to get latest frame for camera {camera_id}")
                else:
                    logger.info(f"Webhook hit found for camera {camera_id}, no alert needed")
            else:
                logger.info(f"No time period match for camera {camera_id}: {start_time_str}-{end_time_str} local ({start_time_utc}-{end_time_utc} UTC). Current UTC time: {current_time_only_utc}")

    redis_client.close()
    logger.info("Completed no-show checks")

async def run_no_show_checks():
    while True:
        try:
            check_no_shows()
        except Exception as e:
            logger.error(f"Error in no-show checks: {str(e)}")
        await asyncio.sleep(180)  # Check every 3 minutes

def cleanup_old_entries():
    logger.info('Starting cleanup operation...')
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    logger.info(f'Will delete entries older than: {thirty_days_ago}')
    
    try:
        with connection.cursor() as cursor:
            logger.info('Executing deletion query...')
            cursor.execute("""
                WITH old_metadata AS (
                    SELECT id, data_id 
                    FROM visionmon_metadata 
                    WHERE timestamp < %s
                ),
                deleted_metadata AS (
                    DELETE FROM visionmon_metadata
                    WHERE id IN (SELECT id FROM old_metadata)
                    RETURNING id
                ),
                deleted_binary_data AS (
                    DELETE FROM visionmon_binary_data
                    WHERE id IN (SELECT data_id FROM old_metadata)
                    RETURNING id
                ),
                old_state_results AS (
                    SELECT id
                    FROM state_result 
                    WHERE timestamp < %s
                ),
                deleted_state_results AS (
                    DELETE FROM state_result
                    WHERE id IN (SELECT id FROM old_state_results)
                    RETURNING id
                )
                SELECT 
                    (SELECT COUNT(*) FROM deleted_metadata) +
                    (SELECT COUNT(*) FROM deleted_binary_data) +
                    (SELECT COUNT(*) FROM deleted_state_results) as total_deleted;
            """, [thirty_days_ago, thirty_days_ago])
            
            deleted_count = cursor.fetchone()[0]
            logger.info(f'Successfully deleted {deleted_count} entries')

    except Exception as e:
        logger.error(f'Error during cleanup: {str(e)}')
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT pid, state, query_start, query
                    FROM pg_stat_activity
                    WHERE state != 'idle';
                """)
                active_queries = cursor.fetchall()
                logger.info('Active database queries:')
                for query in active_queries:
                    logger.info(f'    PID: {query[0]}, State: {query[1]}, Started: {query[2]}')
                    logger.info(f'    Query: {query[3]}')
        except Exception as db_error:
            logger.error(f"Failed to fetch active queries: {db_error}")
        raise

    logger.info('Cleanup operation completed')

async def run_cleanup_old_entries():
    while True:
        try:
            # Wrap the synchronous cleanup_old_entries in sync_to_async
            await sync_to_async(cleanup_old_entries)()
        except Exception as e:
            logger.error(f"Error in cleanup old entries: {str(e)}")
        await asyncio.sleep(86400)  # Run once a day