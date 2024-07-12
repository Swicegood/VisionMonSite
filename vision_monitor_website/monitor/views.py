from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.conf import settings
import psycopg2
import logging

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
                SELECT vb.data
                FROM visionmon_metadata vm
                JOIN visionmon_binary_data vb ON vm.data_id = vb.id
                WHERE vm.camera_index = %s
                ORDER BY vm.timestamp DESC
                LIMIT 1
            """, [camera_index])
            result = cursor.fetchone()
        
        if result:
            image_data = result[0]
            return HttpResponse(image_data, content_type='image/jpeg')
        else:
            raise Http404("Image not found")
    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        raise Http404("Database error occurred")
    finally:
        conn.close()
        
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging
import time

logger = logging.getLogger(__name__)

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
    
    time.sleep(1)  # Give some time for the message to be processed
    logger.info("Rendering response")
    return render(request, 'monitor/monitor.html')