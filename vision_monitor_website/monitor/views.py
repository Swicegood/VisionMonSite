from django.shortcuts import render
from django.http import HttpResponse, Http404, JsonResponse
from django.conf import settings
import psycopg2
import logging
from .discord_client import send_discord
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import os
import tempfile
from django.shortcuts import render
from django.db import connection
import redis
import base64
import json

# Initialize Redis connection
redis_client = redis.Redis(host='192.168.0.71', port=6379)

logger = logging.getLogger(__name__)

def get_db_connection():
    try:
        return psycopg2.connect(
            host=settings.DATABASES['default']['HOST'],
            database=settings.DATABASES['default']['NAME'],
            user=settings.DATABASES['default']['USER'],
            password=settings.DATABASES['default']['PASSWORD'],
            port=settings.DATABASES['default']['PORT'],
        )
    except psycopg2.Error as e:
        logger.error(f"Unable to connect to the database: {e}")
        return None

def home(request):
    return render(request, 'monitor/home.html')



def monitor(request):
    with connection.cursor() as cursor:
        # Fetch the latest facility state
        cursor.execute("""
            SELECT raw_message, timestamp
            FROM state_result
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        raw_message = cursor.fetchone()
        facility_state, camera_states = parse_facility_state(raw_message[0]) if raw_message else (None, {})

        # Fetch the latest frame analyses for each camera
        cursor.execute("""
            SELECT DISTINCT ON (camera_id)
                camera_id, camera_index, timestamp, description
            FROM visionmon_metadata
            ORDER BY camera_id, timestamp DESC
        """)
        latest_frame_analyses = cursor.fetchall()

        # Fetch the last 50 LLM outputs
        cursor.execute("""
            SELECT camera_id, camera_index, timestamp, description
            FROM visionmon_metadata
            ORDER BY timestamp DESC
            LIMIT 50
        """)
        llm_outputs = cursor.fetchall()

    # Fetch composite images from Redis
    composite_images = {}
    for analysis in latest_frame_analyses:
        camera_id = analysis[0]
        composite_key = f'composite_{camera_id}'
        composite_data = redis_client.get(composite_key)
        if composite_data:
            composite_images[camera_id] = base64.b64encode(composite_data).decode('utf-8')

    initial_data = {
        'facility_state': facility_state,
        'camera_states': camera_states,
        'camera_feeds': [
            {
                'cameraName': analysis[0],
                'cameraIndex': analysis[1],
                'timestamp': analysis[2].isoformat(),
                'description': analysis[3],
                'compositeImage': composite_images.get(analysis[0], '')  # Add composite image data
            } for analysis in latest_frame_analyses
        ],
        'llm_outputs': [
            {
                'cameraName': output[0],
                'cameraIndex': output[1],
                'timestamp': output[2].isoformat(),
                'description': output[3]
            } for output in llm_outputs
        ]
    }

    return render(request, 'monitor/monitor.html', {
        'initial_data': initial_data,
        'composite_images': composite_images  # Add composite images to the context
    })
    
    
def get_latest_image(request, camera_index):
     conn = get_db_connection()
     if not conn:
        raise Http404("Database connection failed")
     try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT vb.data, vm.timestamp
                FROM visionmon_metadata vm
                JOIN visionmon_binary_data vb ON vm.data_id = vb.id
                WHERE vm.camera_index = %s
                ORDER BY vm.timestamp DESC
                LIMIT 1
            """, [camera_index])
            result = cursor.fetchone()
            
            if result:
                image_data, timestamp = result
                response = HttpResponse(image_data, content_type='image/jpeg')
                
                # Add cache-busting headers
                response['Cache-Control'] = 'no-store, must-revalidate'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
                
                # Add a custom header with the timestamp
                response['X-Image-Timestamp'] = timestamp.isoformat()
                
                return response
            else:
                raise Http404("Image not found")
     except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        raise Http404("Database error occurred")
     finally:
        conn.close()
        
def get_composite_image(request, camera_name):
    composite_key = f'composite_{camera_name}'
    composite_data = redis_client.get(composite_key)
    if composite_data:
        return HttpResponse(composite_data, content_type='image/png')
    else:
        return HttpResponse(status=404)
        
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def test_websocket(request):
    logger.info("test_websocket view called")
    channel_layer = get_channel_layer()
    logger.info(f"Channel layer type: {type(channel_layer)}")
    
    try:
        async_to_sync(channel_layer.group_send)(
            "llm_output",
            {
                "type": "send_message",
                "message": "Test message from view"
            }
        )
        logger.info("Message sent to channel layer successfully")
    except Exception as e:
        logger.error(f"Error sending message to channel layer: {str(e)}")
    
    return render(request, 'monitor/monitor.html')

