"""
Pure math helpers for EQ response visualization.

All functions accept a 40-value list representing 10 parametric bands:
[freq, gain, q, type] repeated. Bands with type==0 are treated as disabled.

These helpers are deterministic and have no side effects, which makes them
easy to unit test.
"""

from __future__ import annotations

from typing import List
import math


def _band_gain_at(f: float, fc: float, gain: float, q: float, ftype: int) -> float:
    """Approximate band contribution at frequency f.

    Matches the visual approximation used in EQCanvas._draw.
    """
    if ftype == 0 or f <= 0 or fc <= 0 or q <= 0:
        return 0.0
    # Peaking / notch
    if ftype in (1, 6):
        ww = (f / fc) - (fc / f)
        return gain / (1 + (q * q) * (ww * ww))
    # High shelf (visual approx)
    if ftype == 2:
        return gain * (1 / (1 + (fc / max(f, 1e-6)) ** (2 * q)))
    # Low shelf (visual approx)
    if ftype == 4:
        return gain * (1 / (1 + (max(f, 1e-6) / fc) ** (2 * q)))
    # High pass (visual approx)
    if ftype == 3:
        return -abs(gain) * (1 / (1 + (fc / max(f, 1e-6)) ** (2 * q)))
    # Low pass (visual approx)
    if ftype == 5:
        return -abs(gain) * (1 / (1 + (max(f, 1e-6) / fc) ** (2 * q)))
    return 0.0


def _iter_bands(values: List[float]):
    n = len(values) // 4
    for i in range(n):
        base = i * 4
        yield (
            float(values[base]),
            float(values[base + 1]),
            float(values[base + 2]),
            int(values[base + 3]) if len(values) >= 40 else 1,
        )


def compute_response(values: List[float], width: int) -> List[float]:
    """Compute overall response curve across all enabled bands.

    Returns an array of length width+1 with gain values in dB, clamped to [-15, 15].
    """
    width = max(1, int(width))
    log_min, log_max = math.log10(20), math.log10(20000)
    out: List[float] = [0.0] * (width + 1)
    bands = list(_iter_bands(values))
    for x in range(width + 1):
        f = 10 ** (log_min + (x / width) * (log_max - log_min))
        total = 0.0
        for fc, gain, q, ftype in bands:
            if ftype == 0:
                continue
            total += _band_gain_at(f, fc, gain, q, ftype)
        out[x] = max(-15.0, min(15.0, total))
    return out


def compute_type_curve(
    values: List[float], active_type: int, width: int
) -> List[float]:
    """Compute the summed response for a single EQ type.

    Returns an array of length width+1 with gain values in dB, clamped to [-15, 15].
    If no bands of the requested type are enabled, returns an all-zero array.
    """
    width = max(1, int(width))
    log_min, log_max = math.log10(20), math.log10(20000)
    out: List[float] = [0.0] * (width + 1)
    bands = [b for b in _iter_bands(values) if b[3] == int(active_type) and b[3] != 0]
    if not bands:
        return out
    for x in range(width + 1):
        f = 10 ** (log_min + (x / width) * (log_max - log_min))
        total = 0.0
        for fc, gain, q, ftype in bands:
            total += _band_gain_at(f, fc, gain, q, ftype)
        out[x] = max(-15.0, min(15.0, total))
    return out
