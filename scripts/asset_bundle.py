"""Verified, portable release archives. Never extract arbitrary ZIP paths."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
import zipfile


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def asset_path(root, name):
    if not isinstance(name, str):
        raise ValueError('Asset path must be a string')
    path = PurePosixPath(name)
    if ('\\' in name or ':' in name
            or path.is_absolute() or '..' in path.parts or str(path) != name):
        raise ValueError(f'Unsafe asset path: {name}')
    allowed = name == '.runtime/portal-seed.json'
    allowed |= name.startswith('edge_ai/outputs/') and path.suffix in {'.json', '.jsonl', '.mp4', '.jpg', '.png'}
    allowed |= name.startswith('edge_ai/test_videos/') and path.suffix in {'.mp4', '.jpg', '.png', '.json'}
    allowed |= name.startswith('edge_ai/models/') and path.suffix in {'.pt', '.onnx', '.yaml', '.json'}
    if not allowed or any(part.startswith('.') for part in path.parts if part != '.runtime'):
        raise ValueError(f'Not an allowed asset: {name}')
    target = root.joinpath(*path.parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Asset escapes destination: {name}')
    return target


def read_manifest(archive):
    if archive.getinfo('manifest.json').file_size > 8 * 1024 * 1024:
        raise ValueError('Asset manifest too large')
    raw = archive.read('manifest.json')
    manifest = json.loads(raw)
    if manifest.get('schema') != 1 or not isinstance(manifest.get('files'), list):
        raise ValueError('Unsupported asset manifest')
    entries = manifest['files']
    names = [row['path'] for row in entries]
    if len(names) != len(set(names)) or len(names) > 20000:
        raise ValueError('Duplicate or excessive asset paths')
    if sorted(archive.namelist()) != sorted(['manifest.json', *names]):
        raise ValueError('Archive members do not match manifest')
    for row in entries:
        if not re.fullmatch('[0-9a-f]{64}', row['sha256']) or not isinstance(row['bytes'], int) or row['bytes'] < 0:
            raise ValueError('Invalid asset checksum/size')
        if archive.getinfo(row['path']).file_size != row['bytes']:
            raise ValueError('Asset size does not match manifest')
    if sum(row['bytes'] for row in entries) > 4 * 1024**3:
        raise ValueError('Archive exceeds extraction limit')
    return manifest


def install_bundle(archive_path, root, expected_sha256):
    root = Path(root).resolve()
    if digest(archive_path) != expected_sha256:
        raise ValueError('Archive checksum mismatch; nothing installed')
    with zipfile.ZipFile(archive_path) as archive:
        manifest = read_manifest(archive)
        targets = [(row, asset_path(root, row['path'])) for row in manifest['files']]
        # Preflight all conflicts before creating or changing any asset.
        pending = []
        for row, target in targets:
            if target.exists():
                if not target.is_file() or target.stat().st_size != row['bytes'] or digest(target) != row['sha256']:
                    raise ValueError(f'Existing file differs; preserved: {row["path"]}. Use a fresh clone or move that file aside.')
            else:
                pending.append((row, target))
        runtime = root / '.runtime'
        runtime.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='asset-import-', dir=runtime) as temp:
            staged = []
            for index, (row, target) in enumerate(pending):
                temporary = Path(temp) / str(index)
                with archive.open(row['path']) as source, temporary.open('xb') as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
                if digest(temporary) != row['sha256']:
                    raise ValueError(f'Asset checksum mismatch: {row["path"]}; nothing installed')
                staged.append((temporary, target))
            for temporary, target in staged:
                # Recheck containment in case a destination symlink changed.
                asset_path(root, target.relative_to(root).as_posix())
                target.parent.mkdir(parents=True, exist_ok=True)
                with temporary.open('rb') as source, target.open('xb') as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
        return {'files': len(targets), 'installed': len(pending), 'unchanged': len(targets) - len(pending)}
