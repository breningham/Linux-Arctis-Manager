# Architecture

**Analysis Date:** 2026-03-30

## Pattern Overview

**Overall:** Headless device daemon exposing a D-Bus API, with multi-frontend GUI/CLI clients

**Key Characteristics:**
- Long-running user daemon manages USB device, audio routing, and state persistence
- D-Bus interfaces provide status and settings for decoupled clients (Qt/QML, GTK, systray, CLI)
- Device behavior is data-driven via YAML configurations loaded at runtime

## Layers

**Core Device Engine:**
- Purpose: USB HID I/O, status polling/parse, settings application, audio sink control
- Location: `src/linux_arctis_manager/core.py`
- Contains: USB communication, observers, EQ application, PulseAudio routing
- Depends on: `pyusb`, `pyudev`, `pulsectl`, config/settings modules
- Used by: D-Bus services (`src/linux_arctis_manager/dbus_service.py`), daemon entrypoint

**Configuration & Parsing:**
- Purpose: Load and validate YAML device configs; transform status values
- Location: `src/linux_arctis_manager/config.py`, `src/linux_arctis_manager/status_parser_fn.py`, `src/linux_arctis_manager/devices/*.yaml`
- Contains: Dataclasses (DeviceConfiguration, ConfigSetting, etc.), status parsers, loader
- Depends on: `ruamel.yaml`
- Used by: `core.py`, D-Bus services

**Audio (PulseAudio/PipeWire):**
- Purpose: Discover sinks, create/remove virtual media/chat sinks, redirect default, set mix
- Location: `src/linux_arctis_manager/pactl.py`
- Contains: `PulseAudioManager` singleton wrapping `pulsectl`
- Depends on: `pulsectl`
- Used by: `core.py` (mix and routing)

**IPC (D-Bus Services):**
- Purpose: Expose status, settings, and config APIs via D-Bus
- Location: `src/linux_arctis_manager/dbus_service.py`
- Contains: `ArctisManagerDbus{Config,Status,Settings}Service`, `DbusManager`
- Depends on: `dbus-next`, `constants.py`
- Used by: `lam-daemon` process

**Persistence:**
- Purpose: Persist per-device settings and parametric EQ banks
- Location: `src/linux_arctis_manager/settings.py`, `src/linux_arctis_manager/eq_store.py`
- Contains: YAML-backed settings, JSON-backed EQ store, observable settings dict
- Depends on: filesystem under `~/.config/arctis_manager`
- Used by: `core.py`, D-Bus services, GUIs

**Frontends (Clients):**
- Purpose: Present UI, call D-Bus methods, react to signals
- Location: Qt/QML: `src/linux_arctis_manager/gui/*`; GTK: `src/linux_arctis_manager/gui_gtk/*`; Systray: `src/linux_arctis_manager/scripts/systray.py`
- Contains: D-Bus wrappers, QML/GTK views, systray indicator
- Depends on: `dbus-next`, `PySide6` or `PyGObject`
- Used by: `lam-gui`, `lam-gui-gtk`, `lam-systray`

**System Integration:**
- Purpose: User-level systemd unit management, udev rules, desktop entries
- Location: `src/linux_arctis_manager/systemd.py`, `src/linux_arctis_manager/scripts/cli.py`, `src/linux_arctis_manager/desktop/*.desktop`
- Contains: systemd unit writer/enabler, CLI commands, .desktop files
- Used by: installers, users

## Data Flow

**End-to-end Device Lifecycle:**

