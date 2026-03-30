# Coding Conventions

**Analysis Date:** 2026-03-30

## Naming Patterns

**Files:**
- Python modules use snake_case under `src/linux_arctis_manager/` (e.g., `src/linux_arctis_manager/eq_store.py`).
- Tests live in `tests/` and use `test_*.py` or `*_test.py` per `pyproject.toml`.

**Functions:**
- snake_case with type hints (PEP 484/585). Example: `def _normalize_any(values_like: Any) -> list[float] | None` in `src/linux_arctis_manager/eq_store.py`.

**Variables:**
- snake_case for locals and attributes. Example: `general_settings`, `device_settings` in `src/linux_arctis_manager/settings.py`.

**Types:**
- Modern built-in generics (PEP 585), unions with `|` (PEP 604). Example: `ObservableDict[str, int | list[int]]` in `src/linux_arctis_manager/settings.py`.

## Code Style

**Formatting:**
- Tools present in dev group: `isort`, `autoflake` from `pyproject.toml` `[dependency-groups.dev]` (`/pyproject.toml`).
- No explicit Black or Ruff formatter configuration files detected.
- Prescriptive: Keep imports sorted with `isort` and remove unused imports with `autoflake` before committing.

**Type Checking:**
  - Config files: `/pyrightconfig.json`, `/pyproject.toml` (`[tool.pyright]`).
  - Target Python: 3.10 per `.python-version` and pyright config.

**Linting:**
- Ruff cache present (`/.ruff_cache/`), but no `ruff.toml`/`.ruff.toml` or `[tool.ruff]` in `/pyproject.toml`.
- No Flake8/Pylint config files found.
- Prescriptive: Adopt Ruff with a repo config (`ruff.toml`) to standardize lint + formatting, or document `isort`/`autoflake` usage in CI.

## Import Organization

**Order:**
1. Standard library
2. Third-party
3. Local package (`linux_arctis_manager.*`)

This pattern is visible across files such as `src/linux_arctis_manager/eq_store.py` and `src/linux_arctis_manager/settings.py`. Use `isort` to enforce.

**Path Aliases:**
- None. Absolute imports from `src/` are enabled by adding `src` to `sys.path` in tests (`/tests/conftest.py`).

## Error Handling

**Patterns:**
- Broad exception handling with safe fallbacks in persistence routines. Example in `src/linux_arctis_manager/eq_store.py`:
  - `_load()` wraps JSON load in `try/except` and resets to minimal state on failure.
  - `_atomic_save()` catches all exceptions and silently ignores failures.
- Prescriptive: Prefer catching specific exceptions and log the error context. Avoid swallowing exceptions that hide I/O errors.

## Logging

**Framework:** console/none observed (no shared logging setup found).

**Patterns:**
- No centralized logger utility detected. Prescriptive: Introduce a module-level `logging` setup (e.g., in `src/linux_arctis_manager/__init__.py` or `src/linux_arctis_manager/logging.py`) and use structured messages at INFO/WARNING/ERROR.

## Comments

**When to Comment:**
- Public classes/functions should include short docstrings describing behavior and side effects. Example: class docstring in `src/linux_arctis_manager/gui_gtk/widgets.py`.
- Inline comments explain non-obvious logic (e.g., EQ bank normalization) in `src/linux_arctis_manager/eq_store.py`.

**Docstrings:**
- PEP 257 style recommended. Current usage is partial; expand where missing.

## Function Design

**Size:**
- Small, single-responsibility preferred. Helper privates like `_normalize_any` and `_atomic_save` are used in `src/linux_arctis_manager/eq_store.py`.

**Parameters:**
- Typed parameters and return values throughout core modules.

**Return Values:**
- Prefer explicit return types; use `None` where appropriate and document via type hints.

## Module Design

**Exports:**
- Modules expose classes/functions directly (no barrel files in Python context).

**Package Layout:**
- Runtime code under `src/linux_arctis_manager/`; UI code in `src/linux_arctis_manager/gui_gtk/`; scripts entry points in `src/linux_arctis_manager/scripts/` referenced by `/pyproject.toml` `[project.scripts]`.

## Git Conventions

**Commit Message Style:**
- Observed Conventional Commits (e.g., `feat:`, `fix:`, with scopes like `fix(cli): ...`). Derived from `git log` history; no explicit linter config present.
- No `commitlint`/config files detected in repo.
- Prescriptive: Continue using `type(scope): summary` with imperative mood and concise body.

**Branching Strategy:**
- Default branch is `develop` (`remotes/origin/HEAD -> origin/develop`). `main` exists for releases. Feature branches use `feature/*` (e.g., `remotes/origin/feature/awake-from-sleep`).
- Prescriptive: Open PRs against `develop`; merge/release to `main` with version bump and changelog update.

## CI Checks

**Workflows:**
- `.github/workflows/wheel-install-test.yaml` builds a wheel with `uv build` and verifies installation across multiple Linux containers. No unit tests or linting jobs currently run in CI.

**Prescriptive CI Matrix:**
- TODO: Add a `pytest` job (e.g., `uv run -q pytest`) and a type-check/lint job (pyright + ruff/isort/autoflake) in `.github/workflows/`.

## Release and Versioning

**Scheme:**
- Semantic Versioning with Keep a Changelog.
  - `/CHANGELOG.md` states adherence to SemVer + Keep a Changelog.
  - Version declared in `/pyproject.toml` `[project].version` (e.g., `2.3.0-dev`).
  - Built artifacts in `/dist/` (e.g., `dist/linux_arctis_manager-2.3.0.dev0-...whl`).

**Process (observed):**
- Build via `uv build` (see `.github/workflows/wheel-install-test.yaml`).
- TODO: Document release steps (tagging, changelog update, publishing to PyPI/AUR packaging coordination) and ensure `main` reflects released versions.

## Issue and PR Templates

- Not detected. No `.github/ISSUE_TEMPLATE/` or `PULL_REQUEST_TEMPLATE.md` present.
- TODO: Add issue templates (bug, feature) and a PR template under `.github/` to standardize triage and review.

## Environment and Tooling

- Python 3.10 per `/.python-version` and Pyright config.
- `uv` used for build and recommended for dev (`/README.md`, workflow).
- `.env` present at repo root for local env; do not commit secrets (referenced by VS Code settings at `/.vscode/settings.json`).

---

*Convention analysis: 2026-03-30*
