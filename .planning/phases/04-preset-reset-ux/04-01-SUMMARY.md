---
phase: 04-preset-reset-ux
plan: 01
subsystem: [ui, testing]
tags: [gtk, libadwaita, python, pytest, eq, presets]

# Dependency graph
requires: []
provides:
  - Pure reset visibility/target logic for EQ
  - Unit tests covering graphic and parametric reset behavior
affects: [04-preset-reset-ux, ui, eq]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Pure function helpers for UI logic", "TDD: tests-first for behavior"]

key-files:
  created: [src/linux_arctis_manager/gui_gtk/eq_ui_logic.py, tests/gui_gtk/test_eq_ui_logic.py]
  modified: []

key-decisions:
  - "Honor UX decision: reset restores the selected preset, not Flat (D-01)"
  - "Show Reset only when current values differ from the selected preset (D-02)"

patterns-established:
  - "Keep UI decision logic in pure, testable modules"
  - "Parametric comparisons use tolerance-based values_match (gains only)"

requirements-completed: [PR-01, PR-02]

# Metrics
duration: ~5min
completed: 2026-03-30
---

# Phase 04 Plan 01: Pure reset logic Summary

Reset-to-preset behavior implemented as pure helpers with TDD, covering graphic equality and parametric tolerance via values_match.

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-30T20:54:26Z
- **Completed:** 2026-03-30T20:59:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added should_show_reset and get_reset_target pure helpers
- Tests cover graphic exact equality and parametric tolerance-based matching
- No GTK/UI imports; logic is isolated and reusable

## Task Commits

Each task was committed atomically:

1. Task 0: Add failing tests for reset logic (TDD RED) - `08ffcc9` (test)
2. Task 1: Implement eq_ui_logic to make tests pass - `770f003` (feat)

## Files Created/Modified
- src/linux_arctis_manager/gui_gtk/eq_ui_logic.py - Pure reset visibility/target helpers
- tests/gui_gtk/test_eq_ui_logic.py - Unit tests for logic

## Decisions Made
- Followed plan decisions D-01 and D-02 exactly; no additional choices required

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Local pytest command not available; used project virtualenv `.venv/bin/pytest` to run tests. No code changes required. [Tracked as normal tooling usage]

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Logic helpers ready for UI wiring in Plan 04-02; import path verified in tests.

## Self-Check: PASSED

FOUND: src/linux_arctis_manager/gui_gtk/eq_ui_logic.py
FOUND: tests/gui_gtk/test_eq_ui_logic.py
FOUND: 08ffcc9
FOUND: 770f003

---
*Phase: 04-preset-reset-ux*
*Completed: 2026-03-30*
