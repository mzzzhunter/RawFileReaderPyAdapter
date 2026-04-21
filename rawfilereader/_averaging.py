"""
AveragingMixin
==============
Scan averaging and background subtraction via the RawFileReader DLL.
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Union

from .models import AveragedScan, BackgroundSubtractedSpectrum
from .exceptions import AssemblyLoadError


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
