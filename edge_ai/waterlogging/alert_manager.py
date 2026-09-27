from .config import CONFIDENCE_THRESHOLD
from datetime import datetime


class AlertManager:

    def __init__(
        self,
        required_detections=2,
        cooldown_frames=30,
        bus_id="BUS_01"
    ):
        self.required_detections = required_detections
        self.cooldown_frames = cooldown_frames
        self.bus_id = bus_id

        self.detection_count = 0
        self.cooldown_counter = 0
        self.event_counter = 0

    def process_detection(self, detections):
        """
        Process detections from one video frame.

        Returns a validated alert object when enough
        high-confidence detections are observed.
        """

        # Handle cooldown
        if self.cooldown_counter > 0:
            self.cooldown_counter -= 1
            return None

        valid_detections = []

        # Check confidence threshold
        for detection in detections:

            confidence = detection["confidence"]

            if confidence >= CONFIDENCE_THRESHOLD:
                valid_detections.append(detection)

        # No valid detection in this frame
        if not valid_detections:
            return None

        # Count valid detections
        self.detection_count += 1

        # Not enough detections yet
        if self.detection_count < self.required_detections:
            return None

        # Select highest-confidence detection
        best_detection = max(
            valid_detections,
            key=lambda x: x["confidence"]
        )

        # Generate unique event ID
        self.event_counter += 1

        # Create alert object
        alert = {
            "event_id": f"EVT_{self.event_counter:04d}",
            "event_type": best_detection["event_type"],
            "confidence": best_detection["confidence"],
            "latitude": 13.0358,
            "longitude": 77.5970,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "severity": "medium",
            "priority": "medium",
            "bus_id": self.bus_id,
            "report_count": 1,
            "status": "open"
        }

        # Reset detection count
        self.detection_count = 0

        # Start cooldown
        self.cooldown_counter = self.cooldown_frames

        return alert


if __name__ == "__main__":

    manager = AlertManager()

    print("Alert Manager loaded successfully.")
    print("Confidence threshold:", CONFIDENCE_THRESHOLD)
    print("Required detections:", manager.required_detections)
    print("Cooldown frames:", manager.cooldown_frames)
    print("Bus ID:", manager.bus_id)
