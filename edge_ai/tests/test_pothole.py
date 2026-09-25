"""Check coordinate recovery and class filtering without downloading weights."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from edge_ai.detectors.road_hazards.pothole_detector import RoadDetector


class StubSession:
    def run(self, _, inputs):
        assert inputs["images"].shape == (1, 3, 640, 640)
        # A pothole and a manhole. Coordinates are in a letterboxed 640x640 input.
        return [np.array([[[320, 160], [320, 320], [320, 160], [160, 160],
                           [0.8, 0.1], [0.1, 0.9]]], dtype=np.float32)]


class DashcamTests(unittest.TestCase):
    def test_letterbox_offset_and_manhole_filter(self):
        detector = RoadDetector.__new__(RoadDetector)
        detector.session = StubSession()
        detector.input = SimpleNamespace(name="images")
        detector.size = 640
        detector.names = {0: "pothole", 1: "manhole"}
        detector.classes = [0]
        detector.confidence = 0.25
        boxes, confidence = detector.crop_predict(np.zeros((200, 400, 3), np.uint8), (50, 200))
        np.testing.assert_allclose(boxes, [[150, 250, 350, 350]], atol=0.001)
        np.testing.assert_allclose(confidence, [0.8], atol=0.001)

    def test_overlapping_views_remove_contained_fragment(self):
        detector = RoadDetector.__new__(RoadDetector)
        detector.top, detector.bottom, detector.confidence = 0.16, 0.73, 0.25
        outputs = iter([
            (np.array([[100, 200, 400, 400]], dtype=float), np.array([0.8])),
            (np.array([[150, 250, 180, 280]], dtype=float), np.array([0.9])),
            (np.array([[700, 300, 800, 400]], dtype=float), np.array([0.7])),
        ])
        detector.crop_predict = lambda image, offset: next(outputs)
        detections = detector.predict(np.zeros((720, 1280, 3), np.uint8))
        self.assertEqual(2, len(detections))
        self.assertEqual([100, 200, 400, 400], detections[0]["bbox_xyxy"])
        self.assertEqual([700, 300, 800, 400], detections[1]["bbox_xyxy"])


if __name__ == "__main__":
    unittest.main()
