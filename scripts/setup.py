"""Create a local environment and install dependencies without overwriting secrets."""
import argparse
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config-only', action='store_true', help='Only create missing .env files')
    parser.add_argument('--skip-assets', action='store_true', help='Install code dependencies without downloading shared videos')
    parser.add_argument('--with-models', action='store_true', help='Also restore all saved model weights for new inference')
    parser.add_argument('--with-originals', action='store_true', help='Also download full original input videos')
    parser.add_argument('--assets-dir', type=Path, help='Folder containing the release ZIPs for offline asset installation')
    args = parser.parse_args()
    env = ROOT / 'backend/.env'
    if not env.exists():
        with env.open('x', encoding='utf-8') as out:
            out.write('DATABASE_URL=sqlite:///./app.db\nSECRET_KEY=' + secrets.token_urlsafe(48)
                      + '\nGOVERNMENT_USERNAME=admin\nGOVERNMENT_PASSWORD='
                      + secrets.token_urlsafe(18) + '\n')
        print('Created backend/.env. Read it locally for government credentials.')
    for portal in ('user_portal', 'government_portal'):
        target = ROOT / portal / '.env'
        if not target.exists():
            with target.open('x', encoding='utf-8') as out:
                out.write((ROOT / portal / '.env.example').read_text(encoding='utf-8'))
    if args.config_only:
        return
    npm = shutil.which('npm.cmd' if sys.platform == 'win32' else 'npm')
    if not npm:
        parser.error('Install Node.js 22.12+ and npm first.')
    folder = ROOT / '.venv'
    python = folder / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    if not python.exists():
        venv.create(folder, with_pip=True)
    subprocess.run([str(python), '-m', 'pip', 'install', '-r', 'requirements-dev.txt'], cwd=ROOT, check=True)
    for portal in ('user_portal', 'government_portal'):
        subprocess.run([npm, 'ci'], cwd=ROOT / portal, check=True)
    if not args.skip_assets:
        for bundle in ['portal'] + (['models'] if args.with_models else []) + (['originals'] if args.with_originals else []):
            command = [str(python), 'scripts/fetch_shared_assets.py', '--bundle', bundle]
            if args.assets_dir:
                command += ['--from-dir', str(args.assets_dir.resolve())]
            subprocess.run(command, cwd=ROOT, check=True)
        subprocess.run([str(python), 'scripts/seed_portal.py'], cwd=ROOT, check=True)
    print('Setup complete. Run start.ps1 on Windows, or use the README startup commands.')


if __name__ == '__main__':
    main()
