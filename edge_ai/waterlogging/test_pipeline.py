from edge_ai.waterlogging.alert_manager import AlertManager
from edge_ai.waterlogging.detector import WaterloggingDetector
from edge_ai.waterlogging.gps import SimulatedGPS


def test_waterlogging_pipeline_components():

    detector = WaterloggingDetector(
        model_path="models/best.pt",
        confidence_threshold=0.25
    )

    alert_manager = AlertManager(
        required_detections=2,
        cooldown_frames=30,
        bus_id="BUS_01"
    )

    gps = SimulatedGPS()

    assert detector.model is not None
    assert alert_manager.bus_id == "BUS_01"

    location = gps.get_location(0)

    assert "latitude" in location
    assert "longitude" in location


def test_pipeline_alert_generation():

    alert_manager = AlertManager(
        required_detections=2,
        cooldown_frames=30,
        bus_id="BUS_01"
    )

    detection = [{
        "event_type": "waterlogging",
        "confidence": 0.85,
        "bbox": [100, 200, 500, 400]
    }]

    assert alert_manager.process_detection(detection) is None

    alert = alert_manager.process_detection(detection)

    assert alert is not None
    assert alert["event_type"] == "waterlogging"
    assert alert["bus_id"] == "BUS_01"
    assert alert["severity"] == "medium"
    assert alert["status"] == "open"