import cv2
from detector import WaterloggingDetector


video_path = "videos/waterlogging.mp4"

detector = WaterloggingDetector(
    model_path="models/best.pt",
    confidence_threshold=0.25
)

cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("ERROR: Could not open video.")
    exit()

print("Video opened successfully.")

frame_number = 0
detections_found = 0

while True:

    ret, frame = cap.read()

    if not ret:
        break

    # Test every 30th frame
    if frame_number % 30 == 0:

        detections = detector.detect(frame)

        print(
            f"Frame {frame_number}: "
            f"{len(detections)} detection(s)"
        )

        for detection in detections:
            print("   ", detection)

            detections_found += 1

    frame_number += 1

cap.release()

print()
print("Test completed.")
print("Total frames checked:", frame_number // 30 + 1)
print("Total detection results:", detections_found)