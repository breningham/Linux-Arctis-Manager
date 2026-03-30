# External Integrations

**Analysis Date:** 2026-03-30

## APIs & External Services

**Audio (PulseAudio/PipeWire-pulse):**
- Purpose: Manage default sink, create/remove virtual sinks, set per-stream volume for Media/Chat.
  - SDK/Client: pulsectl (Python) 24.12.0
  - Code: `src/linux_arctis_manager/pactl.py`
  - Virtual nodes: `PULSE_MEDIA_NODE_NAME` = "Arctis_Media", `PULSE_CHAT_NODE_NAME` = "Arctis_Chat" (`src/linux_arctis_manager/constants.py`)
  - Modules loaded: `module-null-sink`, `module-loopback` (via pulsectl `module_load`) (`src/linux_arctis_manager/pactl.py` lines 79–90, 85–90)
  - System libs: libpulse (CI installs `libpulse0`) (`.github/workflows/wheel-install-test.yaml`)

**D-Bus (session bus):**
- Purpose: IPC between daemon and frontends (settings and status).
  - SDK/Client: dbus-next 0.2.3
  - Server: `src/linux_arctis_manager/dbus_service.py`
  - Client (GTK): `src/linux_arctis_manager/gui_gtk/dbus_client.py`
  - Bus name: `name.giacomofurlan.ArctisManager.Next`
  - Interfaces/paths (see `docs/dbus.md`):
    - Settings: `DBUS_SETTINGS_INTERFACE_NAME` at `DBUS_SETTINGS_OBJECT_PATH`
      - Methods: GetSettings, SetSetting, GetListOptions, SetEqTarget
      - Signals: SettingsChanged
    - Status: `DBUS_STATUS_INTERFACE_NAME` at `DBUS_STATUS_OBJECT_PATH`
      - Methods: GetStatus
      - Signals: StatusChanged
    - Config: `DBUS_CONFIG_INTERFACE_NAME` at `DBUS_CONFIG_OBJECT_PATH`
      - Methods: ReloadConfigs

**USB (HID/control transfers):**
- Purpose: Communicate with SteelSeries devices (read status, write settings, init sequences).
  - Library: pyusb 1.3.1 (`src/linux_arctis_manager/core.py`)
  - Hotplug monitor: pyudev 0.24.4 (`src/linux_arctis_manager/usb_devices_monitor.py`)
  - Kernel driver detach/attach and interface claiming handled in code (`core.py`: `kernel_detach`, `kernel_attach`)

**udev (rules and reload):**
- Purpose: Grant user access to USB devices and trigger permissions.
  - CLI: `udevadm control --reload-rules`, `udevadm trigger --subsystem-match=usb`
  - Rules path candidates: `/etc/udev/rules.d/91-steelseries-arctis.rules`, `/usr/lib/udev/rules.d/91-steelseries-arctis.rules` (`src/linux_arctis_manager/constants.py`)
  - Managed by: `lam-cli udev write-rules --force --reload` (`src/linux_arctis_manager/scripts/cli.py`)

**Systemd (user service):**
- Purpose: Manage the background daemon lifecycle.
  - Service name: `arctis-manager.service` (`src/linux_arctis_manager/constants.py`)
  - Writer: `src/linux_arctis_manager/systemd.py` (writes service, enables via `systemctl --user`)
  - ExecStart target: `lam-daemon` (`systemd.py` resolves via PATH)

**Desktop integration:**
- Purpose: Menu entries and autostart entries for Qt/GTK frontends.
  - Files: `src/linux_arctis_manager/desktop/*.desktop`
  - Writer: `lam-cli desktop write/remove` (`src/linux_arctis_manager/scripts/cli.py`)
  - Installs icon to `$HOME/.local/share/icons/arctis-manager.svg`

**Privilege elevation:**
- Purpose: Write udev rules when not writable by user.
  - CLI: `pkexec` (polkit) invoked by `lam-cli` when needed (`src/linux_arctis_manager/scripts/cli.py`)

**CI:**
- Service: GitHub Actions
  - Workflow: `.github/workflows/wheel-install-test.yaml` builds the wheel with `uv build` and test-installs across Fedora/Ubuntu/Debian/Arch containers.

## Data Storage

**Databases:**
- Not applicable (no DB layer)

**File Storage:**
- General settings YAML: `~/.config/arctis_manager/settings/general_settings.yaml` (`src/linux_arctis_manager/settings.py`)
- Per-device settings YAML: `~/.config/arctis_manager/settings/{vendor}_{product}.yaml` (`src/linux_arctis_manager/settings.py`)
- Parametric EQ state: `~/.config/arctis_manager/settings/eq_state.json` (`src/linux_arctis_manager/eq_store.py`)
- Device definitions (read-only defaults): `src/linux_arctis_manager/devices/*.yaml` with optional user overrides in `~/.config/arctis_manager/devices/*.yaml` (`src/linux_arctis_manager/config.py`, `src/linux_arctis_manager/constants.py`)

