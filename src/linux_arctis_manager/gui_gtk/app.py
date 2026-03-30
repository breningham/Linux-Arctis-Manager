import sys
import gi
import logging
import math
import time
from pathlib import Path

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, GObject, Gdk, Gio  # noqa: E402
from linux_arctis_manager.gui_gtk.widgets import TextToggle  # noqa: E402

from linux_arctis_manager.i18n import I18n  # noqa: E402
from linux_arctis_manager.gui_gtk.dbus_client import GtkDbusClient  # noqa: E402
import subprocess  # noqa: E402

logger = logging.getLogger("GtkApp")

from linux_arctis_manager.gui_gtk.preset_manager import (
    PresetManager,
    normalize_parametric_to_40,
    values_match,
    EqStateCache,
)

preset_manager = PresetManager()


class GtkLogHandler(logging.Handler):
    def __init__(self, buffer):
        super().__init__()
        self.buffer = buffer

    def emit(self, record):
        msg = self.format(record)
        GLib.idle_add(self._append_to_buffer, msg)

    def _append_to_buffer(self, msg):
        end_iter = self.buffer.get_end_iter()
        self.buffer.insert(end_iter, msg + "\n")


class HeroBox(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.set_halign(Gtk.Align.CENTER)
        self.set_hexpand(True)
        self.set_margin_top(48)
        self.set_margin_bottom(48)

        self.icon = Gtk.Image.new_from_icon_name("audio-headset-symbolic")
        self.icon.set_pixel_size(96)
        self.icon.set_halign(Gtk.Align.CENTER)
        self.icon.set_valign(Gtk.Align.CENTER)

        self.text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.text_box.set_halign(Gtk.Align.CENTER)

        self.title_label = Gtk.Label()
        self.title_label.add_css_class("title-1")
        self.title_label.set_wrap(True)
        self.title_label.set_justify(Gtk.Justification.CENTER)
        self.title_label.set_halign(Gtk.Align.CENTER)

        self.desc_label = Gtk.Label()
        self.desc_label.add_css_class("body")
        self.desc_label.set_wrap(True)
        self.desc_label.set_justify(Gtk.Justification.CENTER)
        self.desc_label.set_halign(Gtk.Align.CENTER)

        self.text_box.append(self.title_label)
        self.text_box.append(self.desc_label)

        self.append(self.icon)
        self.append(self.text_box)

        self._state = "disconnected"  # "online", "offline", "disconnected"
        self._update_layout()

    def set_state(self, state):
        if self._state != state:
            self._state = state
            self._update_layout()

    def _update_layout(self):
        if self._state == "online":
            self.icon.set_visible(True)
            self.icon.remove_css_class("dim-label")
            self.icon.set_from_icon_name("audio-headset-symbolic")
            self.desc_label.set_visible(True)
            self.desc_label.remove_css_class("dim-label")
            self.title_label.set_halign(Gtk.Align.CENTER)
            self.desc_label.set_halign(Gtk.Align.CENTER)
            self.title_label.set_justify(Gtk.Justification.CENTER)

        elif self._state == "offline":
            self.icon.set_visible(True)
            self.icon.add_css_class("dim-label")
            self.icon.set_from_icon_name("audio-headset-symbolic")
            self.desc_label.set_visible(True)
            self.desc_label.add_css_class("dim-label")
            self.title_label.set_halign(Gtk.Align.CENTER)
            self.desc_label.set_halign(Gtk.Align.CENTER)
            self.title_label.set_justify(Gtk.Justification.CENTER)

        else:  # disconnected
            self.icon.set_visible(False)
            self.desc_label.set_visible(True)
            self.desc_label.add_css_class("dim-label")
            self.title_label.set_halign(Gtk.Align.CENTER)
            self.title_label.set_justify(Gtk.Justification.CENTER)
            self.desc_label.set_halign(Gtk.Align.CENTER)
            self.desc_label.set_justify(Gtk.Justification.CENTER)

    def set_title(self, text):
        self.title_label.set_label(text)

    def set_description(self, text):
        self.desc_label.set_label(text)

    def set_icon_name(self, name):
        self.icon.set_from_icon_name(name)


class EQCanvas(Gtk.DrawingArea):
    def __init__(self, name, dbus_client):
        super().__init__()
        self.set_hexpand(True)
        self.set_size_request(-1, 250)
        self.set_focusable(True)
        self.set_can_target(True)
        self.name = name
        self.dbus_client = dbus_client
        # Parametric EQ values: 10 bands x (freq, gain, Q, type)
        # Legacy 30-value lists will be normalized on set_values
        self.values = [0.0] * 40
        self.selected_band = -1
        self.hover_band = -1
        self.drag_band = -1
        self._updating = False
        self._is_dragging = False

        self.set_draw_func(self._draw)

        # Use GestureDrag for both clicking and dragging to avoid conflicts
        self.drag_gesture = Gtk.GestureDrag()
        self.drag_gesture.connect("drag-begin", self._on_drag_begin)
        self.drag_gesture.connect("drag-update", self._on_drag_update)
        self.drag_gesture.connect("drag-end", self._on_drag_end)
        self.add_controller(self.drag_gesture)

        # Click to deselect/close popover
        self.click_gesture = Gtk.GestureClick()
        try:
            self.click_gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        except Exception as e:
            logger.debug("Gesture propagation phase not supported: %s", e)

        def _on_click(_g, n_press, x, y):
            band = self._get_band_at(x, y, self.get_width(), self.get_height())
            if band == -1:
                self.selected_band = -1
                self.popover.popdown()
                self.queue_draw()

        self.click_gesture.connect("pressed", _on_click)

        def _on_release(_g, n_press, x, y):
            if not self._is_dragging:
                band = self._get_band_at(x, y, self.get_width(), self.get_height())
                if band == -1:
                    self.selected_band = -1
                    self.popover.popdown()
                    self.queue_draw()

        self.click_gesture.connect("released", _on_release)
        self.add_controller(self.click_gesture)

        # Motion for hover detection
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_motion)
        motion.connect("leave", self._on_leave)
        self.add_controller(motion)

        # Scroll for Q-factor
        scroll = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.VERTICAL)
        scroll.connect("scroll", self._on_scroll)
        self.add_controller(scroll)

        # Keyboard accessibility
        self._has_focus = False
        key = Gtk.EventControllerKey()
        key.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key)
        focus = Gtk.EventControllerFocus()
        focus.connect("enter", lambda *_: self._set_focus(True))
        focus.connect("leave", lambda *_: self._set_focus(False))
        self.add_controller(focus)

        # Popover for editing
        self.popover = Gtk.Popover()
        self.popover.set_parent(self)
        self.popover.set_autohide(True)
        self.popover.set_position(Gtk.PositionType.TOP)
        self.popover.set_has_arrow(True)

        pop_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        pop_box.set_margin_start(12)
        pop_box.set_margin_end(12)
        pop_box.set_margin_top(12)
        pop_box.set_margin_bottom(12)
        self.popover.set_child(pop_box)

        self.pop_title = Gtk.Label()
        self.pop_title.add_css_class("title-4")
        pop_box.append(self.pop_title)

        grid = Gtk.Grid(column_spacing=12, row_spacing=8)
        pop_box.append(grid)

        grid.attach(Gtk.Label(label="Freq (Hz)", halign=Gtk.Align.START), 0, 0, 1, 1)
        self.freq_spin = Gtk.SpinButton.new_with_range(20, 20000, 1)
        self.freq_spin.connect("value-changed", self._on_popover_change)
        grid.attach(self.freq_spin, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label="Gain (dB)", halign=Gtk.Align.START), 0, 1, 1, 1)
        self.gain_spin = Gtk.SpinButton.new_with_range(-12, 12, 0.1)
        self.gain_spin.connect("value-changed", self._on_popover_change)
        grid.attach(self.gain_spin, 1, 1, 1, 1)

        grid.attach(Gtk.Label(label="Width (Q)", halign=Gtk.Align.START), 0, 2, 1, 1)
        self.q_spin = Gtk.SpinButton.new_with_range(0.1, 10.0, 0.1)
        self.q_spin.set_digits(2)
        self.q_spin.connect("value-changed", self._on_popover_change)
        grid.attach(self.q_spin, 1, 2, 1, 1)

        grid.attach(Gtk.Label(label="Type", halign=Gtk.Align.START), 0, 3, 1, 1)
        self.type_combo = Gtk.ComboBoxText()
        for label in [
            "Disabled",
            "Peaking EQ",
            "High Shelf",
            "High Pass",
            "Low Shelf",
            "Low Pass",
            "Notch",
        ]:
            self.type_combo.append_text(label)
        self.type_combo.connect("changed", self._on_type_change)
        grid.attach(self.type_combo, 1, 3, 1, 1)

    def set_values(self, values):
        if self._updating or self._is_dragging:
            return
        vals = list(values)

        # Normalize to 40 values (freq,gain,Q,type) for 10 bands
        norm = normalize_parametric_to_40(vals)
        if norm is None:
            # Initialize sensible defaults
            vals = []
            for i in range(10):
                log_f = math.log10(31) + (i / 9) * (math.log10(16000) - math.log10(31))
                vals.extend([10**log_f, 0.0, 1.414, 1.0])
        else:
            vals = norm

        # If all frequencies are zero, initialize
        all_zero = True
        for i in range(0, 40, 4):
            if vals[i] > 0:
                all_zero = False
                break
        if all_zero:
            for i in range(10):
                log_f = math.log10(31) + (i / 9) * (math.log10(16000) - math.log10(31))
                vals[i * 4] = 10**log_f
                vals[i * 4 + 2] = 1.414

        self.values = vals

        self.queue_draw()
        if self.popover.get_visible() and self.selected_band != -1:
            self._update_popover_values()

    def get_active_count(self) -> int:
        # Count bands where type != 0
        if len(self.values) < 40:
            return 10
        return sum(1 for i in range(10) if int(self.values[i * 4 + 3]) != 0)

    def _get_coords(self, band_idx, width, height):
        # Plot region with padding to fit axis labels
        left_pad, right_pad, top_pad, bottom_pad = 48, 56, 8, 20
        plot_w = max(10, width - left_pad - right_pad)
        plot_h = max(10, height - top_pad - bottom_pad)
        log_min = math.log10(20)
        log_max = math.log10(20000)
        if band_idx * 4 >= len(self.values):
            return 0, 0
        freq = self.values[band_idx * 4]
        gain = self.values[band_idx * 4 + 1]
        x = (
            (math.log10(max(20, freq)) - log_min) / (log_max - log_min)
        ) * plot_w + left_pad
        y = top_pad + plot_h / 2 - (gain / 15.0) * (plot_h / 2)
        return x, y

    def _get_band_at(self, x, y, width, height):
        for i in range(min(10, len(self.values) // 4)):
            if int(self.values[i * 4 + 3]) == 0:
                continue
            bx, by = self._get_coords(i, width, height)
            dist = math.sqrt((x - bx) ** 2 + (y - by) ** 2)
            if dist < 20:  # Generous hitbox
                return i
        return -1

    def _on_drag_begin(self, gesture, x, y):
        width = self.get_width()
        height = self.get_height()
        band = self._get_band_at(x, y, width, height)
        if band != -1:
            self.drag_band = band
            self.selected_band = band
            self._is_dragging = False  # Not dragging yet, just pressed
            self.queue_draw()
        else:
            self.drag_band = -1
            self.selected_band = -1
            self.popover.popdown()
            self.queue_draw()

    def _on_drag_update(self, gesture, x, y):
        if self.drag_band == -1:
            return

        # If we moved more than 3 pixels, it's a drag
        if not self._is_dragging:
            if abs(x) > 3 or abs(y) > 3:
                self._is_dragging = True
                self.popover.popdown()
                self.set_cursor(Gdk.Cursor.new_from_name("grabbing", None))

        if self._is_dragging:
            width = self.get_width()
            height = self.get_height()
            success, start_x, start_y = gesture.get_start_point()
            if not success:
                return
            cur_x = start_x + x
            cur_y = start_y + y

            log_min = math.log10(20)
            log_max = math.log10(20000)
            norm_x = max(0, min(1, cur_x / width))
            freq = 10 ** (log_min + norm_x * (log_max - log_min))
            gain = ((height / 2 - cur_y) / (height / 2)) * 15.0
            gain = max(-12.0, min(12.0, gain))

            # Normalize index for 40-value layout
            if len(self.values) >= 40:
                self.values[self.drag_band * 4] = freq
                self.values[self.drag_band * 4 + 1] = gain
            else:
                self.values[self.drag_band * 3] = freq
                self.values[self.drag_band * 3 + 1] = gain
            self.queue_draw()
            if hasattr(self, "on_modified_callback") and self.on_modified_callback:
                self.on_modified_callback()

    def _on_drag_end(self, gesture, x, y):
        if self.drag_band != -1:
            # If we never crossed the drag threshold, treat it as a click
            if not self._is_dragging:
                self._show_popover()
            else:
                # End of drag: send final update to D-Bus
                self.dbus_client.change_setting(self.name, self.values)
                if hasattr(self, "on_modified_callback") and self.on_modified_callback:
                    self.on_modified_callback()

        self._is_dragging = False
        self.drag_band = -1
        self._update_cursor()
        self.queue_draw()

    def _on_motion(self, controller, x, y):
        width = self.get_width()
        height = self.get_height()
        band = self._get_band_at(x, y, width, height)
        if band != self.hover_band:
            self.hover_band = band
            self._update_cursor()
            self.queue_draw()

    def _on_leave(self, controller):
        self.hover_band = -1
        self._update_cursor()
        self.queue_draw()

    def _update_cursor(self):
        if self._is_dragging:
            self.set_cursor(Gdk.Cursor.new_from_name("grabbing", None))
        elif self.hover_band != -1:
            self.set_cursor(Gdk.Cursor.new_from_name("pointer", None))
        else:
            self.set_cursor(None)

    def _set_focus(self, value: bool):
        self._has_focus = value
        self.queue_draw()

    def _on_key_pressed(self, controller, keyval, keycode, state):
        # Select a band if none selected
        if self.selected_band == -1:
            if len(self.values) >= 40:
                self.selected_band = 0
            else:
                return False

        idx = self.selected_band * 4
        if idx + 3 >= len(self.values):
            return False

        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        step_gain = 2.0 if ctrl else 0.5
        freq_factor_small = 1.03
        freq_factor_big = 1.10

        handled = True
        if keyval in (Gdk.KEY_Up,):
            self.values[idx + 1] = max(
                -12.0, min(12.0, self.values[idx + 1] + step_gain)
            )
        elif keyval in (Gdk.KEY_Down,):
            self.values[idx + 1] = max(
                -12.0, min(12.0, self.values[idx + 1] - step_gain)
            )
        elif keyval in (Gdk.KEY_Page_Up,):
            self.values[idx + 1] = max(-12.0, min(12.0, self.values[idx + 1] + 2.0))
        elif keyval in (Gdk.KEY_Page_Down,):
            self.values[idx + 1] = max(-12.0, min(12.0, self.values[idx + 1] - 2.0))
        elif keyval in (Gdk.KEY_Left,):
            factor = freq_factor_big if ctrl else freq_factor_small
            self.values[idx] = max(20.0, self.values[idx] / factor)
        elif keyval in (Gdk.KEY_Right,):
            factor = freq_factor_big if ctrl else freq_factor_small
            self.values[idx] = min(20000.0, self.values[idx] * factor)
        elif keyval in (Gdk.KEY_plus, Gdk.KEY_KP_Add):
            # Enable next disabled band
            for bi in range(10):
                if int(self.values[bi * 4 + 3]) == 0:
                    self.values[bi * 4 + 3] = 1.0
                    break
        elif keyval in (Gdk.KEY_minus, Gdk.KEY_KP_Subtract):
            # Disable last enabled band
            for bi in range(9, -1, -1):
                if int(self.values[bi * 4 + 3]) != 0:
                    self.values[bi * 4 + 3] = 0.0
                    if self.selected_band == bi:
                        self.selected_band = max(0, bi - 1)
                    break
        else:
            handled = False

        if handled:
            self.queue_draw()
            self.dbus_client.change_setting(self.name, self.values)
            if hasattr(self, "on_modified_callback") and self.on_modified_callback:
                self.on_modified_callback()
            return True
        return False

    def _on_scroll(self, controller, dx, dy):
        band = self.hover_band if self.hover_band != -1 else self.selected_band
        if band == -1 or band * 4 >= len(self.values):
            return
        q = self.values[band * 4 + 2]
        q -= dy * 0.1
        self.values[band * 4 + 2] = max(0.1, min(10.0, q))

        self._update_popover_values()
        self.queue_draw()
        self.dbus_client.change_setting(self.name, self.values)
        if hasattr(self, "on_modified_callback") and self.on_modified_callback:
            self.on_modified_callback()
        # Safety net: dismiss the editor after committing the type change
        try:
            self.popover.popdown()
        except Exception:
            pass

    def _show_popover(self):
        if self.selected_band == -1:
            return
        self.pop_title.set_label(f"Band {self.selected_band + 1}")
        self._update_popover_values()
        self._update_popover_pos()
        self.popover.popup()

    def _update_popover_values(self):
        if self.selected_band == -1 or (
            self.selected_band * 4 >= len(self.values)
            and self.selected_band * 3 >= len(self.values)
        ):
            return
        self._updating = True
        if len(self.values) >= 40:
            base = self.selected_band * 4
            self.freq_spin.set_value(self.values[base])
            self.gain_spin.set_value(self.values[base + 1])
            self.q_spin.set_value(self.values[base + 2])
            t = int(self.values[base + 3])
            self.type_combo.set_active(max(0, min(6, t)))
        else:
            base = self.selected_band * 3
            self.freq_spin.set_value(self.values[base])
            self.gain_spin.set_value(self.values[base + 1])
            self.q_spin.set_value(self.values[base + 2])
            self.type_combo.set_active(1)
        self._updating = False

    def _update_popover_pos(self):
        if self.selected_band == -1:
            return
        x, y = self._get_coords(self.selected_band, self.get_width(), self.get_height())
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
        self.popover.set_pointing_to(rect)
        # Ensure cleanup when the popover closes (no input grabting)
        try:
            # Connect only once
            if not hasattr(self, "_popover_close_hook"):

                def _on_popover_closed(*_args):
                    # Defensive cleanup: ensure hover state/cursor are reset
                    try:
                        self.hover_band = -1
                        self._is_dragging = False
                        self._update_cursor()
                        self.queue_draw()
                    except Exception:
                        pass

                self._popover_close_hook = self.popover.connect(
                    "closed", _on_popover_closed
                )
        except Exception:
            pass

    def _on_popover_change(self, *args):
        if (
            self._updating
            or self.selected_band == -1
            or self.selected_band * 4 >= len(self.values)
        ):
            return
        self.values[self.selected_band * 4] = self.freq_spin.get_value()
        self.values[self.selected_band * 4 + 1] = self.gain_spin.get_value()
        self.values[self.selected_band * 4 + 2] = self.q_spin.get_value()
        self.queue_draw()
        self.dbus_client.change_setting(self.name, self.values)
        if hasattr(self, "on_modified_callback") and self.on_modified_callback:
            self.on_modified_callback()

    def _on_type_change(self, combo):
        if self._updating or self.selected_band == -1 or len(self.values) < 40:
            return
        t = combo.get_active()
        self.values[self.selected_band * 4 + 3] = float(t)
        self.queue_draw()
        self.dbus_client.change_setting(self.name, self.values)
        if hasattr(self, "on_modified_callback") and self.on_modified_callback:
            self.on_modified_callback()

    def _draw(self, area, cr, width, height):
        # Grid within padded plot area
        left_pad, right_pad, top_pad, bottom_pad = 48, 56, 8, 20
        plot_w = max(10, width - left_pad - right_pad)
        plot_h = max(10, height - top_pad - bottom_pad)
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.1)
        cr.set_line_width(1.0)
        log_min, log_max = math.log10(20), math.log10(20000)
        for f in [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]:
            x = ((math.log10(f) - log_min) / (log_max - log_min)) * plot_w + left_pad
            cr.move_to(x, top_pad)
            cr.line_to(x, top_pad + plot_h)
            cr.stroke()
        for g in [-12, -6, 0, 6, 12]:
            y = top_pad + plot_h / 2 - (g / 15.0) * (plot_h / 2)
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.3 if g == 0 else 0.1)
            cr.move_to(left_pad, y)
            cr.line_to(left_pad + plot_w, y)
            cr.stroke()

        # Curve
        cr.set_source_rgba(0.2, 0.6, 1.0, 1.0)
        cr.set_line_width(3.0)
        num_bands = len(self.values) // 4
        for x in range(int(plot_w) + 1):
            f = 10 ** (log_min + (x / plot_w) * (log_max - log_min))
            total_gain = 0.0
            for i in range(num_bands):
                fc, gain, q, ftype = (
                    self.values[i * 4],
                    self.values[i * 4 + 1],
                    self.values[i * 4 + 2],
                    int(self.values[i * 4 + 3]) if len(self.values) >= 40 else 1,
                )
                if ftype == 0:
                    continue
                if f > 0 and fc > 0 and q > 0:
                    # Keep math simple; peaking accurate, others approximated for visualization
                    if ftype in (1, 6):  # peaking / notch
                        ww = (f / fc) - (fc / f)
                        total_gain += gain / (1 + (q * q) * (ww * ww))
                    elif ftype == 2:  # high shelf
                        total_gain += gain * (1 / (1 + (fc / max(f, 1e-6)) ** (2 * q)))
                    elif ftype == 4:  # low shelf
                        total_gain += gain * (1 / (1 + (max(f, 1e-6) / fc) ** (2 * q)))
                    elif ftype == 3:  # high pass
                        total_gain += -abs(gain) * (
                            1 / (1 + (fc / max(f, 1e-6)) ** (2 * q))
                        )
                    elif ftype == 5:  # low pass
                        total_gain += -abs(gain) * (
                            1 / (1 + (max(f, 1e-6) / fc) ** (2 * q))
                        )
            y = (
                top_pad
                + plot_h / 2
                - (max(-15.0, min(15.0, total_gain)) / 15.0) * (plot_h / 2)
            )
            xp = left_pad + x
            if x == 0:
                cr.move_to(xp, y)
            else:
                cr.line_to(xp, y)
        cr.stroke()
        cr.line_to(left_pad + plot_w, top_pad + plot_h)
        cr.line_to(left_pad, top_pad + plot_h)
        cr.close_path()
        cr.set_source_rgba(0.2, 0.6, 1.0, 0.1)
        cr.fill()

        # Focus ring if canvas is focused
        if self._has_focus:
            cr.set_source_rgba(0.2, 0.6, 1.0, 0.5)
            cr.set_line_width(2.0)
            cr.rectangle(1.0, 1.0, width - 2.0, height - 2.0)
            cr.stroke()

        # Axis labels
        try:
            cr.set_source_rgba(0.7, 0.7, 0.7, 0.9)
            cr.set_font_size(11)
            # Y-axis: -12 dB, 0 dB, +12 dB
            for g in (-12, 0, 12):
                y = top_pad + plot_h / 2 - (g / 15.0) * (plot_h / 2)
                label = f"{g:+.0f} dB"
                cr.move_to(8, y - 2)
                cr.show_text(label)
            # X-axis endpoints: 20 Hz (left), 8 kHz (right)
            cr.move_to(left_pad, top_pad + plot_h + 14)
            cr.show_text("20 Hz")
            cr.move_to(
                max(left_pad + plot_w - 40, left_pad + 10), top_pad + plot_h + 14
            )
            cr.show_text("8 kHz")
        except Exception as e:
            logger.debug("Failed to draw axis labels: %s", e)

        # Nodes
        for i in range(num_bands):
            if len(self.values) >= 40 and int(self.values[i * 4 + 3]) == 0:
                continue
            nx, ny = self._get_coords(i, width, height)
            if i == self.selected_band or i == self.hover_band:
                cr.set_source_rgba(0.2, 0.6, 1.0, 0.3)
                cr.arc(nx, ny, 12, 0, 2 * math.pi)
                cr.fill()
            cr.set_source_rgba(1, 1, 1, 1)
            cr.arc(nx, ny, 6, 0, 2 * math.pi)
            cr.fill()
            cr.set_source_rgba(0.2, 0.6, 1.0, 1)
            cr.set_line_width(2)
            cr.arc(nx, ny, 6, 0, 2 * math.pi)
            cr.stroke()
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.8)
            cr.set_font_size(10)
            cr.move_to(nx - 4, ny - 10)
            cr.show_text(str(i + 1))

        # Highlight curve for the current type (sum of all bands of that type)
        hilite_idx = self.selected_band if self.selected_band != -1 else self.hover_band
        if hilite_idx is not None and hilite_idx >= 0 and len(self.values) >= 40:
            t = int(self.values[hilite_idx * 4 + 3])
            if t != 0:
                colors = {
                    1: (0.2, 0.8, 0.2),  # peaking
                    2: (0.9, 0.6, 0.2),  # high shelf
                    3: (0.9, 0.2, 0.2),  # high pass
                    4: (0.2, 0.6, 0.9),  # low shelf
                    5: (0.6, 0.2, 0.9),  # low pass
                    6: (0.9, 0.2, 0.6),  # notch
                }
                r, g, b = colors.get(t, (1.0, 1.0, 0.2))
                cr.set_source_rgba(r, g, b, 1.0)
                cr.set_line_width(2.5)
                first = True
                for x in range(width + 1):
                    f = 10 ** (log_min + (x / width) * (log_max - log_min))
                    gsum = 0.0
                    for i in range(len(self.values) // 4):
                        fc = self.values[i * 4]
                        gain = self.values[i * 4 + 1]
                        q = self.values[i * 4 + 2]
                        ftype = int(self.values[i * 4 + 3])
                        if ftype != t or ftype == 0:
                            continue
                        if f > 0 and fc > 0 and q > 0:
                            if ftype in (1, 6):
                                ww = (f / fc) - (fc / f)
                                gsum += gain / (1 + (q * q) * (ww * ww))
                            elif ftype == 2:
                                gsum += gain * (
                                    1 / (1 + (fc / max(f, 1e-6)) ** (2 * q))
                                )
                            elif ftype == 4:
                                gsum += gain * (
                                    1 / (1 + (max(f, 1e-6) / fc) ** (2 * q))
                                )
                            elif ftype == 3:
                                gsum += -abs(gain) * (
                                    1 / (1 + (fc / max(f, 1e-6)) ** (2 * q))
                                )
                            elif ftype == 5:
                                gsum += -abs(gain) * (
                                    1 / (1 + (max(f, 1e-6) / fc) ** (2 * q))
                                )
                    y = height / 2 - (max(-15.0, min(15.0, gsum)) / 15.0) * (height / 2)
                    if first:
                        cr.move_to(x, y)
                        first = False
                    else:
                        cr.line_to(x, y)
                cr.stroke()

        # Highlight single-band curve on hover/selection
        hilite_idx = self.selected_band if self.selected_band != -1 else self.hover_band
        if hilite_idx is not None and hilite_idx >= 0 and len(self.values) >= 40:
            base = hilite_idx * 4
            fc = self.values[base]
            gain = self.values[base + 1]
            q = self.values[base + 2]
            ftype = int(self.values[base + 3])
            if ftype != 0 and fc > 0 and q > 0:
                # Color by type
                colors = {
                    1: (0.2, 0.8, 0.2),  # peaking
                    2: (0.9, 0.6, 0.2),  # high shelf
                    3: (0.9, 0.2, 0.2),  # high pass
                    4: (0.2, 0.6, 0.9),  # low shelf
                    5: (0.6, 0.2, 0.9),  # low pass
                    6: (0.9, 0.2, 0.6),  # notch
                }
                r, g, b = colors.get(ftype, (1.0, 1.0, 0.2))
                cr.set_source_rgba(r, g, b, 1.0)
                cr.set_line_width(2.5)
                first = True
                for x in range(width + 1):
                    f = 10 ** (log_min + (x / width) * (log_max - log_min))
                    if ftype in (1, 6):
                        ww = (f / fc) - (fc / f)
                        gval = gain / (1 + (q * q) * (ww * ww))
                    elif ftype == 2:
                        gval = gain * (1 / (1 + (fc / max(f, 1e-6)) ** (2 * q)))
                    elif ftype == 4:
                        gval = gain * (1 / (1 + (max(f, 1e-6) / fc) ** (2 * q)))
                    elif ftype == 3:
                        gval = -abs(gain) * (1 / (1 + (fc / max(f, 1e-6)) ** (2 * q)))
                    elif ftype == 5:
                        gval = -abs(gain) * (1 / (1 + (max(f, 1e-6) / fc) ** (2 * q)))
                    else:
                        gval = 0.0
                    y = height / 2 - (max(-15.0, min(15.0, gval)) / 15.0) * (height / 2)
                    if first:
                        cr.move_to(x, y)
                        first = False
                    else:
                        cr.line_to(x, y)
                cr.stroke()

    def get_values(self):
        # Return a shallow copy to avoid accidental external mutation
        return list(self.values)


class ArctisManagerWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Arctis Manager")
        self.set_default_size(650, 850)
        self._load_styles()
        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)
        self.view_stack = Adw.ViewStack()
        self.header_bar = Adw.HeaderBar()
        settings = Gtk.Settings.get_default()
        if settings:
            layout = settings.get_property("gtk-decoration-layout")
            if layout:
                self.header_bar.set_decoration_layout(layout)
            if settings.get_property("gtk-application-prefer-dark-theme"):
                Adw.StyleManager.get_default().set_color_scheme(
                    Adw.ColorScheme.PREFER_DARK
                )
        switcher_title = Adw.ViewSwitcherTitle()
        switcher_title.set_stack(self.view_stack)
        self.header_bar.set_title_widget(switcher_title)
        try:
            toolbar_view.add_top_bar(self.header_bar)
        except Exception:
            pass
        self.view_stack.set_vexpand(True)
        toolbar_view.set_content(self.view_stack)
        switcher_bar = Adw.ViewSwitcherBar()
        switcher_bar.set_stack(self.view_stack)
        try:
            toolbar_view.add_bottom_bar(switcher_bar)
        except Exception:
            pass
        switcher_title.bind_property(
            "title-visible", switcher_bar, "reveal", GObject.BindingFlags.SYNC_CREATE
        )
        self._eq_mode = "wireless"
        self._parametric_names = set()
        # Per-target cache for EQ values (bootstrapped from disk cache on startup)
        self._eq_cache = EqStateCache()
        self._eq_values_by_mode: dict[str, dict[str, list[float]]] = {
            "wi_hp": dict(self._eq_cache.parametric.get("wi_hp", {})),
            "bt_hp": dict(self._eq_cache.parametric.get("bt_hp", {})),
            "wi_mic": dict(self._eq_cache.parametric.get("wi_mic", {})),
            "bt_mic": dict(self._eq_cache.parametric.get("bt_mic", {})),
        }
        # Bootstrap flags for prefetching all target banks on startup
        self._bootstrap_scheduled = False
        self._bootstrap_in_progress = False
        self._bootstrap_done = False
        self._bootstrap_seq: list[str] = []
        self._bootstrap_idx: int = 0
        self._bootstrap_prev_mode: str = self._eq_mode
        # Track which target we requested settings for, to avoid caching under the wrong key
        self._pending_fetch_mode: str | None = None

        # Helper to resolve the best available icon in the current theme
        def _best_icon(candidates: list[str]) -> str:
            theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
            for name in candidates:
                try:
                    if theme and theme.has_icon(name):
                        return name
                except Exception:
                    pass
            return candidates[0] if candidates else ""

        self._best_icon = _best_icon

        def _cache_key_for_mode(mode: str) -> str:
            if mode == "bluetooth":
                return "bt_hp"
            if mode == "microphone":
                return "wi_mic"  # future: differentiate bt_mic when supported
            return "wi_hp"

        self._cache_key_for_mode = _cache_key_for_mode

        # TAB 1: Dashboard
        self.dashboard_scroll = Gtk.ScrolledWindow()
        dash_page = self.view_stack.add_titled(
            self.dashboard_scroll, "dashboard", I18n.translate("ui", "status")
        )
        dash_page.set_icon_name("audio-card-symbolic")
        dash_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.dashboard_scroll.set_child(dash_vbox)
        self.hero = HeroBox()
        dash_vbox.append(self.hero)
        self.dash_clamp = Adw.Clamp()
        self.dash_clamp.set_maximum_size(600)
        dash_vbox.append(self.dash_clamp)
        self.dash_vbox_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        self.dash_vbox_inner.set_margin_start(16)
        self.dash_vbox_inner.set_margin_end(16)
        self.dash_vbox_inner.set_margin_bottom(32)
        self.dash_group = Adw.PreferencesGroup()
        self.mix_group = Adw.PreferencesGroup()
        self.mix_group.set_title(I18n.translate("ui", "audio_mix"))
        self.dash_vbox_inner.append(self.dash_group)
        self.dash_vbox_inner.append(self.mix_group)
        self.dash_clamp.set_child(self.dash_vbox_inner)
        self.dash_clamp.set_visible(False)
        self.mix_group.set_visible(False)

        # TAB 2: Settings
        self.settings_page = Adw.PreferencesPage()
        set_page = self.view_stack.add_titled(
            self.settings_page, "settings", I18n.translate("ui", "settings")
        )
        set_page.set_icon_name("preferences-system-symbolic")

        # TAB 3: Logs
        self.logs_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        log_page = self.view_stack.add_titled(
            self.logs_vbox, "logs", I18n.translate("ui", "logs")
        )
        log_page.set_icon_name("view-list-bullet-symbolic")
        log_toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        log_toolbar.set_margin_start(12)
        log_toolbar.set_margin_end(12)
        log_toolbar.set_margin_top(6)
        log_toolbar.set_margin_bottom(6)
        self.logs_vbox.append(log_toolbar)
        self.log_source_combo = Gtk.DropDown.new_from_strings(
            [I18n.translate("ui", "gui_logs"), I18n.translate("ui", "daemon_logs")]
        )
        self.log_source_combo.connect("notify::selected", self.on_log_source_changed)
        log_toolbar.append(self.log_source_combo)
        refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh_btn.connect("clicked", lambda _: self.refresh_logs())
        log_toolbar.append(refresh_btn)
        clear_btn = Gtk.Button.new_from_icon_name("edit-clear-symbolic")
        clear_btn.connect("clicked", lambda _: self.clear_logs())
        log_toolbar.append(clear_btn)
        log_scroll = Gtk.ScrolledWindow()
        log_scroll.set_vexpand(True)
        self.logs_vbox.append(log_scroll)
        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_monospace(True)
        self.log_view.set_left_margin(12)
        self.log_view.set_right_margin(12)
        self.log_view.set_top_margin(12)
        self.log_view.set_bottom_margin(12)
        log_scroll.set_child(self.log_view)
        self.gui_log_buffer = Gtk.TextBuffer()
        self.daemon_log_buffer = Gtk.TextBuffer()
        self.log_view.set_buffer(self.gui_log_buffer)
        handler = GtkLogHandler(self.gui_log_buffer)
        handler.setFormatter(
            logging.Formatter("%(created).0f %(levelname)s: %(message)s")
        )
        logging.getLogger().addHandler(handler)
        self._gtk_log_handler = handler

        self.dbus_client = GtkDbusClient(
            on_status_cb=self.on_status_received,
            on_settings_cb=self.on_settings_received,
        )
        (
            self._settings_widgets,
            self._settings_page_groups,
            self._settings_data,
            self._status_data,
        ) = {}, {}, {}, {}
        (
            self._option_lists,
            self._updating_ui,
            self._dash_widgets,
            self._dash_rows,
            self._mix_rows,
        ) = {}, False, {}, [], []
        self._is_offline = True
        self.dbus_client.start()
        self.connect("close-request", self.on_close)

    def on_log_source_changed(self, dropdown, pspec):
        self.log_view.set_buffer(
            self.gui_log_buffer
            if dropdown.get_selected() == 0
            else self.daemon_log_buffer
        )
        if dropdown.get_selected() == 1:
            self.refresh_logs()

    def refresh_logs(self):
        if self.log_source_combo.get_selected() == 1:
            # Run journalctl in a worker thread to avoid freezing the UI
            import threading

            threading.Thread(target=self._fetch_daemon_logs, daemon=True).start()

    def _fetch_daemon_logs(self):
        # Worker-thread context. Do not touch GTK widgets directly here.
        try:
            from linux_arctis_manager.constants import SYSTEMD_SERVICE_NAME

            cmd = [
                "journalctl",
                "--user",
                "-u",
                SYSTEMD_SERVICE_NAME,
                "-o",
                "short-unix",
                "-n",
                "100",
                "--no-pager",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            def apply(text):
                self.daemon_log_buffer.set_text(text)
                mark = self.daemon_log_buffer.get_insert()
                self.log_view.scroll_to_mark(mark, 0.0, True, 0.5, 0.5)

            GLib.idle_add(apply, result.stdout)
        except subprocess.TimeoutExpired:
            GLib.idle_add(
                self.daemon_log_buffer.set_text,
                I18n.translate("ui", "log_timeout"),
            )
        except Exception as e:
            GLib.idle_add(
                self.daemon_log_buffer.set_text,
                I18n.translate("ui", "log_error").format(error=str(e)),
            )

    def clear_logs(self):
        if self.log_source_combo.get_selected() == 0:
            self.gui_log_buffer.set_text("")
        else:
            self.daemon_log_buffer.set_text("")

    def on_close(self, *args):
        # Detach GUI log handler and stop background services
        try:
            if hasattr(self, "_gtk_log_handler") and self._gtk_log_handler:
                logging.getLogger().removeHandler(self._gtk_log_handler)
                self._gtk_log_handler = None
        except Exception:
            pass
        self.dbus_client.stop()
        return False

    def get_list_options_cb(self, list_name, opts):
        self._option_lists[list_name] = opts
        if self._settings_data:
            self.refresh_settings_ui()

    def on_status_received(self, status: dict):
        if status == self._status_data and getattr(
            self, "_first_status_handled", False
        ):
            return
        self._first_status_handled = True
        self._status_data = status
        flat_status = {k: v for cat, obj in status.items() for k, v in obj.items()}
        power_val = flat_status.get("headset_power_status", {}).get("value", "offline")
        was_offline = getattr(self, "_is_offline", True)
        self._is_offline = not status or power_val == "offline"
        if was_offline != self._is_offline:
            self.refresh_settings_ui()
        dev_name = self._settings_data.get(
            "device_name", I18n.translate("ui", "app_name")
        )
        if self._is_offline:
            # Use compact hero state when offline/disconnected
            if not status:
                self.hero.set_state("disconnected")
                self.hero.set_title(I18n.translate("ui", "app_name"))
                self.hero.set_description(I18n.translate("ui", "no_device_detected"))
            else:
                self.hero.set_state("offline")
                self.hero.set_title(dev_name)
                self.hero.set_description(I18n.translate("status_values", "offline"))
            self.hero.set_visible(True)
            self.dash_clamp.set_visible(False)
            self._dash_widgets.clear()
            for row in self._dash_rows:
                self.dash_group.remove(row)
            self._dash_rows.clear()
            for row in self._mix_rows:
                self.mix_group.remove(row)
            self._mix_rows.clear()
            return
        self.dash_clamp.set_visible(True)
        self.hero.set_state("online")
        self.hero.set_title(dev_name)
        self.hero.set_description(
            I18n.translate("ui", "connected_active")
            if power_val == "online"
            else I18n.translate("ui", "charging_offline")
        )
        expected = set()
        if flat_status.get("headset_battery_charge"):
            expected.add("battery")
        if flat_status.get("bluetooth_connection"):
            expected.add("bluetooth")
        if flat_status.get("chat_mix") and flat_status.get("media_mix"):
            expected.add("mix")
        if flat_status.get("mic_status"):
            expected.add("mic")
        if set(self._dash_widgets.keys()) != expected:
            self._dash_widgets.clear()
            for row in self._dash_rows:
                self.dash_group.remove(row)
            self._dash_rows.clear()
            for row in self._mix_rows:
                self.mix_group.remove(row)
            self._mix_rows.clear()
            if "battery" in expected:
                row = Adw.ActionRow(title=I18n.translate("ui", "battery"))
                icon = Gtk.Image.new_from_icon_name("battery-level-100-symbolic")
                row.add_prefix(icon)
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                level_bar = Gtk.LevelBar()
                level_bar.set_min_value(0)
                level_bar.set_max_value(100)
                level_bar.set_size_request(100, -1)
                lbl = Gtk.Label()
                lbl.add_css_class("numeric")
                box.append(level_bar)
                box.append(lbl)
                row.add_suffix(box)
                self.dash_group.add(row)
                self._dash_rows.append(row)
                self._dash_widgets["battery"] = {
                    "row": row,
                    "icon": icon,
                    "bar": level_bar,
                    "label": lbl,
                }
            if "bluetooth" in expected:
                row = Adw.ActionRow(title=I18n.translate("ui", "bluetooth"))
                icon = Gtk.Image.new_from_icon_name("bluetooth-active-symbolic")
                row.add_prefix(icon)
                lbl = Gtk.Label()
                row.add_suffix(lbl)
                self.dash_group.add(row)
                self._dash_rows.append(row)
                self._dash_widgets["bluetooth"] = {
                    "row": row,
                    "icon": icon,
                    "label": lbl,
                }
            if "mix" in expected:
                self.mix_group.set_visible(True)
                row = Adw.ActionRow()
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                box.set_margin_top(12)
                box.set_margin_bottom(12)
                box.set_margin_start(16)
                box.set_margin_end(16)
                icon_game = Gtk.Image.new_from_icon_name("input-gaming-symbolic")
                box.append(icon_game)
                scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
                scale.set_hexpand(True)
                scale.set_draw_value(False)
                scale.add_mark(50, Gtk.PositionType.BOTTOM, None)
                scale.connect("change-value", lambda *args: True)
                box.append(scale)
                icon_chat = Gtk.Image.new_from_icon_name("audio-headset-symbolic")
                box.append(icon_chat)
                row.set_child(box)
                self.mix_group.add(row)
                self._mix_rows.append(row)
                self._dash_widgets["mix"] = {"row": row, "scale": scale}
            if "mic" in expected:
                row = Adw.ActionRow(title=I18n.translate("ui", "microphone"))
                icon = Gtk.Image.new_from_icon_name("audio-input-microphone-symbolic")
                row.add_prefix(icon)
                lbl = Gtk.Label()
                row.add_suffix(lbl)
                self.dash_group.add(row)
                self._dash_rows.append(row)
                self._dash_widgets["mic"] = {"row": row, "icon": icon, "label": lbl}
        if "battery" in expected:
            w = self._dash_widgets["battery"]
            val = float(flat_status["headset_battery_charge"]["value"])
            is_charging = flat_status.get("cable_charging", {}).get("value") == "on"
            icon_name = (
                "battery-level-100-charged-symbolic"
                if is_charging
                else (
                    "battery-level-20-symbolic"
                    if val <= 20
                    else (
                        "battery-level-50-symbolic"
                        if val <= 50
                        else "battery-level-100-symbolic"
                    )
                )
            )
            w["icon"].set_from_icon_name(icon_name)
            w["bar"].set_value(val)
            w["label"].set_label(f"{int(val)}%" + (" ⚡" if is_charging else ""))
        if "bluetooth" in expected:
            w = self._dash_widgets["bluetooth"]
            is_bt = flat_status["bluetooth_connection"]["value"] == "connected"
            w["icon"].set_from_icon_name(
                "bluetooth-active-symbolic" if is_bt else "bluetooth-disabled-symbolic"
            )
            w["label"].set_label(
                I18n.translate("status_values", "connected")
                if is_bt
                else I18n.translate("status_values", "disconnected")
            )
            w["label"].set_css_classes(["success" if is_bt else "error"])
        if "mix" in expected:
            w = self._dash_widgets["mix"]
            chat, media = (
                float(flat_status["chat_mix"]["value"]),
                float(flat_status["media_mix"]["value"]),
            )
            w["scale"].set_value(
                50.0 if (chat + media) == 0 else (chat / (chat + media)) * 100.0
            )
        if "mic" in expected:
            w = self._dash_widgets["mic"]
            is_muted = flat_status["mic_status"]["value"] == "muted"
            w["icon"].set_from_icon_name(
                "microphone-sensitivity-muted-symbolic"
                if is_muted
                else "audio-input-microphone-symbolic"
            )
            w["label"].set_label(
                I18n.translate("status_values", "muted")
                if is_muted
                else I18n.translate("status_values", "unmuted")
            )
            w["label"].set_css_classes(["error" if is_muted else "success"])

    def on_settings_received(self, new_settings: dict):
        if new_settings == self._settings_data:
            return
        dev_name = new_settings.get("device_name")
        if dev_name and not getattr(self, "_is_offline", True):
            # Update hero title when online
            try:
                self.hero.set_title(dev_name)
            except Exception:
                pass
        # Prefer daemon-provided banks; otherwise cache current-target value only
        banks = (
            new_settings.get("parametric_eq_banks")
            if isinstance(new_settings, dict)
            else None
        )
        if isinstance(banks, dict):
            self._has_banks = True
            config = new_settings.get("settings_config", {})
            # Determine parametric setting names
            param_names = set()
            for section, data in new_settings.items():
                if section in ("settings_config", "device_name") or not isinstance(
                    data, dict
                ):
                    continue
                for s_name in data.keys():
                    if config.get(s_name, {}).get("type") == "parametric_eq":
                        param_names.add(s_name)
            # Ingest each bank for each parametric setting name
            for ck in ("wi_hp", "bt_hp", "wi_mic", "bt_mic"):
                bank = banks.get(ck)
                if isinstance(bank, dict) and isinstance(
                    bank.get("parametric_eq"), list
                ):
                    for s_name in param_names:
                        self._eq_values_by_mode.setdefault(ck, {})[s_name] = list(
                            bank["parametric_eq"]
                        )  # type: ignore
                        try:
                            self._eq_cache.set_value(
                                ck, s_name, list(bank["parametric_eq"])
                            )  # type: ignore
                            if isinstance(bank.get("preset"), str):
                                self._eq_cache.set_preset(
                                    ck, s_name, str(bank["preset"])
                                )
                        except Exception:
                            pass
            self._pending_fetch_mode = None
            # Skip bootstrap if banks are present
            self._bootstrap_scheduled = True
            self._bootstrap_done = True
        else:
            try:
                mode = self._pending_fetch_mode or getattr(self, "_eq_mode", "wireless")
                config = new_settings.get("settings_config", {})
                for section, data in new_settings.items():
                    if section in ("settings_config", "device_name") or not isinstance(
                        data, dict
                    ):
                        continue
                    for s_name, s_val in data.items():
                        if config.get(s_name, {}).get("type") == "parametric_eq":
                            ck = self._cache_key_for_mode(mode)
                            self._eq_values_by_mode.setdefault(ck, {})[s_name] = s_val
                            try:
                                self._eq_cache.set_value(
                                    ck,
                                    s_name,
                                    list(s_val) if isinstance(s_val, list) else s_val,
                                )
                            except Exception:
                                pass
            except Exception:
                pass
            finally:
                self._pending_fetch_mode = None
        for name, kwargs in new_settings.get("settings_config", {}).items():
            if kwargs.get("type") == "select":
                source = kwargs.get("options_source")
                if source and source not in self._option_lists:
                    self.dbus_client.request_list_options(
                        source, self.get_list_options_cb
                    )
        self._settings_data = new_settings
        # Start one-time bootstrap to prefetch EQ values for all targets (only if banks absent)
        if not self._bootstrap_scheduled and not getattr(self, "_has_banks", False):
            self._bootstrap_scheduled = True
            GLib.timeout_add(50, self._bootstrap_eq_start)
        self.refresh_settings_ui()

    def _bootstrap_eq_start(self):
        if self._bootstrap_in_progress or self._bootstrap_done:
            return False
        self._bootstrap_in_progress = True
        self._bootstrap_prev_mode = self._eq_mode
        self._bootstrap_seq = ["wireless", "bluetooth", "microphone"]
        self._bootstrap_idx = 0
        # Run first step soon; keep returning True to continue
        GLib.timeout_add(150, self._bootstrap_eq_step)
        return False

    def _bootstrap_eq_step(self):
        try:
            if self._bootstrap_idx >= len(self._bootstrap_seq):
                # Restore previous mode and fetch settings again
                self._eq_mode = self._bootstrap_prev_mode
                try:
                    self.dbus_client.set_eq_target(self._bootstrap_prev_mode)
                    self._pending_fetch_mode = self._bootstrap_prev_mode
                    self.dbus_client.request_settings()
                except Exception:
                    pass
                self._bootstrap_in_progress = False
                self._bootstrap_done = True
                # UI will update on next settings, but also refresh now
                self.refresh_settings_ui()
                return False
            mode = self._bootstrap_seq[self._bootstrap_idx]
            self._eq_mode = mode
            try:
                self.dbus_client.set_eq_target(mode)
                self._pending_fetch_mode = mode
                self.dbus_client.request_settings()
            except Exception:
                pass
            self._bootstrap_idx += 1
            return True
        except Exception:
            # Fail-safe: stop loop
            self._bootstrap_in_progress = False
            return False

    def refresh_settings_ui(self):
        self._updating_ui = True
        config = self._settings_data.get("settings_config", {})
        label_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        active_names = set()
        for section, data in self._settings_data.items():
            if section in ("settings_config", "parametric_eq_banks") or not isinstance(
                data, dict
            ):
                continue
            is_offline = (
                section in ["device", "audio", "microphone", "mic"] and self._is_offline
            )
            if section not in self._settings_page_groups:
                self._settings_page_groups[section] = Adw.PreferencesGroup(
                    title=I18n.translate("ui", section)
                )
                self.settings_page.add(self._settings_page_groups[section])
            group = self._settings_page_groups[section]
            group.set_visible(not is_offline and bool(data))
            if is_offline:
                continue
            for name, value in data.items():
                cfg = config.get(name, {})
                stype = cfg.get("type")
                active_names.add(name)
                if stype in ["equalizer", "parametric_eq"]:
                    # Ensure Equalizer ViewStack exists once
                    if "equalizer" not in self._settings_page_groups:
                        # Use no group title to avoid floating headers
                        self._settings_page_groups["equalizer"] = Adw.PreferencesGroup(
                            title=""
                        )
                        self.settings_page.add(self._settings_page_groups["equalizer"])
                    if not hasattr(self, "_eq_stack"):
                        # Build ViewStack and Switcher (3-way tab: 2.4G Headphones, Bluetooth Headphones, 2.4G Mic)
                        self._eq_stack = Adw.ViewStack()
                        self._eq_switcher = Adw.ViewSwitcher()
                        self._eq_switcher.set_stack(self._eq_stack)
                        container = Gtk.Box(
                            orientation=Gtk.Orientation.VERTICAL, spacing=8
                        )
                        container.set_margin_top(6)
                        container.set_margin_bottom(6)
                        # Add the tab switcher visibly above the stack
                        container.append(self._eq_switcher)
                        container.append(self._eq_stack)
                        # Pages
                        self._eq_wireless_group = Adw.PreferencesGroup()
                        self._eq_stack.add_titled(
                            self._eq_wireless_group, "wireless", "2.4GHz Headphones"
                        )
                        self._eq_bluetooth_group = Adw.PreferencesGroup()
                        self._eq_stack.add_titled(
                            self._eq_bluetooth_group,
                            "bluetooth",
                            "Bluetooth Headphones",
                        )
                        self._eq_mic_group = Adw.PreferencesGroup()
                        self._eq_stack.add_titled(
                            self._eq_mic_group, "microphone", "2.4GHz Mic"
                        )
                        # Add container to the Equalizer group as a single row
                        self._eq_tabs_row = Adw.ActionRow()
                        self._eq_tabs_row.set_child(container)
                        self._settings_page_groups["equalizer"].add(self._eq_tabs_row)

                    # Respond to tab changes: set EQ target + update only visible tab from cached banks
                    def on_stack_change(_stack, _pspec=None):
                        name = self._eq_stack.get_visible_child_name()
                        if name == "bluetooth":
                            self._eq_mode = "bluetooth"
                            self.dbus_client.set_eq_target("bluetooth")
                        elif name == "microphone":
                            self._eq_mode = "microphone"
                            self.dbus_client.set_eq_target("microphone")
                        else:
                            self._eq_mode = "wireless"
                            self.dbus_client.set_eq_target("wireless")
                        tmp = self._updating_ui
                        self._updating_ui = True
                        bank_name = (
                            "microphone" if self._eq_mode == "microphone" else "output"
                        )
                        ck = self._cache_key_for_mode(self._eq_mode)
                        for key, w in self._settings_widgets.items():
                            if (
                                "preset_row" in w
                                and "preset_names" in w
                                and "canvas" in w
                                and w.get("mode") == self._eq_mode
                            ):
                                setting_name = w.get("setting_name")
                                presets = preset_manager.get_parametric_eq_presets(
                                    bank_name
                                )
                                names = list(presets.keys())
                                if (
                                    "Custom" in w.get("preset_names", [])
                                    and "Custom" not in names
                                ):
                                    names.append("Custom")
                                w["preset_names"] = names
                                w["preset_row"].set_model(Gtk.StringList.new(names))
                                mv = (
                                    self._eq_values_by_mode.get(ck, {}).get(
                                        setting_name
                                    )
                                    if setting_name
                                    else None
                                )
                                if mv is not None:
                                    w["canvas"].set_values(mv)
                                target_idx = -1
                                if mv is not None:
                                    for i, nm in enumerate(names):
                                        if nm in presets and values_match(
                                            mv, presets[nm]
                                        ):
                                            target_idx = i
                                            break
                                if target_idx == -1 and "Custom" in names:
                                    target_idx = names.index("Custom")
                                if target_idx != -1:
                                    w["preset_row"].set_selected(target_idx)
                        self._updating_ui = tmp

                    self._eq_stack.connect(
                        "notify::visible-child-name", on_stack_change
                    )
                    # Do not trigger on_stack_change on build to avoid flicker/override

                    # Wire up routing switches
                    def _update_routing():
                        # Read from TextToggle components
                        transport = (
                            "wireless"
                            if getattr(self, "_transport_toggle", None) is None
                            or self._transport_toggle.get_active_index() == 0
                            else "bluetooth"
                        )
                        endpoint = (
                            "headphone"
                            if getattr(self, "_endpoint_toggle", None) is None
                            or self._endpoint_toggle.get_active_index() == 0
                            else "microphone"
                        )
                        # Enforce: Microphone EQ is Wireless only
                        if endpoint == "microphone" and transport != "wireless":
                            transport = "wireless"
                            if hasattr(self, "_transport_toggle"):
                                self._transport_toggle.set_active_index(0)
                        # Disable Bluetooth option when Mic selected; enable otherwise
                        if hasattr(self, "_transport_toggle"):
                            self._transport_toggle.btn_right.set_sensitive(
                                endpoint != "microphone"
                            )
                        self._eq_transport = transport
                        self._eq_endpoint = endpoint
                        self._eq_mode = (
                            "microphone" if endpoint == "microphone" else transport
                        )
                        # Set target on daemon
                        if endpoint == "microphone":
                            # Both wireless and (likely) BT mic use target 'microphone' until proven otherwise
                            self.dbus_client.set_eq_target("microphone")
                        else:
                            self.dbus_client.set_eq_target(
                                "bluetooth" if transport == "bluetooth" else "wireless"
                            )
                        # After changing target, refresh settings so the EQ view updates
                        try:
                            self._pending_fetch_mode = self._eq_mode
                            self.dbus_client.request_settings()
                        except Exception:
                            pass
                        # Swap preset bank for mic/output
                        bank = "microphone" if endpoint == "microphone" else "output"
                        tmp = self._updating_ui
                        self._updating_ui = True
                        for key, w in self._settings_widgets.items():
                            if (
                                "preset_row" in w
                                and "preset_names" in w
                                and "canvas" in w
                                and w.get("mode") == self._eq_mode
                            ):
                                presets = preset_manager.get_parametric_eq_presets(bank)
                                names = list(presets.keys())
                                if (
                                    "Custom" in w.get("preset_names", [])
                                    and "Custom" not in names
                                ):
                                    names.append("Custom")
                                sel_idx = w["preset_row"].get_selected()
                                prev_names = w.get("preset_names", [])
                                prev_sel_name = (
                                    prev_names[sel_idx]
                                    if 0 <= sel_idx < len(prev_names)
                                    else None
                                )
                                w["preset_names"] = names
                                w["preset_row"].set_model(Gtk.StringList.new(names))
                                target_idx = -1
                                setting_name = w.get("setting_name")
                                if setting_name:
                                    ck = self._cache_key_for_mode(self._eq_mode)
                                    mv = self._eq_values_by_mode.get(ck, {}).get(
                                        setting_name
                                    )
                                    if mv is not None:
                                        for i, nm in enumerate(names):
                                            if nm in presets and values_match(
                                                mv, presets[nm]
                                            ):
                                                target_idx = i
                                                break
                                if target_idx == -1:
                                    if prev_sel_name and prev_sel_name in names:
                                        target_idx = names.index(prev_sel_name)
                                    elif "Flat" in names:
                                        target_idx = names.index("Flat")
                                    elif "Custom" in names:
                                        target_idx = names.index("Custom")
                                if target_idx != -1:
                                    w["preset_row"].set_selected(target_idx)
                                if "delete_btn" in w and 0 <= w[
                                    "preset_row"
                                ].get_selected() < len(names):
                                    sel_name = names[w["preset_row"].get_selected()]
                                    w["delete_btn"].set_visible(
                                        sel_name in presets
                                        and not preset_manager.is_builtin_parametric(
                                            sel_name, bank
                                        )
                                    )
                        self._updating_ui = tmp

                    # Connect new toggles if present
                    if hasattr(self, "_transport_toggle"):
                        self._transport_toggle.btn_left.connect(
                            "toggled", lambda *_: _update_routing()
                        )
                        self._transport_toggle.btn_right.connect(
                            "toggled", lambda *_: _update_routing()
                        )
                    if hasattr(self, "_endpoint_toggle"):
                        self._endpoint_toggle.btn_left.connect(
                            "toggled", lambda *_: _update_routing()
                        )
                        self._endpoint_toggle.btn_right.connect(
                            "toggled", lambda *_: _update_routing()
                        )
                    _update_routing()
                    # Add EQ rows to all three tabs
                    eq_group = self._eq_wireless_group
                    self._settings_page_groups["equalizer"].set_visible(
                        not self._is_offline
                    )
                    if stype == "parametric_eq":
                        # Use cached banks if present; fallback to legacy value
                        def _bank(mode):
                            ck = self._cache_key_for_mode(mode)
                            return self._eq_values_by_mode.get(ck, {}).get(name)

                        w_val = _bank("wireless") or value
                        b_val = _bank("bluetooth") or value
                        m_val = _bank("microphone") or value
                        self._update_or_create_parametric_equalizer(
                            name, w_val, cfg, self._eq_wireless_group, mode="wireless"
                        )
                        self._update_or_create_parametric_equalizer(
                            name, b_val, cfg, self._eq_bluetooth_group, mode="bluetooth"
                        )
                        self._update_or_create_parametric_equalizer(
                            name, m_val, cfg, self._eq_mic_group, mode="microphone"
                        )
                    else:
                        self._update_or_create_equalizer(name, value, cfg, eq_group)
                    continue
                if name in self._settings_widgets:
                    self._update_existing_setting_widget(name, value, cfg)
                else:
                    self._create_new_setting_widget(
                        name,
                        value,
                        cfg,
                        group,
                        I18n.translate("settings", name),
                        I18n.translate("settings_descriptions", name),
                        label_group,
                    )
        # Clean up widgets for settings that are no longer present, considering mode-suffixed keys
        stale_keys = []
        for key in list(self._settings_widgets.keys()):
            base = key.split("@", 1)[0]
            if base not in active_names:
                stale_keys.append(key)
        for key in stale_keys:
            widget_data = self._settings_widgets.pop(key)
            if "row" in widget_data:
                for group in self._settings_page_groups.values():
                    try:
                        group.remove(widget_data["row"])
                    except Exception:
                        pass
        self._updating_ui = False

    def _update_or_create_parametric_equalizer(
        self, name, value, cfg, group, mode: str = "wireless"
    ):
        if not isinstance(value, list) or (len(value) not in (30, 40)):
            value = cfg.get("default_value", [0.0] * 30)
        bank = "microphone" if mode == "microphone" else "output"
        presets = preset_manager.get_parametric_eq_presets(bank)
        widget_key = f"{name}@{mode}"

        if widget_key not in self._settings_widgets:
            eq_widgets = {}
            # Preset dropdown with delete button
            preset_row = Adw.ComboRow(title="EQ Preset")
            preset_names = list(presets.keys())
            curr_idx = -1
            # Prefer cached preset name for this target if available
            try:
                ck = self._cache_key_for_mode(mode)
                cached_name = self._eq_cache.get_preset(ck, name)
                if cached_name and cached_name in preset_names:
                    curr_idx = preset_names.index(cached_name)
            except Exception:
                pass
            for i, pn in enumerate(preset_names):
                target = presets[pn]
                if values_match(value, target):
                    curr_idx = i
                    break
            if curr_idx == -1:
                preset_names.append("Custom")
                curr_idx = len(preset_names) - 1
            preset_row.set_model(Gtk.StringList.new(preset_names))
            preset_row.set_selected(curr_idx)

            delete_btn = Gtk.Button()
            delete_btn.set_icon_name(
                self._best_icon(
                    [
                        "user-trash-symbolic",
                        "edit-delete-symbolic",
                        "user-trash",
                    ]
                )
            )
            delete_btn.set_valign(Gtk.Align.CENTER)
            delete_btn.set_tooltip_text("Delete preset")
            delete_btn.set_visible(False)
            preset_row.add_suffix(delete_btn)

            def _update_delete_visibility(selected_name: str):
                delete_btn.set_visible(
                    selected_name in preset_manager.get_parametric_eq_presets(bank)
                    and not preset_manager.is_builtin_parametric(selected_name, bank)
                )

            def on_sel(cr, ps, n=name):
                if self._updating_ui:
                    return
                pl = eq_widgets["preset_names"]
                sn = pl[cr.get_selected()]
                _update_delete_visibility(sn)
                new_presets = preset_manager.get_parametric_eq_presets(bank)
                if sn in new_presets:
                    fv = list(new_presets[sn])
                    canvas = self._settings_widgets[widget_key]["canvas"]
                    canvas.set_values(fv)
                    if "bands_label" in eq_widgets:
                        eq_widgets["bands_label"].set_label(
                            f"{canvas.get_active_count()} / 10 bands"
                        )
                    self._settings_widgets[widget_key]["last_value"] = fv
                    self.dbus_client.change_setting(n, fv)
                    # Persist chosen preset and values into local cache for this target
                    try:
                        ck = self._cache_key_for_mode(mode)
                        self._eq_cache.set_value(ck, n, fv)
                        self._eq_cache.set_preset(ck, n, sn)
                    except Exception:
                        pass
                eq_widgets["revealer"].set_reveal_child(False)

            preset_row.connect("notify::selected", on_sel)
            group.add(preset_row)
            eq_widgets["preset_row"] = preset_row
            eq_widgets["preset_names"] = preset_names
            eq_widgets["delete_btn"] = delete_btn

            def on_delete_clicked(_):
                pl = eq_widgets["preset_names"]
                if not pl:
                    return
                sn = pl[preset_row.get_selected()]
                if preset_manager.delete_parametric_preset(sn, bank):
                    new_presets = preset_manager.get_parametric_eq_presets(bank)
                    new_names = list(new_presets.keys())
                    if "Custom" in pl and "Custom" not in new_names:
                        new_names.append("Custom")
                    eq_widgets["preset_names"] = new_names
                    preset_row.set_model(Gtk.StringList.new(eq_widgets["preset_names"]))
                    if "Flat" in new_presets:
                        preset_row.set_selected(
                            eq_widgets["preset_names"].index("Flat")
                        )
                    delete_btn.set_visible(False)

            delete_btn.connect("clicked", on_delete_clicked)

            # Reset row
            reset_row = Adw.ActionRow(
                title="Manual Adjustment", subtitle="Reset all bands to 0dB Gain"
            )
            reset_btn = Gtk.Button(label="Reset to Flat")
            reset_btn.set_valign(Gtk.Align.CENTER)
            reset_btn.add_css_class("suggested-action")

            def on_reset(_):
                fv = cfg.get("default_value", [0.0] * 30).copy()
                for i in range(0, len(fv), 3):
                    fv[i + 1] = 0.0
                self._settings_widgets[widget_key]["canvas"].set_values(fv)
                self._settings_widgets[widget_key]["last_value"] = fv
                self.dbus_client.change_setting(name, fv)
                try:
                    ck = self._cache_key_for_mode(mode)
                    self._eq_cache.set_value(ck, name, fv)
                    # Flat likely matches
                    self._eq_cache.set_preset(ck, name, "Flat")
                except Exception:
                    pass

            reset_btn.connect("clicked", on_reset)
            reset_row.add_suffix(reset_btn)
            group.add(reset_row)

            # Canvas + Band controls + Save Preset revealer
            canvas_row = Adw.ActionRow()
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            canvas = EQCanvas(name, self.dbus_client)
            canvas.set_values(value)
            # If initial value matches a preset with active_bands metadata, apply it
            if 0 <= curr_idx < len(preset_names):
                init_name = preset_names[curr_idx]
                if init_name in presets and isinstance(presets[init_name], dict):
                    ab = presets[init_name].get("active_bands")
                    if isinstance(ab, int):
                        canvas.set_active_bands(ab)
            vbox.append(canvas)
            # Band controls (remove / label / add)
            band_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            band_box.set_halign(Gtk.Align.CENTER)
            minus_btn = Gtk.Button()
            minus_btn.set_icon_name(
                self._best_icon(
                    [
                        "list-remove-symbolic",
                        "remove-symbolic",
                        "edit-delete-symbolic",
                    ]
                )
            )
            minus_btn.set_has_frame(False)
            plus_btn = Gtk.Button()
            plus_btn.set_icon_name(
                self._best_icon(
                    [
                        "list-add-symbolic",
                        "add-symbolic",
                        "list-new-symbolic",
                        "document-new-symbolic",
                    ]
                )
            )
            plus_btn.set_has_frame(False)
            bands_label = Gtk.Label(label=f"{canvas.get_active_count()} / 10 bands")
            band_box.append(minus_btn)
            band_box.append(bands_label)
            band_box.append(plus_btn)
            vbox.append(band_box)
            revealer = Gtk.Revealer()
            revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
            revealer.set_reveal_child(False)
            rbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            rbox.set_halign(Gtk.Align.CENTER)
            rbox.set_margin_top(12)
            rbox.set_margin_bottom(8)
            rbox.set_margin_start(16)
            rbox.set_margin_end(16)
            entry = Gtk.Entry()
            entry.set_hexpand(True)
            entry.set_width_chars(30)
            entry.set_placeholder_text("Custom-1")
            save_btn = Gtk.Button(label="Save Preset")
            save_btn.add_css_class("suggested-action")
            save_btn.add_css_class("pill")
            rbox.append(entry)
            rbox.append(save_btn)
            revealer.set_child(rbox)
            vbox.append(revealer)
            canvas_row.set_child(vbox)
            group.add(canvas_row)

            eq_widgets["canvas"] = canvas
            eq_widgets["revealer"] = revealer
            eq_widgets["entry"] = entry
            eq_widgets["save_btn"] = save_btn
            eq_widgets["bands_label"] = bands_label
            eq_widgets["last_value"] = value
            eq_widgets["mode"] = mode
            eq_widgets["setting_name"] = name
            self._settings_widgets[widget_key] = eq_widgets

            def _update_revealer_visibility():
                curr = eq_widgets["canvas"].get_values()
                all_presets = preset_manager.get_parametric_eq_presets(bank).values()
                is_match = any(values_match(curr, pv) for pv in all_presets)
                revealer.set_reveal_child(not is_match)

            canvas.on_modified_callback = _update_revealer_visibility

            # Band controls handlers
            def update_band_ui():
                c = eq_widgets["canvas"]
                ab = c.get_active_count()
                eq_widgets["bands_label"].set_label(f"{ab} / 10 bands")
                minus_btn.set_sensitive(ab > 1)
                plus_btn.set_sensitive(ab < 10)

            def on_minus(_):
                c = eq_widgets["canvas"]
                if len(c.values) >= 40:
                    for idx in range(9, -1, -1):
                        if int(c.values[idx * 4 + 3]) != 0:
                            c.values[idx * 4 + 3] = 0.0
                            c.queue_draw()
                            c.dbus_client.change_setting(c.name, c.values)
                            break
                update_band_ui()

            def on_plus(_):
                c = eq_widgets["canvas"]
                if len(c.values) >= 40:
                    for idx in range(10):
                        if int(c.values[idx * 4 + 3]) == 0:
                            c.values[idx * 4 + 3] = 1.0
                            c.queue_draw()
                            c.dbus_client.change_setting(c.name, c.values)
                            break
                update_band_ui()

            minus_btn.connect("clicked", on_minus)
            plus_btn.connect("clicked", on_plus)
            update_band_ui()

            def on_save_clicked(_):
                base = entry.get_text().strip() or "Custom-1"
                # ensure not overwriting built-ins
                candidate = base
                i = 1
                while preset_manager.is_builtin_parametric(
                    candidate, bank
                ) or candidate in preset_manager.get_parametric_eq_presets(bank):
                    i += 1 if i > 1 else 1
                    candidate = f"{base}-{i}"
                c = eq_widgets["canvas"]
                vals = list(c.get_values())
                preset_manager.add_parametric_preset(candidate, vals, bank)
                new_presets = preset_manager.get_parametric_eq_presets(bank)
                new_names = list(new_presets.keys())
                if "Custom" in eq_widgets["preset_names"] and "Custom" not in new_names:
                    new_names.append("Custom")
                eq_widgets["preset_names"] = new_names
                preset_row.set_model(Gtk.StringList.new(eq_widgets["preset_names"]))
                preset_row.set_selected(eq_widgets["preset_names"].index(candidate))
                delete_btn.set_visible(True)
                revealer.set_reveal_child(False)
                try:
                    ck = self._cache_key_for_mode(mode)
                    self._eq_cache.set_value(ck, name, vals)
                    self._eq_cache.set_preset(ck, name, candidate)
                except Exception:
                    pass

            save_btn.connect("clicked", on_save_clicked)
        else:
            w = self._settings_widgets[widget_key]
            # Ensure legacy widgets carry mode metadata for tab-aware updates
            if "mode" not in w:
                w["mode"] = mode
            # Only update the canvas/last_value for the currently active EQ target
            if mode == self._eq_mode:
                w["last_value"] = value
                w["canvas"].set_values(value)
            pn = w["preset_names"]

            curr_idx = -1
            current_presets = preset_manager.get_parametric_eq_presets(bank)
            for i, p_name in enumerate(pn):
                if p_name in current_presets and values_match(
                    value, current_presets[p_name]
                ):
                    curr_idx = i
                    break
            if curr_idx == -1 and "Custom" in pn:
                curr_idx = pn.index("Custom")
            if curr_idx != -1 and w["preset_row"].get_selected() != curr_idx:
                temp = self._updating_ui
                self._updating_ui = True
                w["preset_row"].set_selected(curr_idx)
                self._updating_ui = temp
            # update delete button state if available
            if "delete_btn" in w and 0 <= w["preset_row"].get_selected() < len(pn):
                sel_name = pn[w["preset_row"].get_selected()]
                w["delete_btn"].set_visible(
                    sel_name in current_presets
                    and not preset_manager.is_builtin_parametric(sel_name, bank)
                )
            if "bands_label" in w:
                c = w["canvas"]
                w["bands_label"].set_label(f"{c.get_active_count()} / 10 bands")

    def _update_or_create_equalizer(self, name, value, cfg, group):
        bands = cfg.get("bands", [])
        if not isinstance(value, list) or len(value) != len(bands):
            value = [0] * len(bands)
        if name not in self._settings_widgets:
            eq_widgets = {}
            preset_row = Adw.ComboRow(title="EQ Preset")
            presets = preset_manager.get_graphic_eq_presets()
            preset_names = list(presets.keys())
            curr_idx = -1
            for i, pn in enumerate(preset_names):
                if pn in presets and presets[pn] == value:
                    curr_idx = i
                    break
            if curr_idx == -1:
                preset_names.append("Custom")
                curr_idx = len(preset_names) - 1
            preset_row.set_model(Gtk.StringList.new(preset_names))
            preset_row.set_selected(curr_idx)

            # Trash icon for deleting a custom preset
            delete_btn = Gtk.Button()
            delete_btn.set_icon_name(
                self._best_icon(
                    [
                        "user-trash-symbolic",
                        "edit-delete-symbolic",
                        "user-trash",
                    ]
                )
            )
            delete_btn.set_valign(Gtk.Align.CENTER)
            delete_btn.set_tooltip_text("Delete preset")
            delete_btn.set_visible(False)
            preset_row.add_suffix(delete_btn)

            def _update_delete_visibility(selected_name: str):
                delete_btn.set_visible(
                    selected_name in preset_manager.get_graphic_eq_presets()
                    and not preset_manager.is_builtin_graphic(selected_name)
                )

            def on_sel(cr, ps, n=name):
                if self._updating_ui:
                    return
                pl = eq_widgets["preset_names"]
                sn = pl[cr.get_selected()]
                _update_delete_visibility(sn)
                curr_presets = preset_manager.get_graphic_eq_presets()
                if sn in curr_presets:
                    nv = curr_presets[sn]
                    self._settings_widgets[n]["last_value"] = nv
                    for i, sc in enumerate(self._settings_widgets[n]["scales"]):
                        sc.set_value(float(nv[i]))
                    self.dbus_client.change_setting(n, nv)
                # hide revealer on explicit preset selection
                eq_widgets["revealer"].set_reveal_child(False)

            preset_row.connect("notify::selected", on_sel)
            group.add(preset_row)
            eq_widgets["preset_row"] = preset_row
            eq_widgets["preset_names"] = preset_names
            eq_widgets["delete_btn"] = delete_btn

            def on_delete_clicked(_):
                pl = eq_widgets["preset_names"]
                if not pl:
                    return
                sn = pl[preset_row.get_selected()]
                if preset_manager.delete_graphic_preset(sn):
                    new_presets = preset_manager.get_graphic_eq_presets()
                    new_names = list(new_presets.keys())
                    if "Custom" in pl and "Custom" not in new_names:
                        new_names.append("Custom")
                    eq_widgets["preset_names"] = new_names
                    preset_row.set_model(Gtk.StringList.new(eq_widgets["preset_names"]))
                    if "Flat" in new_presets:
                        preset_row.set_selected(
                            eq_widgets["preset_names"].index("Flat")
                        )
                    delete_btn.set_visible(False)

            delete_btn.connect("clicked", on_delete_clicked)
            reset_row = Adw.ActionRow(
                title="Manual Adjustment", subtitle="Reset all bands to 0dB"
            )
            reset_btn = Gtk.Button(label="Reset to Flat")
            reset_btn.set_valign(Gtk.Align.CENTER)
            reset_btn.add_css_class("suggested-action")

            def on_reset(_):
                fv = [0] * len(bands)
                self._settings_widgets[name]["last_value"] = fv
                for sc in self._settings_widgets[name]["scales"]:
                    sc.set_value(0.0)
                self.dbus_client.change_setting(name, fv)

            reset_btn.connect("clicked", on_reset)
            reset_row.add_suffix(reset_btn)
            group.add(reset_row)
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            box.set_halign(Gtk.Align.CENTER)
            box.set_margin_top(24)
            box.set_margin_bottom(24)
            scales = []
            for i, freq in enumerate(bands):
                vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
                sc = Gtk.Scale.new_with_range(Gtk.Orientation.VERTICAL, -12, 12, 1)
                sc.set_inverted(True)
                sc.set_value(float(value[i]))
                sc.set_vexpand(True)
                sc.set_size_request(-1, 200)
                sc.set_draw_value(False)
                sc.add_mark(0, Gtk.PositionType.RIGHT, None)

                def on_ch(s, idx=i, n=name):
                    if self._updating_ui:
                        return
                    curr = list(self._settings_widgets[n]["last_value"])
                    curr[idx] = int(s.get_value())
                    self.dbus_client.change_setting(n, curr)

                sc.connect("value-changed", on_ch)
                scales.append(sc)
                lbl = Gtk.Label(
                    label=f"{freq}Hz" if freq < 1000 else f"{freq // 1000}k"
                )
                lbl.add_css_class("dimmed")
                lbl.set_size_request(40, -1)
                vb.append(sc)
                vb.append(lbl)
                box.append(vb)
            vbox.append(box)
            revealer = Gtk.Revealer()
            revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
            revealer.set_reveal_child(False)
            rb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            rb.set_halign(Gtk.Align.CENTER)
            rb.set_margin_top(12)
            rb.set_margin_bottom(8)
            rb.set_margin_start(16)
            rb.set_margin_end(16)
            entry = Gtk.Entry()
            entry.set_hexpand(True)
            entry.set_width_chars(30)
            entry.set_placeholder_text("Custom-1")
            save_btn = Gtk.Button(label="Save Preset")
            save_btn.add_css_class("suggested-action")
            save_btn.add_css_class("pill")
            rb.append(entry)
            rb.append(save_btn)
            revealer.set_child(rb)
            vbox.append(revealer)
            row = Adw.ActionRow()
            row.set_child(vbox)
            group.add(row)
            eq_widgets["scales"] = scales
            eq_widgets["last_value"] = value
            eq_widgets["revealer"] = revealer
            eq_widgets["entry"] = entry
            eq_widgets["save_btn"] = save_btn
            self._settings_widgets[name] = eq_widgets

            def _update_revealer_visibility_from_scales():
                curr = [float(sc.get_value()) for sc in eq_widgets["scales"]]
                presets_now = preset_manager.get_graphic_eq_presets().values()
                is_match = any(list(pv) == curr for pv in presets_now)
                eq_widgets["revealer"].set_reveal_child(not is_match)

            for sc in scales:
                sc.connect(
                    "value-changed",
                    lambda *_: _update_revealer_visibility_from_scales(),
                )

            def on_save_clicked(_):
                base = entry.get_text().strip() or "Custom-1"
                candidate = base
                i = 1
                curr_all = preset_manager.get_graphic_eq_presets()
                while (
                    preset_manager.is_builtin_graphic(candidate)
                    or candidate in curr_all
                ):
                    i += 1 if i > 1 else 1
                    candidate = f"{base}-{i}"
                vals = [float(sc.get_value()) for sc in eq_widgets["scales"]]
                preset_manager.add_graphic_preset(candidate, vals)
                new_presets = preset_manager.get_graphic_eq_presets()
                new_names = list(new_presets.keys())
                if "Custom" in eq_widgets["preset_names"] and "Custom" not in new_names:
                    new_names.append("Custom")
                eq_widgets["preset_names"] = new_names
                preset_row.set_model(Gtk.StringList.new(eq_widgets["preset_names"]))
                preset_row.set_selected(eq_widgets["preset_names"].index(candidate))
                delete_btn.set_visible(True)
                revealer.set_reveal_child(False)

            save_btn.connect("clicked", on_save_clicked)
        else:
            w = self._settings_widgets[name]
            w["last_value"] = value
            for i, sc in enumerate(w["scales"]):
                if i < len(value) and abs(sc.get_value() - value[i]) > 0.1:
                    sc.set_value(float(value[i]))
            pn = w["preset_names"]
            curr_idx = -1
            curr_presets = preset_manager.get_graphic_eq_presets()
            for i, p_name in enumerate(pn):
                if p_name in curr_presets and curr_presets[p_name] == value:
                    curr_idx = i
                    break
            if curr_idx == -1 and "Custom" in pn:
                curr_idx = pn.index("Custom")
            if curr_idx != -1 and w["preset_row"].get_selected() != curr_idx:
                w["preset_row"].set_selected(curr_idx)
            if "delete_btn" in w and 0 <= w["preset_row"].get_selected() < len(pn):
                sel_name = pn[w["preset_row"].get_selected()]
                w["delete_btn"].set_visible(
                    sel_name in curr_presets
                    and not preset_manager.is_builtin_graphic(sel_name)
                )

    def _update_existing_setting_widget(self, name, value, cfg):
        w = self._settings_widgets[name]
        stype = cfg.get("type")
        if stype == "toggle":
            is_on = value == cfg.get("values", {}).get("on", True)
            if w["widget"].get_active() != is_on:
                w["widget"].set_active(is_on)
        elif stype == "slider":
            if "combo" in w:
                idx = next((i for i, o in enumerate(w["opts"]) if o["id"] == value), 0)
                if w["combo"].get_selected() != idx:
                    w["combo"].set_selected(idx)
            elif "spin" in w:
                if abs(w["spin"].get_value() - float(value)) > 0.1:
                    w["spin"].set_value(float(value))
            elif "scale" in w:
                if abs(w["scale"].get_value() - float(value)) > 0.1:
                    w["scale"].set_value(float(value))
                w["label"].set_label(
                    I18n.translate(
                        "settings_values",
                        cfg.get("values_mapping", {}).get(str(int(value)), str(value)),
                    )
                )
        elif stype in ["select", "discrete_map"]:
            idx = next((i for i, o in enumerate(w["opts"]) if o["id"] == value), 0)
            if w["combo"].get_selected() != idx:
                w["combo"].set_selected(idx)

    def _create_new_setting_widget(
        self, name, value, cfg, group, title, desc, label_group
    ):
        stype = cfg.get("type")
        wd = {}
        if stype == "toggle":
            row = Adw.SwitchRow(title=title, subtitle=desc)
            row.set_active(value == cfg.get("values", {}).get("on", True))
            row.connect(
                "notify::active",
                lambda sw, ps: self._on_setting_changed(name, cfg, sw.get_active()),
            )
            group.add(row)
            wd = {"row": row, "widget": row}
        elif stype == "slider":
            if name in [
                "mic_side_tone",
                "mic_mute_led_brightness",
                "bluetooth_auto_mute",
            ]:
                maps = cfg.get("values_mapping", {})
                opts = [
                    {"id": int(k), "name": I18n.translate("settings_values", maps[k])}
                    for k in sorted(maps.keys(), key=lambda x: int(x))
                ]
                row = Adw.ComboRow(
                    title=title,
                    subtitle=desc,
                    model=Gtk.StringList.new([o["name"] for o in opts]),
                )
                row.set_selected(
                    next((i for i, o in enumerate(opts) if o["id"] == value), 0)
                )
                row.connect(
                    "notify::selected",
                    lambda cr, ps: (
                        self.dbus_client.change_setting(
                            name, opts[cr.get_selected()]["id"]
                        )
                        if not self._updating_ui
                        else None
                    ),
                )
                group.add(row)
                wd = {"row": row, "combo": row, "opts": opts}
            elif name == "pm_shutdown":
                row = Adw.SpinRow(title=title, subtitle=desc)
                row.set_adjustment(
                    Gtk.Adjustment(
                        value=float(value),
                        lower=cfg.get("min", 0),
                        upper=cfg.get("max", 120),
                        step_increment=cfg.get("step", 1),
                    )
                )
                row.connect(
                    "changed",
                    lambda sr: (
                        self.dbus_client.change_setting(name, int(sr.get_value()))
                        if not self._updating_ui
                        else None
                    ),
                )
                group.add(row)
                wd = {"row": row, "spin": row}
            else:
                row = Adw.ActionRow(title=title, subtitle=desc)
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                if name == "mic_volume":
                    icon = Gtk.Image.new_from_icon_name(
                        "audio-input-microphone-symbolic"
                    )
                    box.append(icon)
                sc = Gtk.Scale.new_with_range(
                    Gtk.Orientation.HORIZONTAL,
                    cfg.get("min", 0),
                    cfg.get("max", 100),
                    cfg.get("step", 1),
                )
                sc.set_value(float(value))
                sc.set_hexpand(True)
                sc.set_margin_start(8)
                sc.set_margin_end(8)
                vl = Gtk.Label(label=str(value))

                def on_ch(s, n=name, c=cfg, l=vl):
                    v = int(s.get_value())
                    l.set_label(
                        I18n.translate(
                            "settings_values",
                            c.get("values_mapping", {}).get(str(v), str(v)),
                        )
                    )
                    if not self._updating_ui:
                        self.dbus_client.change_setting(n, v)

                sc.connect("value-changed", on_ch)
                vl.set_label(
                    I18n.translate(
                        "settings_values",
                        cfg.get("values_mapping", {}).get(str(int(value)), str(value)),
                    )
                )
                vl.set_xalign(1.0)
                label_group.add_widget(vl)
                box.append(sc)
                box.append(vl)
                row.add_suffix(box)
                if name == "mic_volume":
                    row.set_activatable_widget(sc)
                group.add(row)
                wd = {"row": row, "scale": sc, "label": vl}
        elif stype in ["select", "discrete_map"]:
            src = cfg.get("options_source")
            opts = []
            if stype == "discrete_map":
                opts = [
                    {"id": int(k), "name": I18n.translate("settings_values", v)}
                    for k, v in cfg.get("values_mapping", {}).items()
                ]
            else:
                opts = self._option_lists.get(src, [])
                if src == "pulse_audio_devices":
                    opts = [
                        {
                            "id": "none",
                            "name": I18n.translate("settings_values", "none"),
                        }
                    ] + opts
            if opts:
                row = Adw.ComboRow(
                    title=title,
                    subtitle=desc,
                    model=Gtk.StringList.new([o["name"] for o in opts]),
                )
                row.set_selected(
                    next((i for i, o in enumerate(opts) if o["id"] == value), 0)
                )
                row.connect(
                    "notify::selected",
                    lambda cr, ps: (
                        self.dbus_client.change_setting(
                            name, opts[cr.get_selected()]["id"]
                        )
                        if not self._updating_ui
                        else None
                    ),
                )
                group.add(row)
                wd = {"row": row, "combo": row, "opts": opts}
        if wd:
            self._settings_widgets[name] = wd

    def _on_setting_changed(self, name, cfg, active):
        if self._updating_ui:
            return
        self.dbus_client.change_setting(
            name, cfg.get("values", {}).get("on" if active else "off", active)
        )

    def _load_styles(self):
        style_path = Path(__file__).parent / "style.css"
        if style_path.exists():
            provider = Gtk.CssProvider()
            provider.load_from_path(str(style_path))
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )


class ArctisManagerApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id="dev.ingham.lam-gui.gtk", **kwargs)

    def do_activate(self):
        # Fallback: ensure an icon theme with GNOME symbolic icons is available
        try:
            theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
            if theme and not theme.has_icon("audio-headset-symbolic"):
                s = Gtk.Settings.get_default()
                if s:
                    s.set_property("gtk-icon-theme-name", "Adwaita")
        except Exception:
            pass
        win = self.get_active_window()
        if not win:
            win = ArctisManagerWindow(application=self)
        win.present()


def main():
    import signal

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    I18n.get_instance().set_language("en")
    app = ArctisManagerApp()
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()
