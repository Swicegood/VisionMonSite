from django.shortcuts import render
from django.http import HttpResponse
from django.db import connection
import base64

def home(request):
    return render(request, 'monitor/home.html')

def monitor(request):
    return render(request, 'monitor/monitor.html')

def get_latest_image(request, camera_index):
    with connection.cursor() as cursor:
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
        # Return a placeholder or error image
        return HttpResponse(status=404)
    
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