### Phase 01: gui-stability

Goal: Polish the GTK GUI for stability and UX, fixing node editor popover behavior and EQ visualization/state bugs so the app feels responsive and reliable.

Requirements:
- GUI-01: Node editor popover closes reliably on outside click after changing band type; no UI lockups.
- GUI-02: EQ state is isolated per target (2.4GHz Headphones, Bluetooth Headphones, 2.4GHz Microphone); editing one does not affect the others.
- GUI-03: On hover/selection, at most one highlight curve is rendered for the current EQ type (no duplicate lines).

**Plans:** 3 plans

Plans:
- [ ] 01-01-PLAN.md — Fix stuck node editor popover behavior
- [ ] 01-02-PLAN.md — TDD: single highlight per EQ type via eq_math
- [ ] 01-03-PLAN.md — Ensure EQ state isolation across targets with tests