1. Process start: `lam-daemon` (`src/linux_arctis_manager/scripts/daemon.py`) initializes `DbusManager` and `CoreEngine`
2. USB event: `USBDevicesMonitor` (`src/linux_arctis_manager/usb_devices_monitor.py`) detects add/remove via `pyudev`
3. On connect: `CoreEngine.configure_virtual_sinks()` selects matching `DeviceConfiguration` (`src/linux_arctis_manager/devices/*.yaml`), claims HID interfaces, loads settings/EQ, configures PulseAudio virtual sinks via `PulseAudioManager`
4. Status loop: `CoreEngine.loop()` requests device status and listens on configured HID IN endpoints; raw responses are mapped to keys and parsed via `status_parser_fn.py`
5. D-Bus status: `ArctisManagerDbusStatusService` publishes categorized JSON status; clients subscribe to `StatusChanged`
6. Setting change (client): UI calls `ArctisManagerDbusSettingsService.SetSetting`, which validates and mutates `GeneralSettings` or `DeviceSettings`
7. Hardware apply: `CoreEngine.on_setting_changed()` converts values to device command sequences and writes via HID OUT or control transfer; updates persisted stores as needed
8. On disconnect: `CoreEngine.teardown()` removes virtual sinks, releases HID interfaces, optionally redirects audio per general settings

**State Management:**
- Device status: `ObservableDict` in `core.py` emits per-key updates to observers, triggering D-Bus notifications and audio mix recalculation
- Settings: `DeviceSettings.settings` is an `ObservableDict`; writes go to YAML; general settings persisted to `~/.config/arctis_manager/settings/general_settings.yaml`
- EQ banks: `EqStore` keeps per-target banks in `~/.config/arctis_manager/settings/eq_state.json`

## Key Abstractions

**DeviceConfiguration (YAML-driven):**
- Purpose: Declarative mapping of HID interfaces, init sequences, status layout, parsers, and settings
- Examples: `src/linux_arctis_manager/devices/nova_pro_wireless.yaml`, `src/linux_arctis_manager/devices/nova_7x_gen2.yaml`
- Pattern: Data-driven configuration consumed by `core.py` and `config.py`

**ConfigSetting:**
- Purpose: Typed setting definition (slider, toggle, select, equalizer, parametric_eq) with update sequences
- Examples: Within each device YAML, consumed in `config.py`
- Pattern: Command sequence templating (`'value'` token, transforms like `nibble_pack`)

**PulseAudioManager:**
- Purpose: High-level control of PulseAudio/PipeWire for virtual sinks and routing
- Examples: `src/linux_arctis_manager/pactl.py`
- Pattern: Singleton with retry loops and sink discovery helpers

**Dbus Services:**
- Purpose: Stable API boundary for clients
- Examples: `src/linux_arctis_manager/dbus_service.py` (`GetStatus`, `SettingsChanged`, `SetSetting`, `ReloadConfigs`, `SetEqTarget`)
- Pattern: JSON payloads for schema-lite interop across languages/toolkits

## Entry Points

**Daemon (user service):**

**GUI (Qt/Kirigami):**

**GUI (GTK/libadwaita):**

**Systray:**

**CLI:**

## Error Handling

**Strategy:**
- Defensive checks around USB/device presence; log-and-continue on transient I/O errors
- Validation on configuration load; type checks for settings before apply; JSON parsing guarded in D-Bus calls

**Patterns:**
- USB exceptions filtered by errno (busy/timeout) in `core.py::listen_endpoint_loop` and `send_command`
- Retry loops for Pulse sink listing and discovery in `pactl.py`

## Cross-Cutting Concerns

**Logging:** Python `logging` across subsystems (`CoreEngine`, `PulseAudioManager`, D-Bus services, GUIs)
**Validation:** YAML config validation in `DeviceConfiguration.__init__` raises explicit `ValueError`s for missing/invalid fields
**Authentication:** None; D-Bus API is un-authenticated and assumes a trusted local session

## Processes and Daemons

- User-level systemd service `arctis-manager.service` written/enabled by `src/linux_arctis_manager/systemd.py`; `ExecStart=lam-daemon`
- Sleep/wake integration via system bus `org.freedesktop.login1` in `src/linux_arctis_manager/scripts/dbus_awake.py`

## IPC / Networking

