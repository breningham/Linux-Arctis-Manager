import logging
from typing import Any, Dict, List
from PySide6.QtCore import QObject, Signal, Slot, Property
from linux_arctis_manager.gui.dbus_wrapper import DbusWrapper
from linux_arctis_manager.config import SettingType
from linux_arctis_manager.i18n import I18n

logger = logging.getLogger("QmlBackend")


class ArctisBackend(QObject):
    # Signals for UI updates
    stateChanged = Signal()
    settingsChanged = Signal()
    _sigListReceived = Signal(object)

    def __init__(self, dbus_wrapper: DbusWrapper, parent=None):
        super().__init__(parent)
        self.dbus = dbus_wrapper

        self._status = {}
        self._settings = {}
        self._settings_config = {}
        self._option_lists = {}

        self.dbus.sig_status.connect(self._on_status)
        self.dbus.sig_settings.connect(self._on_settings)
        self._sigListReceived.connect(self._on_list_received)

        # We need a custom signal from dbus for option list returns,
        # but in standard DbusWrapper it uses request_list_options(callback).

    def _on_status(self, status: dict):
        if status == self._status:
            return

        was_offline = self.isOffline
        self._status = status
        self.stateChanged.emit()

        if was_offline != self.isOffline:
            self.settingsChanged.emit()

    def _on_settings(self, settings: dict):
        if settings == self._settings:
            return
        self._settings = settings
        self._settings_config = settings.get("settings_config", {})

        # Request any lists needed by 'select' settings
        for name, cfg in self._settings_config.items():
            if cfg.get("type") == "select":
                source = cfg.get("options_source")
                if source and source not in self._option_lists:
                    DbusWrapper.request_list_options(source, self._sigListReceived)

        self.settingsChanged.emit()

    @Slot(object)
    def _on_list_received(self, data: dict):
        self._option_lists[data["name"]] = data["list"]
        self.settingsChanged.emit()

    @Property(bool, notify=stateChanged)
    def isOffline(self) -> bool:
        flat = self._get_flat_status()
        power = flat.get("headset_power_status", {}).get("value", "offline")
        return not self._status or power == "offline"

    @Property(bool, notify=stateChanged)
    def isDisconnected(self) -> bool:
        return not self._status

    @Property(str, notify=settingsChanged)
    def deviceName(self) -> str:
        return self._settings.get("device_name", I18n.translate("ui", "app_name"))

    def _get_flat_status(self) -> dict:
        flat = {}
        for cat, obj in self._status.items():
            if isinstance(obj, dict):
                for k, v in obj.items():
                    flat[k] = v
        return flat

    @Property("QVariantMap", notify=stateChanged)
    def deviceStatus(self) -> dict:
        flat = self._get_flat_status()
        # Pre-process for QML
        return {
            "batteryLevel": int(flat.get("headset_battery_charge", {}).get("value", 0)),
            "isCharging": flat.get("cable_charging", {}).get("value") == "on",
            "mixChat": float(flat.get("chat_mix", {}).get("value", 50)),
            "mixMedia": float(flat.get("media_mix", {}).get("value", 50)),
            "micMuted": flat.get("mic_status", {}).get("value") == "muted",
            "bluetoothConnected": flat.get("bluetooth_connection", {}).get("value")
            == "connected",
            "hasBattery": "headset_battery_charge" in flat,
            "hasMix": "chat_mix" in flat and "media_mix" in flat,
            "hasMic": "mic_status" in flat,
            "hasBluetooth": "bluetooth_connection" in flat,
        }

    def _format_settings_section(self, section_name: str) -> list:
        result = []
        section_vals = self._settings.get(section_name, {})
        if not section_vals:
            return result

        for name, value in section_vals.items():
            cfg = self._settings_config.get(name, {})
            if not cfg:
                continue

            stype = cfg.get("type")
            title = I18n.translate("settings", name)
            desc = I18n.translate("settings_descriptions", name)
            if desc == name:
                desc = ""

            item = {
                "id": name,
                "title": title,
                "description": desc,
                "type": stype,
                "value": value,
            }

            if stype == "slider":
                if (
                    name
                    in [
                        "mic_side_tone",
                        "mic_mute_led_brightness",
                        "bluetooth_auto_mute",
                    ]
                    and "values_mapping" in cfg
                ):
                    item["type"] = "discrete_map"
                    options = []
                    values_map = cfg.get("values_mapping", {})
                    # Ensure numerical keys are sorted properly
                    for k in sorted(
                        values_map.keys(),
                        key=lambda x: int(x) if str(x).isdigit() else x,
                    ):
                        v = values_map[k]
                        try:
                            k_val = int(k)
                        except ValueError:
                            k_val = k
                        lbl = I18n.translate("settings_values", v)
                        options.append({"value": k_val, "label": lbl})
                    item["options"] = options
                else:
                    item["min"] = cfg.get("min", 0)
                    item["max"] = cfg.get("max", 100)
                    item["step"] = cfg.get("step", 1)
            elif stype == "discrete_map":
                options = []
                values_map = cfg.get("values_mapping", {})
                # values_mapping keys are strings of ints in the JSON/dict, but could be ints
                for k, v in values_map.items():
                    try:
                        k_val = int(k)
                    except ValueError:
                        k_val = k
                    lbl = I18n.translate("settings_values", v)
                    options.append({"value": k_val, "label": lbl})
                item["options"] = options
            elif stype == "select":
                source = cfg.get("options_source")
                raw_opts = self._option_lists.get(source, [])
                opts = []

                # Special case: add "None" / "Do nothing" to audio devices routing
                if source == "pulse_audio_devices":
                    opts.append(
                        {
                            "value": "none",
                            "label": I18n.translate("settings_values", "none"),
                        }
                    )

                for o in raw_opts:
                    # select lists from dbus return {'id': ..., 'name': ...}
                    val = o.get("id", o.get("value"))
                    lbl = o.get("name", o.get("label", str(val)))
                    opts.append({"value": val, "label": lbl})
                item["options"] = opts

            result.append(item)

        return result

    @Property("QVariantList", notify=settingsChanged)
    def generalSettings(self) -> list:
        return self._format_settings_section("general")

    @Property("QVariantList", notify=settingsChanged)
    def deviceSettings(self) -> list:
        if self.isOffline:
            return []
        return self._format_settings_section("device")

    @Slot(str, "QVariant")
    def changeSetting(self, name: str, value: Any):
        cfg = self._settings_config.get(name, {})
        if cfg.get("type") == "toggle":
            # Convert boolean back to expected dbus on/off strings if needed
            # Look at how original did it
            # Actually original config.type gives enum, but we serialized to dict
            dbus_val = (
                cfg.get("values", {}).get("on", True)
                if value
                else cfg.get("values", {}).get("off", False)
            )
            DbusWrapper.change_setting(name, dbus_val)
        else:
            DbusWrapper.change_setting(name, value)
