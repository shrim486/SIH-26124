# Repository and shared assets

Use `AI-POWERED-URBAN-INTELLIGENCE` as the repository root, not the parent desktop workspace. The GitHub repository is [shrim486/SIH-26124](https://github.com/shrim486/SIH-26124), branch `main`.

Included: source, tests, dependency manifests, npm lockfiles, environment examples, setup scripts, CI and the pinned release-asset manifest. The existing waterlogging prototype also includes its small model and videos from the upstream repository.

Larger model/video assets are distributed through [versioned release downloads](SHARED_VIDEOS.md), installed by `scripts/setup.py`. They stay outside Git history. `.env`, operational SQLite databases, dependencies, build output, logs, caches and old migration notes remain private/local. Review before committing:

```sh
git status --short
git add --dry-run .
```

When ready, stage and commit locally:

```sh
git add .
git diff --cached --stat
git commit -m "Prepare urban intelligence project"
```

Fetch and integrate `origin/main` before pushing; never force-push over teammates' commits. This repository and its releases are public. Government-only application access does not restrict downloaded GitHub assets. Third-party media/model provenance is documented separately; no project-wide source-code license has been selected.
