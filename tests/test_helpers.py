import pytest

from rawfilereader.adapter import (
    _apply_mass_range,
    _average_centroid_peaks,
    _find_closest,
    _linear_interp,
    _normalize_to_tic,
    _py_subtract_peaks,
)


def test_apply_mass_range_is_inclusive_and_keeps_parallel_values():
    masses, intensities = _apply_mass_range(
        [99.0, 100.0, 101.0, 102.0],
        [1.0, 2.0, 3.0, 4.0],
        (100.0, 101.0),
    )

    assert masses == [100.0, 101.0]
    assert intensities == [2.0, 3.0]


def test_normalize_to_tic_preserves_zero_tic_and_normalizes_nonzero_values():
    assert _normalize_to_tic([0.0, 0.0]) == [0.0, 0.0]
    assert _normalize_to_tic([1.0, 3.0]) == pytest.approx([0.25, 0.75])


def test_find_closest_obeys_ppm_tolerance():
    masses = [99.0, 100.0004, 101.0]

    assert _find_closest(100.0, masses, tol_ppm=5.0) == 1
    assert _find_closest(100.0, masses, tol_ppm=3.0) is None
    assert _find_closest(100.0, [], tol_ppm=5.0) is None


def test_linear_interp_handles_exact_interpolated_and_out_of_range_points():
    assert _linear_interp(
        [0.0, 1.0, 1.5, 2.0, 3.0],
        [1.0, 2.0],
        [10.0, 20.0],
    ) == pytest.approx([0.0, 10.0, 15.0, 20.0, 0.0])


def test_python_peak_subtraction_drops_nonpositive_background_corrected_peaks():
    masses, intensities = _py_subtract_peaks(
        [100.0, 101.0, 102.0],
        [10.0, 5.0, 3.0],
        [100.0004, 101.0],
        [4.0, 6.0],
        tol_ppm=5.0,
    )

    assert masses == [100.0, 102.0]
    assert intensities == pytest.approx([6.0, 3.0])


def test_average_centroid_peaks_merges_matches_and_averages_over_all_scans():
    masses, intensities = _average_centroid_peaks(
        [[100.0, 200.0], [100.0002]],
        [[10.0, 4.0], [30.0]],
        tol_ppm=5.0,
    )

    assert masses == pytest.approx([100.00015, 200.0])
    assert intensities == pytest.approx([20.0, 2.0])


def test_average_centroid_peaks_handles_empty_input():
    assert _average_centroid_peaks([], []) == ([], [])
