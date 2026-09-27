"""Local ONNX plate detection and OCR. No owner lookup or persistent plate tracking."""

from edge_ai.config.config import BASE_DIR


class NumberPlateDetector:
    def __init__(self, confidence=0.4):
        import onnxruntime as ort
        from fast_alpr import ALPR
        from fast_plate_ocr.inference import hub as ocr_hub
        from open_image_models.detection.core import hub as detection_hub

        cache = BASE_DIR / "models/number_plate"
        ocr_hub.MODEL_CACHE_DIR = cache / "ocr"
        # Both libraries expose a module cache directory; keep assets in this project.
        detection_hub.MODEL_CACHE_DIR = cache / "detection"
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        self.model = ALPR(
            detector_model="yolo-v9-t-384-license-plate-end2end",
            ocr_model="cct-xs-v2-global-model",
            detector_conf_thresh=confidence,
            detector_providers=["CPUExecutionProvider"],
            ocr_device="cpu",
            detector_sess_options=options,
            ocr_sess_options=options,
        )

    def predict(self, frame):
        detections = []
        for result in self.model.predict(frame):
            box = result.detection.bounding_box
            record = {
                "label": "number_plate",
                "confidence": float(result.detection.confidence),
                "bbox_xyxy": [
                    float(box.x1),
                    float(box.y1),
                    float(box.x2),
                    float(box.y2),
                ],
            }
            if result.ocr:
                confidence = result.ocr.confidence
                if not isinstance(confidence, (int, float)):
                    confidence = (
                        sum(confidence) / len(confidence) if len(confidence) else 0
                    )
                record.update(text=result.ocr.text, ocr_confidence=float(confidence))
            detections.append(record)
        return detections
