# Triple-riding detection

This module applies conservative triple-riding detection to motorcycle tracks. It uses the same YOLO vehicle model as the motorcycle and helmet pipeline, associates person boxes inside a strict rider corridor, and requires at least 5 positive frames in the last 8 frames before raising an alert.

The detector is merged into the Video Analysis workflow. It draws cyan associated-person boxes and a red `POSSIBLE TRIPLE RIDING` alert on the same annotated output as motorcycle and helmet detections.
