---
phase: 05-audio-routing-resilience
plan: 05-02
subsystem: core+gtk
tags: [parametric-eq, alias, gtk, smoke-test]
requires: [AR-03, AR-04]
provides: [parametric-alias, gtk-offline-hero]
affects: [CoreEngine.on_setting_changed, GUI offline state]
tech_stack:
  added: []
  patterns: [alias-resolution, ui-smoke-test]
key_files:
  created:
    - tests/core/test_core_parametric_alias.py
    - tests/gui_gtk/test_smoke_offline_hero.py
  modified:
    - src/linux_arctis_manager/core.py
decisions: []
metrics:
  started: 2026-03-31T10:00:56Z
  completed: 2026-03-31T10:04:47Z
  duration: ~3m51s (overlapped in phase run)
---

# Phase 05 Plan 02: Parametric EQ alias + GTK smoke Summary

One-liner: CoreEngine now resolves the 'parametric_eq' alias to the configured PARAMETRIC_EQ setting; added GTK smoke test to ensure offline hero renders non-blank.

## What Changed

- CoreEngine.on_setting_changed: If setting is 'parametric_eq' and not found by name, resolve to the first configuration whose type is PARAMETRIC_EQ, preserving existing EqStore persistence and USB packing logic.
- Added unit test to exercise alias mapping when the config names the setting 'equalizer'.
- Added GTK smoke test that constructs ArctisManagerWindow with a stub D-Bus client and validates that the offline/disconnected hero is visible with non-empty title/description.

### Tasks & Commits

1) Map 'parametric_eq' alias to actual PARAMETRIC_EQ config (AR-03)
- Commit: 6e7c52a — feat(05-02): map 'parametric_eq' alias to PARAMETRIC_EQ config
- Files: src/linux_arctis_manager/core.py, tests/core/test_core_parametric_alias.py

2) GTK smoke: verify offline hero renders (AR-04)
- Commit: 265f47f — test(05-02): GTK smoke test ensures offline hero renders
- Files: tests/gui_gtk/test_smoke_offline_hero.py

## Verification

Planned test commands:
- pytest -q tests/core -q
- pytest -q tests/gui_gtk/test_smoke_offline_hero.py -q

Result: Not executed in this environment (pytest not available). Note: PyGObject appears importable, but without pytest we did not run the suite. Execute on a dev machine/CI with project deps installed.

## Success Criteria Evaluation

- No 'Unknown setting: parametric_eq' warning: Addressed by alias resolution; validated by unit test logic (pending execution).
- GTK opens with offline hero (non-blank) when device is offline: Covered by smoke test that simulates no-device state.

## Deviations from Plan

### Auto-fixed / Adjustments

- [Rule 3 - Blocking] Test execution blocked by missing pytest
  - Action: Wrote tests and guarded GTK test with skip-if-GTK-missing. Execution deferred to CI/dev environment.

## Known Stubs

- None introduced by this plan.

## Self-Check: PASSED

- FOUND: .planning/phases/05-audio-routing-resilience/05-02-SUMMARY.md
- FOUND commit: 6e7c52a (parametric alias)
- FOUND commit: 265f47f (GTK smoke test)
