"""Run the existing car-dashcam pothole pipeline: python -m edge_ai.main."""
import argparse
from edge_ai.config.config import probability, project_path
from edge_ai.processing.frame_processor import run

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--weights", default="models/road_hazards/pothole/best.onnx")
    parser.add_argument("--output", default="outputs/dashcam_potholes")
    parser.add_argument("--conf", type=probability, default=0.25)
    parser.add_argument("--road-top", type=probability, default=0.16)
    parser.add_argument("--road-bottom", type=probability, default=0.73)
    args = parser.parse_args()
    run(project_path(args.source), project_path(args.weights), project_path(args.output),
        args.conf, args.road_top, args.road_bottom)


if __name__ == "__main__":
    main()