def parse_facility_state(raw_message):
    try:
        outer_data = json.loads(raw_message)
        return outer_data.get('facility_state', '').strip(), outer_data.get('camera_states', {})
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error while parsing facility state: {str(e)}")
    return None, {}

def get_facility_status():
    conn = get_db_connection()
    if not conn:
        logger.error("Database connection failed")
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT raw_message
                FROM state_result
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            if result:
                raw_message = result[0]
                return parse_facility_state(raw_message)
            return None
    except psycopg2.Error as e:
        logger.error(f"Database error when fetching facility status: {e}")
        return None
    finally:
        conn.close()

def notify(request, raw_message=None):
    if raw_message is None:
        status, camera_states = get_facility_status()
    else:
        status, camera_states = parse_facility_state(raw_message)
    
    if status == "busy" and any("busy" in state.lower() for state in camera_states.values()):
        message = f"Facility status update - Overall: {status}\n\nBusy cameras:"
        image_paths = []

        for camera_name, camera_state in camera_states.items():
            if "busy" in camera_state.lower():
                camera_index = camera_name.split()[-1]  # Assuming camera name format is "Name Index"
                try:
                    latest_image = get_latest_image(request, camera_index)
                    if isinstance(latest_image, HttpResponse) and latest_image.status_code == 200:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_image:
                            temp_image.write(latest_image.content)
                            image_paths.append((temp_image.name, camera_name))
                        message += f"\n- {camera_name}: {camera_state}"
                    else:
                        logger.error(f"Failed to get image for camera {camera_name}")
                except Exception as e:
                    logger.error(f"Error retrieving image for camera {camera_name}: {str(e)}")

        if image_paths:
            try:
                success = send_discord(image_paths, message, str(timezone.now()))
                logger.info(f"send_discord called with images. Result: {success}")
            except Exception as e:
                logger.error(f"Error in send_discord: {str(e)}")
                success = False

            for path, _ in image_paths:
                os.unlink(path)
                logger.info(f"Temporary image file deleted: {path}")

            if success:
                logger.info("Notification sent successfully")
            else:
                logger.error("Failed to send notification")
        else:
            logger.warning("No busy cameras found with valid images")
    else:
        logger.info(f"Current facility status is: {status}. No notification sent.")
        
        

@require_http_methods(["GET"])
def test_notification(request):
    try:
        message = "TEST NOTIFICATION: This is a test message with the latest image."
        current_time = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get the latest image
        try:
            latest_image = get_latest_image(request, 1)  # Assuming camera_index 1 for the main view
            logger.info("Latest image retrieved successfully")
        except Exception as e:
            logger.error(f"Error retrieving latest image: {str(e)}")
            latest_image = None

        if isinstance(latest_image, HttpResponse) and latest_image.status_code == 200:
            # Create a temporary file to store the image
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_image:
                temp_image.write(latest_image.content)
                temp_image_path = temp_image.name
            
            logger.info(f"Temporary image file created at: {temp_image_path}")
            
            # Send the notification with the image
            try:
                success = send_discord(temp_image_path, message, current_time)
                logger.info(f"send_discord called with image. Result: {success}")
            except Exception as e:
                logger.error(f"Error in send_discord: {str(e)}")
                success = False
            
            # Delete the temporary file
            os.unlink(temp_image_path)
            logger.info("Temporary image file deleted")
            
            if success:
                return JsonResponse({"status": "success", "message": "Test notification with image sent successfully"})
            else:
                return JsonResponse({"status": "error", "message": "Failed to send test notification with image"}, status=500)
        else:
            logger.warning("Latest image not available or invalid")
            # If we couldn't get the latest image, send notification without image
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
@csrf_exempt
@require_http_methods(["POST"])
def update_state(request):
    try:
        raw_message = request.body.decode('utf-8')
        
        conn = get_db_connection()
        if not conn:
            return JsonResponse({"status": "error", "message": "Database connection failed"}, status=500)
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO facility_status (raw_message, timestamp)
                    VALUES (%s, %s)
                """, (raw_message, timezone.now()))
            conn.commit()
            
            # Trigger notification after updating the state
            notify(request, raw_message)
            
            return JsonResponse({"status": "success", "message": "State updated and notification sent"})
        except psycopg2.Error as e:
            logger.error(f"Database error when updating state: {e}")
            return JsonResponse({"status": "error", "message": "Database error occurred"}, status=500)
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error in update_state: {str(e)}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

# You might want to call notify() periodically or based on certain events
# For example, you could set up a Django management command or a celery task to run this function