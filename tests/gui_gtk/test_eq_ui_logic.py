import copy
import pytest


def _make_graphic_presets():
    return {
        "Smiley": [4.0, 2.0, 0.0, -1.0, -2.0, -2.0, -1.0, 0.0, 2.0, 4.0],
        "Flat": [0.0] * 10,
    }


def _make_parametric_presets():
    # Use the real project presets to validate integration of values_match behavior
    from linux_arctis_manager.gui_gtk.preset_manager import (
        PARAMETRIC_EQ_PRESETS,
    )

    # Shallow copy to avoid mutation of module constant
    return {k: list(v) for k, v in PARAMETRIC_EQ_PRESETS.items()}


class TestEqUiLogic:
    def test_graphic_visibility_true_when_values_differ(self):
        presets = _make_graphic_presets()
        selected = "Smiley"
        # Modify first band to ensure difference
        current = list(presets[selected])
        current[0] += 1.0

        from linux_arctis_manager.gui_gtk.eq_ui_logic import should_show_reset

        assert should_show_reset(selected, current, presets, mode="graphic") is True

    def test_graphic_visibility_false_when_values_equal_and_target_correct(self):
        presets = _make_graphic_presets()
        selected = "Smiley"
        current = list(presets[selected])

        from linux_arctis_manager.gui_gtk.eq_ui_logic import (
            should_show_reset,
            get_reset_target,
        )

        assert should_show_reset(selected, current, presets, mode="graphic") is False
        target = get_reset_target(selected, presets)
        # Should be a copy, not the same object
        assert target == presets[selected]
        assert target is not presets[selected]

    def test_parametric_visibility_uses_values_match_tolerance(self):
        presets = _make_parametric_presets()
        selected = "Arc Raiders"
        base = presets[selected]
        assert len(base) == 40  # safety

        # Gains are at indices 1,5,9,...; tweak a gain within tolerance (0.02 < 0.05)
        within_tol = list(base)
        within_tol[1] = float(within_tol[1]) + 0.02

        # Tweak a gain beyond tolerance (0.2 > 0.05)
        beyond_tol = list(base)
        beyond_tol[5] = float(beyond_tol[5]) + 0.2

        from linux_arctis_manager.gui_gtk.eq_ui_logic import should_show_reset

        assert (
            should_show_reset(selected, within_tol, presets, mode="parametric") is False
        ), "Within tolerance differences should not show reset"

        assert (
            should_show_reset(selected, beyond_tol, presets, mode="parametric") is True
        ), "Beyond tolerance differences should show reset"

    @pytest.mark.parametrize("selected", [None, "Custom", "Nonexistent"])
    def test_invalid_or_custom_selection_disables_reset(self, selected):
        gpresets = _make_graphic_presets()
        ppresets = _make_parametric_presets()

        from linux_arctis_manager.gui_gtk.eq_ui_logic import (
            should_show_reset,
            get_reset_target,
        )

        # Graphic
        current_g = [0.0] * 10
        assert should_show_reset(selected, current_g, gpresets, mode="graphic") is False
        assert get_reset_target(selected, gpresets) is None

        # Parametric
        current_p = ppresets.get("Arc Raiders") or []
        assert (
            should_show_reset(selected, current_p, ppresets, mode="parametric") is False
        )
        assert get_reset_target(selected, ppresets) is None
