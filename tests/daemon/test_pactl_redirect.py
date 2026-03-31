import types


class StubSink:
    def __init__(self, proplist: dict):
        self.proplist = proplist


class StubPulse:
    def __init__(self):
        self.last_default = None

    def default_set(self, sink):
        self.last_default = sink


def mk_manager(sinks):
    from linux_arctis_manager.pactl import PulseAudioManager

    mgr = PulseAudioManager.get_instance()
    # Replace underlying Pulse with stub to avoid real system changes
    mgr.pulse = StubPulse()

    # Monkeypatch sink_list_wrapper to return our fakes
    def _sinks():
        return list(sinks)

    mgr.sink_list_wrapper = _sinks  # type: ignore[method-assign]
    return mgr


def test_redirect_audio_matches_by_description_substring():
    # Only description present, ensure substring works
    sinks = [
        StubSink({"node.description": "LG Soundbar Digital Output"}),
        StubSink({"node.nick": "USB Headset"}),
    ]
    mgr = mk_manager(sinks)

    mgr.redirect_audio("Soundbar")

    assert isinstance(mgr.pulse.last_default, StubSink)
    assert mgr.pulse.last_default.proplist["node.description"].startswith("LG")


def test_redirect_audio_prefers_exact_node_name():
    # Exact node.name should be selected even if nick/description also match
    target_name = "alsa_output.usb-1234_Soundbar-00.analog-stereo"
    sinks = [
        StubSink(
            {
                "node.name": target_name,
                "node.nick": "Living Room Soundbar",
                "node.description": "Living Room Soundbar",
            }
        ),
        StubSink({"node.nick": "Soundbar"}),
    ]
    mgr = mk_manager(sinks)
    mgr.redirect_audio(target_name)
    assert mgr.pulse.last_default.proplist.get("node.name") == target_name
