import json

from app.services.analysis_evidence import detection_segments


def test_evidence_includes_rare_helmet_class_and_counts_actual_frames(tmp_path):
    rows = []
    for index in range(21):
        labels = ["without_helmet"]
        if index == 7:  # Not one of the five evenly spaced preview frames.
            labels.append("with_helmet")
        rows.append({"frame_index": index, "timestamp_seconds": index / 12,
                     "detections": [{"label": label, "confidence": .9} for label in labels]})
    (tmp_path / "detections.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    segment, = detection_segments(tmp_path)
    assert segment["label_frame_counts"] == {"without_helmet": 21, "with_helmet": 1}
    assert segment["detected_labels"] == ["with_helmet", "without_helmet"]
    assert len(segment["frames"]) == 5
    assert 7 in [frame["frame_index"] for frame in segment["frames"]]
    assert {label for frame in segment["frames"] for label in frame["labels"]} == {"with_helmet", "without_helmet"}
