"""Run both installed models on the same car-dashcam clip and produce MP4s."""
import argparse
from datetime import datetime
from pathlib import Path
import subprocess
import sys

import imageio_ffmpeg


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='test_videos/dashcam/candidate.mp4',
                        help='Absolute path or path relative to edge_ai')
    args = parser.parse_args()
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    source = Path(args.source)
    if not source.is_absolute():
        source = root / 'edge_ai' / source
    if not source.is_file():
        parser.error(f'Video not found: {source}')
    subprocess.run([sys.executable, '-m', 'edge_ai.main', '--source', str(source),
                    '--output', f'outputs/potholes_{stamp}'], cwd=root, check=True)
    damage_name = f'damaged_road_{stamp}'
    subprocess.run([sys.executable, '-m', 'edge_ai.training.predict_damaged_road',
                    '--source', str(source), '--name', damage_name], cwd=root, check=True)
    folder = root / 'edge_ai' / 'outputs' / damage_name
    for video in folder.glob('*.avi'):
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-v', 'error',
                        '-i', str(video), '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                        '-movflags', '+faststart', str(video.with_suffix('.mp4'))], check=True)
    print(f'Pothole output: {root / "edge_ai/outputs" / ("potholes_" + stamp)}')
    print(f'Damaged-road output: {folder}')


if __name__ == '__main__':
    main()
