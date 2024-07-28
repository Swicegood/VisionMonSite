import logging
import tempfile
import os
import json
import base64
import time
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from .discord_client import send_discord
from .image_handling import get_latest_image
from .state_management import parse_facility_state, alert_manager
from .db_operations import fetch_latest_facility_state
from .config import camera_names

logger = logging.getLogger(__name__)

ALERT_QUEUE = 'alert_queue'

def notify(request, raw_message=None, specific_camera_id=None):
    if raw_message is None:
        raw_message = fetch_latest_facility_state()
        if raw_message is None:
            logger.error("Failed to fetch facility status")
            return
        raw_message = raw_message[0]
    
    facility_state, camera_states, alerts = parse_facility_state(raw_message)
    
    if specific_camera_id:
        alerts = [alert for alert in alerts if alert[0] == specific_camera_id]
    
    for camera_id, alert_type, state in alerts:
        if alert_type in ["ALERT", "RESOLVED", "FLAPPING_START", "FLAPPING_END"]:
            presented_state = state
            if alert_type == "RESOLVED":
                presented_state = ""
            message = f"Alert for camera {camera_id} {alert_type} - State: {state}"
            title = f"{camera_id} {alert_type} {presented_state}"
            image_paths = []
            

            try:
                latest_image = get_latest_image(request, camera_id.split(' ')[1])
                if isinstance(latest_image, HttpResponse) and latest_image.status_code == 200:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_image:
                        temp_image.write(latest_image.content)
                        image_paths.append((temp_image.name, camera_id))
                else:
                    logger.error(f"Failed to get image for camera {camera_id}")
            except Exception as e:
                logger.error(f"Error retrieving image for camera {camera_id}: {str(e)}")

            if image_paths:
                try:
                    success = send_discord(image_paths, message, str(timezone.localtime(timezone.now()).strftime("%Y-%m-%d %I:%M:%S %p")), title)
                    logger.info(f"send_discord called for camera {camera_id}. Result: {success}")
                except Exception as e:
                    logger.error(f"Error in send_discord for camera {camera_id}: {str(e)}")
                    success = False

                for path, _ in image_paths:
                    os.unlink(path)
                    logger.info(f"Temporary image file deleted: {path}")

                if success:
                    logger.info(f"Notification sent successfully for camera {camera_id}")
                else:
                    logger.error(f"Failed to send notification for camera {camera_id}")
            else:
                logger.warning(f"No valid image found for camera {camera_id}")
        else:
            logger.info(f"No notification required for camera {camera_id} ({alert_type})")
    
    if facility_state:
        if facility_state.lower() in ["bustling", "festival happening", "crowd gathering", "over capacity"]:      
            logger.info("Facility state is bustling")
            message = "Facility state is bustling"
            title = "ALERT Facility: {facility_state}"
            try:
                success = send_discord([], message, str(timezone.localtime(timezone.now()).strftime("%Y-%m-%d %I:%M:%S %p")), title)
                if success:
                    logger.info("Discord message sent for ALERT facility state")
                else:
                    logger.error("Failed to send Discord message for ALERT facility state")
            except Exception as e:
                logger.error(f"Error in send_discord for facility state: {str(e)}")    
        logger.info(f"Facility state: {facility_state}")
    else:
        logger.warning("No facility state available")
    
    if alerts:
        logger.info("Alerts processed successfully")
    else:
        logger.info("No alerts to process")

def process_scheduled_alerts_sync(redis_client):
    while True:
        try:
            # Wait for alert in the queue
            alert_data = redis_client.blpop(ALERT_QUEUE, timeout=1)
            if alert_data:
                _, alert_json = alert_data
                alert = json.loads(alert_json)

                camera_id = alert['camera_id']
                check_time = alert['check_time']
                message = alert['message']
                title = f"NOSHOW ALERT {camera_names[alert['camera_id']]}" 
                frame_data = alert['frame']

                if frame_data:
                    # Decode the base64 image
                    image_data = base64.b64decode(frame_data)
                    
                    # Create a temporary file for the image
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_image:
                        temp_image.write(image_data)
                        image_path = temp_image.name

                    # Send the alert with the image
                    try:
                        success = send_discord([(image_path, camera_id)], message, str(timezone.localtime(timezone.now()).strftime("%Y-%m-%d %I:%M:%S %p")), title)
                        if success:
                            logger.info(f"Scheduled alert sent successfully for camera {camera_id}")
                        else:
                            logger.error(f"Failed to send scheduled alert for camera {camera_id}")
                    except Exception as e:
                        logger.error(f"Error in send_discord for scheduled alert, camera {camera_id}: {str(e)}")
                    
                    # Clean up the temporary file
                    os.unlink(image_path)
                else:
                    logger.warning(f"No image data available for scheduled alert from camera {camera_id}")
                    # Send the alert without an image
                    try:
                        success = send_discord([], message, str(timezone.localtime(timezone.now()).strftime("%Y-%m-%d %I:%M:%S %p")), title)
                        if success:
                            logger.info(f"Scheduled alert sent successfully for camera {camera_id} (without image)")
                        else:
                            logger.error(f"Failed to send scheduled alert for camera {camera_id} (without image)")
                    except Exception as e:
                        logger.error(f"Error in send_discord for scheduled alert, camera {camera_id}: {str(e)}")

        except Exception as e:
            logger.error(f"Error processing scheduled alert: {str(e)}")
        
        time.sleep(0.1)  # Small delay to prevent CPU overuse

def test_notification(request):
    try:
        message = "TEST NOTIFICATION: This is a test message with the latest image."
        current_time = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S")
        title = f"Test ALTERT {current_time}"
        
        try:
            latest_image = get_latest_image(request, 1)  # Assuming camera_index 1 for the test
            logger.info("Latest image retrieved successfully for test notification")
        except Exception as e:
            logger.error(f"Error retrieving latest image for test notification: {str(e)}")
            latest_image = None

        if isinstance(latest_image, HttpResponse) and latest_image.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_image:
                temp_image.write(latest_image.content)
                temp_image_path = temp_image.name
            
            logger.info(f"Temporary image file created at: {temp_image_path}")
            
            try:
                success = send_discord([(temp_image_path, "Test Camera")], message, current_time, title)
                logger.info(f"send_discord called with image for test. Result: {success}")
            except Exception as e:
                logger.error(f"Error in send_discord for test notification: {str(e)}")
                success = False
            
            os.unlink(temp_image_path)
            logger.info("Temporary image file deleted after test notification")
            
            if success:
                return JsonResponse({"status": "success", "message": "Test notification with image sent successfully"})
            else:
                return JsonResponse({"status": "error", "message": "Failed to send test notification with image"}, status=500)
        else:
            logger.warning("Latest image not available or invalid for test notification")
            try:
                success = send_discord([], message + " (Image unavailable)", current_time, title)
                logger.info(f"send_discord called without image for test. Result: {success}")
            except Exception as e:
                logger.error(f"Error in send_discord for test notification without image: {str(e)}")
                success = False
            
            if success:
                return JsonResponse({"status": "success", "message": "Test notification sent successfully (without image)"})
            else:
                return JsonResponse({"status": "error", "message": "Failed to send test notification"}, status=500)
    except Exception as e:
        logger.exception("Unexpected error in test_notification view")
        return JsonResponse({"status": "error", "message": f"Unexpected error: {str(e)}"}, status=500)

             