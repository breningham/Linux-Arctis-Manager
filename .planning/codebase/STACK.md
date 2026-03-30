# Technology Stack

**Analysis Date:** 2026-03-30

## Languages

**Primary:**
- Python >=3.10 (target 3.10) - App/daemon, CLI, GUI backends (`pyproject.toml`, `.python-version`, `src/**.py`)

**Secondary:**
- QML (Qt Quick) - Qt frontend views (`src/linux_arctis_manager/gui/qml/*.qml`)
- CSS (GTK styling) - GTK frontend styles (`src/linux_arctis_manager/gui_gtk/style.css`)

## Runtime

**Environment:**
- CPython 3.10+ (type checking via Pyright) (`pyproject.toml`, `pyrightconfig.json`)

**Package Manager:**
- uv (build/run) - uv_build backend (`pyproject.toml` [build-system], `uv.lock`)
- pipx (user installation of wheel) (`install.sh`)
- Lockfile: uv.lock (present)

How to verify locally:
- python --version; cat .python-version
- uv --version; uv build
- uv pip list | grep -E "(dbus-next|pulsectl|pyusb|pyudev|PyGObject|pycairo|PySide6|ruamel|pytest)"

## Frameworks

**Core:**
- D-Bus (dbus-next 0.2.3) - IPC between daemon and UIs (`src/linux_arctis_manager/dbus_service.py`, `src/linux_arctis_manager/gui_gtk/dbus_client.py`, `docs/dbus.md`)
- PulseAudio/PipeWire (via pulsectl 24.12.0) - audio device control, virtual sinks (`src/linux_arctis_manager/pactl.py`)
- USB (pyusb 1.3.1) - HID/control transfers to headsets (`src/linux_arctis_manager/core.py`)
- udev (pyudev 0.24.4) - USB device monitoring (`src/linux_arctis_manager/usb_devices_monitor.py`)

**GUI (two frontends):**
- Qt 6 (PySide6 6.10.1 + QML) - main Qt/Kirigami-style UI (`src/linux_arctis_manager/gui/*`, `src/linux_arctis_manager/gui/qml/*.qml`)
- GTK (PyGObject 3.56.1 + PyCairo) - GNOME/libadwaita-style UI (`src/linux_arctis_manager/gui_gtk/*`)

**Testing:**
- pytest 9.0.2 (+ pytest-asyncio in tests) (`pyproject.toml [dependency-groups.dev]`, `tests/requirements.txt`)

**Build/Dev:**
- uv_build >=0.10.9 - build backend (`pyproject.toml`)
- Pyright - type checking (`pyproject.toml [tool.pyright]`, `pyrightconfig.json`)
- isort 7, autoflake 2 - import/order cleanup (`pyproject.toml [dependency-groups.dev]`)

## Key Dependencies

**Critical:**
- dbus-next 0.2.3 - Exposes/consumes D-Bus services for settings/status (`src/linux_arctis_manager/dbus_service.py`, `docs/dbus.md`)
- pulsectl 24.12.0 - Controls PulseAudio/pipewire-pulse modules and defaults (`src/linux_arctis_manager/pactl.py`)
- pyusb 1.3.1 - USB control transfers and endpoint I/O (`src/linux_arctis_manager/core.py`)
- pyudev 0.24.4 - Hotplug detection and callbacks (`src/linux_arctis_manager/usb_devices_monitor.py`)

**Infrastructure/UI:**
- PySide6 6.10.1 - Qt/QML UI (`src/linux_arctis_manager/gui/*`)
- PyGObject 3.56.1, pycairo 1.29.0 - GTK UI (`src/linux_arctis_manager/gui_gtk/*`)
- ruamel-yaml 0.19.1 - YAML device/config parsing (`src/linux_arctis_manager/config.py`, `src/linux_arctis_manager/devices/*.yaml`)

Concrete versions are pinned in `uv.lock` and minimums in `pyproject.toml`.

## Configuration

**Environment:**
- No required env vars detected. `.env` file exists at project root but is not read by the application (not referenced in code). Sensitive values are not used.
- Runtime/system configuration is read from the user’s home config:
  - General and per-device settings: `~/.config/arctis_manager/settings/*.yaml` (`src/linux_arctis_manager/settings.py`, `src/linux_arctis_manager/constants.py`)
  - Parametric EQ state: `~/.config/arctis_manager/settings/eq_state.json` (`src/linux_arctis_manager/eq_store.py`)
  - Device YAML overrides: `~/.config/arctis_manager/devices/*.yaml` (merged with `src/linux_arctis_manager/devices/*.yaml`)

**Build:**
- uv build (PEP 517 backend `uv_build`) produces wheels in `dist/` (`install.sh`, `pyproject.toml`)

## Platform Requirements

**Development:**
- Linux desktop environment
- System packages: libpulse (e.g., `libpulse0`), D-Bus, polkit `pkexec` for privileged actions (`.github/workflows/wheel-install-test.yaml`, `src/linux_arctis_manager/scripts/cli.py`)
- Tools: uv, pipx, pytest
- Verify: `uv run lam-cli -h`, `uv run lam-daemon -h`

**Production:**
- Deployment target: Linux user session (systemd user service) (`src/linux_arctis_manager/systemd.py`, service name `arctis-manager.service`)
- Desktop entries install to `$HOME/.local/share/applications` and autostart to `$HOME/.config/autostart` (`src/linux_arctis_manager/scripts/cli.py`, `src/linux_arctis_manager/desktop/*.desktop`)
- Udev rules under `/etc/udev/rules.d/91-steelseries-arctis.rules` or `/usr/lib/udev/rules.d/91-steelseries-arctis.rules` (`src/linux_arctis_manager/constants.py`, `src/linux_arctis_manager/scripts/cli.py`)

## Databases / Messaging / Storage

- Databases: Not applicable
- Messaging: D-Bus over the session bus (`src/linux_arctis_manager/dbus_service.py`, `docs/dbus.md`)
- File storage: YAML/JSON in `~/.config/arctis_manager/` (`src/linux_arctis_manager/settings.py`, `src/linux_arctis_manager/eq_store.py`)

## OS Support

- Linux only (PulseAudio/udev/systemd dependencies). CI validates across Fedora/Ubuntu/Debian/Arch (`.github/workflows/wheel-install-test.yaml`).

## How to check versions locally

- App version: `uv run python -c "from linux_arctis_manager.utils import project_version; print(project_version())"`
- dbus-next: `uv run python -c "import dbus_next,importlib.metadata as m;print(m.version('dbus-next'))"`
- pulsectl: `uv run python -c "import importlib.metadata as m;print(m.version('pulsectl'))"`
- PyGObject: `uv run python -c "import importlib.metadata as m;print(m.version('pygobject'))"`
- PySide6: `uv run python -c "import importlib.metadata as m;print(m.version('pyside6'))"`

---

*Stack analysis: 2026-03-30*
