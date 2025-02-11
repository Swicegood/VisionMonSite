import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from datetime import timedelta

from .db_operations import fetch_latest_facility_state, fetch_latest_frame_analyses, fetch_recent_llm_outputs, insert_facility_status, fetch_timeline_events, fetch_timeline_events_paginated
from .state_management import parse_facility_state
from .image_handling import get_composite_images
from .notifications import notify, test_notification
import base64
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from .db_operations import get_latest_frame
from .redis_operations import connect_redis
from .config import ALERT_QUEUE

logger = logging.getLogger(__name__)
timezone.activate(timezone.get_current_timezone())

def home(request):
    return render(request, 'monitor/home.html')

def monitor(request):
    raw_message = fetch_latest_facility_state()
    if raw_message:
        facility_state, camera_states, alerts = parse_facility_state(raw_message[0])
        timestamp = raw_message[1]
    else:
        facility_state, camera_states = None, {}

    latest_frame_analyses = fetch_latest_frame_analyses()
    llm_outputs = fetch_recent_llm_outputs()

    composite_images = get_composite_images(latest_frame_analyses)

    initial_data = {
        'facility_state': facility_state,
        'camera_states': camera_states,
        'camera_feeds': [
            {
                'cameraId': analysis[0],
                'cameraIndex': analysis[1],
                'timestamp': analysis[2].isoformat(),
                'description': analysis[3],
                'cameraName': analysis[4],
                'compositeImage': composite_images.get(analysis[0], '')
            } for analysis in latest_frame_analyses
        ],
        'llm_outputs': [
            {
                'cameraId': output[0],
                'cameraIndex': output[1],
                'timestamp': output[2].isoformat(),
                'description': output[3],
                'cameraName': output[4]
            } for output in llm_outputs
        ]
    }

    return render(request, 'monitor/monitor.html', {
        'initial_data': initial_data,
        'composite_images': composite_images
    })

def timeline_view(request):
    end_time = timezone.now()
    start_time = end_time - timedelta(hours=1)  # Show last 1 hour
    
    latest_analyses = fetch_latest_frame_analyses()
    events = fetch_timeline_events(start_time, end_time, camera_id=None)
    
    initial_data = {
        'cameras': [
            {
                'id': analysis[0],
                'name': analysis[4],
                'image': f'/get_latest_image/{analysis[1]}' if get_latest_frame(analysis[0]) else '',
                'index': analysis[1],
            } for analysis in latest_analyses
        ],
        'events': events
    }
    return render(request, 'monitor/timeline.html', {'initial_data': initial_data})

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

