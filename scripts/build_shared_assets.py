"""Build versioned public-source asset bundles; never package credentials or the database."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import zipfile

from asset_bundle import asset_path, digest

ROOT = Path(__file__).resolve().parents[1]


def portable(value):
    if isinstance(value, dict):
        return {key: portable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [portable(item) for item in value]
    if isinstance(value, str):
        normalized = value.replace('\\', '/')
        if normalized.startswith(ROOT.as_posix() + '/'):
            return normalized[len(ROOT.as_posix()) + 1:]
        if re.match(r'^[A-Za-z]:/', normalized) or normalized.startswith('/Users/') or normalized.startswith('/home/'):
            return normalized.rsplit('/', 1)[-1]
    return value


def seed_records():
    runs = {hashlib.sha256(folder.name.encode()).hexdigest()[:24]: folder.name
            for folder in (ROOT / 'edge_ai/outputs').iterdir() if folder.is_dir()}
    with sqlite3.connect((ROOT / 'backend/app.db').as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute('''SELECT e.*, i.run_id, i.segment_id FROM events e
            JOIN analysis_incidents i ON i.event_id=e.id
            JOIN alert_events ae ON ae.event_id=e.id JOIN alerts a ON a.id=ae.alert_id
            WHERE e.status NOT IN ('resolved','closed') AND (a.expires_at IS NULL OR a.expires_at > CURRENT_TIMESTAMP)
            ORDER BY e.id''').fetchall()
    result = []
    for row in rows:
        metadata = json.loads(row['event_metadata'] or '{}')
        if not metadata.get('is_demo'):
            raise ValueError('Only assigned public-footage records may be exported by this script')
        result.append(dict(run=runs[row['run_id']], segment_id=row['segment_id'],
                           latitude=row['latitude'], longitude=row['longitude'],
                           occurred_at=row['timestamp'].replace(' ', 'T') + '+00:00',
                           location_name=f'{row["latitude"]:.6f}, {row["longitude"]:.6f}',
                           description=metadata.get('description', ''), demo=True))
    return json.dumps({'schema': 1, 'incidents': result}, indent=2).encode()


def make_bundle(name, paths, output, extra=None):
    archive_path = output / f'urban-iq-{name}.zip'
    entries = []
    with zipfile.ZipFile(archive_path, 'x', compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for path in sorted(paths):
            relative = path.relative_to(ROOT).as_posix()
            asset_path(ROOT, relative)
            if path.suffix == '.json':
                raw = json.dumps(portable(json.loads(path.read_text(encoding='utf-8'))), indent=2).encode()
                archive.writestr(relative, raw, compress_type=zipfile.ZIP_DEFLATED)
                entries.append(dict(path=relative, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
            else:
                archive.write(path, relative, compress_type=zipfile.ZIP_DEFLATED if path.suffix == '.jsonl' else zipfile.ZIP_STORED)
                entries.append(dict(path=relative, bytes=path.stat().st_size, sha256=digest(path)))
        for relative, raw in (extra or {}).items():
            asset_path(ROOT, relative)
            archive.writestr(relative, raw)
            entries.append(dict(path=relative, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
        archive.writestr('manifest.json', json.dumps({'schema': 1, 'files': entries}, indent=2))
    return dict(name=archive_path.name, bytes=archive_path.stat().st_size, sha256=digest(archive_path), files=len(entries))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9._-]+', args.tag):
        parser.error('Use a plain release tag')
    output = ROOT / '.runtime/releases' / args.tag
    output.mkdir(parents=True, exist_ok=True)
    # All public-source completed examples; uploaded private video-analysis jobs are excluded.
    runs = [folder for folder in (ROOT / 'edge_ai/outputs').iterdir()
            if folder.is_dir() and folder.name != 'video_analysis']
    media = {path for folder in runs for path in folder.rglob('*')
             if path.is_file() and path.suffix in {'.mp4', '.jpg', '.png', '.json', '.jsonl'}}
    clips = set((ROOT / 'edge_ai/test_videos/multi_demo').glob('*_clip.mp4'))
    clips.update((ROOT / 'edge_ai/test_videos/dashcam').glob('*.mp4'))
    media.update(clips)
    originals = {path for base in ('multi_demo', 'damaged_road')
                 for path in (ROOT / 'edge_ai/test_videos' / base).glob('*.mp4')} - clips
    models = {path for path in (ROOT / 'edge_ai/models').rglob('*')
              if path.is_file() and path.suffix in {'.pt', '.onnx', '.yaml', '.json'}
              and not any(part.startswith('.') for part in path.relative_to(ROOT).parts)}
    # Tracked configs are already in the clone (and Git may normalize line endings).
    tracked = subprocess.check_output(['git', 'ls-files', '-z', 'edge_ai/models'], cwd=ROOT).decode().split('\0')
    models.difference_update(ROOT / name for name in tracked if name)
    bundles = {}
    for name, paths in [('portal', media), ('models', models), ('originals', originals)]:
        entry = make_bundle(name, paths, output, {'.runtime/portal-seed.json': seed_records()} if name == 'portal' else None)
        entry['url'] = f'https://github.com/shrim486/SIH-26124/releases/download/{args.tag}/{entry["name"]}'
        bundles[name] = entry
        print(f'{name}: {entry["files"]} files, {entry["bytes"] / 1024**2:.1f} MiB', flush=True)
    result = dict(schema=1, tag=args.tag, repository='shrim486/SIH-26124',
                  created_at=datetime.now(timezone.utc).isoformat(), bundles=bundles)
    (ROOT / 'docs/release-assets.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f'Prepared {output}')


if __name__ == '__main__':
    main()
