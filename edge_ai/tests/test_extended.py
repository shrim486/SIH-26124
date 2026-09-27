import json
from pathlib import Path
import tempfile
import unittest
import yaml
from PIL import Image
from edge_ai.processing.traffic_analytics import TrafficAnalytics
from edge_ai.training.manage_dataset import validate
from edge_ai.models.triple_riding.detector import TripleRidingDetector
from types import SimpleNamespace
from unittest.mock import Mock
import numpy as np
from edge_ai.processing.annotations import filter_detections


class AnnotationTests(unittest.TestCase):
    def test_dashboard_region_and_accident_threshold(self):
        detections = [
            {
                "label": "zebra_crossing",
                "bbox_xyxy": [0, 85, 100, 100],
                "confidence": 0.8,
            },
            {"label": "waterlogging", "bbox_xyxy": [0, 30, 50, 60], "confidence": 0.3},
            {
                "label": "accident_candidate",
                "bbox_xyxy": [0, 10, 30, 40],
                "confidence": 0.4,
            },
        ]
        self.assertEqual(
            [d["label"] for d in filter_detections(detections, 100, 0.7)],
            ["waterlogging"],
        )
        self.assertEqual(len(detections), 3)
        with self.assertRaises(ValueError):
            filter_detections([], 100, 0)


def tracks(y=20, dx=0):
    return [
        {"track_id": i, "bbox_xyxy": [i * 15 + dx, y, i * 15 + dx + 10, y + 20]}
        for i in range(5)
    ]


class TrafficTests(unittest.TestCase):
    def test_queue_requires_persistent_measured_tracks(self):
        detector = TrafficAnalytics(duration=2)
        self.assertFalse(
            detector.update(tracks(), 0, 200, 200)["zones"]["road"][
                "congestion_candidate"
            ]
        )
        for t in [0.5, 1, 1.5, 2]:
            self.assertFalse(
                detector.update(tracks(), t, 200, 200)["zones"]["road"][
                    "congestion_candidate"
                ]
            )
        self.assertTrue(
            detector.update(tracks(), 2.5, 200, 200)["zones"]["road"][
                "congestion_candidate"
            ]
        )
        self.assertFalse(
            detector.update([], 3, 200, 200)["zones"]["road"]["congestion_candidate"]
        )

    def test_moving_vehicles_are_not_queue(self):
        detector = TrafficAnalytics(duration=1)
        for i in range(10):
            state = detector.update(tracks(dx=i * 10), i * 0.5, 300, 200)
            self.assertFalse(state["zones"]["road"]["congestion_candidate"])

    def test_bottleneck_needs_downstream_flow(self):
        detector = TrafficAnalytics(
            {"upstream": [0, 0, 1, 0.5], "downstream": [0, 0.5, 1, 1]}, duration=1
        )
        for i in range(6):
            data = tracks() + [
                {"track_id": 9, "bbox_xyxy": [i * 10, 120, i * 10 + 10, 140]}
            ]
            state = detector.update(data, i * 0.5, 200, 200)
        self.assertTrue(state["bottleneck_candidate"])
        state = detector.update(tracks(), 3, 200, 200)
        self.assertFalse(state["bottleneck_candidate"])

    def test_gap_and_bad_zones(self):
        detector = TrafficAnalytics(duration=1)
        detector.update(tracks(), 0, 200, 200)
        state = detector.update(tracks(), 10, 200, 200)
        self.assertEqual(state["zones"]["road"]["measured_tracks"], 0)
        with self.assertRaises(ValueError):
            detector.update([], 10, 200, 200)
        with self.assertRaises(ValueError):
            TrafficAnalytics({"road": [0.5, 0, 0.2, 1]})


class RiderTests(unittest.TestCase):
    def model(self):
        coordinates = Mock()
        coordinates.cpu.return_value.numpy.return_value = np.array(
            [[40, 30, 55, 100], [55, 30, 70, 100], [70, 30, 85, 100]]
        )
        return Mock(
            return_value=[SimpleNamespace(boxes=SimpleNamespace(xyxy=coordinates))]
        )

    def test_people_are_not_counted_for_two_motorcycles(self):
        detector = TripleRidingDetector()
        found = detector.detect(
            self.model(),
            None,
            [((30, 80, 90, 140), 1), ((40, 80, 100, 140), 2)],
            200,
            200,
        )
        self.assertEqual(sum(d["rider_count"] for d in found.values()), 3)
        self.assertFalse(any(d["confirmed"] for d in found.values()))

    def test_confirmation_and_disappearance_reset(self):
        detector = TripleRidingDetector()
        model = self.model()
        bikes = [((30, 80, 90, 140), 1)]
        for _ in range(4):
            self.assertFalse(
                detector.detect(model, None, bikes, 200, 200)[1]["confirmed"]
            )
        self.assertTrue(detector.detect(model, None, bikes, 200, 200)[1]["confirmed"])
        detector.detect(model, None, [], 200, 200)
        self.assertFalse(detector.detect(model, None, bikes, 200, 200)[1]["confirmed"])


class DatasetTests(unittest.TestCase):
    def test_valid_data_and_leakage_and_invalid_boxes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for i, split in enumerate(["train", "val", "test"]):
                (root / split / "images").mkdir(parents=True)
                (root / split / "labels").mkdir()
                Image.new("RGB", (20, 20), (i * 50, 20, 0)).save(
                    root / split / "images/a.png"
                )
                (root / split / "labels/a.txt").write_text("0 .5 .5 .2 .2\n")
            path = root / "data.yaml"
            path.write_text(
                yaml.safe_dump(
                    {
                        "names": {0: "sign"},
                        **{s: f"{s}/images" for s in ["train", "val", "test"]},
                    }
                )
            )
            _, counts = validate(path)
            self.assertEqual(counts["test"]["boxes"], 1)
            (root / "test/labels/a.txt").write_text("0 nan .5 .2 .2")
            with self.assertRaises(ValueError):
                validate(path)
            (root / "test/labels/a.txt").write_text("0 .5 .5 .2 .2")
            (root / "test/images/a.png").write_bytes(
                (root / "train/images/a.png").read_bytes()
            )
            with self.assertRaises(ValueError):
                validate(path)


if __name__ == "__main__":
    unittest.main()
