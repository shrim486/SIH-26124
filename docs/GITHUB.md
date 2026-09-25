# First GitHub commit

Use `AI-POWERED-URBAN-INTELLIGENCE` as the repository root, not the parent desktop workspace. A local Git repository on branch `main` is initialized. No remote, commit, or push was created during preparation.

Included: source, tests, dependency manifests, npm lockfiles, environment examples, setup scripts and CI.

Ignored and preserved locally: `.env`, weights, input/output media, raw/labeled datasets, SQLite databases, dependencies, build output, logs, caches and old migration notes. Review before committing:

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

No remote URL is assumed. Configure your own GitHub remote when ready. Before sharing model/data binaries separately, establish their provenance and redistribution licenses. No source-code license has been selected; add one when ownership and intended terms are decided.
