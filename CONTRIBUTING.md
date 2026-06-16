# Contributing to leptonai

First and foremost, thank you for considering contributing to leptonai! We appreciate the time and effort you're putting into helping improve our project. This guide outlines the process and standards we expect from contributors.


## Development

First clone the source code from Github

```
git clone https://github.com/leptonai/leptonai.git
```

Use `pip` to install `leptonai` from source

```shell
cd leptonai
pip install -e .
```

`-e` means "editable mode" in pip. With "editable mode" all changes to python code will immediately become effective in the current environment.

## Testing

We highly recommend writing tests for new features or bug fixes and ensure all tests passing before submitting a PR.

To run tests locally, first install test driver by doing

```shell
pip install -e ".[test]"
```

To run all existing test cases together, simply run

```
pytest
```
If you only want to run specific test case, append the corresponding test file and test case name in the pytest command, e.g.:

```
pytest leptonai/cli/tests/test_cli.py::TestLepCli::test_version
```

## Coding Standards
Ensure your code is clean, readable, and well-commented. We use [black](https://github.com/psf/black) and [ruff](https://github.com/astral-sh/ruff) as code linter.

To run lint locally, first install linters by doing

```shell
pip install -e ".[lint]"
```

Then run
```
black .
ruff check .
```
to check code.

### Auto-format on commit (recommended)

This repo ships a [pre-commit](https://pre-commit.com/) config that runs `ruff --fix` and `black` on the files you are committing, so formatting stays consistent without having to remember to run it by hand.

Installing `.[lint]` (above) installs the `pre-commit` tool, but the git hook is **not** active until you enable it **once per clone**:

```shell
pre-commit install
```

After that the hooks run automatically on `git commit`. If a hook reformats a file, the commit is aborted so you can review the change — just `git add` the updated files and commit again. To format the whole repo in one pass, run `pre-commit run --all-files`.
