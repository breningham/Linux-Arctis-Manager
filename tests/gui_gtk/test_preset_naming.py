import pytest

from linux_arctis_manager.gui_gtk.preset_manager import (
    friendly_preset_name,
    PresetManager,
)


def test_friendly_preset_name_strips_gg_prefix():
    assert friendly_preset_name("GG: Arc Raiders") == "Arc Raiders"


def test_friendly_preset_name_leaves_other_names():
    assert friendly_preset_name("Flat") == "Flat"
    assert friendly_preset_name("Custom-1") == "Custom-1"


def test_is_builtin_parametric_non_regression_for_gg_imports():
    pm = PresetManager()
    # Imported presets with GG: prefix should be treated as non-deletable built-ins
    assert pm.is_builtin_parametric("GG: Arc Raiders", "output") is True
    # Mic mode only treats 'Flat' as builtin unless GG-imported
    assert pm.is_builtin_parametric("Flat", "microphone") is True
    assert pm.is_builtin_parametric("Arc Raiders", "microphone") is False
