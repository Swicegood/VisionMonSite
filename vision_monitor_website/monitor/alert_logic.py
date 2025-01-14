
import time
from collections import deque

class AlertState:
    def __init__(self, name, flap_threshold=3, flap_interval=600):
        self.name = name
        self.is_alerting = False
        self.last_change = time.time()
        self.state_changes = deque(maxlen=flap_threshold)
        self.flap_threshold = flap_threshold
        self.flap_interval = flap_interval
        self.is_flapping = False

    def update(self, new_state):
        current_time = time.time()
        if new_state != self.is_alerting:
            self.state_changes.append(current_time)
            self.is_alerting = new_state
            self.last_change = current_time

            if len(self.state_changes) == self.flap_threshold:
                oldest_change = self.state_changes[0]
                if current_time - oldest_change <= self.flap_interval:
                    if not self.is_flapping:
                        self.is_flapping = True
                        return "FLAPPING_START"
                elif self.is_flapping:
                    self.is_flapping = False
                    return "FLAPPING_END"

            if self.is_flapping:
                return None

            return "ALERT" if new_state else "RESOLVED"

        return None

class AlertManager:
    def __init__(self):
        self.states = {}

    def update_state(self, name, is_alerting):
        if name not in self.states:
            self.states[name] = AlertState(name)

        return self.states[name].update(is_alerting)

# Example usage
if __name__ == "__main__":
    manager = AlertManager()
    
    # Simulate some state changes
    for i in range(20):
        state = i % 2 == 0
        result = manager.update_state("test_alert", state)
        if result:
            print(f"Alert 'test_alert' state change: {result}")
        time.sleep(1)  # Simulate time passing