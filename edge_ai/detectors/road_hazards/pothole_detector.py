"""Learned pothole predictions on overlapping forward-facing road crops."""
import ast
import cv2
import numpy as np
import onnxruntime as ort

class RoadDetector:
    def __init__(self, weights, confidence=0.25, top=0.16, bottom=0.73):
        if not 0 <= top < bottom <= 1:
            raise ValueError("Require 0 <= road-top < road-bottom <= 1")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(weights), sess_options=options,
                                           providers=["CPUExecutionProvider"])
        self.input = self.session.get_inputs()[0]
        self.size = self.input.shape[-1]
        metadata = self.session.get_modelmeta().custom_metadata_map
        self.names = ast.literal_eval(metadata["names"])
        self.classes = [k for k, v in self.names.items() if v.lower() in {"pothole", "potholes"}]
        if not self.classes:
            raise ValueError("Model has no explicitly named pothole class")
        self.confidence, self.top, self.bottom = confidence, top, bottom

    def crop_predict(self, image, offset=(0, 0)):
        height, width = image.shape[:2]
        ratio = min(self.size / width, self.size / height)
        new_width, new_height = round(width * ratio), round(height * ratio)
        left, top = (self.size - new_width) // 2, (self.size - new_height) // 2
        canvas = np.full((self.size, self.size, 3), 114, dtype=np.uint8)
        canvas[top:top + new_height, left:left + new_width] = cv2.resize(image, (new_width, new_height))
        tensor = np.ascontiguousarray(canvas[:, :, ::-1].transpose(2, 0, 1)[None], dtype=np.float32) / 255
        # YOLOv8/11 raw output: xywh, class scores, optional mask coefficients.
        prediction = self.session.run(None, {self.input.name: tensor})[0][0].T
        scores = prediction[:, 4:4 + len(self.names)]
        classes = scores.argmax(axis=1)
        confidence = scores.max(axis=1)
        keep = (confidence >= self.confidence) & np.isin(classes, self.classes)
        prediction, confidence = prediction[keep], confidence[keep]
        boxes = prediction[:, :4].copy()
        boxes[:, :2] -= boxes[:, 2:] / 2
        boxes[:, 2:] += boxes[:, :2]
        boxes[:, [0, 2]] = np.clip((boxes[:, [0, 2]] - left) / ratio, 0, width) + offset[0]
        boxes[:, [1, 3]] = np.clip((boxes[:, [1, 3]] - top) / ratio, 0, height) + offset[1]
        return boxes, confidence

    def predict(self, frame):
        height, width = frame.shape[:2]
        top, bottom = int(height * self.top), int(height * self.bottom)
        # Wide crops keep large potholes intact; a narrower central view helps small ones.
        tile_width = round(width * 0.65)
        boxes, scores = [], []
        views = [(0, tile_width), (width - tile_width, width), (width // 4, 3 * width // 4)]
        for x, right in views:
            b, s = self.crop_predict(frame[top:bottom, x:right], (x, top))
            boxes.extend(b.tolist())
            scores.extend(s.tolist())
        if not boxes:
            return []
        xywh = [[x1, y1, x2 - x1, y2 - y1] for x1, y1, x2, y2 in boxes]
        selected = cv2.dnn.NMSBoxes(xywh, scores, self.confidence, 0.4)
        # Suppress near-contained duplicates produced at overlapping tile edges.
        accepted = []
        for i in sorted(np.asarray(selected).reshape(-1), key=lambda j: xywh[j][2] * xywh[j][3], reverse=True):
            if min(xywh[i][2:]) <= 1:
                continue
            a = boxes[i]
            duplicate = False
            for j in accepted:
                b = boxes[j]
                intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
                if intersection / min(xywh[i][2] * xywh[i][3], xywh[j][2] * xywh[j][3]) >= 0.85:
                    duplicate = True
                    break
            if not duplicate:
                accepted.append(i)
        return [{"class_name": "pothole", "confidence": float(scores[i]), "bbox_xyxy": boxes[i]} for i in accepted]


PotholeDetector = RoadDetector
