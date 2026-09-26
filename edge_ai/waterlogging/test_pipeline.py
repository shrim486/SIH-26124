from video_reader import read_video
from detector import WaterloggingDetector
from alert_manager import AlertManager


VIDEO_PATH = "videos/waterlogging.mp4"


detector = WaterloggingDetector(
    model_path="models/best.pt",
    confidence_threshold=0.25
)

alert_manager = AlertManager(
    required_detections=2,
    cooldown_frames=30,
    bus_id="BUS_01"
)


frame_count = 0
alert_count = 0


def process_frame(frame, frame_number):

    global frame_count
    global alert_count

    frame_count += 1

    detections = detector.detect(frame)

    alert = alert_manager.process_detection(detections)

    if alert is not None:

        alert_count += 1

        print()
        print("========================================")
        print("VALIDATED ALERT")
        print("========================================")
        print(alert)


print("Starting Edge AI pipeline test...")
print()

read_video(
    VIDEO_PATH,
    process_frame
)

print()
print("========================================")
print("PIPELINE TEST COMPLETED")
print("========================================")
print("Frames processed:", frame_count)
print("Alerts generated:", alert_count)