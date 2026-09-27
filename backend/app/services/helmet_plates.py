"""Conservative same-frame motorcycle/helmet/plate associations from saved ML.

Never associate a plate merely because it occurs in the same video. Ambiguous
overlapping motorcycle boxes are rejected. OCR remains an unverified candidate.
"""
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re


def box(value):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        x1, y1, x2, y2 = map(float, value)
        if all(math.isfinite(v) for v in (x1, y1, x2, y2)) and x2 > x1 and y2 > y1:
            return x1, y1, x2, y2
    except (ValueError, TypeError):
        pass
    return None


def contains_plate(bike, plate):
    x1, y1, x2, y2 = bike
    a, b, c, d = plate
    cx, cy = (a + c) / 2, (b + d) / 2
    overlap = max(0, min(x2, c) - max(x1, a)) * max(0, min(y2, d) - max(y1, b))
    return x1 <= cx <= x2 and y1 <= cy <= y2 and overlap / ((c - a) * (d - b)) >= .8


def associate_rows(rows, start=0, end=float('inf')):
    matched = defaultdict(list)
    for row in rows:
        timestamp = row.get('timestamp_seconds', -1)
        if not start <= timestamp <= end:
            continue
        detections = row.get('detections', [])
        heads = {d.get('track_id'): d for d in detections
                 if d.get('label') == 'without_helmet' and d.get('track_id') is not None
                 and (d.get('confidence') or 0) >= .5 and box(d.get('bbox_xyxy'))}
        bikes = [(d, box(d.get('bbox_xyxy'))) for d in detections
                 if d.get('label') == 'motorcycle' and d.get('track_id') is not None]
        bikes = [(d, bounds) for d, bounds in bikes if bounds]
        for plate in detections:
            bounds = box(plate.get('bbox_xyxy'))
            if plate.get('label') != 'number_plate' or (plate.get('confidence') or 0) < .4 or not bounds:
                continue
            owners = [d for d, bike_box in bikes if contains_plate(bike_box, bounds)]
            if len(owners) != 1 or owners[0]['track_id'] not in heads:
                continue
            identity = owners[0]['track_id']
            head = heads[identity]
            head_box = box(head['bbox_xyxy'])
            # The associated head must be above this plate, within the bike's horizontal extent.
            bike_box = box(owners[0]['bbox_xyxy'])
            hx, hy = (head_box[0] + head_box[2]) / 2, (head_box[1] + head_box[3]) / 2
            if not bike_box[0] <= hx <= bike_box[2] or hy >= bounds[1]:
                continue
            text = re.sub('[^A-Z0-9]', '', str(plate.get('text') or '').upper())
            if not 6 <= len(text) <= 12:
                text = ''
            score = float(plate.get('ocr_confidence') or 0)
            if not math.isfinite(score) or not 0 <= score <= 1:
                score = 0
            matched[identity].append({
                'frame_index': row['frame_index'], 'time_seconds': timestamp,
                'plate_text': text or None, 'ocr_confidence': score,
                'plate_bbox': list(bounds), 'helmet_bbox': head['bbox_xyxy'],
            })
    results = []
    for identity, observations in matched.items():
        readings = [r for r in observations if r['plate_text'] and r['ocr_confidence'] >= .8]
        votes = Counter((r['plate_text'], r['frame_index']) for r in readings)
        counts = Counter(text for text, _ in votes)
        text = counts.most_common(1)[0][0] if counts else None
        candidates = [r for r in readings if r['plate_text'] == text] if text else observations
        best = max(candidates, key=lambda r: r['ocr_confidence'])
        support = counts[text] if text else 0
        # Even repeated OCR is not an independently verified registration.
        consistent = support >= 3 and support / max(1, len({r['frame_index'] for r in readings})) >= .6
        results.append({**best, 'track_id': identity,
                        'plate_text': text if text else best['plate_text'],
                        'reading_status': 'repeated_ocr_candidate' if consistent else 'uncertain' if best['plate_text'] else 'unreadable',
                        'matching_frames': len({r['frame_index'] for r in observations}),
                        'text_support_frames': support,
                        'method': 'same_frame_unique_motorcycle_box',
                        'verified': False})
    return results[:10]


def helmet_plate_evidence(folder, segment):
    with (Path(folder) / 'detections.jsonl').open(encoding='utf-8') as handle:
        return associate_rows((json.loads(line) for line in handle),
                              segment['start_seconds'], segment['end_seconds'])
