---
phase: 02-eq-ux-polish
plan: 01
subsystem: [ui]
tags: [gtk4, libadwaita, presets, testing, pytest]

# Dependency graph
requires: []
provides:
  - EQ popover lifecycle safety on Type change
  - Friendly preset display naming with real-key mapping
affects: [eq, ui, presets]

# Tech tracking
tech-stack:
  added: [pytest (venv scoped)]
  patterns: [Parallel real_names/display names for ComboRow models]

key-files:
  created: [src/linux_arctis_manager/gui_gtk/preset_manager.py, tests/gui_gtk/test_preset_naming.py]
  modified: [src/linux_arctis_manager/gui_gtk/app.py]

key-decisions:
  - "None - followed plan as specified"

patterns-established:
  - "UI uses friendly names for display while preserving canonical keys for logic and persistence"

requirements-completed: [GUI-04, GUI-05]

# Metrics
duration: 4m
completed: 2026-03-30
---

# Phase 02 Plan 01: EQ UX Polish Summary

Explicit EQ editor popover dismissal on Type change and friendly preset display names with index-based mapping to original keys, verified by unit tests

## Performance

- Duration: ~4m
- Started: 2026-03-30T18:43:19Z
- Completed: 2026-03-30T18:47:23Z
- Tasks: 2
- Files modified: 3

## Accomplishments
- Prevented stuck EQ editor popover by explicitly popping it down after Type changes
- Introduced friendly_preset_name helper and applied parallel real/display name lists to ComboRow models
- Preserved correct selection mapping, cache persistence, and delete visibility for built-in vs custom presets

## Task Commits

1. Task 1: Ensure EQ editor popover closes after Type change (per GUI-04) - `51a70af` (fix)
2. Task 2: Show friendly preset names without "GG:" while mapping to real keys (per GUI-05) - `68e3f9e` (feat)

Plan metadata commit added separately below.

## Files Created/Modified
- src/linux_arctis_manager/gui_gtk/app.py - Added explicit popover.popdown() on Type change and wired friendly display mapping
- src/linux_arctis_manager/gui_gtk/preset_manager.py - Added friendly_preset_name helper and cache utilities (tracked)
- tests/gui_gtk/test_preset_naming.py - Unit tests for naming and builtin behavior

## Decisions Made
None - followed plan as specified

## Deviations from Plan

### Auto-fixed Issues

1. [Rule 3 - Blocking] Test runner not available in system Python
- Found during: Task 2 (running pytest)
- Issue: `pytest` and `pip` unavailable in system-managed Python (PEP 668)
- Fix: Created local virtual environment `.venv`, installed test deps from tests/requirements.txt, ran tests via venv
- Files modified: (no repo files modified for env creation)
- Verification: `./.venv/bin/pytest -q tests/gui_gtk/test_preset_naming.py` passed

---

Total deviations: 1 auto-fixed (1 blocking)
Impact on plan: Necessary to run tests; no scope creep.

## Issues Encountered
- None beyond the local test environment bootstrapping noted above

## Known Stubs
- UI placeholder label text "Custom-1" for save entry is intentional and not a data stub

## Next Phase Readiness
- EQ UI polish complete for this plan; ready for broader UX refinements if scoped in future phases

## Self-Check: PASSED
All expected files and commits found:
- FOUND: .planning/phases/02-eq-ux-polish/02-01-SUMMARY.md
- FOUND: 51a70af
- FOUND: 68e3f9e
