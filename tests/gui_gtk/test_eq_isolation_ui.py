import os
import types
import pytest


gi = pytest.importorskip("gi")
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw  # noqa: E402


class _StubDbusClient:
    def __init__(self):
        self.changed = []  # list[(name, values)]
        self.targets = []  # list[str]

    def change_setting(self, name, values):
        # store shallow copy to avoid external mutation confusion
        self.changed.append(
            (name, list(values) if isinstance(values, list) else values)
        )

    def set_eq_target(self, mode):
        self.targets.append(mode)


def _isolate_window(monkeypatch, tmp_path):
    # Ensure settings/cache writes go to temp location
    monkeypatch.setenv("HOME", str(tmp_path))
    from linux_arctis_manager import constants as C

    monkeypatch.setattr(C, "SETTINGS_FOLDER", tmp_path / "settings", raising=False)
    from linux_arctis_manager.gui_gtk.app import ArctisManagerWindow

    win = ArctisManagerWindow(application=None)  # type: ignore
    # Replace dbus client with stub to avoid real D-Bus traffic
    win.dbus_client = _StubDbusClient()
    return win


def _mk_param40(band1_gain=0.0, band2_gain=0.0):
    # Minimal distinct 40-list with gains at index 1 and 5
    vals = []
    for i in range(10):
        g = 0.0
        if i == 0:
            g = band1_gain
        if i == 1:
            g = band2_gain
        # freq, gain, Q, type
        vals.extend([31.0 + i * 10.0, g, 1.414, 1.0])
    return vals


def test_parametric_canvases_isolated_across_tabs(monkeypatch, tmp_path):
    win = _isolate_window(monkeypatch, tmp_path)

    # Prepare a fake eq stack that can report visible child name
    class _FakeStack:
        def __init__(self):
            self._name = "wireless"

        def get_visible_child_name(self):
            return self._name

        def set_visible_child_name(self, name):
            self._name = name

    win._eq_stack = _FakeStack()

    # Seed three canvases with distinct values
    cfg = {"type": "parametric_eq", "default_value": [0.0] * 30}
    grp = Adw.PreferencesGroup()
    name = "parametric_test"

    w_vals = _mk_param40(1.0, 0.0)
    b_vals = _mk_param40(0.0, 2.0)
    m_vals = _mk_param40(0.0, -3.0)

    win._eq_mode = "wireless"
    win._update_or_create_parametric_equalizer(name, w_vals, cfg, grp, mode="wireless")
    win._update_or_create_parametric_equalizer(name, b_vals, cfg, grp, mode="bluetooth")
    win._update_or_create_parametric_equalizer(
        name, m_vals, cfg, grp, mode="microphone"
    )

    # Verify initial assignment took for each widget
    cw = win._settings_widgets[f"{name}@wireless"]["canvas"].get_values()
    cb = win._settings_widgets[f"{name}@bluetooth"]["canvas"].get_values()
    cm = win._settings_widgets[f"{name}@microphone"]["canvas"].get_values()
    assert abs(cw[1] - 1.0) < 1e-6
    assert abs(cb[5] - 2.0) < 1e-6
    assert abs(cm[5] - -3.0) < 1e-6

    # While on wireless tab, updating bluetooth should NOT update its canvas (hidden)
    win._eq_mode = "wireless"
    win._eq_stack.set_visible_child_name("wireless")
    b_new = _mk_param40(0.0, 6.0)
    win._update_or_create_parametric_equalizer(name, b_new, cfg, grp, mode="bluetooth")
    cb_after = win._settings_widgets[f"{name}@bluetooth"]["canvas"].get_values()
    assert abs(cb_after[5] - 2.0) < 1e-6, "hidden canvas must not update"

    # Switch to bluetooth tab and update again — now the visible canvas should update
    win._eq_mode = "bluetooth"
    win._eq_stack.set_visible_child_name("bluetooth")
    win._update_or_create_parametric_equalizer(name, b_new, cfg, grp, mode="bluetooth")
    cb_now = win._settings_widgets[f"{name}@bluetooth"]["canvas"].get_values()
    assert abs(cb_now[5] - 6.0) < 1e-6


def test_eq_target_switches_on_tab_change(monkeypatch, tmp_path):
    win = _isolate_window(monkeypatch, tmp_path)

    # Build equalizer stack by simulating settings with one parametric_eq
    win._settings_data = {
        "settings_config": {
            "parametric_test": {"type": "parametric_eq", "default_value": [0.0] * 30}
        },
        "audio": {"parametric_test": [0.0] * 30},
    }
    win.refresh_settings_ui()

    # The stack should exist now; flip tabs and ensure target sync is called
    stack = getattr(win, "_eq_stack", None)
    assert stack is not None

    # Start from wireless (default), then bluetooth, then microphone
    # Adw.ViewStack exposes a property; try the method if available, else set property
    if hasattr(stack, "set_visible_child_name"):
        stack.set_visible_child_name("bluetooth")
        stack.set_visible_child_name("microphone")
    else:
        stack.props.visible_child_name = "bluetooth"  # type: ignore
        stack.props.visible_child_name = "microphone"  # type: ignore

    # Allow GTK to process queued updates (if any)
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)

    # Verify target calls recorded
    # Expect at least the last two explicit switches (bluetooth, microphone)
    targets = win.dbus_client.targets
    assert any(t == "bluetooth" for t in targets)
    assert any(t == "microphone" for t in targets)


def test_friendly_names_are_stripped_in_ui(monkeypatch, tmp_path):
    win = _isolate_window(monkeypatch, tmp_path)

    # Inject a custom GG: preset into the output bank
    from linux_arctis_manager.gui_gtk import preset_manager as pm_mod

    pm = pm_mod.PresetManager()
    pm.add_parametric_preset("GG: Test Boom", [0.0] * 40, mode="output")

    # Use the instance inside app module
    from linux_arctis_manager.gui_gtk import app as app_mod

    app_mod.preset_manager = pm

    cfg = {"type": "parametric_eq", "default_value": [0.0] * 30}
    grp = Adw.PreferencesGroup()
    name = "parametric_test"
    win._update_or_create_parametric_equalizer(
        name, [0.0] * 30, cfg, grp, mode="wireless"
    )

    eqw = win._settings_widgets[f"{name}@wireless"]
    # Display names should be friendly (no GG: prefix)
    assert all(not n.startswith("GG: ") for n in eqw.get("preset_names", []))
