import cv2


def read_video(source, frame_callback):
    """
    Read frames from either:
    - a video file path
    - a camera device index such as 0
    """

    if isinstance(source, int):
        print("Opening camera:", source)
        cap = cv2.VideoCapture(source)
    else:
        print("Opening video:", source)
        cap = cv2.VideoCapture(str(source))

    if not cap.isOpened():
        print("Error: Could not open source.")
        return

    frame_number = 0

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        frame_callback(frame, frame_number)
        frame_number += 1

    cap.release()

    print("Source finished.")
    print("Total frames processed:", frame_number)


if __name__ == "__main__":

    source = "videos/waterlogging.mp4"

    def process_frame(frame, frame_number):
        print("Reading frame:", frame_number)

    read_video(source, process_frame)
