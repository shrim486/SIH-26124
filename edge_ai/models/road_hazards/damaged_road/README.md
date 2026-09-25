# Damaged-road model

Place the trained checkpoint here as `best.pt` after training. This model is
separate from `road_hazards/pothole/` and detects cracks, alligator damage, and
potholes as distinct classes.

The current `best.pt` is a public RDD2022 checkpoint. Model 2 filters it to
D00 longitudinal cracks, D10 transverse cracks, and D20 alligator cracks;
D40 potholes and `Repair` predictions are excluded. Replace it with a locally
trained checkpoint after adding labeled local dashcam data.
