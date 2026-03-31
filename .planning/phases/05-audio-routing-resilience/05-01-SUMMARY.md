---
phase: 05-audio-routing-resilience
plan: 05-01
subsystem: daemon/audio-routing
tags: [pulseaudio, dbus, resilience, tests]
requires: [AR-01, AR-02]
provides: [robust-device-options, resilient-redirect]
affects: [GUI settings select, CoreEngine.redirect_audio_on_disconnect]
tech_stack:
  added: []
  patterns: [fallback-selection, prioritized-matching]
key_files:
  created:
    - tests/daemon/test_pulse_device_options.py
    - tests/daemon/test_pactl_redirect.py
  modified:
    - src/linux_arctis_manager/dbus_service.py
    - src/linux_arctis_manager/pactl.py
decisions: []
metrics:
  started: 2026-03-31T10:00:56Z
  completed: 2026-03-31T10:04:47Z
  duration: ~3m51s
---

# Phase 05 Plan 01: PulseAudio options + redirect Summary

One-liner: Robust PulseAudio device options via stable ids and resilient sink redirection using prioritized property matching.

## What Changed

- Implemented robust options list for PulseAudio devices on D-Bus settings API, prioritizing node.name as stable id and node.nick/description for user labels, with fallbacks to device.* and sink.name.
- Hardened audio redirection by introducing a helper that matches sinks by exact node.name, then node.nick, then node.description, and finally case-insensitive substring across nick/description.
- Added daemon tests to validate both behaviors.

### Tasks & Commits

1) Implement robust PulseAudio device options (AR-01)
- Commit: 472c73e — feat(05-01): robust PulseAudio device options list
- Files: src/linux_arctis_manager/dbus_service.py, tests/daemon/test_pulse_device_options.py

2) Harden redirect_audio sink matching (AR-02)
- Commit: 4102186 — feat(05-01): harden redirect_audio sink matching
- Files: src/linux_arctis_manager/pactl.py, tests/daemon/test_pactl_redirect.py

## Verification

Planned test commands:
- pytest -q tests/daemon -q

Result: Not executed in this environment (pytest and runtime deps unavailable). Manual smoke-run attempted but import dependencies (dbus-next, pulsectl) are not installed; see Deviations.

## Success Criteria Evaluation

- Dropdown shows real sinks even when node.nick is absent: Implemented via multi-source fallback; validated by unit tests (pending execution).
- Redirecting to a human-entered device like "Soundbar" succeeds: Implemented with substring matching; validated by unit tests (pending execution).

## Deviations from Plan

### Auto-fixed / Adjustments

- [Rule 3 - Blocking] Test execution blocked by missing tooling
  - Issue: pytest and Python deps (dbus-next, pulsectl) not available; could not run tests.
  - Action: Wrote tests as specified and verified logic by code review. Execution deferred to CI/dev machine with dependencies.
  - Impact: No runtime validation performed here; behavior covered by unit tests once environment is provisioned.

## Known Stubs

- None introduced by this plan.

## Self-Check: PASSED

- FOUND: .planning/phases/05-audio-routing-resilience/05-01-SUMMARY.md
- FOUND commit: 472c73e (device options)
- FOUND commit: 4102186 (redirect matching)
