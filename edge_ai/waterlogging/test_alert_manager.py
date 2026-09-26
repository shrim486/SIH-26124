from alert_manager import AlertManager


manager = AlertManager(
    required_detections=2,
    cooldown_frames=3
)


def make_detection(confidence):
    return [{
        "event_type": "waterlogging",
        "confidence": confidence,
        "bbox": [100, 200, 500, 400]
    }]


print("Testing Alert Manager...")
print()


# Frame 1: confidence below threshold
result = manager.process_detection(make_detection(0.55))
print("Frame 1 (0.55):", result)


# Frame 2: valid detection
result = manager.process_detection(make_detection(0.73))
print("Frame 2 (0.73):", result)


# Frame 3: second valid detection
result = manager.process_detection(make_detection(0.82))
print("Frame 3 (0.82):", result)


# Cooldown test
print()
print("Testing cooldown...")

result = manager.process_detection(make_detection(0.90))
print("Cooldown frame 1:", result)

result = manager.process_detection(make_detection(0.90))
print("Cooldown frame 2:", result)

result = manager.process_detection(make_detection(0.90))
print("Cooldown frame 3:", result)

result = manager.process_detection(make_detection(0.90))
print("After cooldown:", result)