"""Time-based queue indicators from tracked vehicles in a fixed camera.

These are configurable rules on learned detections, not trained congestion or
bottleneck classifiers. No metric speeds are inferred without calibration.
"""

from collections import defaultdict, deque
from math import hypot


class TrafficAnalytics:
    def __init__(self, zones=None, min_vehicles=5, slow_speed=0.15, duration=3.0):
        if min_vehicles < 1 or duration <= 0 or slow_speed < 0:
            raise ValueError("Invalid traffic thresholds")
        self.zones = zones or {"road": [0, 0, 1, 1]}
        for box in self.zones.values():
            if len(box) != 4 or not (
                0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1
            ):
                raise ValueError("Zones must be normalized x1,y1,x2,y2 rectangles")
        self.minimum, self.slow_speed, self.duration = (
            min_vehicles,
            slow_speed,
            duration,
        )
        self.tracks = defaultdict(deque)
        self.since = {}
        self.last_timestamp = None

    def update(self, tracks, timestamp, width, height):
        if self.last_timestamp is not None and timestamp <= self.last_timestamp:
            raise ValueError("Timestamps must increase")
        self.last_timestamp = timestamp
        speeds = {}
        for track in tracks:
            identity = track["track_id"]
            x1, y1, x2, y2 = track["bbox_xyxy"]
            history = self.tracks[identity]
            if history and timestamp - history[-1][0] > 1.0:
                history.clear()
            history.append((timestamp, (x1 + x2) / 2, (y1 + y2) / 2, max(1, y2 - y1)))
            while history and timestamp - history[0][0] > 2:
                history.popleft()
            if len(history) >= 2 and timestamp - history[0][0] >= 0.5:
                old, new = history[0], history[-1]
                speeds[identity] = (
                    hypot(new[1] - old[1], new[2] - old[2])
                    / ((new[3] + old[3]) / 2)
                    / (new[0] - old[0])
                )
        for identity in list(self.tracks):
            if timestamp - self.tracks[identity][-1][0] > 2:
                del self.tracks[identity]
        states = {}
        for name, (left, top, right, bottom) in self.zones.items():
            visible = [
                t
                for t in tracks
                if left <= (t["bbox_xyxy"][0] + t["bbox_xyxy"][2]) / 2 / width <= right
                and top
                <= (t["bbox_xyxy"][1] + t["bbox_xyxy"][3]) / 2 / height
                <= bottom
            ]
            measured = [
                speeds[t["track_id"]] for t in visible if t["track_id"] in speeds
            ]
            slow = sum(s <= self.slow_speed for s in measured)
            ratio = slow / len(measured) if measured else 0
            queued = len(measured) >= self.minimum and ratio >= 0.6
            if queued:
                self.since.setdefault(name, timestamp)
            else:
                self.since.pop(name, None)
            states[name] = {
                "vehicle_count": len(visible),
                "measured_tracks": len(measured),
                "slow_fraction": ratio,
                "congestion_candidate": queued
                and timestamp - self.since[name] >= self.duration,
            }
        upstream, downstream = states.get("upstream"), states.get("downstream")
        bottleneck = bool(
            upstream
            and downstream
            and upstream["congestion_candidate"]
            and downstream["measured_tracks"] >= 1
            and downstream["slow_fraction"] < 0.3
        )
        return {
            "zones": states,
            "bottleneck_candidate": bottleneck,
            "method": "fixed-camera tracked motion rules; speed in vehicle-heights/second",
        }
