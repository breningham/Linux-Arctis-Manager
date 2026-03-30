# Codebase Structure

**Analysis Date:** 2026-03-30

## Directory Layout

```
[project-root]/
├── src/                      # Python package source (PEP 420 layout via src/)
│   └── linux_arctis_manager/
│       ├── __init__.py
│       ├── core.py           # Core USB/audio engine and main loop
│       ├── config.py         # YAML config loader/types
│       ├── constants.py      # Paths, D-Bus names, Pulse sink names
│       ├── dbus_service.py   # D-Bus services and manager
│       ├── eq_store.py       # Parametric EQ bank persistence (JSON)
│       ├── i18n.py           # INI language loader
│       ├── pactl.py          # PulseAudio/PipeWire manager
│       ├── settings.py       # Device/general settings persistence (YAML)
│       ├── status_parser_fn.py # Status parsing functions registry
│       ├── usb_devices_monitor.py # pyudev-based USB watcher
│       ├── utils.py          # Utilities (systray ensure, JSON serialize, ObservableDict)
│       ├── desktop/          # .desktop launchers (window/systray for Qt and GTK)
│       ├── devices/          # Bundled device YAMLs
│       ├── gui/              # Qt/Kirigami frontend (backend + QML)
│       │   ├── backend.py
│       │   ├── base_app.py
│       │   ├── dbus_wrapper.py
│       │   ├── images/
│       │   ├── main_app.py
│       │   ├── qml/
│       │   ├── systray_app.py
│       │   └── ui_utils.py
│       ├── gui_gtk/          # GTK/libadwaita frontend
│       │   ├── app.py
│       │   ├── dbus_client.py
│       │   ├── preset_manager.py
│       │   ├── style.css
│       │   └── widgets.py
│       └── scripts/          # Console entrypoints
│           ├── cli.py        # lam-cli
│           ├── daemon.py     # lam-daemon
│           ├── dbus_awake.py # login1 sleep/wake listener
│           ├── gui.py        # lam-gui (Qt)
│           ├── gui_gtk.py    # lam-gui-gtk (GTK)
│           ├── import_gg_presets.py
│           └── systray.py    # lam-systray
├── tests/                    # Pytest suite
│   ├── core/
│   │   └── test_core_eq_integration.py
│   ├── daemon/
│   ├── eq_store/
│   ├── conftest.py
│   ├── test_config.py
│   └── test_status_parser_fn.py
├── docs/                     # Project documentation
│   ├── dbus.md
│   └── device_configuration_file_specs.md
├── .planning/                # GSD planning artifacts
│   └── codebase/
│       └── .gitkeep
├── dist/                     # Built wheels (generated; retained in repo)
├── GG/                       # EQ preset sources for importer (dev aid)
├── scripts/                  # Dev scripts (e.g., distrobox.sh)
├── pyproject.toml            # Build system, console scripts, dev deps
├── uv.lock                   # uv resolver lockfile
├── README.md                 # Usage, install, run docs
└── install.sh                # Automated installer (build+pipx+setup)
```

## Directory Purposes

