# Release Workflow for Python SDK

## How the version is determined

The package version is **not** stored in any source file. It is derived from the
latest git tag by [`setuptools_scm`](https://github.com/pypa/setuptools-scm)
(configured under `[tool.setuptools_scm]` in `pyproject.toml`, which writes
`leptonai/_version.py` at build time). `leptonai/_version.py` is auto-generated —
do not edit it, and do not commit changes to it.

Bumping the version therefore means creating a git tag; there is no source file to
edit when cutting a release.

## Releasing an SDK & CLI python package

To release, you tag a commit on `main` and let the release workflow build and
publish the wheel from that tag.

### 1. Choose the commit and version

- Check out and update main: `git checkout main && git pull`.
- Make sure the working tree is clean.
- Pick the new version `<major>.<minor>.<patch>`. To see the current latest,
  run `git tag --sort=-v:refname | head` or check
  https://github.com/leptonai/leptonai/tags. Tags use a plain numeric form with
  **no `v` prefix** (e.g. `0.27.4`).

### 2. Tag and push

- Tag the exact commit you want to release: `git tag <major>.<minor>.<patch>`
- Push the tag: `git push origin <major>.<minor>.<patch>`

> Important: the release workflow must build from the tagged commit. `setuptools_scm`
> produces a clean version (e.g. `0.27.4`) only when `HEAD` is exactly on the tag.
> Building from a commit that is N commits ahead of the tag yields a dev version
> like `0.27.4.post1.devN+g<sha>`, which is not a publishable release.

### 3. Create release notes

- Go to https://github.com/leptonai/leptonai/releases and click "Draft a new release".
- Select the tag you just pushed, choose "Generate release notes", and publish.

### 4. Publish to PyPI

- Go to https://github.com/leptonai/leptonai/actions/workflows/release.yaml
- Click "Run workflow" in the top right corner.
  - Click the ref selector, open the "Tags" tab, and choose the tag you just
    created (`<major>.<minor>.<patch>`). Do **not** run it on `main` (see the note
    above about dev versions).
  - Enable "Whether publish to PyPI". Optionally enable "Is this a release package"
    and "Whether run end to end testing".
  - Run the workflow and wait for it to finish. The `publish-pypi` job builds the
    wheel (version comes from the tag) and uploads it to PyPI via `twine`.

That concludes the release.

For a quick verification, in a pristine environment, do:
```
pip install -U leptonai
lep -v
```
and see if the version is correct.

## Test instructions for CLI

Run the script [here](https://github.com/leptonai/lepton/blob/main/sdk/release_scripts/e2e_sdk_cli_test.sh) and make sure all tests pass as the terminal output shows:
 
```shell
All tests finished. Errors so far = 0
```