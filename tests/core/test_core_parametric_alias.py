from types import SimpleNamespace


def test_parametric_eq_alias_maps_to_actual_config(monkeypatch):
    from linux_arctis_manager.core import CoreEngine
    from linux_arctis_manager.config import SettingType

    engine = CoreEngine()

    # Minimal fake device_config with one PARAMETRIC_EQ setting named 'equalizer'
    eq_config = SimpleNamespace(
        name="equalizer",
        type=SettingType.PARAMETRIC_EQ,
        update_sequence=[0x33, 0x00],
        transform=None,
        get_update_sequences=lambda v: [0x33, 0x00],  # not used for EQ path
    )

    device_config = SimpleNamespace(
        name="Stub Device",
        settings={"audio": [eq_config]},
        command_interface_index=(0x00, 0),
    )

    engine.device_config = device_config  # type: ignore[assignment]

    # Stub out methods accessed by on_setting_changed
    sent_commands: list[list[int]] = []

    def fake_send(cmd, endpoint, idx=0):
        sent_commands.append(list(cmd))

    engine.send_command = fake_send  # type: ignore[method-assign]
    engine.get_command_endpoint_address = lambda: 0  # type: ignore[assignment]

    # Ensure EqStore persistence path does not crash
    class StubEqStore:
        def set_bank(self, key, vals):
            self.last = (key, list(vals))

    engine.eq_store = StubEqStore()  # type: ignore[assignment]
    engine.eq_target = 0

    # 40-length values typical for parametric EQ UI
    vals_40 = [
        100,
        0,
        1.0,
        1,
        200,
        0.5,
        1.0,
        1,
        300,
        -1.5,
        1.2,
        1,
        400,
        0,
        1.0,
        1,
        500,
        2.5,
        0.7,
        1,
        600,
        -3.0,
        1.1,
        1,
        700,
        0.0,
        1.0,
        1,
        800,
        1.5,
        1.0,
        1,
        900,
        -2.0,
        1.0,
        1,
        1000,
        0.0,
        1.0,
        1,
    ]

    # Call with alias name 'parametric_eq' which is not present by name
    engine.on_setting_changed("parametric_eq", vals_40)

    # Should result in at least one send_command invocation
    assert sent_commands, "Parametric EQ alias should trigger send_command"
