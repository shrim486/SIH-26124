"""Run downloaded public clips through selected local models. No fabricated predictions."""
import concurrent.futures
import json
from pathlib import Path
import subprocess
import sys

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
PLANS = {
    'slow_riders': (['helmet', 'number_plate'], 'dashcam', 0, 16, None),
    'video1': (['road_divider', 'zebra_crossing', 'number_plate'], 'fixed', 0, 5, None),
    'video2': (['congestion', 'bottleneck'], 'fixed', 0, 30,
               {'upstream': [.35, 0, .6, .7], 'downstream': [.4, .7, .7, 1]}),
    'waterlogging': (['waterlogging'], 'handheld', 0, 6, None),
    'triple_riders': (['helmet', 'triple_riding'], 'handheld', 5, 6, None),
    'queue': (['congestion', 'bottleneck'], 'fixed', 10, 18,
              {'upstream': [0, .15, 1, .65], 'downstream': [0, .65, 1, 1]}),
    'traffic_sign': (['traffic_sign', 'road_divider'], 'dashcam', 0, 2, None),
    'crosswalk': (['zebra_crossing'], 'handheld', 1, 5, None),
    'motorcycles': (['helmet', 'triple_riding', 'number_plate'], 'handheld', 0, 4, None),
    'traffic': (['congestion', 'bottleneck'], 'fixed', 0, 20,
                {'upstream': [.35, .35, .95, .7], 'downstream': [0, .7, 1, 1]}),
    'highway': (['road_divider', 'congestion', 'bottleneck'], 'fixed', 0, 10,
                {'upstream': [.35, .25, .52, .5], 'downstream': [0, .5, .5, 1]}),
}


def process(source):
    name = source['name']
    if name not in PLANS:
        return
    tasks, camera, start, duration, zones = PLANS[name]
    dimension = int(source.get('max_dimension', 1280))
    output = ROOT / 'edge_ai/outputs' / ('demo_' + name)
    if (output / 'summary.json').exists():
        print(name, 'already completed', flush=True)
        return
    clip = ROOT / 'edge_ai/test_videos/multi_demo' / (name + '_clip.mp4')
    if not clip.exists():
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error',
                        '-ss', str(start), '-i', str(ROOT / source['path']), '-t', str(duration),
                        '-vf', f"scale={dimension}:{dimension}:force_original_aspect_ratio=decrease:force_divisible_by=2,fps=12",
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-an', '-movflags', '+faststart', str(clip)], check=True)
    command = [sys.executable, '-u', '-m', 'edge_ai.suite', '--source', str(clip),
               '--output', str(output), '--camera', camera, '--tasks', *tasks]
    if zones:
        zone_path = clip.with_suffix('.zones.json')
        zone_path.write_text(json.dumps(zones))
        command.extend(['--zones', str(zone_path)])
    log = ROOT / '.runtime' / ('demo_' + name + '.log')
    print('Processing', name, tasks, flush=True)
    with log.open('w') as handle:
        subprocess.run(command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT, check=True)
    summary_path = output / 'summary.json'
    summary = json.loads(summary_path.read_text())
    summary['camera'] = camera
    summary['source_info'] = {**source, 'clip_start_seconds': start, 'clip_max_duration_seconds': duration,
                              'preparation': f'Excerpt resized to fit {dimension} pixels and resampled at 12 FPS; playback time preserved.',
                              'location_note': 'Bengaluru map placement is simulated; original location and time are unknown.'}
    summary_path.write_text(json.dumps(summary, indent=2))
    subprocess.run([sys.executable, '-m', 'edge_ai.processing.export_frames', '--run', str(output)], cwd=ROOT, check=True)
    print('Completed', name, flush=True)


if __name__ == '__main__':
    sources = json.loads((ROOT / 'docs/multi-demo-sources.json').read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        for result in executor.map(process, sources):
            pass
