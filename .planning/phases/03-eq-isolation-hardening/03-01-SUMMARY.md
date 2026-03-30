---
phase: 03-eq-isolation-hardening
plan: 01
subsystem: gui-gtk
tags: [gtk4, eq, presets, tests]
requires: [EQISO-01, EQISO-02, EQISO-03, EQISO-04]
provides: [eq-isolation, tab-target-sync, friendly-preset-display]
tech-stack:
  added: [pytest]
  patterns: [Adw.ViewStack tabs, GLib main context loop]
key-files:
  created: []
  modified:
    - tests/gui_gtk/test_eq_isolation_ui.py
    - src/linux_arctis_manager/gui_gtk/app.py
    - src/linux_arctis_manager/gui_gtk/preset_manager.py
decisions: []
metrics:
  duration_sec: 246
  completed_at: 2026-03-30T20:34:17Z
---

# Phase 03 Plan 01: EQ isolation hardening Summary

One-liner: Three independent parametric EQ canvases with tab→eq_target sync verified; friendly preset names displayed without 'GG:' prefix.

## What Changed

- Added and executed integration-style GTK tests verifying per-tab EQ isolation and tab-to-eq_target synchronization, plus friendly preset display without 'GG:' prefixes.
- Ensured the Equalizer ViewStack is constructed even when the device is offline, so tab switching still updates eq_target and tests can run headlessly.
- Fixed PresetManager API issues and test isolation so pytest can reliably validate behavior.

## Commits

- da9164d: fix(03-01): enable EQ ViewStack offline; verify isolation and target sync
- 9d88fae: fix(03-01): make SETTINGS_FOLDER monkeypatchable in tests

## Tests and Results

- Task 1 (isolation/target): .venv/bin/pytest -q tests/gui_gtk/test_eq_isolation_ui.py -k "isolation or target" → PASS
- Task 2 (friendly names): .venv/bin/pytest -q tests/gui_gtk/test_eq_isolation_ui.py -k friendly → PASS
- Regression suite: .venv/bin/pytest -q → PASS (skipped some GUI-dependent tests as expected)

## Deviations from Plan

### Auto-fixed Issues

1. [Rule 1 - Bug] EQ tabs not built when offline prevented tab→eq_target sync
- Found during: Task 1
- Issue: refresh_settings_ui short-circuited entire settings sections when offline, so _eq_stack was never created in tests.
- Fix: Build the Equalizer ViewStack regardless of offline state (keep groups hidden when offline). Connect tab change handler to set_eq_target and update only the visible canvas.
- Files modified: src/linux_arctis_manager/gui_gtk/app.py
- Commit: da9164d

2. [Rule 1 - Bug] PresetManager.delete_parametric_preset not accessible due to bad indentation
- Found during: Task 1
- Issue: Method was inadvertently nested under friendly_preset_name and not part of PresetManager.
- Fix: Implement delete_parametric_preset as a proper PresetManager method.
- Files modified: src/linux_arctis_manager/gui_gtk/preset_manager.py
- Commit: da9164d

3. [Rule 1 - Bug] GTK4 main loop pump in tests
- Found during: Task 1
- Issue: Tests used Gtk.events_pending()/Gtk.main_iteration_do, which are GTK3 patterns.
- Fix: Use GLib.MainContext.default().pending()/iteration(False) for GTK4-compatible event flushing.
- Files modified: tests/gui_gtk/test_eq_isolation_ui.py
- Commit: da9164d

4. [Rule 1/3 - Test isolation] SETTINGS_FOLDER bound at import time blocked monkeypatching
- Found during: Regression run
- Issue: preset_manager imported SETTINGS_FOLDER directly; pytest monkeypatch of linux_arctis_manager.constants.SETTINGS_FOLDER did not affect it.
- Fix: Import constants module and reference C.SETTINGS_FOLDER at runtime so per-test tmp paths apply.
- Files modified: src/linux_arctis_manager/gui_gtk/preset_manager.py
- Commit: 9d88fae

### Auth Gates

None.

## Known Stubs

None detected.

## Verification Steps

1) Isolation/target tests: .venv/bin/pytest -q tests/gui_gtk/test_eq_isolation_ui.py -k "isolation or target"
2) Friendly preset display: .venv/bin/pytest -q tests/gui_gtk/test_eq_isolation_ui.py -k friendly
3) Regression: .venv/bin/pytest -q

## Self-Check: PASSED

- Found summary file at .planning/phases/03-eq-isolation-hardening/03-01-SUMMARY.md
- Found commits da9164d and 9d88fae in repo history
