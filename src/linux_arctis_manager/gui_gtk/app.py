import sys
import gi
import logging
import math

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

from linux_arctis_manager.i18n import I18n
from linux_arctis_manager.gui_gtk.dbus_client import GtkDbusClient

logger = logging.getLogger('GtkApp')


class MixDialWidget(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.set_size_request(150, 110)
        self.set_draw_func(self.on_draw)
        self.mix_value = 50.0  # 0 to 100 (0 = Game, 100 = Chat)

    def set_mix(self, val):
        self.mix_value = val
        self.queue_draw()

    def on_draw(self, area, cr, width, height):
        # Enable anti-aliasing for smooth rounded edges
        import cairo
        cr.set_antialias(cairo.ANTIALIAS_BEST)
        
        xc = width / 2.0
        yc = height * 0.80
        radius = min(width/2.0, height * 0.75) - 14
        
        start_angle = math.pi * 0.85
        end_angle = math.pi * 2.15
        
        # 1. Draw Media Background Arc (Purple/Blue-ish)
        cr.set_source_rgba(0.53, 0.35, 0.96, 1.0)
        cr.set_line_width(16)
        cr.set_line_cap(cairo.LineCap.ROUND)
        cr.arc(xc, yc, radius, start_angle, end_angle)
        cr.stroke()

        # 2. Draw Chat Overlay Arc (Green/Teal-ish)
        split_angle = start_angle + (self.mix_value / 100.0) * (end_angle - start_angle)
        
        if split_angle > start_angle:
            cr.set_source_rgba(0.18, 0.8, 0.44, 1.0)
            cr.set_line_width(16)
            cr.set_line_cap(cairo.LineCap.ROUND)
            cr.arc(xc, yc, radius, start_angle, split_angle)
            cr.stroke()

        # 3. Draw the Knob indicator
        ix = xc + radius * math.cos(split_angle)
        iy = yc + radius * math.sin(split_angle)
        
        # Knob Drop Shadow
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.15)
        cr.arc(ix, iy + 2, 12, 0, 2*math.pi)
        cr.fill()
        
        # Knob Body
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.arc(ix, iy, 12, 0, 2*math.pi)
        cr.fill()
        
        # Knob Border
        cr.set_source_rgba(0.85, 0.85, 0.85, 1.0)
        cr.set_line_width(1.5)
        cr.arc(ix, iy, 12, 0, 2*math.pi)
        cr.stroke()

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
        
        dash_page = self.view_stack.add_titled(self.dashboard_scroll, "dashboard", I18n.translate('ui', 'status'))
        dash_page.set_icon_name("dashboard-show-symbolic")

        dash_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.dashboard_scroll.set_child(dash_vbox)

        self.hero = Adw.StatusPage()
        self.hero.set_title(I18n.translate('ui', 'app_name'))
        self.hero.set_icon_name("audio-headset-symbolic")
        self.hero.set_description(I18n.translate('ui', 'no_device_detected'))
        dash_vbox.append(self.hero)

        self.dash_clamp = Adw.Clamp()
        self.dash_clamp.set_maximum_size(600)
        dash_vbox.append(self.dash_clamp)

        self.dash_grid = Gtk.Grid()
        self.dash_grid.set_column_spacing(16)
        self.dash_grid.set_row_spacing(16)
        self.dash_grid.set_margin_start(16)
        self.dash_grid.set_margin_end(16)
        self.dash_grid.set_margin_bottom(32)
        self.dash_grid.set_column_homogeneous(True)
        self.dash_clamp.set_child(self.dash_grid)

        # --- TAB 2: Settings ---
        self.settings_page = Adw.PreferencesPage()
        set_page = self.view_stack.add_titled(self.settings_page, "settings", "Settings")
        set_page.set_icon_name("preferences-system-symbolic")

        self.dbus_client = GtkDbusClient(
            on_status_cb=self.on_status_received,
            on_settings_cb=self.on_settings_received
        )
        
        self._settings_groups = []
        self._settings_data = {}
        self._status_data = {}
        self._option_lists = {}
        self._updating_ui = False
        
        self.dbus_client.start()
        self.connect('close-request', self.on_close)

    def on_close(self, *args):
        self.dbus_client.stop()
        return False

    def get_list_options_cb(self, list_name, opts):
        self._option_lists[list_name] = opts
        if self._settings_data:
            self.refresh_settings_ui()

    def make_value_card(self, title, value_text, icon_name, css_class="title-1"):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        card.add_css_class("card")

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        inner.set_margin_top(24); inner.set_margin_bottom(24)
        inner.set_margin_start(24); inner.set_margin_end(24)
        inner.set_vexpand(True)
        card.append(inner)

        top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(24)
        top_box.append(icon)

        lbl_title = Gtk.Label(label=title)
        lbl_title.add_css_class("heading")
        top_box.append(lbl_title)
        inner.append(top_box)

        lbl_val = Gtk.Label(label=value_text)
        lbl_val.add_css_class(css_class)
        lbl_val.add_css_class("numeric")
        lbl_val.set_halign(Gtk.Align.CENTER)
        lbl_val.set_valign(Gtk.Align.CENTER)
        lbl_val.set_vexpand(True)
        inner.append(lbl_val)

        return card

    def make_mix_dial_card(self, title, chat_val):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        card.add_css_class("card")

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        inner.set_margin_top(24); inner.set_margin_bottom(24)
        inner.set_margin_start(24); inner.set_margin_end(24)
        card.append(inner)

        lbl_title = Gtk.Label(label=title)
        lbl_title.add_css_class("heading")
        lbl_title.set_halign(Gtk.Align.START)
        inner.append(lbl_title)

        dial_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        lbl_game = Gtk.Label(label="Game")
        lbl_game.add_css_class("dim-label")
        lbl_game.set_valign(Gtk.Align.END)
        lbl_game.set_margin_bottom(12)
        
        dial = MixDialWidget()
        dial.set_mix(chat_val)
        dial.set_hexpand(True)
        
        lbl_chat = Gtk.Label(label="Chat")
        lbl_chat.add_css_class("dim-label")
        lbl_chat.set_valign(Gtk.Align.END)
        lbl_chat.set_margin_bottom(12)
        
        dial_box.append(lbl_game)
        dial_box.append(dial)
        dial_box.append(lbl_chat)
        
        inner.append(dial_box)
        return card

    def on_status_received(self, status: dict):
        if status == self._status_data:
            return
        self._status_data = status
        
        while child := self.dash_grid.get_first_child():
            self.dash_grid.remove(child)

        if not status:
            self.hero.set_title(I18n.translate('ui', 'app_name'))
            self.hero.set_description(I18n.translate('ui', 'no_device_detected'))
            self.dash_clamp.set_visible(False)
            self.settings_page.set_visible(False)
            return
            
        self.dash_clamp.set_visible(True)
        self.settings_page.set_visible(True)

        flat_status = {}
        for cat, obj in status.items():
            for k, v in obj.items():
                flat_status[k] = v

        power_val = flat_status.get('headset_power_status', {}).get('value', 'offline')
        if power_val == 'online':
            self.hero.set_description("Connected and Active")
        elif power_val == 'charging':
            self.hero.set_description("Charging (Offline)")
        else:
            self.hero.set_description("Offline")

        # Grid layout logic
        row_idx = 0

        # Battery & Bluetooth row
        batt_o = flat_status.get('headset_battery_charge')
        charging_o = flat_status.get('cable_charging')
        if batt_o:
            val = float(batt_o['value'])
            is_charging = charging_o and charging_o['value'] == 'on'
            
            icon = "battery-level-100-charging-symbolic" if is_charging else "battery-level-100-symbolic"
            if not is_charging and val <= 20: icon = "battery-level-20-symbolic"
            elif not is_charging and val <= 50: icon = "battery-level-50-symbolic"
            
            txt = f"{int(val)}%" + (" ⚡" if is_charging else "")
            batt_card = self.make_value_card("Battery", txt, icon, "title-1")
            self.dash_grid.attach(batt_card, 0, row_idx, 1, 1)

        bt_o = flat_status.get('bluetooth_connection')
        if bt_o:
            bt_val = bt_o['value']
            is_bt_conn = bt_val == 'connected'
            icon = "bluetooth-active-symbolic" if is_bt_conn else "bluetooth-disabled-symbolic"
            txt = "Connected" if is_bt_conn else "Disconnected"
            bt_card = self.make_value_card("Bluetooth", txt, icon, "title-2" if is_bt_conn else "title-3")
            self.dash_grid.attach(bt_card, 1, row_idx, 1, 1)
            
        if batt_o or bt_o:
            row_idx += 1

        # Mixes
        chat_o = flat_status.get('chat_mix')
        media_o = flat_status.get('media_mix')
        if chat_o and media_o:
            mix_card = self.make_mix_dial_card("Audio Mix", float(chat_o['value']))
            self.dash_grid.attach(mix_card, 0, row_idx, 2, 1)
            row_idx += 1

        # Mic
        mic_o = flat_status.get('mic_status')
        if mic_o:
            is_muted = mic_o['value'] == 'muted'
            icon = "audio-input-microphone-muted-symbolic" if is_muted else "audio-input-microphone-symbolic"
            txt = "Muted" if is_muted else "Active"
            mic_card = self.make_value_card("Microphone", txt, icon, "title-3" if is_muted else "title-2")
            self.dash_grid.attach(mic_card, 0, row_idx, 2, 1)

    def on_settings_received(self, new_settings: dict):
        if new_settings == self._settings_data:
            return
            
        dev_name = new_settings.get('device_name')
        if dev_name:
            self.hero.set_title(dev_name)
            
        settings_config = new_settings.get('settings_config', {})
        for config_name, kwargs in settings_config.items():
            if kwargs.get('type') == 'select':
                source = kwargs.get('options_source')
                if source and source not in self._option_lists:
                    self.dbus_client.request_list_options(source, self.get_list_options_cb)

        self._settings_data = new_settings
        self.refresh_settings_ui()

    def refresh_settings_ui(self):
        self._updating_ui = True
        
        for group in self._settings_groups:
            self.settings_page.remove(group)
        self._settings_groups.clear()

        settings_config = self._settings_data.get('settings_config', {})
        
        for section in ['general', 'device']:
            settings_group = self._settings_data.get(section, {})
            if not settings_group:
                continue
                
            group = Adw.PreferencesGroup(title=I18n.translate('ui', section))
            self.settings_page.add(group)
            self._settings_groups.append(group)
                
            for name, value in settings_group.items():
                cfg = settings_config.get(name, {})
                stype = cfg.get('type')
                
                title = I18n.translate('settings', name)
                desc = I18n.translate('settings_descriptions', name)
                if desc == name:
                    desc = ""
                    
                if stype == 'toggle':
                    row = Adw.SwitchRow(title=title, subtitle=desc)
                    is_on = value == cfg.get('values', {}).get('on', True)
                    row.set_active(is_on)
                    
                    def on_switch_change(sw, pspec, n=name, c=cfg):
                        if self._updating_ui: return
                        val = c.get('values', {}).get('on', True) if sw.get_active() else c.get('values', {}).get('off', False)
                        self.dbus_client.change_setting(n, val)
                        
                    row.connect('notify::active', on_switch_change)
                    group.add(row)
                    
                elif stype == 'slider':
                    row = Adw.ActionRow(title=title, subtitle=desc)
                    
                    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                    scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, cfg.get('min', 0), cfg.get('max', 100), cfg.get('step', 1))
                    scale.set_value(float(value))
                    scale.set_hexpand(True)
                    
                    val_lbl = Gtk.Label(label=str(value))
                    
                    def on_scale_change(sc, n=name, c=cfg, l=val_lbl):
                        v = int(sc.get_value())
                        mapped = c.get('values_mapping', {}).get(str(v), str(v))
                        trans = I18n.translate('settings_values', mapped)
                        l.set_label(trans)
                        if not self._updating_ui:
                            self.dbus_client.change_setting(n, v)
                    
                    scale.connect('value-changed', on_scale_change)
                    on_scale_change(scale) # Init label
                    
                    box.append(scale)
                    box.append(val_lbl)
                    
                    row.add_suffix(box)
                    box.set_size_request(200, -1)
                    group.add(row)
                    
                elif stype == 'select':
                    source = cfg.get('options_source')
                    opts = self._option_lists.get(source, [])
                    if source == 'pulse_audio_devices':
                        opts = [{'id': 'none', 'name': I18n.translate('settings_values', 'none')}] + opts

                    if opts:
                        model = Gtk.StringList.new([o['name'] for o in opts])
                        row = Adw.ComboRow(title=title, subtitle=desc, model=model)
                        
                        idx = next((i for i, o in enumerate(opts) if o['id'] == value), 0)
                        row.set_selected(idx)
                        
                        def on_combo_change(cr, pspec, n=name, o=opts):
                            if self._updating_ui: return
                            i = cr.get_selected()
                            self.dbus_client.change_setting(n, o[i]['id'])
                            
                        row.connect('notify::selected', on_combo_change)
                        group.add(row)
                        
                elif stype == 'discrete_map':
                    mappings = cfg.get('values_mapping', {})
                    opts = [{'id': int(k), 'name': I18n.translate('settings_values', v)} for k, v in mappings.items()]
                    
                    model = Gtk.StringList.new([o['name'] for o in opts])
                    row = Adw.ComboRow(title=title, subtitle=desc, model=model)
                    
                    idx = next((i for i, o in enumerate(opts) if o['id'] == value), 0)
                    row.set_selected(idx)
                    
                    def on_discrete_change(cr, pspec, n=name, o=opts):
                        if self._updating_ui: return
                        i = cr.get_selected()
                        self.dbus_client.change_setting(n, o[i]['id'])
                        
                    row.connect('notify::selected', on_discrete_change)
                        
                    group.add(row)
                    
        self._updating_ui = False

class ArctisManagerApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.github.arctismanager')

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = ArctisManagerWindow(application=self)
        win.present()

def main():
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    I18n.get_instance().set_language('en')
    app = ArctisManagerApp()
    try:
        sys.exit(app.run(sys.argv))
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == '__main__':
    main()
