# Restore the same videos after cloning or downloading ZIP

The source repository and its asset release are public. Anyone who downloads a
release can view its footage without a portal login. Government credentials still
protect the application's evidence APIs; they do not encrypt downloaded files.
Only the existing public-source analysis examples are included. Credentials,
users, the operational database, camera feeds and uploaded analysis jobs are not
distributed.

## Recommended setup

Install Python 3.10 and Node.js 22.12+, then run from the repository folder:

```powershell
python scripts/setup.py
powershell -NoProfile -ExecutionPolicy Bypass -File ./start.ps1
```

This works for both `git clone` and GitHub's **Download ZIP**. Setup installs the
dependencies, generates local government credentials, downloads the pinned portal
bundle and creates the five linked incident records in an **empty** database.
The videos already contain detection boxes; viewing them does not rerun inference.
Existing incident databases are preserved. Repeat setup will not duplicate alerts.
The records retain their assigned-coordinate and unknown-recording-time provenance.

For model inference and full original videos too:

```powershell
python scripts/setup.py --with-models --with-originals
```

The three files are on the [asset release](https://github.com/shrim486/SIH-26124/releases/tag/assets-2026-09-27):

| Bundle | Contents | Needed for |
| --- | --- | --- |
| `urban-iq-portal.zip` | Saved annotated videos, detected images, prediction records, source excerpts and five map records | Same portal evidence and map alerts |
| `urban-iq-models.zip` | Local model weights, OCR assets and model configuration | Running new detections |
| `urban-iq-originals.zip` | Full source videos, excluding duplicate rider-candidate downloads | Reprocessing longer recordings |

The default portal download is about **157 MiB**. The optional model and original
video bundles add about **986 MiB** and **627 MiB** respectively.

Exact byte sizes, SHA-256 checksums and download URLs are versioned in
[release-assets.json](release-assets.json). Setup checks the archive and every
installed file, rejects unsafe archive paths, and refuses to overwrite changed
assets. For a clean checkout this installs the exact saved video bytes. Full
source recordings and model weights are optional large downloads.

## Already installed dependencies

Use the virtual environment's Python (`.venv/Scripts/python.exe` on Windows,
`.venv/bin/python` on macOS/Linux):

```powershell
.venv/Scripts/python.exe scripts/fetch_shared_assets.py
.venv/Scripts/python.exe scripts/seed_portal.py
```

For all optional assets use `scripts/fetch_shared_assets.py --bundle all`.
To use ZIPs downloaded manually from the release, pass
`--from-dir 'C:/Downloads/urban-iq-assets'` to that script, or
`--assets-dir 'C:/Downloads/urban-iq-assets'` to setup. Dependencies still need
internet access unless already installed.

`--skip-assets` installs code dependencies without videos or map records.
`--config-only` only creates missing environment files.

## Credentials, limitations and updates

Each clone gets its own generated government password in `backend/.env`.
Read that file locally; never commit it. The release contains no user accounts.
Use citizen registration to create an account on the new installation.

These are saved detections, not a live public-transport camera connection.
Model quality and dataset limitations remain documented in
[EXTENDED_MODELS.md](EXTENDED_MODELS.md). Media/model source information is in
[ASSETS.md](ASSETS.md), [multi-demo-sources.json](multi-demo-sources.json),
[accident-demo-source.json](accident-demo-source.json) and
[extended-model-assets.json](extended-model-assets.json). Third-party ownership
and license terms are not replaced by this project's download links.

For maintainers, `scripts/build_shared_assets.py --tag <new-tag>` prepares bundles
and a new pinned manifest locally. Publish those ZIPs with the matching code;
do not replace an existing release's files or silently change checksums.
