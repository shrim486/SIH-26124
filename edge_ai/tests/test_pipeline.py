"""Regression checks for dataset correctness and detection serialization."""
import argparse
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import torch
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from edge_ai.config.config import probability, validate_names
from edge_ai.training.check_dataset import check_dataset
from edge_ai.processing.inference_manager import detection_record, resolve_source
from edge_ai.training.import_dataset import import_dataset


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for i, split in enumerate(("train", "val", "test")):
            (self.root / split / "images").mkdir(parents=True)
            (self.root / split / "labels").mkdir()
            Image.new("RGB", (32, 24), (i * 50, 70, 90)).save(self.root / split / "images" / "road.png")
            (self.root / split / "labels" / "road.txt").write_text("0 0.5 0.5 0.2 0.2\n")
        self.config = self.root / "data.yaml"
        self.config.write_text(yaml.safe_dump({"train": "train/images", "val": "val/images",
                                             "test": "test/images", "nc": 1, "names": ["pothole"]}))

    def errors(self):
        return check_dataset(self.config)[1]["errors"]

    def test_yaml_controls_val_directory(self):
        config, report = check_dataset(self.config)
        self.assertEqual([], report["errors"])
        self.assertEqual(str(self.root / "val" / "images"), config["val"])

    def test_bad_boxes_fail(self):
        for label in ("1 0.5 0.5 0.2 0.2", "0 nan 0.5 0.2 0.2", "0 0.5 0.5 0 0.2",
                      "0 0.99 0.5 0.4 0.2", "0 0.5 0.5", "0.0 0.5 0.5 0.2 0.2"):
            with self.subTest(label=label):
                (self.root / "train/labels/road.txt").write_text(label)
                self.assertTrue(self.errors())

    def test_missing_label_requires_review(self):
        (self.root / "train/labels/road.txt").unlink()
        self.assertTrue(any("Missing label" in error for error in self.errors()))

    def test_explicit_negative_image_is_accepted(self):
        Image.new("RGB", (32, 24), (240, 240, 240)).save(self.root / "train/images/negative.png")
        (self.root / "train/labels/negative.txt").write_text("")
        _, report = check_dataset(self.config)
        self.assertEqual([], report["errors"])
        self.assertEqual(1, report["splits"]["train"]["negative_images"])

    def test_split_leakage_fails(self):
        shutil.copy2(self.root / "train/images/road.png", self.root / "test/images/road.png")
        self.assertTrue(any("Split leakage" in error for error in self.errors()))

    def test_orphan_annotation_fails(self):
        (self.root / "train/labels/orphan.txt").write_text("0 0.5 0.5 0.2 0.2")
        self.assertTrue(any("Orphan" in error for error in self.errors()))

    def test_corrupt_image_fails(self):
        (self.root / "train/images/road.png").write_bytes(b"not an image")
        self.assertTrue(any("Unreadable" in error for error in self.errors()))

    def test_missing_test_split_fails(self):
        config = yaml.safe_load(self.config.read_text())
        del config["test"]
        self.config.write_text(yaml.safe_dump(config))
        self.assertTrue(any("Missing test" in error for error in self.errors()))

    def test_zip_import_preserves_class_and_split(self):
        archive = self.root / "fixture.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            for path in self.root.rglob("*"):
                if path.is_file() and path != archive:
                    bundle.write(path, str(Path("export") / path.relative_to(self.root)))
        destination = self.root / "imported"
        destination.mkdir()
        with patch("edge_ai.training.import_dataset.BASE_DIR", destination):
            import_dataset(archive)
            with self.assertRaises(ValueError):
                import_dataset(archive)  # Do not merge exports into an existing dataset.
        _, report = check_dataset(destination / "dataset/data.yaml")
        self.assertEqual([], report["errors"])
        self.assertTrue((destination / "dataset/data.original.yaml").is_file())

    def test_zip_traversal_rejected(self):
        archive = self.root / "unsafe.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("../escaped.txt", "bad")
        destination = self.root / "imported"
        destination.mkdir()
        with patch("edge_ai.training.import_dataset.BASE_DIR", destination):
            with self.assertRaisesRegex(ValueError, "Unsafe path"):
                import_dataset(archive)
        self.assertFalse((destination / "escaped.txt").exists())


class PredictionTests(unittest.TestCase):
    def test_pixel_coordinates_and_confidence(self):
        boxes = SimpleNamespace(xyxy=torch.tensor([[12., 24., 40., 50.]]),
                                conf=torch.tensor([0.75]), cls=torch.tensor([0.]))
        result = SimpleNamespace(path="road.jpg", orig_shape=(80, 100), boxes=boxes, names={0: "pothole"})
        record = detection_record(result, 3)
        self.assertEqual([12., 24., 40., 50.], record["detections"][0]["bbox_xyxy"])
        self.assertEqual(0.75, record["detections"][0]["confidence"])
        self.assertEqual(3, record["sequence_index"])
        self.assertEqual({"height": 80, "width": 100}, record["image_size"])

    def test_no_detection_frame_is_preserved(self):
        result = SimpleNamespace(path="road.jpg", orig_shape=(80, 100), boxes=None)
        self.assertEqual([], detection_record(result, 0)["detections"])

    def test_webcam_mapping(self):
        self.assertEqual(0, resolve_source("webcam"))
        self.assertEqual(2, resolve_source("2"))

    def test_invalid_threshold_fails(self):
        for value in ("nan", "inf", "-0.1", "1.1"):
            with self.assertRaises(argparse.ArgumentTypeError):
                probability(value)

    def test_wrong_classes_are_rejected(self):
        for names in (["person"], {0: "pothole", 1: "damage"}, {1: "pothole"}):
            with self.assertRaises(ValueError):
                validate_names(names)
        self.assertEqual({0: "potholes"}, validate_names(["potholes"]))


if __name__ == "__main__":
    unittest.main()
