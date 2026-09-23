# Contributing to leptonai

Contributions and collaborations are welcome.

## Development

Use [uv](https://docs.astral.sh/uv/getting-started/installation/) to manage this repository's Python environment and dependencies. The default development Python version is 3.13, pinned in `.python-version`.

After installing uv, clone the repository and synchronize the environment:

```shell
git clone https://github.com/leptonai/leptonai.git
cd leptonai
uv sync --locked
uv run lep --help
```

`uv sync --locked` creates or updates `.venv` and installs the local project in editable mode, together with the default `dev` dependency group. That group includes the existing `lint` and `test` extras, so source changes take effect immediately and development tools are ready to use. The command fails if `uv.lock` needs updating.

Run project commands with `uv run`; activation is optional. To use `lep` directly in your shell:

```shell
source .venv/bin/activate
lep --help
```

Creating or activating an empty virtual environment alone does not install `lep`; run `uv sync --locked` first.

### Managing dependencies

Keep `pyproject.toml`, `uv.lock`, and `.python-version` in version control. Let uv generate `uv.lock`; do not edit it by hand. Keep `.venv` untracked.

- Use `uv add <package>` or `uv remove <package>` for runtime dependencies.
- Use `uv add --dev <package>` for development-only dependencies. Add shared test or lint tools with `uv add --optional test <package>` or `uv add --optional lint <package>`.
- After editing dependency declarations manually, run `uv lock`, then `uv sync --locked`.
- To upgrade a dependency intentionally, run `uv lock --upgrade-package <package>`, then `uv sync --locked` and the relevant checks.

Use uv's project commands for this environment instead of installing packages directly with `pip` or `uv pip`, which bypass the project lockfile. See uv's [project environment documentation](https://docs.astral.sh/uv/concepts/projects/layout/#the-project-environment) for details.

## Testing

The default development environment includes the test tools. Run all tests with:

```shell
uv run pytest
```

To run a specific test, append its file and test name:

```shell
uv run pytest leptonai/cli/tests/test_cli.py::TestLepCli::test_version
```

Some tests require workspace credentials or other external services; use focused tests when working offline.

## Coding Standards

Ensure your code is clean, readable, and well-commented. We use [black](https://github.com/psf/black) and [ruff](https://github.com/astral-sh/ruff) for formatting and linting. Both are installed by `uv sync --locked`.

```shell
uv run black --check .
uv run ruff check .
```

To apply formatting, run `uv run black .`.

### Auto-format on commit (recommended)

This repo ships a [pre-commit](https://pre-commit.com/) config that runs `ruff --fix` and `black` on the files you are committing, so formatting stays consistent without having to remember to run it by hand.

The development environment includes `pre-commit` on Python 3.10 and later, but the git hook is **not** active until you enable it **once per clone**:

```shell
uv run pre-commit install
```

After that the hooks run automatically on `git commit`. If a hook reformats a file, the commit is aborted so you can review the change — just `git add` the updated files and commit again. To format the whole repo in one pass, run `uv run pre-commit run --all-files`.
