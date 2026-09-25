"""Verify the exact locally tested model/video assets without downloading files."""
import hashlib
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    failures = 0
    for asset in json.loads((root / 'docs/assets.json').read_text(encoding='utf-8')):
        path = (root / asset['path']).resolve()
        path.relative_to(root)
        if not path.is_file():
            print(f'MISSING: {asset["path"]}')
            failures += 1
            continue
        digest = hashlib.sha256()
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(chunk)
        valid = path.stat().st_size == asset['bytes'] and digest.hexdigest() == asset['sha256']
        print(f'{"OK" if valid else "MISMATCH"}: {asset["path"]}')
        failures += not valid
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
