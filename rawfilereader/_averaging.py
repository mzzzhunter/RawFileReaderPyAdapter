"""
AveragingMixin
==============
Scan averaging and background subtraction via the RawFileReader DLL.
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Union

from .models import AveragedScan, BackgroundSubtractedSpectrum
from .exceptions import AssemblyLoadError


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
        opts = MassOptions()
        if filter_string:
            filt = self._raw_file.GetFilterForScanNumber(first_scan)
            avg = self._raw_file.AverageScansInScanRange(first_scan, last_scan, filt, opts)
        else:
            avg = self._raw_file.AverageScansInScanRange(first_scan, last_scan, None, opts)

        masses = [float(m) for m in avg.PreferredMasses] if avg.PreferredMasses else []
        intensities = [float(i) for i in avg.PreferredIntensities] if avg.PreferredIntensities else []

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
        opts = MassOptions()

        from System.Collections.Generic import List as DotNetList  # type: ignore
        from System import Int32  # type: ignore

        dn_list = DotNetList[Int32]()
        for s in scan_numbers:
            dn_list.Add(Int32(s))

        avg = self._raw_file.AverageScans(dn_list, opts)

        masses = [float(m) for m in avg.PreferredMasses] if avg.PreferredMasses else []
        intensities = [float(i) for i in avg.PreferredIntensities] if avg.PreferredIntensities else []

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

        Wraps ``AverageScansInTimeRange``.

        Parameters
        ----------
        start_time, end_time:
            Retention-time window in minutes.
        filter_string:
            Optional scan-filter to restrict which scans are averaged.
        """
        self._check_open()
        from ThermoFisher.CommonCore.Data.Business import MassOptions  # type: ignore
        opts = MassOptions()

        if filter_string:
            first, _ = self.get_scan_range()
            filt = self._raw_file.GetFilterForScanNumber(first)
            avg = self._raw_file.AverageScansInTimeRange(start_time, end_time, filt, opts)
        else:
            avg = self._raw_file.AverageScansInTimeRange(start_time, end_time, None, opts)

        masses = [float(m) for m in avg.PreferredMasses] if avg.PreferredMasses else []
        intensities = [float(i) for i in avg.PreferredIntensities] if avg.PreferredIntensities else []

        first_scan = int(self._raw_file.ScanNumberFromRetentionTime(start_time))
        last_scan = int(self._raw_file.ScanNumberFromRetentionTime(end_time))

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
            dn_list = DotNetList[Int32]()
            for s in background_scan_numbers:
                dn_list.Add(Int32(s))
            from ThermoFisher.CommonCore.Data.Business import MassOptions  # type: ignore
        opts = MassOptions()
            bg_centroid = self._raw_file.AverageScans(dn_list, opts)

        result = BackgroundSubtractor().Subtract(fg_centroid, bg_centroid)

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
