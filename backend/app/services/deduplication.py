from math import radians, sin, cos, sqrt, atan2
from datetime import datetime, timedelta

from app.models.road_issue import RoadIssue


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two GPS coordinates in meters.
    """

    earth_radius = 6371000

    lat1 = radians(lat1)
    lat2 = radians(lat2)

    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(delta_lon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return earth_radius * c


def find_duplicate_road_issue(
    db,
    issue_type,
    latitude,
    longitude,
    radius_meters=30,
    time_window_minutes=30
):

    cutoff = datetime.utcnow() - timedelta(
        minutes=time_window_minutes
    )

    issues = (
        db.query(RoadIssue)
        .filter(
            RoadIssue.issue_type == issue_type,
            RoadIssue.last_detected >= cutoff
        )
        .all()
    )

    for issue in issues:

        distance = calculate_distance(
            latitude,
            longitude,
            issue.latitude,
            issue.longitude
        )

        if distance <= radius_meters:
            return issue

    return None