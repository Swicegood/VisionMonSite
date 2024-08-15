import json
import logging
from collections import deque, Counter
from datetime import timedelta
from django.utils import timezone
from .alert_logic import AlertManager
from .config import camera_names

logger = logging.getLogger(__name__)

alert_manager = AlertManager()

camera_state_windows = {}
facility_state_window = deque(maxlen=900)  # 15 minutes * 60 seconds = 900 seconds
state_key_phrases = ["bustling", "festival happening", "crowd gathering", "over capacity", "night-time", "quiet", "person present", "people eating", "door open"]

def parse_facility_state(raw_message):
    try:
        outer_data = json.loads(raw_message)
        facility_state = outer_data.get('facility_state', '').strip()
        camera_states = outer_data.get('camera_states', {})
        
        logger.info(f"Parse Facility Camera states: {camera_states}")
        
        current_time = timezone.now()
        
        update_facility_state(facility_state, current_time)
        for camera_id, state in camera_states.items():
            update_camera_state(camera_id, state, current_time)
        
        most_frequent_facility_state = get_most_frequent_facility_state()
        most_frequent_states = {camera_id: get_most_frequent_state(camera_id) for camera_id in camera_states.keys()}
        
        logger.info(f"Parse Facility Most frequent states: {most_frequent_states}")
        
        alerts = []
        for camera_id, state in most_frequent_states.items():
            is_alerting = any(phrase in state.lower() for phrase in ["festival happening", "crowd gathering", "door open"])
            alert_result = alert_manager.update_state(camera_id, is_alerting)
            if alert_result:
                alerts.append((camera_id, alert_result, state))
        
        logger.info(f"Parse Facility Alerts: {alerts}")
        
        return most_frequent_facility_state, most_frequent_states, alerts
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error while parsing facility state: {str(e)}")
    return None, {}, []

def update_camera_state(camera_id, state, timestamp):
    if camera_id not in camera_state_windows:
        logger.info(f"Creating state window for camera {camera_id}")
        camera_state_windows[camera_id] = deque(maxlen=900)  # 15 minutes * 60 seconds = 900 seconds
    
    if timezone.is_naive(timestamp):
        timestamp = timezone.make_aware(timestamp)
    
    current_time = timestamp
    while camera_state_windows[camera_id] and (current_time - camera_state_windows[camera_id][0][1]) > timedelta(minutes=15):
        camera_state_windows[camera_id].popleft()
    
    camera_state_windows[camera_id].append((state, timestamp))
    logger.info(f"Updated state for camera {camera_id}: {state} at {timestamp}")

# Define alert state penalties and problematic states for specific cameras
camera_alert_config = {
    "Audio_Visual 1": {
        "penalty": 0.7,
        "alert_states": {"bustling"}
    },
    "Back_Driveway 2": {
        "penalty": 0.7,
        "alert_states": {"bustling", "festival happening"}
    },
    "Bhoga_Shed 3": {
        "penalty": 0.7,
        "alert_states": {"door open"}
    },
    "Field 6": {
        "penalty": 0.7,
        "alert_states": {"bustling"}
    },
    "Hall 8": {
        "penalty": 0.4,
        "alert_states": {"bustling", "crowd gathering", "festival happening"}
    },
    "Kitchen 9": {
        "penalty": 0.7,
        "alert_states": {"bustling"}
    },
    "Stage 12": {
        "penalty": 0.4,
        "alert_states": {"bustling", "crowd gathering", "festival happening"}
    },
    "Temple 13": {
        "penalty": 0.5,
        "alert_states": {"festival happening"}
    },
    "Axis 17": {
        "penalty": 0.3,
        "alert_states": {"festival happening"}
    }
    # Add other cameras with their specific penalties and problematic states
}

facility_config = {
    "bustling": {
        "alert_states": ["bustling", "crowd gathering", "festival happening"],
        "penalty":  1
    },
    "quiet": {
        "alert_states": ["quiet"],
        "penalty": 1 # No penalty for quiet state
    },
    "night-time": {
        "alert_states": ["night-time"],
        "penalty": 1
    },
    "person present": {
        "alert_states": ["person present"],
        "penalty": 1
    },
    "people eating": {
        "alert_states": ["people eating"],
        "penalty": 1
    },
    "over capacity": {
        "alert_states": ["over capacity"],
        "penalty": 1.5 # Over capacity is a more serious state
    }
}

def get_most_frequent_state(camera_id):
    if camera_id not in camera_state_windows:
        logger.error(f"Camera {camera_id} not found in state windows")
        return "Unknown"
    
    if not camera_state_windows[camera_id]:
        logger.warning(f"No states recorded for camera {camera_id}")
        return "Unknown"
    
    relevant_states = [state for state, _ in camera_state_windows[camera_id] if any(phrase in state.lower() for phrase in state_key_phrases)]
    
    if not relevant_states:
        logger.warning(f"No relevant states found for camera {camera_id}")
        return camera_state_windows[camera_id][-1][0]  # Return the most recent state if no relevant states
    
    # Get the alert config for this camera
    camera_config = camera_alert_config.get(camera_id)
    
    # Create a weighted Counter
    state_counts = Counter()
    for state in relevant_states:
        if camera_config and any(alert in state.lower() for alert in camera_config["alert_states"]):
            # Apply penalty to specific alert states for this camera
            state_counts[state] += camera_config["penalty"]
        else:
            state_counts[state] += 1.0
    
    most_common_state = state_counts.most_common(1)[0][0]
    logger.info(f"Most frequent state for camera {camera_id}: {most_common_state}")
    return most_common_state

def update_facility_state(facility_state, timestamp):
    global facility_state_window
    
    if timezone.is_naive(timestamp):
        timestamp = timezone.make_aware(timestamp)
    
    current_time = timestamp
    while facility_state_window and (current_time - facility_state_window[0][1]) > timedelta(minutes=15):
        facility_state_window.popleft()
    
    facility_state_window.append((facility_state, timestamp))
    logger.info(f"Updated facility state: {facility_state} at {timestamp}")

def get_most_frequent_facility_state():
    if not facility_state_window:
        logger.warning("No facility states recorded")
        return "Unknown"
    
    relevant_states = [state for state, _ in facility_state_window if any(phrase in state.lower() for phrase in state_key_phrases)]
    
    if not relevant_states:
        logger.warning("No relevant states found in facility states")
        return facility_state_window[-1][0]  # Return the most recent state if no relevant states
    
    # Create a weighted Counter
    state_counts = Counter()
    for state in relevant_states:
        for config_state, config in facility_config.items():
            if config_state in state.lower():
                state_counts[state] += config["penalty"]
                break
        else:
            state_counts[state] += 1.0  # Default weight if no specific config

    most_common_state = state_counts.most_common(1)[0][0]
    logger.info(f"Most frequent facility state: {most_common_state}")
    return most_common_state