@csrf_exempt
@require_http_methods(["POST"])
def update_state(request):
    try:
        raw_message = request.body.decode('utf-8')
        current_time = timezone.now()
        
        if insert_facility_status(raw_message, current_time):
            facility_state, camera_states, alerts = parse_facility_state(raw_message)
            
            # Handle alerts
            for camera_id, alert_type, state in alerts:
                if alert_type == "ALERT":
                    notify(request, raw_message, camera_id)
                send_websocket_update(json.dumps({
                    "type": "alert",
                    "camera_id": camera_id,
                    "alert_type": alert_type
                }))
            
            return JsonResponse({"status": "success", "message": "State updated and alerts processed"})
        else:
            return JsonResponse({"status": "error", "message": "Failed to update state"}, status=500)
    except Exception as e:
        logger.error(f"Error in update_state: {str(e)}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@require_http_methods(["GET"])
def test_notification_view(request):
    return test_notification(request)

# Utility function to send WebSocket updates
def send_websocket_update(message):
    channel_layer = get_channel_layer()
    try:
        async_to_sync(channel_layer.group_send)(
            "llm_output",
            {
                "type": "send_message",
                "message": message
            }
        )
        logger.info("WebSocket update sent successfully")
    except Exception as e:
        logger.error(f"Error sending WebSocket update: {str(e)}")

@csrf_exempt
def no_show_webhook(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        # Get camera_id from headers
        camera_id = request.headers.get('X-Camera-Id')
        
        if not camera_id:
            return JsonResponse({"error": "X-Camera-Id header is missing"}, status=400)

        # Parse the timestamp from the request body
        data = json.loads(request.body)
        timestamp = data['timestamp']

        # Store this webhook hit in Redis with an expiration
        redis_client = connect_redis()
        redis_client.setex(f"webhook:{camera_id}", 1800, timestamp)  # Expire after 30 minutes

        logger.info(f"Processed webhook for camera {camera_id} at timestamp {timestamp}")
        return JsonResponse({"status": "Webhook processed successfully"}, status=200)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
    except KeyError as e:
        logger.error(f"Missing key in JSON data: {str(e)}")
        return JsonResponse({"error": f"Missing key in JSON data: {str(e)}"}, status=400)
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return JsonResponse({"error": f"Error processing webhook: {str(e)}"}, status=500)
    
@require_http_methods(["GET"])
def get_timeline_events(request, camera_id):
    start_time = timezone.now() - timedelta(hours=1)
    end_time = timezone.now()
    events = fetch_timeline_events(start_time, end_time, camera_id)
    return JsonResponse({"events": events})

@require_http_methods(["GET"])
def get_latest_frame_analyses(request):
    latest_analyses = fetch_latest_frame_analyses()
    return JsonResponse({"latest_analyses": latest_analyses})

@require_http_methods(["GET"])
def get_timeline_events_paginated(request):
    """
    Returns a chunk of timeline events based on offset & limit
    """
    try:
        camera_id = request.GET.get('camera_id')  # optional
        offset = int(request.GET.get('offset', 0))
        limit = int(request.GET.get('limit', 20))

        events = fetch_timeline_events_paginated(offset=offset, limit=limit, camera_id=camera_id)
        return JsonResponse({"events": events})
    except Exception as e:
        logger.error(f"Error in get_timeline_events_paginated: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

@require_http_methods(["GET"])
def get_timeline_events_by_date(request):
    """
    Fetch timeline events for a given date/time range in query params:
      ?start_time=YYYY-MM-DDTHH:MM:SSZ
      ?end_time=YYYY-MM-DDTHH:MM:SSZ
    """
    try:
        start_time_str = request.GET.get('start_time')
        end_time_str = request.GET.get('end_time')
        camera_id = request.GET.get('camera_id', None) # optional

        if not start_time_str or not end_time_str:
            return JsonResponse({"error": "Missing start_time or end_time"}, status=400)

        from dateutil import parser
        start_time = parser.parse(start_time_str)
        end_time = parser.parse(end_time_str)

        events = fetch_timeline_events(start_time, end_time, camera_id=camera_id)
        return JsonResponse({"events": events})
    except Exception as e:
        logger.error(f"Error in get_timeline_events_by_date: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

@require_http_methods(["GET"])
def get_timeline_events_by_date_paginated(request):
    """
    Fetch timeline events for a given date/time range with pagination:
      ?start_time=YYYY-MM-DDTHH:MM:SSZ
      ?end_time=YYYY-MM-DDTHH:MM:SSZ
      &offset=0
      &limit=20
    """
    try:
        start_time_str = request.GET.get('start_time')
        end_time_str = request.GET.get('end_time')
        offset = int(request.GET.get('offset', 0))
        limit = int(request.GET.get('limit', 20))
        camera_id = request.GET.get('camera_id', None)  # optional

        if not start_time_str or not end_time_str:
            return JsonResponse({"error": "Missing start_time or end_time"}, status=400)

        from dateutil import parser
        start_time = parser.parse(start_time_str)
        end_time = parser.parse(end_time_str)

        events = fetch_timeline_events_paginated(offset=offset, limit=limit, start_time=start_time, end_time=end_time, camera_id=camera_id)
        return JsonResponse({"events": events})
    except Exception as e:
        logger.error(f"Error in get_timeline_events_by_date_paginated: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)
