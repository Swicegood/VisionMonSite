from django.shortcuts import render

def home(request):
    return render(request, 'monitor/home.html')

def monitor(request):
    # Add your LLM interaction logic here
    return render(request, 'monitor/monitor.html')

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