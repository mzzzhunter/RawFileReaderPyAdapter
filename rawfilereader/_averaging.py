"""
AveragingMixin
==============
Scan averaging and background subtraction via the RawFileReader DLL.
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Union

from .models import AveragedScan, BackgroundSubtractedSpectrum, SubtractedSpectrum
from .exceptions import AssemblyLoadError


# ---------------------------------------------------------------------------
# Pure-Python spectral math helpers (no .NET dependency)
# ---------------------------------------------------------------------------

def _apply_mass_range(masses, intensities, mass_range):
    """Filter parallel mass/intensity lists to *mass_range* (inclusive)."""
    if mass_range is None:
        return masses, intensities
    lo, hi = mass_range
    pairs = [(m, i) for m, i in zip(masses, intensities) if lo <= m <= hi]
    if not pairs:
        return [], []
    m_out, i_out = zip(*pairs)
    return list(m_out), list(i_out)


def _normalize_to_tic(intensities):
    """Divide all intensities by their sum (TIC normalisation)."""
    tic = sum(intensities)
    if tic == 0:
        return intensities[:]
    return [v / tic for v in intensities]


def _find_closest(target, sorted_masses, tol_ppm):
    """Binary-search *sorted_masses* for the index closest to *target* within *tol_ppm*."""
    if not sorted_masses:
        return None
    tol_da = target * tol_ppm * 1e-6
    lo, hi = 0, len(sorted_masses) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if sorted_masses[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    best_idx = None
    best_delta = tol_da
    for idx in (hi, lo):
        if 0 <= idx < len(sorted_masses):
            delta = abs(sorted_masses[idx] - target)
            if delta <= best_delta:
                best_delta = delta
                best_idx = idx
    return best_idx


def _linear_interp(x_out, x_in, y_in):
    """Linearly interpolate (x_in, y_in) at each point in x_out. Out-of-range → 0."""
    if not x_in or not y_in:
        return [0.0] * len(x_out)
    result = []
    j = 0
    n = len(x_in)
    for x in x_out:
        while j < n - 1 and x_in[j + 1] <= x:
            j += 1
        if x < x_in[0] or x > x_in[-1]:
            result.append(0.0)
        elif x == x_in[j]:
            result.append(y_in[j])
        elif j + 1 < n:
            t = (x - x_in[j]) / (x_in[j + 1] - x_in[j])
            result.append(y_in[j] + t * (y_in[j + 1] - y_in[j]))
        else:
            result.append(y_in[j])
    return result


def _reflect_call(obj, method_name, *args):
    """
    Invoke a .NET instance method via reflection.

    pythonnet 3.x interface proxies only expose methods declared on the
    specific interface type.  Averaging methods live on the concrete
    RawFileAccess class, not on the IRawDataPlus / IRawDataExtended proxy,
    so they are unreachable via normal attribute access.

    Explicit interface implementations are non-public in .NET reflection
    and carry a fully-qualified name (e.g. ``IRawDataPlus.AverageScans``),
    so we first search public methods, then widen to non-public + name
    suffix matching to find explicit implementations.
    """
    import System  # type: ignore
    from System.Reflection import BindingFlags  # type: ignore

    nargs = len(args)

    # Pass 1 — public methods only
    method = next(
        (m for m in obj.GetType().GetMethods()
         if m.Name == method_name and m.GetParameters().Length == nargs),
        None,
    )

    # Pass 2 — include non-public; match on name suffix for explicit
    # interface implementations (name = "Namespace.IFace.MethodName")
    if method is None:
        all_flags = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance
        method = next(
            (m for m in obj.GetType().GetMethods(all_flags)
             if (m.Name == method_name or m.Name.endswith("." + method_name))
             and m.GetParameters().Length == nargs),
            None,
        )

    if method is None:
        raise AttributeError(
            f"'{obj.GetType().Name}' has no method '{method_name}' "
            f"with {nargs} parameter(s)"
        )

    arg_array = System.Array[System.Object](list(args))
    return method.Invoke(obj, arg_array)


def _extract_preferred(avg) -> Tuple[List[float], List[float]]:
    """Pull masses and intensities out of an averaged Scan object."""
    masses = [float(m) for m in avg.PreferredMasses] if avg.PreferredMasses else []
    intensities = [float(i) for i in avg.PreferredIntensities] if avg.PreferredIntensities else []
    return masses, intensities


class AveragingMixin:
    """Methods wrapping scan-averaging and subtraction DLL calls."""

    # ------------------------------------------------------------------
    # Average by scan range
    # ------------------------------------------------------------------

    def average_scans_in_range(
        self,
        first_scan: int,
        last_scan: int,
        filter_string: Optional[str] = None,
    ) -> AveragedScan:
        """
        Average all scans between *first_scan* and *last_scan* (inclusive).

        Parameters
        ----------
        first_scan, last_scan:
            Inclusive 1-based scan numbers defining the range.
        filter_string:
            Optional scan-filter to restrict which scans are averaged.
            Pass ``None`` to average all scan types in the range.
        """
        self._check_open()
        from ThermoFisher.CommonCore.Data.Business import MassOptions  # type: ignore
        from System.Collections.Generic import List as DotNetList  # type: ignore
        from System import Int32  # type: ignore

        opts = MassOptions()

        # Try the native 4-arg DLL call first (IScanAveragePlus.AverageScansInScanRange).
        # The filter string is required by that overload; an empty string selects all types.
        try:
            avg = _reflect_call(
                self._raw_file, "AverageScansInScanRange",
                first_scan, last_scan, filter_string or "", opts,
            )
            masses, intensities = _extract_preferred(avg)
            return AveragedScan(
                first_scan=first_scan,
                last_scan=last_scan,
                masses=masses,
                intensities=intensities,
            )
        except AttributeError:
            pass

        # Fallback: build the scan list in Python and call AverageScans.
        if filter_string:
            scan_list = [s for s in self.get_filtered_scan_numbers(filter_string)
                         if first_scan <= s <= last_scan]
        else:
            scan_list = list(range(first_scan, last_scan + 1))

        dn_list = DotNetList[Int32]()
        for s in scan_list:
            dn_list.Add(Int32(s))

        avg = _reflect_call(self._raw_file, "AverageScans", dn_list, opts)
        masses, intensities = _extract_preferred(avg)

        return AveragedScan(
            first_scan=first_scan,
            last_scan=last_scan,
            masses=masses,
            intensities=intensities,
        )

    # ------------------------------------------------------------------
    # Average by scan list
    # ------------------------------------------------------------------

    def average_scans(self, scan_numbers: List[int]) -> AveragedScan:
        """
        Average the spectra for an arbitrary list of *scan_numbers*.

        Parameters
        ----------
        scan_numbers:
            List of 1-based scan numbers to average.
        """
        self._check_open()
        from ThermoFisher.CommonCore.Data.Business import MassOptions  # type: ignore
        from System.Collections.Generic import List as DotNetList  # type: ignore
        from System import Int32  # type: ignore

        opts = MassOptions()
        dn_list = DotNetList[Int32]()
        for s in scan_numbers:
            dn_list.Add(Int32(s))

        avg = _reflect_call(self._raw_file, "AverageScans", dn_list, opts)
        masses, intensities = _extract_preferred(avg)

        return AveragedScan(
            first_scan=min(scan_numbers),
            last_scan=max(scan_numbers),
            masses=masses,
            intensities=intensities,
        )

    # ------------------------------------------------------------------
    # Average by time range
    # ------------------------------------------------------------------

    def average_scans_in_time_range(
        self,
        start_time: float,
        end_time: float,
        filter_string: Optional[str] = None,
    ) -> AveragedScan:
        """
        Average scans within a retention-time window.

        Parameters
        ----------
        start_time, end_time:
            Retention-time window in minutes.
        filter_string:
            Optional scan-filter to restrict which scans are averaged.
        """
        self._check_open()
        from ThermoFisher.CommonCore.Data.Business import MassOptions  # type: ignore
        from System.Collections.Generic import List as DotNetList  # type: ignore
        from System import Int32  # type: ignore

        opts = MassOptions()

        first_scan = int(self._raw_file.ScanNumberFromRetentionTime(start_time))
        last_scan = int(self._raw_file.ScanNumberFromRetentionTime(end_time))

        # Try the native 4-arg DLL call first (IScanAveragePlus.AverageScansInTimeRange).
        try:
            avg = _reflect_call(
                self._raw_file, "AverageScansInTimeRange",
                start_time, end_time, filter_string or "", opts,
            )
            masses, intensities = _extract_preferred(avg)
            return AveragedScan(
                first_scan=first_scan,
                last_scan=last_scan,
                masses=masses,
                intensities=intensities,
                time_range=(start_time, end_time),
            )
        except AttributeError:
            pass

        # Fallback: build the scan list in Python and call AverageScans.
        if filter_string:
            scan_list = self.get_filtered_scan_numbers_over_time(filter_string, start_time, end_time)
        else:
            scan_list = list(range(first_scan, last_scan + 1))

        dn_list = DotNetList[Int32]()
        for s in scan_list:
            dn_list.Add(Int32(s))

        avg = _reflect_call(self._raw_file, "AverageScans", dn_list, opts)
        masses, intensities = _extract_preferred(avg)

        return AveragedScan(
            first_scan=first_scan,
            last_scan=last_scan,
            masses=masses,
            intensities=intensities,
            time_range=(start_time, end_time),
        )

    # ------------------------------------------------------------------
    # Background subtraction
    # ------------------------------------------------------------------

    def subtract_background(
        self,
        scan_number: int,
        background_scan_numbers: Union[int, List[int]],
        mass_range: Optional[Tuple[float, float]] = None,
    ) -> BackgroundSubtractedSpectrum:
        """
        Remove background from *scan_number* using the Thermo Fisher
        ``BackgroundSubtractor`` algorithm.

        Requires ``ThermoFisher.CommonCore.BackgroundSubtraction.dll``.

        Parameters
        ----------
        scan_number:
            1-based foreground scan number.
        background_scan_numbers:
            One background scan (``int``) or a list.  A list is averaged
            by the .NET layer before subtraction.
        mass_range:
            Optional ``(low_mz, high_mz)`` window applied to the result.

        Raises
        ------
        AssemblyLoadError
            If ``ThermoFisher.CommonCore.BackgroundSubtraction.dll`` is not
            loaded.
        """
        self._check_open()
        self._check_scan(scan_number)

        if isinstance(background_scan_numbers, int):
            background_scan_numbers = [background_scan_numbers]
        for bg in background_scan_numbers:
            self._check_scan(bg)

        try:
            from ThermoFisher.CommonCore.BackgroundSubtraction import BackgroundSubtractor  # type: ignore
        except ImportError as exc:
            raise AssemblyLoadError(
                "ThermoFisher.CommonCore.BackgroundSubtraction.dll is not loaded.  "
                "Place it in the libs directory alongside the other RawFileReader DLLs."
            ) from exc

        scan_filter = str(self._raw_file.GetFilterForScanNumber(scan_number))
        fg_centroid = self._raw_file.GetCentroidStream(scan_number, False)

        if len(background_scan_numbers) == 1:
            bg_centroid = self._raw_file.GetCentroidStream(background_scan_numbers[0], False)
        else:
            from System.Collections.Generic import List as DotNetList  # type: ignore
            from System import Int32  # type: ignore
            from ThermoFisher.CommonCore.Data.Business import MassOptions  # type: ignore
            dn_list = DotNetList[Int32]()
            for s in background_scan_numbers:
                dn_list.Add(Int32(s))
            bg_centroid = _reflect_call(self._raw_file, "AverageScans", dn_list, MassOptions())

        result = BackgroundSubtractor().SubtractBackground(fg_centroid, bg_centroid)

        masses = [float(m) for m in result.Masses] if result and result.Masses else []
        intensities = [float(i) for i in result.Intensities] if result and result.Intensities else []

        if mass_range is not None:
            lo, hi = mass_range
            pairs = [(m, i) for m, i in zip(masses, intensities) if lo <= m <= hi]
            masses = [m for m, _ in pairs]
            intensities = [i for _, i in pairs]

        return BackgroundSubtractedSpectrum(
            scan_number=scan_number,
            background_scans=list(background_scan_numbers),
            scan_filter=scan_filter,
            masses=masses,
            intensities=intensities,
        )

    def subtract_scans(
        self,
        foreground_scan: int,
        background_scan: int,
        mass_range: Optional[Tuple[float, float]] = None,
    ) -> BackgroundSubtractedSpectrum:
        """
        Subtract a background scan from a foreground scan using the native
        ``IScanAveragePlus.SubtractScans`` DLL method.

        Unlike :meth:`subtract_background` this does not require the optional
        ``BackgroundSubtraction.dll`` — the subtraction is performed entirely
        by the core RawFileReader assembly.

        Parameters
        ----------
        foreground_scan:
            1-based scan number for the foreground spectrum.
        background_scan:
            1-based scan number for the background spectrum.
        mass_range:
            Optional ``(low_mz, high_mz)`` window applied to the result.
        """
        self._check_open()
        self._check_scan(foreground_scan)
        self._check_scan(background_scan)

        from ThermoFisher.CommonCore.Data.Business import MassOptions  # type: ignore
        from System.Collections.Generic import List as DotNetList  # type: ignore
        from System import Int32  # type: ignore

        opts = MassOptions()

        # Get each scan as a Scan object via AverageScans with a single-item list.
        def _scan_object(scan_no: int):
            dn = DotNetList[Int32]()
            dn.Add(Int32(scan_no))
            return _reflect_call(self._raw_file, "AverageScans", dn, opts)

        fg_scan = _scan_object(foreground_scan)
        bg_scan = _scan_object(background_scan)

        result = _reflect_call(self._raw_file, "SubtractScans", fg_scan, bg_scan, opts)

        masses, intensities = _extract_preferred(result)

        if mass_range is not None:
            lo, hi = mass_range
            pairs = [(m, i) for m, i in zip(masses, intensities) if lo <= m <= hi]
            masses = [m for m, _ in pairs]
            intensities = [i for _, i in pairs]

        scan_filter = str(self._raw_file.GetFilterForScanNumber(foreground_scan))
        return BackgroundSubtractedSpectrum(
            scan_number=foreground_scan,
            background_scans=[background_scan],
            scan_filter=scan_filter,
            masses=masses,
            intensities=intensities,
        )

    # ------------------------------------------------------------------
    # Pure-Python spectral subtraction (no extra DLL needed)
    # ------------------------------------------------------------------

    def subtract_spectra(
        self,
        scan_a: int,
        scan_b: int,
        mass_range: Optional[Tuple[float, float]] = None,
        mass_tolerance_ppm: float = 5.0,
        normalize: bool = False,
    ) -> SubtractedSpectrum:
        """
        Subtract the spectrum of *scan_b* from *scan_a* (A − B) using pure
        Python math — no extra DLL required.

        Both scans must share the same scan filter string.  Use the ``peaks``
        property on the result to iterate surviving (positive) peaks.

        Parameters
        ----------
        scan_a, scan_b:
            1-based scan numbers for foreground and background.
        mass_range:
            Optional ``(low_mz, high_mz)`` window applied before subtraction.
        mass_tolerance_ppm:
            m/z tolerance used to match centroid peaks across scans.
        normalize:
            If ``True``, TIC-normalise both spectra before subtracting.
        """
        self._check_open()
        self._check_scan(scan_a)
        self._check_scan(scan_b)

        filter_a = self._raw_file.GetFilterForScanNumber(scan_a).ToString()
        filter_b = self._raw_file.GetFilterForScanNumber(scan_b).ToString()
        if filter_a != filter_b:
            raise ValueError(
                f"Cannot subtract scans with different filters.\n"
                f"  scan {scan_a}: {filter_a!r}\n"
                f"  scan {scan_b}: {filter_b!r}"
            )

        use_centroid = "FTMS" in filter_a.upper()
        if use_centroid:
            masses, intensities = self._subtract_centroid(
                scan_a, scan_b, mass_range, mass_tolerance_ppm, normalize
            )
        else:
            masses, intensities = self._subtract_profile(scan_a, scan_b, mass_range, normalize)

        return SubtractedSpectrum(
            scan_a=scan_a,
            scan_b=scan_b,
            scan_filter=filter_a,
            mass_range=mass_range,
            is_centroid=use_centroid,
            masses=masses,
            intensities=intensities,
            intensities_clipped=[max(0.0, v) for v in intensities],
        )

    def _subtract_centroid(self, scan_a, scan_b, mass_range, tol_ppm, normalize):
        cs_a = self._raw_file.GetCentroidStream(scan_a, False)
        cs_b = self._raw_file.GetCentroidStream(scan_b, False)

        masses_a = [float(m) for m in cs_a.Masses] if cs_a.Masses else []
        inten_a  = [float(i) for i in cs_a.Intensities] if cs_a.Intensities else []
        masses_b = [float(m) for m in cs_b.Masses] if cs_b.Masses else []
        inten_b  = [float(i) for i in cs_b.Intensities] if cs_b.Intensities else []

        masses_a, inten_a = _apply_mass_range(masses_a, inten_a, mass_range)
        masses_b, inten_b = _apply_mass_range(masses_b, inten_b, mass_range)

        if normalize:
            inten_a = _normalize_to_tic(inten_a)
            inten_b = _normalize_to_tic(inten_b)

        matched_b = [False] * len(masses_b)
        out_masses: List[float] = []
        out_intensities: List[float] = []

        for m_a, i_a in zip(masses_a, inten_a):
            best_idx = _find_closest(m_a, masses_b, tol_ppm)
            if best_idx is not None:
                matched_b[best_idx] = True
                out_masses.append(m_a)
                out_intensities.append(i_a - inten_b[best_idx])
            else:
                out_masses.append(m_a)
                out_intensities.append(i_a)

        for idx, (m_b, i_b) in enumerate(zip(masses_b, inten_b)):
            if not matched_b[idx]:
                out_masses.append(m_b)
                out_intensities.append(-i_b)

        pairs = sorted(zip(out_masses, out_intensities), key=lambda x: x[0])
        if pairs:
            out_m, out_i = zip(*pairs)
            return list(out_m), list(out_i)
        return [], []

    def _subtract_profile(self, scan_a, scan_b, mass_range, normalize):
        stats_a = self._raw_file.GetScanStatsForScanNumber(scan_a)
        stats_b = self._raw_file.GetScanStatsForScanNumber(scan_b)
        seg_a = self._raw_file.GetSegmentedScanFromScanNumber(scan_a, stats_a)
        seg_b = self._raw_file.GetSegmentedScanFromScanNumber(scan_b, stats_b)

        masses_a = [float(p) for p in seg_a.Positions]  if seg_a and seg_a.Positions  else []
        inten_a  = [float(i) for i in seg_a.Intensities] if seg_a and seg_a.Intensities else []
        masses_b = [float(p) for p in seg_b.Positions]  if seg_b and seg_b.Positions  else []
        inten_b  = [float(i) for i in seg_b.Intensities] if seg_b and seg_b.Intensities else []

        masses_a, inten_a = _apply_mass_range(masses_a, inten_a, mass_range)
        masses_b, inten_b = _apply_mass_range(masses_b, inten_b, mass_range)

        if normalize:
            inten_a = _normalize_to_tic(inten_a)
            inten_b = _normalize_to_tic(inten_b)

        inten_b_interp = _linear_interp(masses_a, masses_b, inten_b)
        return masses_a, [a - b for a, b in zip(inten_a, inten_b_interp)]