**src/linux_arctis_manager/**
- Purpose: All runtime package code
- Contains: Core engine, D-Bus services, audio integration, frontends, scripts, resources
- Key files: `core.py`, `dbus_service.py`, `pactl.py`, `settings.py`, `eq_store.py`

**src/linux_arctis_manager/devices/**
- Purpose: Bundled device definitions (YAML)
- Contains: One file per supported device/model SKU
- Key files: `nova_pro_wireless.yaml`, `nova_7x_gen2.yaml`, etc.

**src/linux_arctis_manager/gui/**
- Purpose: Qt/Kirigami GUI
- Contains: QML views (`gui/qml/*.qml`), backend glue, icons
- Key files: `main_app.py`, `backend.py`, `dbus_wrapper.py`, `qml/Main.qml`

**src/linux_arctis_manager/gui_gtk/**
- Purpose: GTK/libadwaita GUI
- Contains: GTK app window, D-Bus client, EQ canvas, styles
- Key files: `app.py`, `dbus_client.py`, `preset_manager.py`, `style.css`

**src/linux_arctis_manager/scripts/**
- Purpose: Console entrypoints installed via `pyproject.toml [project.scripts]`
- Contains: `lam-daemon`, `lam-cli`, `lam-gui`, `lam-gui-gtk`, `lam-systray`
- Key files: `daemon.py`, `cli.py`, `gui.py`, `gui_gtk.py`, `systray.py`

**tests/**
- Purpose: Pytest-based unit/integration tests
- Contains: Parser/config tests, EQ integration tests
- Key files: `test_config.py`, `test_status_parser_fn.py`, `core/test_core_eq_integration.py`

**docs/**
- Purpose: Developer/user documentation
- Contains: D-Bus API doc, device YAML specs, device support guide
- Key files: `docs/dbus.md`, `docs/device_configuration_file_specs.md`, `docs/device_support.md`

**dist/**
- Purpose: Built wheels (`uv build`) - generated artifacts
- Contains: `*.whl` outputs

**.planning/**
- Purpose: Generated planning docs for GSD workflows
- Contains: `codebase/*.md`

## Key File Locations

**Entry Points:**
- `src/linux_arctis_manager/scripts/daemon.py`: lam-daemon (daemon + D-Bus + core loop)
- `src/linux_arctis_manager/scripts/gui.py`: lam-gui (Qt/Kirigami)
- `src/linux_arctis_manager/scripts/gui_gtk.py`: lam-gui-gtk (GTK/libadwaita)
- `src/linux_arctis_manager/scripts/systray.py`: lam-systray (AppIndicator)
- `src/linux_arctis_manager/scripts/cli.py`: lam-cli (udev rules, desktop entries, tools)

**Configuration:**
- `pyproject.toml`: deps, build backend (`uv_build`), console scripts, pytest config
- `src/linux_arctis_manager/constants.py`: runtime paths (settings, devices), D-Bus names/paths
- `src/linux_arctis_manager/devices/*.yaml`: device definitions
- User overrides: `~/.config/arctis_manager/devices/*.yaml`, `~/.config/arctis_manager/lang/*.ini`

**Core Logic:**
- `src/linux_arctis_manager/core.py`: USB command encode/write, status loop, observers, audio routing
- `src/linux_arctis_manager/pactl.py`: virtual sinks and redirection
- `src/linux_arctis_manager/dbus_service.py`: D-Bus JSON endpoints/signals

**Testing:**
- `tests/test_config.py`: YAML config parsing invariants
- `tests/test_status_parser_fn.py`: status parser functions
- `tests/core/test_core_eq_integration.py`: EQ persistence/apply paths

## Build and Run

- Build wheel: `uv build` (outputs to `dist/`)
- Install (pipx): see `install.sh` or `README.md`; typical: `pipx install --force dist/*.whl`
- Run daemon: `uv run lam-daemon`
- Run GUI (Qt): `uv run lam-gui --no-enforce-systemd` (for dev)
- Run GUI (GTK): `uv run lam-gui-gtk`
- Run CLI: `uv run lam-cli`

System integration:
- Write desktop entries: `lam-cli desktop write [--gtk|--qt|--both]`
- Write/reload udev rules: `lam-cli udev write-rules --force --reload`
- Enable user service: `systemctl --user enable --now arctis-manager`

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `dbus_service.py`)
- YAML device configs: `model_name.yaml` (e.g., `nova_5.yaml`)
- QML views: `PascalCase.qml` (e.g., `Main.qml`)

**Directories:**
- Package root: `src/linux_arctis_manager/`
- Frontends segregated by toolkit: `gui/` (Qt), `gui_gtk/` (GTK)
- Device configs co-located under `devices/`

**Console scripts → modules:**
- `lam-daemon` → `linux_arctis_manager.scripts.daemon:main`
- `lam-cli` → `linux_arctis_manager.scripts.cli:main`
- `lam-gui` → `linux_arctis_manager.scripts.gui:main`
- `lam-gui-gtk` → `linux_arctis_manager.scripts.gui_gtk:main`
- `lam-systray` → `linux_arctis_manager.scripts.systray:main`

## Where to Add New Code

**New Device Support:**
- Add YAML under `src/linux_arctis_manager/devices/{model}.yaml`
- Test with `lam-daemon` and `docs/device_configuration_file_specs.md`
- Optionally place user overrides in `~/.config/arctis_manager/devices/`

**New Status Parse or Setting Type:**
- Parsers: add function in `src/linux_arctis_manager/status_parser_fn.py` (decorate with `@status_type`)
- Setting types: extend handling in `src/linux_arctis_manager/config.py` and apply path in `src/linux_arctis_manager/core.py`

**New D-Bus Method:**
- Implement in `src/linux_arctis_manager/dbus_service.py` and thread through `CoreEngine` as needed
- Update GUI clients: `src/linux_arctis_manager/gui/dbus_wrapper.py`, `src/linux_arctis_manager/gui_gtk/dbus_client.py`

**Frontend Feature (Qt):**
- QML in `src/linux_arctis_manager/gui/qml/`; backend glue in `src/linux_arctis_manager/gui/backend.py`

**Frontend Feature (GTK):**
- Widgets/views under `src/linux_arctis_manager/gui_gtk/`; keep `app.py` modular by extracting new widgets

**Utilities:**
- Shared helpers go to `src/linux_arctis_manager/utils.py`

## Special Directories

**dist/**
- Purpose: Wheel build outputs
- Generated: Yes
- Committed: Present in repo; treat as generated artifacts

**.planning/**
- Purpose: Planning and mapping docs for GSD
- Generated: Yes
- Committed: Yes

**GG/**
- Purpose: Source data for EQ preset importer script
- Generated: Mixed (external assets under version control for convenience)
- Committed: Yes

---

*Structure analysis: 2026-03-30*
