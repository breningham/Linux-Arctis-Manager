### Phase 01: gui-stability

Goal: Polish the GTK GUI for stability and UX, fixing node editor popover behavior and EQ visualization/state bugs so the app feels responsive and reliable.

Requirements:
- GUI-01: Node editor popover closes reliably on outside click after changing band type; no UI lockups.
- GUI-02: EQ state is isolated per target (2.4GHz Headphones, Bluetooth Headphones, 2.4GHz Microphone); editing one does not affect the others.
- GUI-03: On hover/selection, at most one highlight curve is rendered for the current EQ type (no duplicate lines).

**Plans:** 3/3 plans complete

Plans:
- [x] 01-01-PLAN.md — Fix stuck node editor popover behavior
- [x] 01-02-PLAN.md — TDD: single highlight per EQ type via eq_math
- [x] 01-03-PLAN.md — Ensure EQ state isolation across targets with tests

### Phase 02: eq-ux-polish

Goal: Refine EQ user experience by guaranteeing the editor popover always closes after type changes and by cleaning preset naming to remove debug prefixes while preserving correct behavior.

Requirements:
- GUI-04: After changing a band Type, clicking outside reliably closes the editor (explicit popdown safety) and no stuck popovers occur.
- GUI-05: Preset list displays friendly names without the "GG:" prefix while selection, deletion rules, and cache mapping still operate on the original keys.

**Plans:** 1/1 plans planned

Plans:
- [ ] 02-01-PLAN.md — Close editor on Type change and show friendly preset names
