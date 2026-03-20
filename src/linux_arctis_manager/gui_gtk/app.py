import sys
import gi
import logging
import math

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from linux_arctis_manager.i18n import I18n
from linux_arctis_manager.gui_gtk.dbus_client import GtkDbusClient

logger = logging.getLogger("GtkApp")


class ArctisManagerWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Arctis Manager")
        self.set_default_size(650, 850)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(vbox)

        self.view_stack = Adw.ViewStack()
        header_bar = Adw.HeaderBar()
        switcher_title = Adw.ViewSwitcherTitle()
        switcher_title.set_stack(self.view_stack)
        header_bar.set_title_widget(switcher_title)
        vbox.append(header_bar)

        self.view_stack.set_vexpand(True)
        vbox.append(self.view_stack)

        # --- TAB 1: Dashboard ---
        self.dashboard_scroll = Gtk.ScrolledWindow()
        self.dashboard_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        dash_page = self.view_stack.add_titled(
            self.dashboard_scroll, "dashboard", I18n.translate("ui", "status")
        )
        dash_page.set_icon_name("audio-card-symbolic")

        dash_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.dashboard_scroll.set_child(dash_vbox)

        self.hero = Adw.StatusPage()
        self.hero.set_title(I18n.translate("ui", "app_name"))
        self.hero.set_icon_name("audio-headset-symbolic")
        self.hero.set_description(I18n.translate("ui", "no_device_detected"))
        dash_vbox.append(self.hero)

        self.dash_clamp = Adw.Clamp()
        self.dash_clamp.set_maximum_size(600)
        dash_vbox.append(self.dash_clamp)

        self.dash_group = Adw.PreferencesGroup()
        self.dash_group.set_margin_start(16)
        self.dash_group.set_margin_end(16)
        self.dash_group.set_margin_bottom(32)
        self.dash_clamp.set_child(self.dash_group)

        # --- TAB 2: Settings ---
        self.settings_page = Adw.PreferencesPage()
        set_page = self.view_stack.add_titled(
            self.settings_page, "settings", "Settings"
        )
        set_page.set_icon_name("preferences-system-symbolic")

        self.dbus_client = GtkDbusClient(
            on_status_cb=self.on_status_received,
            on_settings_cb=self.on_settings_received,
        )

        self._settings_groups = []
        self._settings_data = {}
        self._status_data = {}
        self._option_lists = {}
        self._updating_ui = False
        self._dash_widgets = {}
        self._dash_rows = []
        self._is_offline = True

        self.dbus_client.start()
        self.connect("close-request", self.on_close)

    def on_close(self, *args):
        self.dbus_client.stop()
        return False

    def get_list_options_cb(self, list_name, opts):
        self._option_lists[list_name] = opts
        if self._settings_data:
            self.refresh_settings_ui()

    def on_status_received(self, status: dict):
        if status == self._status_data:
            return
        self._status_data = status

        flat_status = {}
        for cat, obj in status.items():
            for k, v in obj.items():
                flat_status[k] = v

        power_val = flat_status.get("headset_power_status", {}).get("value", "offline")

        self._is_offline = not status or power_val == "offline"

        # If it's completely empty OR it's offline (like a dongle is plugged in but headset is off), hide the cards
        if self._is_offline:
            # We don't overwrite the title if we know what device it is, but if we don't, fall back to app_name
            if not status:
                self.hero.set_title(I18n.translate("ui", "app_name"))
            self.hero.set_description(
                "Offline"
                if power_val == "offline"
                else I18n.translate("ui", "no_device_detected")
            )
            self.dash_clamp.set_visible(False)

            # Make sure settings tab remains visible but without device settings
            self.settings_page.set_visible(True)
            self.refresh_settings_ui()
            
            # Clear widgets dict so they get recreated next time it comes online
            self._dash_widgets.clear()
            for row in self._dash_rows:
                self.dash_group.remove(row)
            self._dash_rows.clear()
            return

        self.dash_clamp.set_visible(True)
        self.settings_page.set_visible(True)

        if power_val == "online":
            self.hero.set_description("Connected and Active")
        elif power_val == "charging":
            self.hero.set_description("Charging (Offline)")

        # Determine which cards should exist
        batt_o = flat_status.get("headset_battery_charge")
        charging_o = flat_status.get("cable_charging")
        bt_o = flat_status.get("bluetooth_connection")
        chat_o = flat_status.get("chat_mix")
        media_o = flat_status.get("media_mix")
        mic_o = flat_status.get("mic_status")
        
        expected_cards = set()
        if batt_o: expected_cards.add("battery")
        if bt_o: expected_cards.add("bluetooth")
        if chat_o and media_o: expected_cards.add("mix")
        if mic_o: expected_cards.add("mic")
        
        # If the expected cards changed, clear and rebuild layout
        if set(self._dash_widgets.keys()) != expected_cards:
            self._dash_widgets.clear()
            for row in self._dash_rows:
                self.dash_group.remove(row)
            self._dash_rows.clear()
                
            if "battery" in expected_cards:
                row = Adw.ActionRow(title="Battery")
                icon = Gtk.Image.new_from_icon_name("battery-level-100-symbolic")
                row.add_prefix(icon)
                
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                box.set_valign(Gtk.Align.CENTER)
                
                level_bar = Gtk.LevelBar()
                level_bar.set_min_value(0)
                level_bar.set_max_value(100)
                level_bar.set_size_request(100, -1)
                level_bar.set_valign(Gtk.Align.CENTER)
                
                lbl = Gtk.Label()
                lbl.add_css_class("numeric")
                
                box.append(level_bar)
                box.append(lbl)
                
                row.add_suffix(box)
                self.dash_group.add(row)
                self._dash_rows.append(row)
                self._dash_widgets["battery"] = {"row": row, "icon": icon, "bar": level_bar, "label": lbl}
                
            if "bluetooth" in expected_cards:
                row = Adw.ActionRow(title="Bluetooth")
                icon = Gtk.Image.new_from_icon_name("bluetooth-active-symbolic")
                row.add_prefix(icon)
                
                lbl = Gtk.Label()
                lbl.set_valign(Gtk.Align.CENTER)
                
                row.add_suffix(lbl)
                self.dash_group.add(row)
                self._dash_rows.append(row)
                self._dash_widgets["bluetooth"] = {"row": row, "icon": icon, "label": lbl}
                
            if "mix" in expected_cards:
                row = Adw.ActionRow(title="Audio Mix")
                icon = Gtk.Image.new_from_icon_name("audio-volume-high-symbolic")
                row.add_prefix(icon)
                
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                box.set_valign(Gtk.Align.CENTER)
                
                icon_game = Gtk.Image.new_from_icon_name("input-gaming-symbolic")
                icon_game.add_css_class("dim-label")
                box.append(icon_game)

                scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
                scale.set_hexpand(True)
                scale.set_draw_value(False)
                scale.set_has_origin(False)
                scale.add_mark(50, Gtk.PositionType.BOTTOM, None)
                scale.set_size_request(200, -1)
                
                def on_scale_change(sc, sc_type, val):
                    return True
                scale.connect("change-value", on_scale_change)
                box.append(scale)
                
                icon_chat = Gtk.Image.new_from_icon_name("audio-headset-symbolic")
                icon_chat.add_css_class("dim-label")
                box.append(icon_chat)
                
                row.add_suffix(box)
                self.dash_group.add(row)
                self._dash_rows.append(row)
                self._dash_widgets["mix"] = {"row": row, "scale": scale}
                
            if "mic" in expected_cards:
                row = Adw.ActionRow(title="Microphone")
                icon = Gtk.Image.new_from_icon_name("audio-input-microphone-symbolic")
                row.add_prefix(icon)
                
                lbl = Gtk.Label()
                lbl.set_valign(Gtk.Align.CENTER)
                
                row.add_suffix(lbl)
                self.dash_group.add(row)
                self._dash_rows.append(row)
                self._dash_widgets["mic"] = {"row": row, "icon": icon, "label": lbl}
                
        # Now update the existing widgets
        if "battery" in expected_cards:
            w = self._dash_widgets["battery"]
            val = float(batt_o["value"])
            is_charging = charging_o and charging_o["value"] == "on"
            icon_name = "battery-level-100-charged-symbolic" if is_charging else "battery-level-100-symbolic"
            if not is_charging and val <= 20: icon_name = "battery-level-20-symbolic"
            elif not is_charging and val <= 50: icon_name = "battery-level-50-symbolic"
            
            w["icon"].set_from_icon_name(icon_name)
            w["bar"].set_value(val)
            w["label"].set_label(f"{int(val)}%" + (" ⚡" if is_charging else ""))
            
        if "bluetooth" in expected_cards:
            w = self._dash_widgets["bluetooth"]
            is_bt_conn = bt_o["value"] == "connected"
            icon_name = "bluetooth-active-symbolic" if is_bt_conn else "bluetooth-disabled-symbolic"
            txt = "Connected" if is_bt_conn else "Disconnected"
            css_cls = "success" if is_bt_conn else "error"
            
            w["icon"].set_from_icon_name(icon_name)
            w["label"].set_label(txt)
            w["label"].set_css_classes([css_cls])
            
        if "mix" in expected_cards:
            w = self._dash_widgets["mix"]
            chat_val = float(chat_o["value"])
            media_val = float(media_o["value"])
            
            total = chat_val + media_val
            if total == 0:
                normalized_val = 50.0
            else:
                normalized_val = (chat_val / total) * 100.0
                
            w["scale"].set_value(normalized_val)
            
        if "mic" in expected_cards:
            w = self._dash_widgets["mic"]
            is_muted = mic_o["value"] == "muted"
            icon_name = "microphone-sensitivity-muted-symbolic" if is_muted else "audio-input-microphone-symbolic"
            txt = "Muted" if is_muted else "Active"
            css_cls = "error" if is_muted else "success"
            
            w["icon"].set_from_icon_name(icon_name)
            w["label"].set_label(txt)
            w["label"].set_css_classes([css_cls])

    def on_settings_received(self, new_settings: dict):
        if new_settings == self._settings_data:
            return

        dev_name = new_settings.get("device_name")
        if dev_name:
            self.hero.set_title(dev_name)

        settings_config = new_settings.get("settings_config", {})
        for config_name, kwargs in settings_config.items():
            if kwargs.get("type") == "select":
                source = kwargs.get("options_source")
                if source and source not in self._option_lists:
                    self.dbus_client.request_list_options(
                        source, self.get_list_options_cb
                    )

        self._settings_data = new_settings
        self.refresh_settings_ui()

    def refresh_settings_ui(self):
        self._updating_ui = True

        for group in self._settings_groups:
            self.settings_page.remove(group)
        self._settings_groups.clear()

        settings_config = self._settings_data.get("settings_config", {})

        label_size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)

        for section in ["general", "device"]:
            if section == "device" and self._is_offline:
                continue

            settings_group = self._settings_data.get(section, {})
            if not settings_group:
                continue

            group = Adw.PreferencesGroup(title=I18n.translate("ui", section))
            self.settings_page.add(group)
            self._settings_groups.append(group)

            for name, value in settings_group.items():
                cfg = settings_config.get(name, {})
                stype = cfg.get("type")

                title = I18n.translate("settings", name)
                desc = I18n.translate("settings_descriptions", name)
                if desc == name:
                    desc = ""

                if stype == "toggle":
                    row = Adw.SwitchRow(title=title, subtitle=desc)
                    is_on = value == cfg.get("values", {}).get("on", True)
                    row.set_active(is_on)

                    def on_switch_change(sw, pspec, n=name, c=cfg):
                        if self._updating_ui:
                            return
                        val = (
                            c.get("values", {}).get("on", True)
                            if sw.get_active()
                            else c.get("values", {}).get("off", False)
                        )
                        self.dbus_client.change_setting(n, val)

                    row.connect("notify::active", on_switch_change)
                    group.add(row)

                elif stype == "slider":
                    if name in [
                        "mic_side_tone",
                        "mic_mute_led_brightness",
                        "bluetooth_auto_mute",
                    ]:
                        mappings = cfg.get("values_mapping", {})
                        opts = []
                        for k in sorted(mappings.keys(), key=lambda x: int(x)):
                            opts.append(
                                {
                                    "id": int(k),
                                    "name": I18n.translate(
                                        "settings_values", mappings[k]
                                    ),
                                }
                            )

                        model = Gtk.StringList.new([o["name"] for o in opts])
                        row = Adw.ComboRow(title=title, subtitle=desc, model=model)

                        idx = next(
                            (i for i, o in enumerate(opts) if o["id"] == value), 0
                        )
                        row.set_selected(idx)

                        def on_combo_mapped_change(cr, pspec, n=name, o=opts):
                            if self._updating_ui:
                                return
                            i = cr.get_selected()
                            self.dbus_client.change_setting(n, o[i]["id"])

                        row.connect("notify::selected", on_combo_mapped_change)
                        group.add(row)

                    elif name == "pm_shutdown":
                        row = Adw.SpinRow(title=title, subtitle=desc)
                        adj = Gtk.Adjustment(
                            value=float(value),
                            lower=cfg.get("min", 0),
                            upper=cfg.get("max", 120),
                            step_increment=cfg.get("step", 1),
                        )
                        row.set_adjustment(adj)

                        def on_spin_change(sr, n=name):
                            if self._updating_ui:
                                return
                            v = int(sr.get_value())
                            self.dbus_client.change_setting(n, v)

                        row.connect("changed", on_spin_change)
                        group.add(row)

                    else:
                        row = Adw.ActionRow(title=title, subtitle=desc)

                        box = Gtk.Box(
                            orientation=Gtk.Orientation.HORIZONTAL, spacing=10
                        )

                        if name == "mic_volume":
                            icon = Gtk.Image.new_from_icon_name(
                                "audio-input-microphone-symbolic"
                            )
                            icon.add_css_class("dim-label")
                            box.append(icon)

                        scale = Gtk.Scale.new_with_range(
                            Gtk.Orientation.HORIZONTAL,
                            cfg.get("min", 0),
                            cfg.get("max", 100),
                            cfg.get("step", 1),
                        )
                        scale.set_value(float(value))
                        scale.set_hexpand(True)
                        scale.set_margin_start(8)
                        scale.set_margin_end(8)

                        val_lbl = Gtk.Label(label=str(value))

                        def on_scale_change(sc, n=name, c=cfg, l=val_lbl):
                            v = int(sc.get_value())
                            mapped = c.get("values_mapping", {}).get(str(v), str(v))
                            trans = I18n.translate("settings_values", mapped)
                            l.set_label(trans)
                            if not self._updating_ui:
                                self.dbus_client.change_setting(n, v)

                        scale.connect("value-changed", on_scale_change)
                        on_scale_change(scale)

                        val_lbl.set_xalign(1.0)
                        label_size_group.add_widget(val_lbl)

                        box.append(scale)
                        box.append(val_lbl)

                        row.add_suffix(box)

                        if name == "mic_volume":
                            row.set_activatable_widget(scale)
                        else:
                            box.set_size_request(250, -1)

                        group.add(row)

                elif stype == "select":
                    source = cfg.get("options_source")
                    opts = self._option_lists.get(source, [])
                    if source == "pulse_audio_devices":
                        opts = [
                            {
                                "id": "none",
                                "name": I18n.translate("settings_values", "none"),
                            }
                        ] + opts

                    if opts:
                        model = Gtk.StringList.new([o["name"] for o in opts])
                        row = Adw.ComboRow(title=title, subtitle=desc, model=model)

                        idx = next(
                            (i for i, o in enumerate(opts) if o["id"] == value), 0
                        )
                        row.set_selected(idx)

                        def on_combo_change(cr, pspec, n=name, o=opts):
                            if self._updating_ui:
                                return
                            i = cr.get_selected()
                            self.dbus_client.change_setting(n, o[i]["id"])

                        row.connect("notify::selected", on_combo_change)
                        group.add(row)

                elif stype == "discrete_map":
                    mappings = cfg.get("values_mapping", {})
                    opts = [
                        {"id": int(k), "name": I18n.translate("settings_values", v)}
                        for k, v in mappings.items()
                    ]

                    model = Gtk.StringList.new([o["name"] for o in opts])
                    row = Adw.ComboRow(title=title, subtitle=desc, model=model)

                    idx = next((i for i, o in enumerate(opts) if o["id"] == value), 0)
                    row.set_selected(idx)

                    def on_discrete_change(cr, pspec, n=name, o=opts):
                        if self._updating_ui:
                            return
                        i = cr.get_selected()
                        self.dbus_client.change_setting(n, o[i]["id"])

                    row.connect("notify::selected", on_discrete_change)

                    group.add(row)

        self._updating_ui = False
        self._dash_widgets = {}


class ArctisManagerApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="dev.ingham.lam-gui.gtk")

    def do_activate(self):
        # Fallback for systems (like bare Arch WMs) that don't set a default GTK icon theme
        settings = Gtk.Settings.get_default()
        if settings and (
            not settings.get_property("gtk-icon-theme-name")
            or settings.get_property("gtk-icon-theme-name") == "gnome"
        ):
            settings.set_property("gtk-icon-theme-name", "Adwaita")

        win = self.props.active_window
        if not win:
            win = ArctisManagerWindow(application=self)
        win.present()


def main():
    import signal

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    I18n.get_instance().set_language("en")
    app = ArctisManagerApp()
    try:
        sys.exit(app.run(sys.argv))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
