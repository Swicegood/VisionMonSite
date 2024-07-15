from django.shortcuts import render
from django.http import HttpResponse, Http404, JsonResponse
from django.conf import settings
import psycopg2
import logging
from django.utils import timezone
from . import discord_client
from django.views.decorators.http import require_http_methods

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
    return render(request, 'monitor/monitor.html')

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

def get_facility_status():
    conn = get_db_connection()
    if not conn:
        logger.error("Database connection failed")
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT status
                FROM facility_status
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            return result[0] if result else None
    except psycopg2.Error as e:
        logger.error(f"Database error when fetching facility status: {e}")
        return None
    finally:
        conn.close()

def notify():
    status = get_facility_status()
    if status == "busy":
        try:
            latest_image = get_latest_image(None, 1)  # Assuming camera_index 1 for the main view
            if isinstance(latest_image, HttpResponse):
                image_data = latest_image.content
                message = f"Facility status is busy! Time: {timezone.now()}"
                discord_client.send_discord(image_data, message, str(timezone.now()))
                logger.info("Discord notification sent successfully")
            else:
                logger.error("Failed to get latest image for Discord notification")
        except Exception as e:
            logger.error(f"Error sending Discord notification: {str(e)}")
    else:
        logger.info(f"Current facility status is: {status}. No notification sent.")

@require_http_methods(["GET"])
def test_notification(request):
    try:
        # Force the status to be "busy" for testing
        status = "busy"
        
        latest_image = get_latest_image(None, 1)  # Assuming camera_index 1 for the main view
        if isinstance(latest_image, HttpResponse):
            image_data = latest_image.content
            message = f"TEST NOTIFICATION: Facility status is {status}! Time: {timezone.now()}"
            discord_client.send_discord(image_data, message, str(timezone.now()))
            logger.info("Test Discord notification sent successfully")
            return JsonResponse({"status": "success", "message": "Test notification sent successfully"})
        else:
            logger.error("Failed to get latest image for test Discord notification")
            return JsonResponse({"status": "error", "message": "Failed to get latest image"}, status=500)
    except Exception as e:
        logger.error(f"Error sending test Discord notification: {str(e)}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
# You might want to call notify() periodically or based on certain events
# For example, you could set up a Django management command or a celery task to run this function