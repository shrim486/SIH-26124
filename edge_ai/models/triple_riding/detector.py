"""Conservative person-to-motorcycle association for triple-riding alerts."""

from collections import defaultdict, deque


class TripleRidingDetector:
    """Apply strict rider association and temporal confirmation."""

    def __init__(self, confidence=0.55):
        self.confidence = confidence
        self.history = defaultdict(lambda: deque(maxlen=8))

    def detect(self, model, frame, motorcycle_boxes, frame_width, frame_height):
        person_results = model(frame, classes=[0], conf=self.confidence, verbose=False)
        people = []
        if person_results and person_results[0].boxes is not None:
            for coordinates in person_results[0].boxes.xyxy.cpu().numpy():
                px1, py1, px2, py2 = map(int, coordinates)
                person_width = px2 - px1
                person_height = py2 - py1
                if person_width < 10 or person_height < 20:
                    continue
                people.append(
                    {
                        "box": (px1, py1, px2, py2),
                        "cx": (px1 + px2) / 2,
                        "cy": (py1 + py2) / 2,
                        "bottom": py2,
                        "width": person_width,
                    }
                )

        detections = {}
        # A detected person can belong to at most one motorcycle. Pick the
        # closest eligible motorcycle rather than counting one person twice.
        assignments = defaultdict(list)
        for person in people:
            eligible = []
            for box, identity in motorcycle_boxes:
                x1, y1, x2, y2 = box
                w, h = x2 - x1, y2 - y1
                if w < 30 or h < 30:
                    continue
                if (
                    x1 - 0.12 * w <= person["cx"] <= x2 + 0.12 * w
                    and max(0, y1 - 1.25 * h)
                    <= person["cy"]
                    <= min(frame_height, y2 + 0.1 * h)
                    and y1 - 0.2 * h <= person["bottom"] <= y2 + 0.15 * h
                    and person["width"] <= 1.2 * w
                ):
                    eligible.append(
                        (abs(person["cx"] - (x1 + x2) / 2) / w, int(identity))
                    )
            if eligible:
                assignments[min(eligible)[1]].append(person)
        visible_ids = {int(identity) for _, identity in motorcycle_boxes}
        for identity in list(self.history):
            if identity not in visible_ids:
                del self.history[identity]
        for motorcycle_box, track_id in motorcycle_boxes:
            x1, y1, x2, y2 = motorcycle_box
            motorcycle_width = x2 - x1
            motorcycle_height = y2 - y1
            if motorcycle_width < 30 or motorcycle_height < 30:
                continue

            associated = assignments[int(track_id)]

            rider_count = len(associated)
            history = self.history[int(track_id)]
            history.append(rider_count >= 3)
            confirmed = len(history) >= 5 and sum(history) >= 5
            detections[int(track_id)] = {
                "rider_count": rider_count,
                "confirmed": confirmed,
                "people": [person["box"] for person in associated],
            }
        return detections
