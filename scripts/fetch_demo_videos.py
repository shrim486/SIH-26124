"""Download the pinned public demonstration videos and verify their recorded hashes."""
import argparse
import hashlib
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]


def main():
    sources = json.loads((ROOT / 'docs/multi-demo-sources.json').read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--videos', nargs='+', choices=[source['name'] for source in sources])
    args = parser.parse_args()
    for source in sources:
        if args.videos and source['name'] not in args.videos:
            continue
        target = (ROOT / source['path'].replace('\\', '/')).resolve()
        if not target.is_relative_to(ROOT / 'edge_ai/test_videos'):
            raise ValueError('Video target must remain inside edge_ai/test_videos')
        if not target.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix('.download')
            with requests.get(source.get('download_url', source['url']), stream=True, timeout=(15, 120)) as response:
                response.raise_for_status()
                with temporary.open('wb') as handle:
                    for block in response.iter_content(1024 * 1024):
                        handle.write(block)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != source['sha256']:
                raise ValueError(f"Source changed for {source['name']}; downloaded file retained for inspection")
            temporary.replace(target)
        if hashlib.sha256(target.read_bytes()).hexdigest() != source['sha256']:
            raise ValueError(f"Local video hash mismatch: {source['name']}")
        print('Verified', source['name'])


if __name__ == '__main__':
    main()
