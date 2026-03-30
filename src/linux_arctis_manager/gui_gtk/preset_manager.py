import json
from linux_arctis_manager.constants import SETTINGS_FOLDER


def normalize_parametric_to_40(values_like) -> list[float] | None:
    """Normalize parametric EQ values into a 40-length list of floats
    (freq, gain, Q, type) x 10 bands.

    Accepts:
    - 40-length list (returned as-is)
    - 30-length list (freq, gain, Q per band) -> expand with type=1.0
    - dict with key 'values' containing one of the above
    Returns None if normalization isn't possible.
    """
    if isinstance(values_like, list) and len(values_like) == 40:
        return list(values_like)
    if isinstance(values_like, list) and len(values_like) == 30:
        out: list[float] = []
        for i in range(0, 30, 3):
            out.extend(
                [
                    float(values_like[i]),
                    float(values_like[i + 1]),
                    float(values_like[i + 2]),
                    1.0,
                ]
            )
        return out
    if isinstance(values_like, dict):
        vals = values_like.get("values")
        if isinstance(vals, list):
            return normalize_parametric_to_40(vals)
    return None


def values_match(
    a: list[float] | dict, b: list[float] | dict, tol: float = 0.05
) -> bool:
    """Compare parametric EQ values, focusing on gains only.

    - Normalizes both inputs to 40-length parametric lists
    - Compares only gain components (index % 4 == 1)
    - Ignores frequency/Q/type differences since devices/targets may vary
    """
    na = (
        normalize_parametric_to_40(a)
        if not (isinstance(a, list) and len(a) == 40)
        else list(a)
    )
    nb = (
        normalize_parametric_to_40(b)
        if not (isinstance(b, list) and len(b) == 40)
        else list(b)
    )
    if na is None or nb is None or len(na) != 40 or len(nb) != 40:
        return False
    for i in range(1, 40, 4):  # gains positions
        try:
            if abs(float(na[i]) - float(nb[i])) > tol:
                return False
        except Exception:
            return False
    return True


class EqStateCache:
    """Simple disk cache for last-known per-target EQ state.

    Keys use future-proof names:
    - wi_hp:  Wireless headphones EQ
    - bt_hp:  Bluetooth headphones EQ
    - wi_mic: Wireless microphone EQ
    - bt_mic: Bluetooth microphone EQ (reserved for future use)
    """

    def __init__(self) -> None:
        self.cache_file = SETTINGS_FOLDER / "eq_cache.json"
        self.parametric: dict[str, dict[str, list[float]]] = {
            "wi_hp": {},
            "bt_hp": {},
            "wi_mic": {},
            "bt_mic": {},
        }
        self.preset: dict[str, dict[str, str]] = {
            "wi_hp": {},
            "bt_hp": {},
            "wi_mic": {},
            "bt_mic": {},
        }
        self._load()

    def _load(self) -> None:
        try:
            if self.cache_file.exists():
                import json as _json

                with open(self.cache_file, "r") as f:
                    data = _json.load(f)
                for k in self.parametric.keys():
                    if isinstance(data.get("parametric", {}).get(k), dict):
                        self.parametric[k].update(data["parametric"][k])
                for k in self.preset.keys():
                    if isinstance(data.get("preset", {}).get(k), dict):
                        self.preset[k].update(data["preset"][k])
        except Exception:
            # Ignore corrupt cache
            pass

    def save(self) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            import json as _json

            with open(self.cache_file, "w") as f:
                _json.dump(
                    {"parametric": self.parametric, "preset": self.preset}, f, indent=2
                )
        except Exception:
            pass

    def get_value(self, target_key: str, setting_name: str) -> list[float] | None:
        return self.parametric.get(target_key, {}).get(setting_name)

    def set_value(
        self, target_key: str, setting_name: str, values: list[float]
    ) -> None:
        self.parametric.setdefault(target_key, {})[setting_name] = values
        self.save()

    def get_preset(self, target_key: str, setting_name: str) -> str | None:
        return self.preset.get(target_key, {}).get(setting_name)

    def set_preset(self, target_key: str, setting_name: str, preset_name: str) -> None:
        self.preset.setdefault(target_key, {})[setting_name] = preset_name
        self.save()


