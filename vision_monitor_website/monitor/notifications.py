import logging
import tempfile
import os
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from .discord_client import send_discord
from .image_handling import get_latest_image
from .state_management import parse_facility_state, alert_manager
from .db_operations import fetch_latest_facility_state

logger = logging.getLogger(__name__)

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
            message = f"Alert for camera {camera_id} {alert_type} - State: {state}"
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
                    success = send_discord(image_paths, message, str(timezone.now()))
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
            
    if alerts:
        logger.info("Alerts processed successfully")
    else:
        logger.info("No alerts to process")
        
def test_notification(request):
    try:
        message = "TEST NOTIFICATION: This is a test message with the latest image."
        current_time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # For testing, we'll use camera index 1
        camera_id = 1
        
        try:
            latest_image = get_latest_image(request, camera_id.split(' ')[1])
            logger.info("Latest image retrieved successfully")
        except Exception as e:
            logger.error(f"Error retrieving latest image: {str(e)}")
            latest_image = None

        if isinstance(latest_image, HttpResponse) and latest_image.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_image:
                temp_image.write(latest_image.content)
                temp_image_path = temp_image.name
            
            logger.info(f"Temporary image file created at: {temp_image_path}")
            
            try:
                success = send_discord([(temp_image_path, f"Camera {camera_id}")], message, current_time)
                logger.info(f"send_discord called with image. Result: {success}")
            except Exception as e:
                logger.error(f"Error in send_discord: {str(e)}")
                success = False
            
            os.unlink(temp_image_path)
            logger.info("Temporary image file deleted")
            
            if success:
                return JsonResponse({"status": "success", "message": "Test notification with image sent successfully"})
            else:
                return JsonResponse({"status": "error", "message": "Failed to send test notification with image"}, status=500)
        else:
            logger.warning("Latest image not available or invalid")
            try:
                success = send_discord(None, message + " (Image unavailable)", current_time)
                logger.info(f"send_discord called without image. Result: {success}")
            except Exception as e:
                logger.error(f"Error in send_discord: {str(e)}")
                success = False
            
            if success:
                return JsonResponse({"status": "success", "message": "Test notification sent successfully (without image)"})
            else:
                return JsonResponse({"status": "error", "message": "Failed to send test notification"}, status=500)
    except Exception as e:
        logger.exception("Unexpected error in test_notification view")
        return JsonResponse({"status": "error", "message": f"Unexpected error: {str(e)}"}, status=500)