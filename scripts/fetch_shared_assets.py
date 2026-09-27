"""Download the exact saved videos/models for this source revision."""
import argparse
import json
from pathlib import Path
import sys
import time
from urllib.request import Request, urlopen

from asset_bundle import digest, install_bundle

ROOT = Path(__file__).resolve().parents[1]


def download(entry, cache):
    target = cache / entry['name']
    if target.is_file() and target.stat().st_size == entry['bytes'] and digest(target) == entry['sha256']:
        return target
    temporary = target.with_suffix('.download')
    for attempt in range(3):
        try:
            print(f'Downloading {entry["name"]} ({entry["bytes"] / 1024**2:.1f} MiB)...', flush=True)
            request = Request(entry['url'], headers={'User-Agent': 'UrbanIQ-AssetSetup/1.0'})
            with urlopen(request, timeout=90) as response, temporary.open('wb') as output:
                received = 0
                report_at = 50 * 1024**2
                while block := response.read(1024 * 1024):
                    output.write(block)
                    received += len(block)
                    if received > entry['bytes']:
                        raise ValueError('Download is larger than the pinned asset')
                    if received >= report_at:
                        print(f'  {received / 1024**2:.0f} MiB received', flush=True)
                        report_at += 50 * 1024**2
            if temporary.stat().st_size != entry['bytes'] or digest(temporary) != entry['sha256']:
                raise ValueError('Download checksum mismatch')
            temporary.replace(target)
            return target
        except (OSError, ValueError):
            temporary.unlink(missing_ok=True)
            if attempt == 2:
                raise
            time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', choices=['portal', 'models', 'originals', 'all'], default='portal')
    parser.add_argument('--from-dir', type=Path, help='Use already downloaded release ZIPs')
    parser.add_argument('--root', type=Path, default=ROOT, help='Installation directory (defaults to this checkout)')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'docs/release-assets.json').read_text(encoding='utf-8'))
    cache = args.root / '.runtime/downloads'
    cache.mkdir(parents=True, exist_ok=True)
    selected = manifest['bundles'].items() if args.bundle == 'all' else [(args.bundle, manifest['bundles'][args.bundle])]
    for name, entry in selected:
        archive = args.from_dir / entry['name'] if args.from_dir else download(entry, cache)
        result = install_bundle(archive, args.root, entry['sha256'])
        print(f'{name}: {result["files"]} verified files; {result["installed"]} installed, {result["unchanged"]} already present.')
    print('Media restored. To create map records in an empty database, run scripts/seed_portal.py with the project Python.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError) as exc:
        print(f'Asset setup failed: {exc}', file=sys.stderr)
        raise SystemExit(1)