# Standard Graphic EQ Presets (10 bands of Gain)
EQ_PRESETS = {
    "Flat": [0.0] * 10,
    "Bass Boost": [6.0, 4.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "Focus": [-2.0, -2.0, -2.0, 0.0, 2.0, 4.0, 4.0, 2.0, 0.0, 0.0],
    "Smiley": [4.0, 2.0, 0.0, -1.0, -2.0, -2.0, -1.0, 0.0, 2.0, 4.0],
}


def _pack_40(bands_with_types: list[tuple[float, float, float, int]]):
    out: list[float] = []
    for f, g, q, t in bands_with_types:
        out.extend([f, g, q, float(t)])
    return out


# Parametric EQ Presets using 40-value lists (freq, gain, Q, type)
PARAMETRIC_EQ_PRESETS: dict[str, list[float]] = {
    "Flat": _pack_40(
        [
            (31.0, 0.0, 1.414, 1),
            (62.0, 0.0, 1.414, 1),
            (125.0, 0.0, 1.414, 1),
            (250.0, 0.0, 1.414, 1),
            (500.0, 0.0, 1.414, 1),
            (1000.0, 0.0, 1.414, 1),
            (2000.0, 0.0, 1.414, 1),
            (4000.0, 0.0, 1.414, 1),
            (8000.0, 0.0, 1.414, 1),
            (16000.0, 0.0, 1.414, 1),
        ]
    ),
    "Arc Raiders": _pack_40(
        [
            (45.0, 6.8, 0.707, 1),
            (199.0, 1.8, 0.707, 1),
            (343.0, 0.2, 0.707, 1),
            (1780.0, 1.9, 5.0, 1),
            (3360.0, 1.0, 5.0, 1),
            (7620.0, 4.7, 0.707, 1),
            (10000.0, 0.0, 1.414, 0),
            (12000.0, 0.0, 1.414, 0),
            (14000.0, 0.0, 1.414, 0),
            (16000.0, 0.0, 1.414, 0),
        ]
    ),
}


class PresetManager:
    def __init__(self):
        self.preset_file = SETTINGS_FOLDER / "custom_presets.json"
        self._custom_graphic_eq = {}
        self._custom_parametric_eq = {}
        self._custom_parametric_mic = {}
        self.load()

    def get_graphic_eq_presets(self) -> dict[str, list[float]]:
        combined = EQ_PRESETS.copy()
        combined.update(self._custom_graphic_eq)
        return combined

    def get_parametric_eq_presets(self, mode: str = "output") -> dict[str, list[float]]:
        combined: dict[str, list[float]] = {}
        # For headphones, include all built-ins. For microphone, include at least Flat.
        if mode != "microphone":
            combined.update(PARAMETRIC_EQ_PRESETS)
        else:
            # Seed mic bank with a Flat baseline so users aren't left with only "Custom"
            if "Flat" in PARAMETRIC_EQ_PRESETS:
                combined["Flat"] = list(PARAMETRIC_EQ_PRESETS["Flat"])
        source = (
            self._custom_parametric_mic
            if mode == "microphone"
            else self._custom_parametric_eq
        )
        for name, data in source.items():
            norm = normalize_parametric_to_40(data)
            if norm is not None:
                combined[name] = norm
        return combined

    def load(self):
        if not self.preset_file.exists():
            return

        try:
            with open(self.preset_file, "r") as f:
                data = json.load(f)
                self._custom_graphic_eq = data.get("graphic", {})
                self._custom_parametric_eq = data.get("parametric", {})
                self._custom_parametric_mic = data.get("parametric_mic", {})
                # Cleanup: drop GG-imported "edited" variants (playground presets)
                # e.g. "GG: Music: Punchy edited"
                to_delete = [
                    k
                    for k in list(self._custom_parametric_eq.keys())
                    if k.lower().startswith("gg: ") and "edited" in k.lower()
                ]
                for k in to_delete:
                    try:
                        del self._custom_parametric_eq[k]
                    except KeyError:
                        pass
                to_delete2 = [
                    k
                    for k in list(self._custom_parametric_mic.keys())
                    if k.lower().startswith("gg: ") and "edited" in k.lower()
                ]
                for k in to_delete2:
                    try:
                        del self._custom_parametric_mic[k]
                    except KeyError:
                        pass
        except Exception as e:
            print(f"Failed to load custom presets: {e}")

    def save(self):
        self.preset_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.preset_file, "w") as f:
                json.dump(
                    {
                        "graphic": self._custom_graphic_eq,
                        "parametric": self._custom_parametric_eq,
                        "parametric_mic": self._custom_parametric_mic,
                    },
                    f,
                    indent=4,
                )
        except Exception as e:
            print(f"Failed to save custom presets: {e}")

    def add_graphic_preset(self, name: str, values: list[float]):
        self._custom_graphic_eq[name] = values
        self.save()

    def add_parametric_preset(
        self, name: str, values: list[float], mode: str = "output"
    ):
        if mode == "microphone":
            self._custom_parametric_mic[name] = values
        else:
            self._custom_parametric_eq[name] = values
        self.save()

    # New: delete helpers and builtin guards
    def is_builtin_graphic(self, name: str) -> bool:
        return name in EQ_PRESETS

    def is_builtin_parametric(self, name: str, mode: str = "output") -> bool:
        # Treat GG-imported presets as non-deletable, plus seeded built-ins
        if isinstance(name, str) and name.startswith("GG: "):
            return True
        if mode == "microphone":
            return name == "Flat"
        return name in PARAMETRIC_EQ_PRESETS

    def delete_graphic_preset(self, name: str) -> bool:
        """Delete a custom graphic preset. Returns True if deleted."""
        if self.is_builtin_graphic(name):
            return False
        if name in self._custom_graphic_eq:
            del self._custom_graphic_eq[name]
            self.save()
            return True
        return False


def friendly_preset_name(name: str) -> str:
    """Return a UI-friendly display name for a preset.

    - Strips the 'GG: ' prefix from imported presets while preserving the
      underlying real key for storage/logic.
    - Returns the original name for non-GG presets or non-strings.
    """
    if isinstance(name, str) and name.startswith("GG: "):
        return name[4:].strip()
    return name

    def delete_parametric_preset(self, name: str, mode: str = "output") -> bool:
        """Delete a custom parametric preset. Returns True if deleted."""
        if self.is_builtin_parametric(name, mode):
            return False
        bucket = (
            self._custom_parametric_mic
            if mode == "microphone"
            else self._custom_parametric_eq
        )
        if name in bucket:
            del bucket[name]
            self.save()
            return True
        return False
