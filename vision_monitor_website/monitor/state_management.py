import json
import logging
from collections import deque, Counter
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

camera_state_windows = {}
state_key_phrases = ["busy", "festival happening", "crowd gathering", "night-time", "quiet", "person present", "people eating"]

def parse_facility_state(raw_message):
    try:
        outer_data = json.loads(raw_message)
        facility_state = outer_data.get('facility_state', '').strip()
        camera_states = outer_data.get('camera_states', {})
        
        current_time = timezone.now()
        for camera_id, state in camera_states.items():
            update_camera_state(camera_id, state, current_time)

        most_frequent_states = {camera_id: get_most_frequent_state(camera_id) for camera_id in camera_states.keys()}

        return facility_state, most_frequent_states
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error while parsing facility state: {str(e)}")
    return None, {}

def update_camera_state(camera_id, state, timestamp):
    if camera_id not in camera_state_windows:
        camera_state_windows[camera_id] = deque(maxlen=900)  # 15 minutes * 60 seconds = 900 seconds

    if timezone.is_naive(timestamp):
        timestamp = timezone.make_aware(timestamp)

    current_time = timestamp
    while camera_state_windows[camera_id] and (current_time - camera_state_windows[camera_id][0][1]) > timedelta(minutes=15):
        camera_state_windows[camera_id].popleft()

    camera_state_windows[camera_id].append((state, timestamp))

def get_most_frequent_state(camera_id):
    if camera_id not in camera_state_windows:
        return "Unknown"

    relevant_states = [state for state, _ in camera_state_windows[camera_id] if any(phrase in state.lower() for phrase in state_key_phrases)]

    if not relevant_states:
        return "Unknown"

    state_counts = Counter(relevant_states)
    return state_counts.most_common(1)[0][0]