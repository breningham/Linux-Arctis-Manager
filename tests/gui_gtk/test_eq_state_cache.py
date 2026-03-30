import json
from pathlib import Path

import pytest


def test_eq_state_cache_isolates_per_target(monkeypatch, tmp_path):
    # Redirect SETTINGS_FOLDER to a temp directory to avoid touching user config
    settings_dir = tmp_path / "settings"
    monkeypatch.setenv("HOME", str(tmp_path))  # fallback if code uses Path.home
    from linux_arctis_manager import constants as C

    monkeypatch.setattr(C, "SETTINGS_FOLDER", settings_dir, raising=False)

    from linux_arctis_manager.gui_gtk.preset_manager import EqStateCache

    cache = EqStateCache()
    assert cache.parametric == {"wi_hp": {}, "bt_hp": {}, "wi_mic": {}, "bt_mic": {}}

    # Values do not overlap by key
    a = [0.0] * 40
    b = [0.0] * 40
    a[1] = 6.0
    b[1] = -3.0
    cache.set_value("wi_hp", "param1", a)
    cache.set_value("bt_hp", "param1", b)

    assert cache.get_value("wi_hp", "param1") == a
    assert cache.get_value("bt_hp", "param1") == b

    # Presets are isolated as well
    cache.set_preset("wi_hp", "param1", "Flat")
    cache.set_preset("bt_hp", "param1", "Bass Boost")
    assert cache.get_preset("wi_hp", "param1") == "Flat"
    assert cache.get_preset("bt_hp", "param1") == "Bass Boost"

    # Save and reload from disk to ensure persistence structure
    cache2 = EqStateCache()
    assert cache2.get_value("wi_hp", "param1") == a
    assert cache2.get_value("bt_hp", "param1") == b
    assert cache2.get_preset("wi_hp", "param1") == "Flat"
    assert cache2.get_preset("bt_hp", "param1") == "Bass Boost"
