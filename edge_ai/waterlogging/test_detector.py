import cv2

from edge_ai.waterlogging.detector import WaterloggingDetector


def test_detector_loads_model():

    detector = WaterloggingDetector(
        model_path="models/best.pt",
        confidence_threshold=0.25
    )

    assert detector.model is not None


def test_detector_processes_video_frame():

    video_path = "videos/waterlogging.mp4"

    detector = WaterloggingDetector(
        model_path="models/best.pt",
        confidence_threshold=0.25
    )

    cap = cv2.VideoCapture(video_path)

    assert cap.isOpened()

    ret, frame = cap.read()

    cap.release()

    assert ret is True
    assert frame is not None

    detections = detector.detect(frame)

    assert isinstance(detections, list)

    for detection in detections:
        assert detection["event_type"] == "waterlogging"
        assert 0 <= detection["confidence"] <= 1
        assert len(detection["bbox"]) == 4