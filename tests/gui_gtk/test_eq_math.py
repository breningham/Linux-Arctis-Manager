import math

from linux_arctis_manager.gui_gtk.eq_math import (
    compute_response,
    compute_type_curve,
)


def _vals_with_types(bands):
    """
    Helper to construct a 40-value list from a list of band tuples:
    bands = [(fc, gain, q, type), ...] for up to 10 bands
    Remaining bands are disabled.
    """
    vals = [0.0] * 40
    for i, (fc, gain, q, t) in enumerate(bands[:10]):
        base = i * 4
        vals[base] = float(fc)
        vals[base + 1] = float(gain)
        vals[base + 2] = float(q)
        vals[base + 3] = float(t)
    # Disable any unspecified bands
    for i in range(len(bands), 10):
        vals[i * 4 + 3] = 0.0
    return vals


def test_type_curve_matches_overall_when_all_bands_same_type():
    # Two peaking bands (type=1) at different freqs
    bands = [
        (200.0, 6.0, 1.2, 1),
        (2000.0, -3.0, 0.9, 1),
    ]
    vals = _vals_with_types(bands)
    width = 120

    overall = compute_response(vals, width)
    tcurve = compute_type_curve(vals, 1, width)

    assert len(overall) == width + 1
    assert len(tcurve) == width + 1
    # With all bands of type 1, the per-type curve equals the overall response
    assert all(abs(a - b) < 1e-6 for a, b in zip(overall, tcurve))
    # And is not a flat zero line
    assert any(abs(v) > 1e-6 for v in overall)


def test_type_curve_zero_when_no_bands_of_that_type():
    bands = [
        (500.0, 5.0, 1.4, 1),  # peaking
        (8000.0, -6.0, 1.0, 5),  # low pass visual approx
    ]
    vals = _vals_with_types(bands)
    width = 64

    tcurve = compute_type_curve(vals, 2, width)  # high shelf — not present
    assert len(tcurve) == width + 1
    assert all(abs(v) < 1e-9 for v in tcurve)


def test_disabled_bands_ignored_in_overall_response():
    # One disabled band with nonzero params should have no effect
    bands = [
        (1000.0, 9.0, 1.0, 0),  # disabled
    ]
    vals = _vals_with_types(bands)
    width = 80
    overall = compute_response(vals, width)
    assert len(overall) == width + 1
    assert all(abs(v) < 1e-9 for v in overall)
