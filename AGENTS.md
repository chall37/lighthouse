# Repository Guidelines

## Project Structure & Module Organization
The Python package lives under `lighthouse/`. `daemon.py` coordinates log watchers, `watcher.py` streams filesystem events, `notifier.py` wraps Pushover delivery, and `state.py` tracks alert history. CLI entry points map to `cli.py` (`lighthouse-notify`) and `daemon.py` (`lighthouse`). Configuration helpers live in `config.py`, with `config.yaml.example` as the starting template. Tests reside in `tests/` and mirror the package layout; add new fixtures beside the module they exercise. Operational assets sit in `systemd/`, while helper automation scripts live in `scripts/`.

## Build, Test, and Development Commands
Create a virtual environment and install dev extras:

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -e .[dev]
```

Run checks locally before opening a PR:

```bash
pytest
ruff check .
mypy lighthouse
scripts/check-ci.sh          # mirrors the CI pipeline
python -m lighthouse.daemon --config config.yaml.example --foreground
```

The final command boots the daemon in the foreground for manual smoke tests.

## Coding Style & Naming Conventions
Target Python 3.12 with four-space indents, type hints on all public functions, and expressive `snake_case` for functions, `CamelCase` for classes. Follow the 100-character soft limit enforced by Ruff; long URLs may exceed it. Keep modules cohesive and prefer dataclasses or Pydantic models for structured data. Use `ruff format` (or `ruff check --fix`) for formatting, and let Ruff linting plus MyPy’s `disallow_untyped_defs` guard style regressions.

## Testing Guidelines
Write tests with `pytest` using the `test_<feature>.py` naming pattern already configured in `pyproject.toml`. Cover both error and success paths, especially around watcher pattern matching and notification rate limits. When adding new YAML schema rules, include serialization tests that load `config.yaml.example` clones via `config.Config`. Run `pytest --maxfail=1 --disable-warnings` before pushing to catch flaky assumptions.

## Commit & Pull Request Guidelines
Keep commit summaries short and imperative (e.g., "Add OS release info debug step"), with optional detail in the body and references to `Fixes #issue`. Group related changes; avoid mixing refactors with feature work. Every PR should describe motivation, note config or systemd changes, and attach screenshots or log snippets when altering notification behavior. Confirm that `pytest`, `ruff check`, `mypy`, and `scripts/check-ci.sh` all pass, and call out any skipped checks explicitly.
