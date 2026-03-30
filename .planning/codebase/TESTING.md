# Testing Patterns

**Analysis Date:** 2026-03-30

## Test Framework

**Runner:**
- pytest (configured in `/pyproject.toml` under `[tool.pytest.ini_options]`)
  - addopts: `-q`
  - testpaths: `tests`
  - python_files: `test_*.py`, `*_test.py`
  - asyncio_mode: `auto`

**Assertion Library:**
- pytest built-ins (`assert`, `pytest.approx`, `pytest.mark.parametrize`)

**Run Commands:**
```bash
# Using uv (recommended for this repo)
uv run pytest                 # Run all tests (respects -q from pyproject)

# Using system Python
python -m pytest              # Run all tests

# If you need to install test deps explicitly (non-uv)
python -m pytest
```

## Test File Organization

**Location:**
- Separate `tests/` tree with subpackages for areas:
  - `tests/eq_store/...`
  - `tests/core/...`
  - `tests/daemon/...`

**Naming:**
- `test_*.py` and `*_test.py` (per `/pyproject.toml`). Examples:
  - `tests/eq_store/test_eq_store.py`
  - `tests/core/test_core_eq_integration.py`
  - `tests/daemon/test_dbus_settings.py`

**Structure:**
```
tests/
├── conftest.py          # shared fixtures, path setup
├── core/
│   └── test_core_eq_integration.py
├── daemon/
│   └── test_dbus_settings.py
├── eq_store/
│   └── test_eq_store.py
├── test_config.py
└── test_status_parser_fn.py
```

## Test Structure

**Suite Organization:**
```python
# tests/eq_store/test_eq_store.py
@pytest.mark.parametrize(
    "target,expect",
    [
        (0, "wi_hp"),
        (1, "bt_hp"),
        (2, "wi_mic"),
        ("wireless", "wi_hp"),
        ("bluetooth", "bt_hp"),
        ("microphone", "wi_mic"),
        (99, "wi_hp"),
    ],
)
def test_map_target_to_key_variants(target, expect, tmp_path: Path):
    store = EqStore(tmp_path / "eq_state.json")
    assert store.map_target_to_key(target) == expect
```

**Patterns:**
- Setup: use `tmp_path` for filesystem isolation; construct stubs for device/config where needed.
- Teardown: implicit via tmp_path and monkeypatch context.
- Assertions: plain `assert`, `pytest.approx` for floats.

## Mocking

**Framework:**
- `pytest` fixtures and `monkeypatch` are used for isolation; no `unittest.mock` helpers observed.

**Patterns:**
```python
# tests/core/test_core_eq_integration.py
def test_on_device_configured_applies_bank(monkeypatch):
    engine = CoreEngine()
    engine.device_config = StubConfig()

    # Patch out hardware/USB and PA calls
    monkeypatch.setattr(engine, "kernel_detach", lambda *a, **k: None)
    monkeypatch.setattr(engine, "init_device", lambda *a, **k: None)
    monkeypatch.setattr(engine.pa_audio_manager, "wait_for_physical_device", lambda *a, **k: None)
    monkeypatch.setattr(engine.pa_audio_manager, "sinks_setup", lambda *a, **k: None)
    monkeypatch.setattr(engine, "redirect_to_media_sink", lambda *a, **k: None)
    monkeypatch.setattr(engine, "get_command_endpoint_address", lambda *a, **k: 0x00)
    monkeypatch.setattr(engine, "send_command", lambda *a, **k: None)
```

**What to Mock:**
- Hardware/USB I/O (`send_command`, `kernel_detach`, `init_device`).
- External audio manager interactions (`pa_audio_manager.*`).

**What NOT to Mock:**
- Pure data transforms and persistence (`EqStore`, normalization routines) should be exercised directly with `tmp_path`.

## Fixtures and Shared Setup

**Test Data:**
```python
# tests/daemon/test_dbus_settings.py
class StubCore:
    def __init__(self, tmp_path: Path):
        from linux_arctis_manager.settings import GeneralSettings, DeviceSettings
        from linux_arctis_manager.eq_store import EqStore
        self.general_settings = GeneralSettings()
        self.device_config = type("Cfg", (), {"name": "Test Device", "settings": {}})()
        self.device_settings = DeviceSettings(0x1234, 0x5678)
        self.eq_store = EqStore(tmp_path / "eq_state.json")

@pytest.fixture
def service(tmp_path: Path):
    core = StubCore(tmp_path)
    return ArctisManagerDbusSettingsService(core)
```

**Location:**
- Shared path/collection behavior in `/tests/conftest.py`:
  - Ensures `src/` is on `sys.path` for imports.
  - Skips legacy upstream tests (`tests/test_config.py`, `tests/test_status_parser_fn.py`).

## Coverage

**Requirements:** None enforced.

**Status:**
- No `pytest-cov` or coverage configuration detected; no coverage collection in CI.

**View Coverage:**
```bash
# TODO: Add pytest-cov to dev deps and collect coverage, e.g.:
uv run pytest --cov=linux_arctis_manager --cov-report=term-missing
```

## How to Run Tests

**Local (uv-managed):**
```bash
uv run pytest            # runs with settings from pyproject
```

**Local (pip-managed):**
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r tests/requirements.txt
python -m pytest
```

**CI:**
- Current workflow `/.github/workflows/wheel-install-test.yaml` performs a build and wheel install smoke test across multiple Linux containers using `uv build` and `tests/install-wheel-test.sh`.
- TODO: Add a CI job that runs `pytest` and (optionally) type checking with `pyright` plus linting.

## Test Types

**Unit Tests:**
- `tests/eq_store/test_eq_store.py` validates pure functions and persistence behavior of `src/linux_arctis_manager/eq_store.py`.

**Integration Tests:**
- `tests/core/test_core_eq_integration.py` exercises `CoreEngine` flows with hardware/network calls patched out.
- `tests/daemon/test_dbus_settings.py` validates DBus settings service composition with a stub core.

**E2E Tests:**
- Not present.

## Flakiness Hotspots

- None observed. Tests isolate filesystem via `tmp_path` and patch hardware interactions. Maintain this pattern for stability.
- Guidance: Avoid timing-based assertions and real hardware/DBus calls; prefer stubs/monkeypatch.

## Adding New Tests

- Place new tests under `tests/<area>/test_*.py` and follow naming patterns from `/pyproject.toml`.
- Prefer pytest fixtures for setup/teardown; use `tmp_path` for disk writes.
- Patch external effects (USB/PA/DBus) with `monkeypatch`.

---

*Testing analysis: 2026-03-30*
