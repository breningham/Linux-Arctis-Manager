import sys
import gi
import logging

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, GObject

from linux_arctis_manager.i18n import I18n
from linux_arctis_manager.gui_gtk.dbus_client import GtkDbusClient

logger = logging.getLogger('GtkApp')

class ArctisManagerWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Arctis Manager")
        self.set_default_size(650, 800)

        # Main vertical box
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(vbox)

        # The ViewStack holds our different pages
        self.view_stack = Adw.ViewStack()
        
        # Header Bar with the ViewSwitcher
        header_bar = Adw.HeaderBar()
        switcher_title = Adw.ViewSwitcherTitle()
        switcher_title.set_stack(self.view_stack)
        header_bar.set_title_widget(switcher_title)
        vbox.append(header_bar)
        
        self.view_stack.set_vexpand(True)
        vbox.append(self.view_stack)

        # --- TAB 1: Dashboard ---
        self.dashboard_page = Adw.PreferencesPage()
        self.dashboard_page.set_icon_name("dashboard-show-symbolic")
        self.view_stack.add_titled(self.dashboard_page, "dashboard", I18n.translate('ui', 'status'))

        # --- TAB 2: Settings ---
        self.settings_page = Adw.PreferencesPage()
        self.settings_page.set_icon_name("preferences-system-symbolic")
        self.view_stack.add_titled(self.settings_page, "settings", "Settings")

        self.dbus_client = GtkDbusClient(
            on_status_cb=self.on_status_received,
            on_settings_cb=self.on_settings_received
        )
        
        self._status_widgets = {}
        self._settings_widgets = {}
        self._settings_data = {}
        self._status_data = {}
        self._option_lists = {}
        self._updating_ui = False
        self._status_rows = []
        self._settings_groups = []
        
        self.status_group = Adw.PreferencesGroup()
        self.dashboard_page.add(self.status_group)
        
        self.dbus_client.start()
        self.connect('close-request', self.on_close)

    def on_close(self, *args):
        self.dbus_client.stop()
        return False

    def get_list_options_cb(self, list_name, opts):
        self._option_lists[list_name] = opts
        # We trigger a refresh of settings to ensure combo boxes update
        if self._settings_data:
            self.refresh_settings_ui()

    def on_status_received(self, status: dict):
        if status == self._status_data:
            return
        self._status_data = status
        
        # Clear existing status rows
        for row in self._status_rows:
            self.status_group.remove(row)
        self._status_rows.clear()

        if not status:
            row = Adw.ActionRow(title=I18n.translate('ui', 'no_device_detected'))
            self.status_group.add(row)
            self._status_rows.append(row)
            return

        for category, status_obj in status.items():
            for stat_name, stat_o in status_obj.items():
                title = I18n.translate('status', stat_name)
                row = Adw.ActionRow(title=title)
                
                if stat_o['type'] == 'percentage':
                    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                    bar = Gtk.ProgressBar()
                    val = float(stat_o['value'])
                    bar.set_fraction(val / 100.0)
                    
                    # You could add CSS classes here to change colors, similar to Qt
                    bar.add_css_class("osd")
                    bar.set_valign(Gtk.Align.CENTER)
                    
                    lbl = Gtk.Label(label=f"{int(val)}%")
                    box.append(bar)
                    box.append(lbl)
                    row.add_suffix(box)
                else:
                    val_str = I18n.translate('status_values', stat_o['value'])
                    if stat_name == 'cable_charging':
                        val_str = f"⚡ {val_str}" if stat_o['value'] == 'on' else f"🔌 {val_str}"
                    elif stat_name == 'bluetooth_connection':
                        val_str = f"🔵 {val_str}" if stat_o['value'] == 'connected' else f"⚪ {val_str}"
                    
                    lbl = Gtk.Label(label=val_str)
                    lbl.set_valign(Gtk.Align.CENTER)
                    row.add_suffix(lbl)
                
                self.status_group.add(row)
                self._status_rows.append(row)

    def on_settings_received(self, new_settings: dict):
        if new_settings == self._settings_data:
            return
            
        # Check if we need to request lists
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
        
        # Clear existing settings groups
        for group in self._settings_groups:
            self.settings_page.remove(group)
        self._settings_groups.clear()

        settings_config = self._settings_data.get('settings_config', {})
        
        # We sort by 'general' and 'device'
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
                    
                    # For libadwaita ActionRow, add child
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
                    # Can map as a combo box in GTK for now
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
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # Allows GTK to handle Ctrl+C cleanly without throwing Python traces
    
    I18n.get_instance().set_language('en')
    app = ArctisManagerApp()
    try:
        sys.exit(app.run(sys.argv))
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == '__main__':
    main()
