from pathlib import Path

from .video_reader import read_video
from .detector import WaterloggingDetector
from .alert_manager import AlertManager
from .api_client import APIClient
from .gps import SimulatedGPS


# Project root: SIH-26124
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Files included in the Git repository
VIDEO_PATH = PROJECT_ROOT / "videos" / "waterlogging.mp4"
MODEL_PATH = PROJECT_ROOT / "models" / "best.pt"


# Source selection
# False = use recorded waterlogging video
# True  = use live camera/webcam
USE_CAMERA = False

if USE_CAMERA:
    SOURCE = 0
else:
    SOURCE = VIDEO_PATH


detector = WaterloggingDetector(
    model_path=str(MODEL_PATH),
    confidence_threshold=0.25
)


alert_manager = AlertManager(
    required_detections=2,
    cooldown_frames=30,
    bus_id="BUS_01"
)


api_client = APIClient()

gps = SimulatedGPS()


frame_count = 0
alert_count = 0


def process_frame(frame, frame_number):

    global frame_count
    global alert_count

    frame_count += 1

    # Run YOLO detection
    detections = detector.detect(frame)

    # Validate detections
    alert = alert_manager.process_detection(detections)

    # Send validated alert
    if alert is not None:

        alert_count += 1

        # Get simulated GPS location for this frame
        location = gps.get_location(frame_number)

        # Update alert with GPS coordinates
        alert["latitude"] = location["latitude"]
        alert["longitude"] = location["longitude"]

        print()
        print("========================================")
        print("VALIDATED WATERLOGGING ALERT")
        print("========================================")
        print(alert)

        api_client.send_alert(alert)


if __name__ == "__main__":

    print("========================================")
    print("Smart Bus Edge AI System")
    print("Waterlogging Detection")
    print("========================================")

    print("Detector loaded.")
    print("Alert manager loaded.")
    print("GPS loaded.")
    print("API client loaded.")
    print("Backend:", api_client.backend_url)

    print()

    if USE_CAMERA:
        print("Source: Live camera")
    else:
        print("Source: Recorded video")
        print("Video:", VIDEO_PATH)

    print()
    print("Starting video processing...")
    print()

    read_video(
        SOURCE,
        process_frame
    )

    print()
    print("========================================")
    print("Edge AI processing completed.")
    print("Frames processed:", frame_count)
    print("Alerts generated:", alert_count)
    print("========================================")
