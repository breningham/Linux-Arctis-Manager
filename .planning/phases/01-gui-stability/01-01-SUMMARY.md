---
phase: 01-gui-stability
plan: 01
subsystem: [ui]
tags: [gtk4, libadwaita, popover, gesture]

# Dependency graph
requires: []
provides:
  - Reliable EQ popover lifecycle (outside-click + type-change closes)
affects: [equalizer, canvas-interaction]

# Tech tracking
tech-stack:
  added: []
  patterns: ["No input grabbing for transient editors; rely on autohide + outside-click handling"]

key-files:
  created: []
  modified: [src/linux_arctis_manager/gui_gtk/app.py]

key-decisions:
  - "Kept canvas can_target enabled while popover is open to allow outside-click close"

patterns-established:
  - "Use popover.autohide + click gestures to dismiss transient editors"

requirements-completed: [GUI-01]

# Metrics
duration: 1m
completed: 2026-03-30
---

# Phase 01: GUI Stability — Plan 01 Summary

EQ editor popover now reliably closes on outside click and immediately after Type changes, removing the input grab so the canvas remains responsive.

## Performance

- **Duration:** ~1m
- **Started:** 2026-03-30T00:00:00Z
- **Completed:** 2026-03-30T00:00:32Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Removed input grabbing in EQCanvas._show_popover so outside clicks reach the canvas and autohide works
- Added defensive popover closed hook to reset hover/cursor state
- On Type change, explicitly pop down the editor to avoid any stuck state

## Task Commits

1. **Task 1: Make popover reliably closable via outside click** - `0524429` (fix)
2. **Task 2: Close editor on explicit Type change commit (safety net)** - `7214f02` (fix)

## Files Created/Modified
- `src/linux_arctis_manager/gui_gtk/app.py` - Popover lifecycle and event handling adjustments

## Decisions Made
None - followed plan as specified.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed test dependencies to run pytest**
- **Found during:** Task 1
- **Issue:** pytest not available in environment
- **Fix:** Created `.venv` and installed tests/requirements.txt locally for verification
- **Files modified:** (none committed — local environment only)
- **Verification:** Pytest ran successfully; suite passed with some skips

---

**Total deviations:** 1 auto-fixed (blocking)
**Impact on plan:** Environment-only change to enable verification.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
Wave 1 complete. Enables Wave 2 work that depends on stable popover interaction.

---
*Phase: 01-gui-stability*
*Completed: 2026-03-30*

## Self-Check: PASSED

FOUND: src/linux_arctis_manager/gui_gtk/app.py
FOUND: 0524429
FOUND: 7214f02
