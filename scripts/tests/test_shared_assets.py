import hashlib
import json
from pathlib import Path
import sys
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asset_bundle import digest, install_bundle


def bundle(tmp_path, files, bad_hash=False):
    archive = tmp_path / 'assets.zip'
    rows = []
    with zipfile.ZipFile(archive, 'w') as output:
        for name, content in files.items():
            output.writestr(name, content)
            rows.append({'path': name, 'bytes': len(content),
                         'sha256': '0' * 64 if bad_hash else hashlib.sha256(content).hexdigest()})
        output.writestr('manifest.json', json.dumps({'schema': 1, 'files': rows}))
    return archive


def test_restore_is_identical_and_repeatable(tmp_path):
    name = 'edge_ai/outputs/clip/annotated.mp4'
    archive = bundle(tmp_path, {name: b'video bytes', '.runtime/portal-seed.json': b'{}'})
    root = tmp_path / 'clone'
    assert install_bundle(archive, root, digest(archive))['installed'] == 2
    assert (root / name).read_bytes() == b'video bytes'
    assert install_bundle(archive, root, digest(archive))['unchanged'] == 2


@pytest.mark.parametrize('name', ['../outside.mp4', 'edge_ai/outputs/../../backend/.env',
                                   'backend/.env', 'C:/outside.mp4', 'edge_ai/outputs/test\\escape.mp4'])
def test_unsafe_paths_never_extract(tmp_path, name):
    archive = bundle(tmp_path, {name: b'bad'})
    root = tmp_path / 'clone'
    with pytest.raises(ValueError):
        install_bundle(archive, root, digest(archive))
    assert not root.exists()


def test_existing_changes_preserved_before_install(tmp_path):
    name = 'edge_ai/outputs/clip/annotated.mp4'
    archive = bundle(tmp_path, {'edge_ai/outputs/new/preview.jpg': b'new', name: b'original'})
    root = tmp_path / 'clone'
    target = root / name
    target.parent.mkdir(parents=True)
    target.write_bytes(b'local edit')
    with pytest.raises(ValueError, match='Existing file differs'):
        install_bundle(archive, root, digest(archive))
    assert target.read_bytes() == b'local edit'
    assert not (root / 'edge_ai/outputs/new').exists()


def test_tampered_zip_rejected_before_install(tmp_path):
    archive = bundle(tmp_path, {'edge_ai/outputs/test/preview.jpg': b'photo'})
    expected = digest(archive)
    with archive.open('ab') as output:
        output.write(b'tampered')
    with pytest.raises(ValueError, match='Archive checksum'):
        install_bundle(archive, tmp_path / 'clone', expected)


def test_inner_checksum_rejected_before_install(tmp_path):
    archive = bundle(tmp_path, {'edge_ai/outputs/test/preview.jpg': b'photo'}, bad_hash=True)
    root = tmp_path / 'clone'
    with pytest.raises(ValueError, match='Asset checksum'):
        install_bundle(archive, root, digest(archive))
    assert not (root / 'edge_ai').exists()
