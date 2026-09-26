from ultralytics import YOLO


class WaterloggingDetector:

    def __init__(self, model_path=r"C:\Users\ADMIN\Downloads\edge-ai\models\best.pt", confidence_threshold=0.25):
        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold

    def detect(self, frame):

        results = self.model(
            frame,
            conf=self.confidence_threshold,
            verbose=False
        )

        detections = []

        for result in results:

            boxes = result.boxes

            for box in boxes:

                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0]
                )

                class_name = self.model.names[class_id]

                if class_name == "water_logging":

                    detections.append({
                        "event_type": "waterlogging",
                        "confidence": round(confidence, 2),
                        "bbox": [x1, y1, x2, y2]
                    })

        return detections


if __name__ == "__main__":

    detector = WaterloggingDetector()

    print("Detector loaded successfully.")
    print("Model classes:", detector.model.names)
    print("Confidence threshold:", detector.confidence_threshold)
