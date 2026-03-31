# Release Plan: v2.3.0

Goal
- Ship v2.3.0 with EQ UX/stability improvements: reliable editor popover, per-target isolation, friendly preset names, and Reset-to-Preset in revealer for Parametric and Graphic EQ. Includes new unit/integration tests to prevent regressions.

Version
- Current: 2.3.0-dev (pyproject.toml)
- Proposed release: 2.3.0
- Previous tag: v2.2.1

Scope Summary
- GUI (GTK):
  - Fix node editor popover closing after Type change and on outside click
  - Single highlight per EQ type; extracted pure eq_math and integrated into canvas
  - Isolation hardened across Wireless/BT/Mic with tab→eq_target sync
  - Friendly preset display names (remove "GG:") while preserving internal keys
  - Reset-to-Preset action: only shows when modified, placed in revealer, destructive style; works for Parametric and Graphic EQ
- Tests: Added unit and lightweight integration tests for eq_math, preset naming, isolation, and UI logic
- Planning docs: Codebase map and phased plans/summaries

Changelog Since v2.2.1 (highlights)
- Features
  - Introduce pure eq_math and drive canvas rendering with it (3a49fee)
  - Friendly preset display names with real-key mapping (68e3f9e)
  - Parametric/Graphic EQ Reset-in-revealer using pure logic (7fddf31, e8ea5c9)
  - Add CLI entry point: lam-systray (pyproject) (pyproject change)
- Fixes
  - Make popover closable via outside click and after Type change (0524429, 7214f02, 51a70af)
  - Guard canvas updates by active mode and visible tab (44a3e42)
  - Enable EQ ViewStack offline; improve tab→eq_target sync (da9164d)
  - Make settings folder monkeypatchable for tests (9d88fae)
  - Multiple QML/Qt frontend improvements and bug fixes
- Tests/Docs
  - Add tests for eq_math, EqStateCache isolation, preset naming, and isolation UI (c4f015a, a0a13b2, tests under tests/gui_gtk)
  - Planning docs for phases 01-04 and codebase map (.planning/codebase/*.md)

Release Checklist
1. Ensure clean working tree and CI is green
2. Bump version in pyproject.toml from 2.3.0-dev → 2.3.0
3. Build artifacts
   - uv build
4. Run tests locally
   - pytest -q
5. Tag the release (signed if configured)
   - git tag -s v2.3.0 -m "v2.3.0"  # or git tag v2.3.0
   - git push origin v2.3.0
6. Push branch (if not already)
   - git push origin develop
7. Create GitHub Release
   - Title: v2.3.0
   - Body: Paste "Changelog Since v2.2.1" from this plan (or CHANGELOG)
   - Upload built wheels/sdist from dist/
8. (Optional) Publish to PyPI
   - Ensure credentials configured
   - uv publish  # or twine upload dist/*
9. Verify install paths
   - pipx install --force dist/*linux_arctis_manager*.whl
   - Launch: lam-gui-gtk and exercise flows below
10. Announce
   - Post in project channels; link release notes and installation steps

Verification (Manual QA)
- Launch GTK UI (lam-gui-gtk):
  - Change EQ Type then click outside: editor closes; no UI lockups
  - Hover/single-select shows only one highlight curve per type
  - Switch between Wireless/BT/Mic tabs: values remain isolated; only visible canvas updates
  - Preset dropdown shows friendly names; underlying key behavior (selection/delete/cache) correct
  - Modify values while on a preset: Reset button appears in revealer, destructive style; click resets to preset values

Backout Plan
- If regressions are found after tag:
  - Revert problematic commits; create hotfix branch
  - Patch release: bump to 2.3.1, build, test, tag, and release

Ownership
- Release lead: @breningham
- QA: contributors

Artifacts
- This file: .planning/release/RELEASE_PLAN.md
- Changelog: .planning/release/CHANGELOG-2.3.0.md
