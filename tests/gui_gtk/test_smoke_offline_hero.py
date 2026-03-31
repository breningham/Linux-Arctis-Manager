import os
import tempfile

import pytest


def _gi_imports():
    try:
        import gi  # noqa: F401

        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk  # noqa: F401

        return True
    except Exception:
        return False


gtk_missing = not _gi_imports()


@pytest.mark.skipif(gtk_missing, reason="GTK4 (PyGObject) not available in test env")
def test_offline_hero_renders_non_blank(monkeypatch):
    # Isolate HOME to avoid reading/writing real config/cache
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("HOME", tmp)

        # Lazy-import inside test to avoid hard dependency when skipped
        from linux_arctis_manager.gui_gtk.app import ArctisManagerWindow

        # Stub dbus_client methods used during startup
        class StubDbus:
            def __init__(self, win):
                self._win = win

            def start(self):
                pass

            def stop(self):
                pass

            def request_settings(self):
                # Provide minimal settings to avoid None lookups
                self._win.on_settings_received({"settings_config": {}})

        # Construct window and replace dbus_client with stub
        win = ArctisManagerWindow(application=None)
        win.dbus_client = StubDbus(win)

        # Simulate 'no device detected' status
        win.on_status_received({})

        # Hero should be visible with non-blank text
        assert win.hero.get_visible() is True
        title = win.hero.title_label.get_text()
        desc = win.hero.desc_label.get_text()
        assert isinstance(title, str) and len(title.strip()) > 0
        assert isinstance(desc, str) and len(desc.strip()) > 0
