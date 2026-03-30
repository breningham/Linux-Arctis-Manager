"""Pure helpers for EQ Reset UI behavior.

These functions encapsulate when to show a destructive "Reset to Preset"
action and what target values should be applied when resetting. They are kept
UI-agnostic for easy unit testing.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .preset_manager import values_match


def _is_invalid_selection(
    selected: Optional[str], presets: Dict[str, List[float]]
) -> bool:
    if not selected:
        return True
    if isinstance(selected, str) and selected == "Custom":
        return True
    if selected not in presets:
        return True
    return False


def should_show_reset(
    selected: Optional[str],
    current: List[float] | Dict,
    presets: Dict[str, List[float]],
    mode: str,
) -> bool:
    """Return True iff the reset action should be visible for the given state.

    Rules:
    - If no real preset is selected (None/"Custom"/missing), do not show reset.
    - Graphic mode: show when list of gains differs (exact equality check).
    - Parametric mode: show when values do not match within tolerance using
      preset_manager.values_match (gain components only).
    """

    if _is_invalid_selection(selected, presets):
        return False

    # Safe access; we've validated the key exists
    target = presets[selected]  # type: ignore[index]

    mode_normalized = (mode or "").strip().lower()
    if mode_normalized == "parametric":
        try:
            return not values_match(current, target)
        except Exception:
            # If comparison fails for any reason, do not show reset to avoid
            # offering a destructive action incorrectly
            return False

    # Default to graphic behavior: strict equality on numeric values
    try:
        current_list = [float(x) for x in list(current)]  # type: ignore[arg-type]
        target_list = [float(x) for x in list(target)]
    except Exception:
        # If we cannot coerce to comparable lists, err on the side of hiding
        return False

    return current_list != target_list


def get_reset_target(
    selected: Optional[str], presets: Dict[str, List[float]]
) -> Optional[List[float]]:
    """Return a copy of the selected preset values, or None if unavailable."""
    if _is_invalid_selection(selected, presets):
        return None
    try:
        return list(presets[selected])  # type: ignore[index]
    except Exception:
        return None