**Caching:**
- None detected beyond local JSON/YAML state files

## Authentication & Identity

**Auth Provider:**
- Local system polkit (`pkexec`) for privileged write of udev rules. No network identity providers.

**Implementation:**
- `lam-cli` detects non-writable destinations and shells out to `pkexec` (`src/linux_arctis_manager/scripts/cli.py`)

## Monitoring & Observability

**Error Tracking:**
- None external; Python logging throughout (`src/linux_arctis_manager/pactl.py`, `src/linux_arctis_manager/core.py`, `src/linux_arctis_manager/dbus_service.py`)

**Logs:**
- Stdout/stderr from CLI/daemon; no structured log export.

## CI/CD & Deployment

**Hosting:**
- GitHub repository; user installs via pipx-installed wheel (`install.sh`)

**CI Pipeline:**
- GitHub Actions matrix validates build/install across distros (`.github/workflows/wheel-install-test.yaml`)

## Environment Configuration

**Required env vars:**
- None detected.

**Secrets location:**
- None used. `.env` exists at repo root but is not referenced by application code.

**System configuration sources:**
 - Udev rules: `/etc/udev/rules.d/91-steelseries-arctis.rules` or `/usr/lib/udev/rules.d/91-steelseries-arctis.rules` (`src/linux_arctis_manager/constants.py`, `src/linux_arctis_manager/scripts/cli.py`)
 - Systemd user unit: `~/.config/systemd/user/arctis-manager.service` (`src/linux_arctis_manager/systemd.py`)
 - Desktop entries: `~/.local/share/applications/dev.ingham.lam-gui.{qt,gtk}.desktop` and autostart entries in `~/.config/autostart/dev.ingham.lam-systray.{qt,gtk}.desktop` (`src/linux_arctis_manager/desktop/*.desktop`, `src/linux_arctis_manager/scripts/cli.py`)
## Protocols, Limits, and Failure Modes

**PulseAudio (pulsectl):**
- Protocol: libpulse client API via pulsectl
- Behavior: Creates `module-null-sink` + `module-loopback`; sets default sink and per-sink volumes
- Failure modes:
  - pulsectl.PulseError on server startup/race; retried up to 15 times with 1s delay (`sink_list_wrapper` in `src/linux_arctis_manager/pactl.py`)
  - Missing `libpulse` library -> import/runtime failure (CI ensures package)
  - Virtual sink not found when setting default -> logs error (`redirect_audio`)

**USB (pyusb):**
- Protocol: Bulk/control transfers and HID-like SET_REPORT depending on config (`src/linux_arctis_manager/core.py`)
- Failure modes:
  - `usb.core.USBError` errno 16 (busy), 32, 110 (timeout) handled with warnings/teardown
  - Permissions denied without udev rules; requires uaccess rule written by `lam-cli udev write-rules`
  - Kernel driver busy on interfaces; code detaches and claims (`kernel_detach`/`kernel_attach`)

**udev/privilege (pkexec):**
- Protocol: polkit prompt for elevated writes
- Failure modes:
  - `pkexec` not installed -> CLI returns 250 (`src/linux_arctis_manager/scripts/cli.py`)
  - User cancels elevation -> rules not written/reloaded

**D-Bus (dbus-next):**
- Protocol: D-Bus over session bus; JSON payloads for methods/signals
- Failure modes:
  - Bus unavailable -> connection warnings in GTK client (`src/linux_arctis_manager/gui_gtk/dbus_client.py`)
  - Malformed JSON in SetSetting -> returns False with error log (`src/linux_arctis_manager/dbus_service.py`)

**Systemd (user):**
- Protocol: `systemctl --user is-enabled|enable --now`
- Failure modes:
  - `lam-daemon` not in PATH -> service file ExecStart invalid; writer resolves path heuristically (`src/linux_arctis_manager/systemd.py`)
  - systemd user not available (non-systemd session) -> commands fail

## Local Dev Stubs/Mocks

- Tests monkeypatch paths and IO to avoid hardware/system side effects:
  - Override `SETTINGS_FOLDER` to temp dir (`tests/core/test_core_eq_integration.py` fixture)
  - Stub CoreEngine methods that touch USB/PulseAudio in tests (`tests/core/test_core_eq_integration.py`)
  - Use in-memory `StubCore` for D-Bus settings serialization tests (`tests/daemon/test_dbus_settings.py`)

## Webhooks & Callbacks

**Incoming:**
- None (no HTTP/webhooks)

**Outgoing:**
- None

---

*Integration audit: 2026-03-30*