- D-Bus bus name: `name.giacomofurlan.ArctisManager.Next` (see `src/linux_arctis_manager/constants.py`)
- Objects/Interfaces:
  - `/name/giacomofurlan/ArctisManager/Next/Status` → `GetStatus()`, `StatusChanged`
  - `/name/giacomofurlan/ArctisManager/Next/Settings` → `GetSettings()`, `SetSetting(setting, valueJSON)`, `SettingsChanged`, `GetListOptions(name)`, `SetEqTarget(target)`
  - `/name/giacomofurlan/ArctisManager/Next/Config` → `ReloadConfigs()`
- Payloads: JSON strings (documented in `docs/dbus.md`)

## Persistence

- Device/user settings YAML: `~/.config/arctis_manager/settings/{vendorId}_{productId}.yaml` (see `src/linux_arctis_manager/settings.py`)
- General settings YAML: `~/.config/arctis_manager/settings/general_settings.yaml`
- Parametric EQ banks JSON: `~/.config/arctis_manager/settings/eq_state.json` (`src/linux_arctis_manager/eq_store.py`)
- Language files: `src/linux_arctis_manager/lang/*.ini` with home overrides `~/.config/arctis_manager/lang/*.ini`
- Device configs: packaged under `src/linux_arctis_manager/devices/*.yaml` with home overrides `~/.config/arctis_manager/devices/*.yaml`

## GUIs / CLIs

- Qt/Kirigami GUI: `src/linux_arctis_manager/gui/*` with QML views in `gui/qml/*.qml` and backend in `gui/backend.py`
- GTK/libadwaita GUI: `src/linux_arctis_manager/gui_gtk/*` (notably `app.py` contains the window and EQ canvas)
- Systray (GTK3/AppIndicator): `src/linux_arctis_manager/scripts/systray.py`
- CLI utilities: `src/linux_arctis_manager/scripts/cli.py`

## Diagrams (as text)

```
[lam-daemon]
  ├─ CoreEngine (USB, status loop, settings apply)
  │    ├─ usb.core (read/write HID)
  │    ├─ PulseAudioManager (create Arctis_Media/Arctis_Chat, redirect)
  │    ├─ DeviceConfiguration (YAML)
  │    ├─ DeviceSettings (YAML) + EqStore (JSON)
  │    └─ USBDevicesMonitor (pyudev)
  └─ DbusManager
       ├─ Settings iface (Get/Set/Changed, lists)
       ├─ Status iface (Get/Changed)
       └─ Config iface (Reload)

Frontends (session processes)
  ├─ lam-gui (Qt/QML) ── D-Bus → Settings/Status
  ├─ lam-gui-gtk (GTK) ── D-Bus → Settings/Status
  └─ lam-systray ── D-Bus → Status
```

```
USB connect → USBDevicesMonitor.on_connect
  → CoreEngine.configure_virtual_sinks
    → Claim HID interfaces; init_device(); request_device_status()
    → PulseAudioManager.sinks_setup() → create Arctis_Media/Arctis_Chat
    → Apply persisted EQ bank for current target

CoreEngine.loop
  → send status request → read IN endpoints → map + parse → ObservableDict update
  → D-Bus StatusChanged(JSON)

Client SetSetting(name, valueJSON)
  → SettingsService.validates → writes YAML/JSON → CoreEngine.on_setting_changed
  → build USB command(s) → usb write/ctrl_transfer
```

## Architectural Risks / Debt

- Very large monolithic GTK UI (`src/linux_arctis_manager/gui_gtk/app.py`, ~2.4k lines) reduces maintainability; consider modularization
- Mixed concurrency model (asyncio + threads + USB I/O + D-Bus loops) can introduce race conditions (e.g., `self.usb_device` mutated mid-loop). Guarding exists but warrants caution
- Unauthenticated D-Bus API on session bus; any local app can mutate settings. Consider policy or scoping if needed
- JSON-over-D-Bus lacks strict schema; clients must be tolerant to shape changes
- File-based stores (`settings.py`, `eq_store.py`) have no explicit locking; concurrent writers could race
- Multi-frontend (Qt and GTK) increases feature parity burden and duplication
- Reliance on PulseAudio modules (null-sink/loopback) may be distro/profile-dependent; error handling is present but users may still hit env issues

---

*Architecture analysis: 2026-03-30*
