import math

import pytest

from rawfilereader.adapter import (
    _apply_mass_range,
    _average_centroid_peaks,
    _find_closest,
    _linear_interp,
    _normalize_to_tic,
    _py_subtract_peaks,
)


def test_apply_mass_range_filters_inclusively():
    masses, intensities = _apply_mass_range(
        [99.0, 100.0, 101.0, 102.0],
        [1.0, 2.0, 3.0, 4.0],
        (100.0, 101.0),
    )
    assert masses == [100.0, 101.0]
    assert intensities == [2.0, 3.0]


def test_normalize_to_tic_preserves_zero_spectrum():
    assert _normalize_to_tic([0.0, 0.0]) == [0.0, 0.0]


def test_normalize_to_tic_sums_to_one():
    result = _normalize_to_tic([1.0, 2.0, 3.0])
    assert math.isclose(sum(result), 1.0)
    assert result == pytest.approx([1 / 6, 2 / 6, 3 / 6])


def test_find_closest_respects_ppm_tolerance():
    masses = [100.0, 100.001, 100.01]
    assert _find_closest(100.0008, masses, 5.0) == 1
    assert _find_closest(100.005, masses, 5.0) is None


def test_linear_interp_returns_zero_outside_range():
    result = _linear_interp([-1.0, 0.5, 2.0], [0.0, 1.0], [0.0, 10.0])
    assert result == pytest.approx([0.0, 5.0, 0.0])


def test_py_subtract_peaks_drops_non_positive_results():
    masses, intensities = _py_subtract_peaks(
        [100.0, 200.0],
        [10.0, 5.0],
        [100.0002, 200.0002],
        [3.0, 8.0],
        tol_ppm=5.0,
    )
    assert masses == [100.0]
    assert intensities == pytest.approx([7.0])


def test_average_centroid_peaks_uses_implicit_zero_for_missing_scan():
    masses, intensities = _average_centroid_peaks(
        [[100.0], []],
        [[10.0], []],
        tol_ppm=5.0,
    )
    assert masses == pytest.approx([100.0])
    assert intensities == pytest.approx([5.0])
