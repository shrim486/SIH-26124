"""Video metadata and explicit camera lifetime management."""
import cv2

def video_info(path):
    capture = cv2.VideoCapture(str(path))
    try:
        info = {
            "fps": capture.get(cv2.CAP_PROP_FPS),
            "frames": int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
            "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        }
        if not capture.isOpened() or min(info.values()) <= 0:
            raise ValueError(f"Cannot read video metadata: {path}")
        info["duration_seconds"] = info["frames"] / info["fps"]
        return info
    finally:
        capture.release()


class CameraManager:
    def __init__(self, source):
        self.source = source
        self.capture = None

    def __enter__(self):
        self.capture = cv2.VideoCapture(self.source)
        if not self.capture.isOpened():
            self.capture.release()
            raise OSError(f"Cannot open camera/video: {self.source}")
        return self

    def __iter__(self):
        if self.capture is None:
            raise RuntimeError("Use CameraManager as a context manager")
        while True:
            ok, frame = self.capture.read()
            if not ok:
                break
            yield frame

    def __exit__(self, *args):
        self.capture.release()
