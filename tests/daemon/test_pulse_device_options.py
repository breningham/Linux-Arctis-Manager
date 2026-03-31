import json

import pytest


class StubPulse:
    def __init__(self, sinks):
        self._sinks = sinks

    def sink_list(self):
        return list(self._sinks)


class StubCore:
    def __init__(self, sinks):
        class _PA:
            def __init__(self, sinks):
                self.pulse = StubPulse(sinks)

        self.pa_audio_manager = _PA(sinks)


class StubSink:
    def __init__(self, name: str | None = None, proplist: dict | None = None):
        self.name = name or ""
        self.proplist = proplist or {}


def mk_service(sinks):
    from linux_arctis_manager.dbus_service import ArctisManagerDbusSettingsService

    return ArctisManagerDbusSettingsService(core=StubCore(sinks))


def parse_options(json_str: str):
    try:
        return json.loads(json_str)
    except Exception:  # pragma: no cover - should always be valid
        return []


def test_pulse_device_options_prefers_node_name_and_nick():
    # node.name is stable id; node.nick becomes label
    sinks = [
        StubSink(
            name="alsa_output.pci-0000_00_1f.3.analog-stereo",
            proplist={
                "node.name": "alsa_output.pci-0000_00_1f.3.analog-stereo",
                "node.nick": "Speakers (Built-in Audio)",
            },
        )
    ]
    service = mk_service(sinks)
    out = parse_options(service.get_list_options("pulse_audio_devices"))
    assert isinstance(out, list) and len(out) == 1
    assert out[0]["id"] == "alsa_output.pci-0000_00_1f.3.analog-stereo"
    assert out[0]["name"] == "Speakers (Built-in Audio)"


def test_pulse_device_options_handles_missing_node_nick():
    # Missing node.nick should fall back to node.description/device.description/id
    sinks = [
        StubSink(
            name="alsa_output.usb-043a_SoundBar-00.analog-stereo",
            proplist={
                "node.name": "alsa_output.usb-043a_SoundBar-00.analog-stereo",
                "node.description": "Soundbar Analog Stereo",
            },
        ),
        # Another sink with only device.* fields
        StubSink(
            name="alsa_output.pci-0000_00_1f.3.hdmi-stereo",
            proplist={
                "device.string": "alsa_output.pci-0000_00_1f.3.hdmi-stereo",
                "device.description": "HDMI Output",
            },
        ),
    ]

    service = mk_service(sinks)
    out = parse_options(service.get_list_options("pulse_audio_devices"))
    # Two options produced with stable ids and user-friendly labels
    assert len(out) == 2
    by_id = {o["id"]: o for o in out}
    assert (
        by_id["alsa_output.usb-043a_SoundBar-00.analog-stereo"]["name"]
        == "Soundbar Analog Stereo"
    )
    assert by_id["alsa_output.pci-0000_00_1f.3.hdmi-stereo"]["name"] == "HDMI Output"
