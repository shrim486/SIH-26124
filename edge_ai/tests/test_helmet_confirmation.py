from collections import defaultdict, deque
from unittest.mock import Mock

import numpy as np

from edge_ai.models.motorcycle_helmet.detect import classify_motorcycle


def test_helmet_analysis_includes_plates_without_duplicating_models():
    from edge_ai.suite import expand_tasks
    assert expand_tasks(['helmet']) == ['helmet', 'number_plate']
    assert expand_tasks(['number_plate', 'helmet', 'helmet']) == ['number_plate', 'helmet']
    assert expand_tasks(['pothole']) == ['pothole']


def test_helmet_history_cannot_relabel_current_head():
    model = Mock()
    model.predict.return_value = {"predictions": [{
        "class": "with_helmet", "confidence": .9,
        "x": 30, "y": 20, "width": 15, "height": 15,
    }]}
    history = defaultdict(lambda: deque(maxlen=5))
    history[7].extend(["without", "without", "without"])
    args = (model, np.zeros((160, 120, 3), dtype=np.uint8), 120, 160,
            (30, 80, 90, 140), .5, history, 7)
    # A current helmet box must not be labelled "without" by old votes.
    assert classify_motorcycle(*args) is None
    assert classify_motorcycle(*args) is None
    confirmed = classify_motorcycle(*args)
    assert confirmed["status"] == "with"
    assert confirmed["confidence"] == .9


def test_independent_riders_confirm_both_helmet_classes():
    model = Mock()
    history = defaultdict(lambda: deque(maxlen=5))
    frame = np.zeros((160, 120, 3), dtype=np.uint8)
    for identity, status in [(1, "with"), (2, "without")]:
        model.predict.return_value = {"predictions": [{
            "class": status + "_helmet", "confidence": .85,
            "x": 30, "y": 20, "width": 15, "height": 15,
        }]}
        args = (model, frame, 120, 160, (30, 80, 90, 140), .5, history, identity)
        assert classify_motorcycle(*args) is None
        assert classify_motorcycle(*args) is None
        assert classify_motorcycle(*args)["status"] == status
