from edge_ai.waterlogging.alert_manager import AlertManager
from edge_ai.waterlogging.gps import SimulatedGPS


def make_detection(confidence):
    return [{
        "event_type": "waterlogging",
        "confidence": confidence,
        "bbox": [100, 200, 500, 400]
    }]


def test_gps_returns_location():

    gps = SimulatedGPS()

    location = gps.get_location(0)

    assert "latitude" in location
    assert "longitude" in location

    assert isinstance(location["latitude"], float)
    assert isinstance(location["longitude"], float)


def test_gps_location_changes_with_frame():

    gps = SimulatedGPS()

    location1 = gps.get_location(0)
    location2 = gps.get_location(100)

    assert location1 != location2


def test_alert_can_receive_gps_coordinates():

    manager = AlertManager(
        required_detections=1,
        cooldown_frames=0,
        bus_id="BUS_01"
    )

    gps = SimulatedGPS()

    alert = manager.process_detection(
        make_detection(0.85)
    )

    assert alert is not None

    location = gps.get_location(100)

    alert["latitude"] = location["latitude"]
    alert["longitude"] = location["longitude"]

    assert alert["latitude"] == location["latitude"]
    assert alert["longitude"] == location["longitude"]