from edge_ai.waterlogging.alert_manager import AlertManager


def make_detection(confidence):
    return [{
        "event_type": "waterlogging",
        "confidence": confidence,
        "bbox": [100, 200, 500, 400]
    }]


def test_alert_requires_valid_detections():
    manager = AlertManager(
        required_detections=2,
        cooldown_frames=3
    )

    # Below confidence threshold
    result = manager.process_detection(
        make_detection(0.55)
    )

    assert result is None

    # First valid detection
    result = manager.process_detection(
        make_detection(0.73)
    )

    assert result is None

    # Second valid detection should generate alert
    result = manager.process_detection(
        make_detection(0.82)
    )

    assert result is not None
    assert result["event_type"] == "waterlogging"
    assert result["confidence"] == 0.82


def test_alert_cooldown():
    manager = AlertManager(
        required_detections=1,
        cooldown_frames=3
    )

    # Generate first alert
    result = manager.process_detection(
        make_detection(0.90)
    )

    assert result is not None

    # These should be blocked by cooldown
    assert manager.process_detection(make_detection(0.90)) is None
    assert manager.process_detection(make_detection(0.90)) is None
    assert manager.process_detection(make_detection(0.90)) is None

    # After cooldown, another alert can be generated
    result = manager.process_detection(
        make_detection(0.90)
    )

    assert result is not None