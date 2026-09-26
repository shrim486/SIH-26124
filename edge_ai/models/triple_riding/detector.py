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
                people.append({
                    "box": (px1, py1, px2, py2),
                    "cx": (px1 + px2) / 2,
                    "cy": (py1 + py2) / 2,
                    "bottom": py2,
                    "width": person_width,
                })

        detections = {}
        for motorcycle_box, track_id in motorcycle_boxes:
            x1, y1, x2, y2 = motorcycle_box
            motorcycle_width = x2 - x1
            motorcycle_height = y2 - y1
            if motorcycle_width < 30 or motorcycle_height < 30:
                continue

            corridor_x1 = x1 - int(motorcycle_width * 0.12)
            corridor_x2 = x2 + int(motorcycle_width * 0.12)
            corridor_y1 = max(0, y1 - int(motorcycle_height * 1.25))
            corridor_y2 = min(frame_height, y2 + int(motorcycle_height * 0.10))
            associated = []
            for person in people:
                if not corridor_x1 <= person["cx"] <= corridor_x2:
                    continue
                if not corridor_y1 <= person["cy"] <= corridor_y2:
                    continue
                if person["bottom"] < y1 - motorcycle_height * 0.20:
                    continue
                if person["bottom"] > y2 + motorcycle_height * 0.15:
                    continue
                if person["width"] > motorcycle_width * 1.2:
                    continue
                associated.append(person)

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
