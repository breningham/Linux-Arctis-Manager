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

**Plans:** 1/1 plans complete

Plans:
- [x] 02-01-PLAN.md — Close editor on Type change and show friendly preset names

### Phase 03: eq-isolation-hardening

Goal: Eliminate any remaining cross-tab state leaks by rendering three independent Parametric EQ canvases/controllers (Wireless, Bluetooth, Mic) with per-target cache binding, ensure D-Bus eq_target stays in sync with the active tab and only the visible canvas updates, and add automated tests to prevent regressions. Also finalize preset naming polish so UI shows friendly names without "GG:" while internal keys remain unchanged.

Requirements:
- EQISO-01: Three independent Parametric EQ canvases/controllers exist (Wireless, Bluetooth, Mic), each bound to its own state model and EqStateCache key; editing one does not affect the others.
- EQISO-02: D-Bus eq_target switches are synchronized with the active tab, and only the visible canvas updates when settings change.
- EQISO-03: Automated tests prove isolation and that inactive targets do not mutate during tab switches; regression suite runs under pytest.
- EQISO-04: Preset lists display friendly names without the "GG:" prefix across GTK views; selection/deletion/cache mapping still operate on the original keys.

**Plans:** 1 plan

Plans:
- [ ] 03-01-PLAN.md — Tests to harden EQ isolation and tab-target sync; verify friendly preset display
