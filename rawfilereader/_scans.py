"""
ScansMixin
==========
Scan data access: centroid/profile spectra, stats, scan info, filters,
events, filtered enumerators, dependents, and mass precision.
"""

from __future__ import annotations

from typing import Generator, List, Optional

from .models import (
    CentroidData,
    MassPrecision,
    ProfileData,
    ScanDependent,
    ScanInfo,
    ScanStats,
)
from .exceptions import AssemblyLoadError


class ScansMixin:
    """Methods wrapping scan-level DLL calls on IRawDataPlus."""

    # ------------------------------------------------------------------
    # Retention time
    # ------------------------------------------------------------------

    def get_retention_time(self, scan_number: int) -> float:
        """Return the retention time in minutes for *scan_number*."""
        self._check_open()
        self._check_scan(scan_number)
        return float(self._raw_file.RetentionTimeFromScanNumber(scan_number))

    def scan_number_from_retention_time(self, retention_time: float) -> int:
        """
        Return the scan number whose retention time is closest to *retention_time*.

        Parameters
        ----------
        retention_time:
            Retention time in minutes.

        Raises
        ------
        ValueError
            If *retention_time* is outside the file's retention-time range.
        """
        self._check_open()
        first_rt = float(self._raw_file.RetentionTimeFromScanNumber(
            int(self._raw_file.RunHeaderEx.FirstSpectrum)
        ))
        last_rt = float(self._raw_file.RetentionTimeFromScanNumber(
            int(self._raw_file.RunHeaderEx.LastSpectrum)
        ))
        if not (first_rt <= retention_time <= last_rt):
            raise ValueError(
                f"retention_time {retention_time:.4f} min is outside the file range "
                f"[{first_rt:.4f}, {last_rt:.4f}] min."
            )
        return int(self._raw_file.ScanNumberFromRetentionTime(retention_time))

    # ------------------------------------------------------------------
    # Scan statistics
    # ------------------------------------------------------------------

    def get_scan_stats(self, scan_number: int) -> ScanStats:
        """
        Return per-scan statistics (TIC, base peak, mass range, …).

        Parameters
        ----------
        scan_number:
            1-based scan number.
        """
        self._check_open()
        self._check_scan(scan_number)
        st = self._raw_file.GetScanStatsForScanNumber(scan_number)
        filt = self._raw_file.GetFilterForScanNumber(scan_number)
        return ScanStats(
            scan_number=scan_number,
            start_time=float(st.StartTime),
            low_mass=float(st.LowMass),
            high_mass=float(st.HighMass),
            tic=float(st.TIC),
            base_peak_mass=float(st.BasePeakMass),
            base_peak_intensity=float(st.BasePeakIntensity),
            packet_count=int(st.PacketCount),
            scan_event_number=int(st.ScanEventNumber),
            master_index=int(st.MasterIndex) if hasattr(st, "MasterIndex") else 0,
            is_centroid_scan=bool(st.IsCentroidScan) if hasattr(st, "IsCentroidScan") else (
                "FTMS" in str(filt).upper()
            ),
        )

    # ------------------------------------------------------------------
    # Centroid data
    # ------------------------------------------------------------------

    def get_centroid_stream(
        self, scan_number: int, prefer_profile_data: bool = False
    ) -> CentroidData:
        """
        Return centroid (peak-picked) mass spectrum data for *scan_number*.

        Parameters
        ----------
        scan_number:
            1-based scan number.
        prefer_profile_data:
            Forwarded to the .NET ``GetCentroidStream`` call.
        """
        self._check_open()
        self._check_scan(scan_number)
        cs = self._raw_file.GetCentroidStream(scan_number, prefer_profile_data)

        masses = [float(m) for m in cs.Masses] if cs.Masses else []
        intensities = [float(i) for i in cs.Intensities] if cs.Intensities else []
        charges = [float(c) for c in cs.Charges] if cs.Charges else []
        baselines = [float(b) for b in cs.Baselines] if cs.Baselines else []
        noises = [float(n) for n in cs.Noises] if cs.Noises else []
        resolutions = [float(r) for r in cs.Resolutions] if cs.Resolutions else []

        return CentroidData(
            scan_number=scan_number,
            masses=masses,
            intensities=intensities,
            charges=charges,
            baselines=baselines,
            noises=noises,
            resolutions=resolutions,
            is_exceptional=bool(cs.IsExceptional) if hasattr(cs, "IsExceptional") else False,
            is_reference=bool(cs.IsReference) if hasattr(cs, "IsReference") else False,
        )

    # ------------------------------------------------------------------
    # Profile data
    # ------------------------------------------------------------------

    def get_profile_data(self, scan_number: int) -> ProfileData:
        """
        Return raw profile (continuous) data for *scan_number*.

        Parameters
        ----------
        scan_number:
            1-based scan number.
        """
        self._check_open()
        self._check_scan(scan_number)
        stats = self._raw_file.GetScanStatsForScanNumber(scan_number)
        seg = self._raw_file.GetSegmentedScanFromScanNumber(scan_number, stats)

        segments = []
        if seg is not None:
            try:
                positions = [float(p) for p in seg.Positions]
                intensities = [float(i) for i in seg.Intensities]
                segments.append((positions, intensities))
            except Exception:
                pass

        return ProfileData(scan_number=scan_number, segments=segments)

    # ------------------------------------------------------------------
    # High-level scan info
    # ------------------------------------------------------------------

    def get_scan_info(self, scan_number: int) -> ScanInfo:
        """
        Return a consolidated :class:`ScanInfo` for *scan_number*.

        Combines filter string, scan event, scan stats, retention time, and
        trailer-extra data into a single dataclass.

        Parameters
        ----------
        scan_number:
            1-based scan number.
        """
        self._check_open()
        self._check_scan(scan_number)

        filter_str = self._raw_file.GetFilterForScanNumber(scan_number).ToString()
        ev = self._raw_file.GetScanEventForScanNumber(scan_number)
        rt = float(self._raw_file.RetentionTimeFromScanNumber(scan_number))

        ms_order = int(ev.MSOrder)
        is_centroid = "FTMS" in filter_str.upper() or "FT" in filter_str.upper()
        detector = str(ev.Detector) if hasattr(ev, "Detector") else ""

        trailer = self._get_trailer_dict(scan_number)
        inj_time = float(trailer.get("Ion Injection Time (ms)", 0.0) or 0.0)

        precursor_mass: Optional[float] = None
        precursor_charge: Optional[int] = None
        collision_energy: Optional[float] = None
        isolation_width: Optional[float] = None
        monoisotopic_mass: Optional[float] = None

        if ms_order >= 2:
            try:
                pm = ev.GetReaction(0).PrecursorMass
                precursor_mass = float(pm) or None
            except Exception:
                pass
            try:
                collision_energy = float(ev.GetReaction(0).CollisionEnergy)
            except Exception:
                pass
            try:
                isolation_width = float(ev.GetReaction(0).IsolationWidth)
            except Exception:
                pass
            try:
                monoisotopic_mass = float(
                    trailer.get("Monoisotopic M/Z:", None) or 0.0
                ) or None
            except Exception:
                pass
            try:
                precursor_charge = int(trailer.get("Charge State:", 0) or 0) or None
            except Exception:
                pass

        return ScanInfo(
            scan_number=scan_number,
            scan_filter=filter_str,
            ms_order=ms_order,
            retention_time=rt,
            injection_time=inj_time,
            is_centroid=is_centroid,
            detector_type=detector,
            activation_type="",
            precursor_mass=precursor_mass,
            precursor_charge=precursor_charge,
            collision_energy=collision_energy,
            isolation_width=isolation_width,
            monoisotopic_mass=monoisotopic_mass,
            ion_injection_time=inj_time or None,
        )

    # ------------------------------------------------------------------
    # Scan filters
    # ------------------------------------------------------------------

    def get_filters(self) -> List[str]:
        """Return all unique scan-filter strings present in the file."""
        self._check_open()
        return [f.ToString() for f in self._raw_file.GetFilters()]

    def get_auto_filters(self) -> List[str]:
        """
        Return auto-generated filter strings that cover all scan types in the
        file (wraps ``GetAutoFilters``).
        """
        self._check_open()
        return [str(f) for f in self._raw_file.GetAutoFilters()]

    def get_filter_for_scan(self, scan_number: int) -> str:
        """Return the scan-filter string for *scan_number*."""
        self._check_open()
        self._check_scan(scan_number)
        return self._raw_file.GetFilterForScanNumber(scan_number).ToString()

    def get_filter_from_string(self, filter_string: str) -> str:
        """
        Parse *filter_string* into a normalised filter and return its string
        representation (wraps ``GetFilterFromString``).

        Parameters
        ----------
        filter_string:
            Human-readable filter string, e.g.
            ``"FTMS + p NSI Full ms [200.00-2000.00]"``.
        """
        self._check_open()
        filt = self._raw_file.GetFilterFromString(filter_string)
        return filt.ToString()

    # ------------------------------------------------------------------
    # Filtered scan enumerators
    # ------------------------------------------------------------------

    def get_filtered_scan_numbers(self, filter_string: str) -> List[int]:
        """
        Return a list of scan numbers that match *filter_string*.

        Wraps ``GetFilteredScanEnumerator``.

        Parameters
        ----------
        filter_string:
            Scan filter string to match against.
        """
        self._check_open()
        filt = self._raw_file.GetFilterFromString(filter_string)
        return [int(s) for s in self._raw_file.GetFilteredScanEnumerator(filt)]

    def get_filtered_scan_numbers_over_time(
        self,
        filter_string: str,
        start_time: float,
        end_time: float,
    ) -> List[int]:
        """
        Return scan numbers matching *filter_string* within a retention-time
        window (wraps ``GetFilteredScanEnumeratorOverTime``).

        Parameters
        ----------
        filter_string:
            Scan filter string to match.
        start_time, end_time:
            Retention-time window in minutes.
        """
        self._check_open()
        filt = self._raw_file.GetFilterFromString(filter_string)
        return [int(s) for s in self._raw_file.GetFilteredScanEnumeratorOverTime(
            filt, start_time, end_time
        )]

    def iterate_filtered_scans(
        self,
        filter_string: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> Generator[int, None, None]:
        """
        Yield scan numbers matching *filter_string*, lazily.

        Unlike :meth:`get_filtered_scan_numbers` (which materialises the full
        list), this generator pulls one scan number at a time from the .NET
        enumerator, making it suitable for very large files.

        Parameters
        ----------
        filter_string:
            Scan filter string to match.
        start_time, end_time:
            Optional retention-time window in minutes.  When both are
            provided the time-range enumerator is used.
        """
        self._check_open()
        filt = self._raw_file.GetFilterFromString(filter_string)
        if start_time is not None and end_time is not None:
            enumerator = self._raw_file.GetFilteredScanEnumeratorOverTime(
                filt, start_time, end_time
            )
        else:
            enumerator = self._raw_file.GetFilteredScanEnumerator(filt)
        for scan_no in enumerator:
            yield int(scan_no)

    # ------------------------------------------------------------------
    # Scan events
    # ------------------------------------------------------------------

    def get_scan_event_for_scan(self, scan_number: int) -> dict:
        """
        Return a dictionary of scan-event parameters for *scan_number*.

        Common keys: ``MSOrder``, ``Polarity``, ``ScanType``, ``Detector``,
        ``MassRangeCount``.
        """
        self._check_open()
        self._check_scan(scan_number)
        ev = self._raw_file.GetScanEventForScanNumber(scan_number)
        result: dict = {}
        try:
            result["MSOrder"] = int(ev.MSOrder)
            result["Polarity"] = str(ev.Polarity)
            result["ScanType"] = str(ev.ScanType)
            result["Detector"] = str(ev.Detector)
            result["MassRangeCount"] = int(ev.MassRangeCount)
            if hasattr(ev, "ScanEventNumber"):
                result["ScanEventNumber"] = int(ev.ScanEventNumber)
        except Exception:
            pass
        return result

    def get_scan_event_string(self, scan_number: int) -> str:
        """
        Return the scan-event string representation for *scan_number*
        (wraps ``GetScanEventStringForScanNumber``).
        """
        self._check_open()
        self._check_scan(scan_number)
        return str(self._raw_file.GetScanEventStringForScanNumber(scan_number))

    def test_scan(self, scan_number: int, filter_string: str) -> bool:
        """
        Return ``True`` if *scan_number* matches *filter_string*
        (wraps ``TestScan``).
        """
        self._check_open()
        self._check_scan(scan_number)
        return bool(self._raw_file.TestScan(scan_number, filter_string))

    # ------------------------------------------------------------------
    # Scan dependents
    # ------------------------------------------------------------------

    def get_scan_dependents(self, scan_number: int, depth: int = 1) -> ScanDependent:
        """
        Return MS^n dependent scan relationships for *scan_number*.

        Parameters
        ----------
        scan_number:
            1-based parent scan number.
        depth:
            Dependency depth to retrieve (1 = direct children only).
        """
        self._check_open()
        self._check_scan(scan_number)
        deps = self._raw_file.GetScanDependents(scan_number, depth)
        dependent_scans: List[int] = []
        try:
            for dep in deps.ScanDependents:
                dependent_scans.append(int(dep.ScanNumber))
        except Exception:
            pass
        return ScanDependent(
            scan_number=scan_number,
            dependent_scan_numbers=dependent_scans,
        )

    # ------------------------------------------------------------------
    # Mass precision
    # ------------------------------------------------------------------

    def get_mass_precision(self, scan_number: int) -> List[MassPrecision]:
        """
        Estimate mass precision for each peak in *scan_number*.

        Requires ``ThermoFisher.CommonCore.MassPrecisionEstimator.dll``.

        Parameters
        ----------
        scan_number:
            1-based scan number (must be an FTMS/Orbitrap scan).
        """
        self._check_open()
        self._check_scan(scan_number)

        try:
            from ThermoFisher.CommonCore.MassPrecisionEstimator import PrecisionEstimate  # type: ignore
        except ImportError as exc:
            raise AssemblyLoadError(
                "MassPrecisionEstimator assembly not loaded.  "
                "Ensure ThermoFisher.CommonCore.MassPrecisionEstimator.dll is present."
            ) from exc

        centroid_stream = self._raw_file.GetCentroidStream(scan_number, False)
        estimator = PrecisionEstimate()
        estimates = estimator.GetMassPrecisionEstimate(
            centroid_stream, self._raw_file, scan_number
        )

        return [
            MassPrecision(
                mass=float(e.Mass),
                intensity=float(e.Intensity),
                resolution=float(e.Resolution),
                mz_accuracy_ppm=float(e.MZAccuracyInPPM),
                mz_accuracy_mmu=float(e.MZAccuracyInMMU),
            )
            for e in estimates
        ]
