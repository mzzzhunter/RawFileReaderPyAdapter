"""
RawFileAdapter
==============
High-level Python wrapper around the Thermo Fisher Scientific RawFileReader
.NET assemblies.  All public methods return plain Python dataclasses defined
in :mod:`rawfilereader.models`; callers never touch .NET objects directly.

Usage
-----
>>> from rawfilereader import RawFileAdapter
>>> with RawFileAdapter("sample.raw") as rf:
...     info = rf.get_file_info()
...     print(info.instrument_name)
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Dict, Iterator, List, Optional, Tuple

from .exceptions import (
    AssemblyLoadError,
    InstrumentSelectionError,
    RawFileInAcquisitionError,
    RawFileNotOpenError,
    ScanNotFoundError,
)
from .loader import load_assemblies
from .models import (
    AveragedScan,
    CentroidData,
    ChromatogramData,
    FileInfo,
    InstrumentInfo,
    MassPrecision,
    ProfileData,
    ScanDependent,
    ScanInfo,
    ScanStats,
    StatusLogEntry,
    SubtractedSpectrum,
    TrailerData,
)

# .NET namespaces – imported lazily after the assemblies are loaded
_ns_data = "ThermoFisher.CommonCore.Data"
_ns_reader = "ThermoFisher.CommonCore.RawFileReader"
_ns_precis = "ThermoFisher.CommonCore.MassPrecisionEstimator"

# ---------------------------------------------------------------------------
# Pure-Python helpers used by spectral subtraction (no .NET dependency)
# ---------------------------------------------------------------------------

def _apply_mass_range(
    masses: List[float],
    intensities: List[float],
    mass_range: Optional[Tuple[float, float]],
) -> Tuple[List[float], List[float]]:
    """Filter parallel mass/intensity lists to *mass_range* (inclusive)."""
    if mass_range is None:
        return masses, intensities
    lo, hi = mass_range
    pairs = [(m, i) for m, i in zip(masses, intensities) if lo <= m <= hi]
    if not pairs:
        return [], []
    m_out, i_out = zip(*pairs)
    return list(m_out), list(i_out)


def _normalize_to_tic(intensities: List[float]) -> List[float]:
    """Divide all intensities by their sum (TIC normalisation)."""
    tic = sum(intensities)
    if tic == 0:
        return intensities[:]
    return [v / tic for v in intensities]


def _find_closest(
    target: float,
    sorted_masses: List[float],
    tol_ppm: float,
) -> Optional[int]:
    """
    Binary-search *sorted_masses* for the index closest to *target* within
    *tol_ppm*.  Returns ``None`` when no match exists within tolerance.
    """
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
    # Check the two neighbouring candidates
    best_idx: Optional[int] = None
    best_delta = tol_da
    for idx in (hi, lo):
        if 0 <= idx < len(sorted_masses):
            delta = abs(sorted_masses[idx] - target)
            if delta <= best_delta:
                best_delta = delta
                best_idx = idx
    return best_idx


def _linear_interp(
    x_out: List[float],
    x_in: List[float],
    y_in: List[float],
) -> List[float]:
    """
    Linearly interpolate (x_in, y_in) at each point in x_out.
    Points outside the range of x_in are extrapolated as 0.
    Both x_out and x_in must be sorted ascending.
    """
    if not x_in or not y_in:
        return [0.0] * len(x_out)

    result: List[float] = []
    j = 0
    n = len(x_in)
    for x in x_out:
        # Advance j so x_in[j] is the first value >= x
        while j < n - 1 and x_in[j + 1] <= x:
            j += 1
        if x < x_in[0] or x > x_in[-1]:
            result.append(0.0)
        elif x == x_in[j]:
            result.append(y_in[j])
        elif j + 1 < n:
            # Interpolate between j and j+1
            t = (x - x_in[j]) / (x_in[j + 1] - x_in[j])
            result.append(y_in[j] + t * (y_in[j + 1] - y_in[j]))
        else:
            result.append(y_in[j])
    return result


class RawFileAdapter:
    """
    Python adapter for reading Thermo Scientific RAW files via RawFileReader.

    Parameters
    ----------
    raw_file_path:
        Absolute or relative path to the ``.raw`` file.
    libs_dir:
        Directory containing the RawFileReader DLLs.  When *None* the loader
        uses the ``RAWFILEREADER_LIBS`` environment variable or searches for a
        *libs/* directory next to the package.
    instrument_type:
        The device type to select on open.  Defaults to ``"MS"``.
    instrument_instance:
        1-based instance number for the selected device.

    Examples
    --------
    >>> adapter = RawFileAdapter("sample.raw")
    >>> adapter.open()
    >>> scans = adapter.get_scan_range()
    >>> adapter.close()

    Use as a context manager to ensure the file is always closed:

    >>> with RawFileAdapter("sample.raw") as rf:
    ...     print(rf.get_file_info().instrument_name)
    """

    # Supported device type strings (mirrors the Device enum in the .NET API)
    DEVICE_TYPES = ("MS", "MSAnalog", "UV", "PDA", "Analog", "ADCard", "Lyra")

    def __init__(
        self,
        raw_file_path: str,
        libs_dir: Optional[str] = None,
        instrument_type: str = "MS",
        instrument_instance: int = 1,
    ) -> None:
        self._path = os.path.abspath(raw_file_path)
        self._libs_dir = libs_dir
        self._instrument_type = instrument_type
        self._instrument_instance = instrument_instance
        self._raw_file = None  # the .NET IRawDataPlus object
        self._device_enum = None  # cached .NET Device enum type

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "RawFileAdapter":
        self.open()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Assembly loading helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """Load .NET assemblies (idempotent)."""
        load_assemblies(self._libs_dir)

    def _import_dotnet_types(self):
        """Import .NET types after assemblies are loaded."""
        from ThermoFisher.CommonCore.RawFileReader import RawFileReaderAdapter  # type: ignore
        from ThermoFisher.CommonCore.Data.Business import Device  # type: ignore
        return RawFileReaderAdapter, Device

    # ------------------------------------------------------------------
    # File open / close
    # ------------------------------------------------------------------

    def open(self) -> None:
        """
        Open the RAW file and select the default instrument device.

        Raises
        ------
        FileNotFoundError
            If the ``.raw`` file does not exist.
        RawFileInAcquisitionError
            If the file is still being acquired.
        InstrumentSelectionError
            If the requested device type / instance cannot be selected.
        AssemblyLoadError
            If the RawFileReader DLLs cannot be located.
        """
        if not os.path.exists(self._path):
            raise FileNotFoundError(f"RAW file not found: {self._path}")

        self._ensure_loaded()
        RawFileReaderAdapter, Device = self._import_dotnet_types()

        raw = RawFileReaderAdapter.FileFactory(self._path)

        if not raw.IsOpen:
            raise RawFileNotOpenError(
                f"RawFileReader could not open: {self._path}"
            )
        if raw.IsError:
            raise RawFileNotOpenError(
                f"RawFileReader reported an error on: {self._path}"
            )
        if raw.InAcquisition:
            raise RawFileInAcquisitionError(
                f"File is still being acquired: {self._path}"
            )

        # Select default instrument
        self._raw_file = raw
        self._device_enum = Device
        self.select_instrument(self._instrument_type, self._instrument_instance)

    def close(self) -> None:
        """Close the RAW file and release .NET resources."""
        if self._raw_file is not None:
            self._raw_file.Dispose()
            self._raw_file = None

    def is_open(self) -> bool:
        """Return ``True`` if the file is currently open."""
        return self._raw_file is not None and self._raw_file.IsOpen

    # ------------------------------------------------------------------
    # Internal guards
    # ------------------------------------------------------------------

    def _check_open(self) -> None:
        if self._raw_file is None or not self._raw_file.IsOpen:
            raise RawFileNotOpenError("File is not open.  Call open() first.")

    def _check_scan(self, scan_number: int) -> None:
        first, last = self.get_scan_range()
        if not (first <= scan_number <= last):
            raise ScanNotFoundError(
                f"Scan {scan_number} is outside the valid range [{first}, {last}]."
            )

    def _get_device(self, device_type: str):
        """Return the .NET Device enum value for *device_type* string."""
        Device = self._device_enum
        mapping = {
            "MS": Device.MS,
            "MSAnalog": Device.MSAnalog,
            "UV": Device.UV,
            "PDA": Device.PDA,
            "Analog": Device.Analog,
            "ADCard": getattr(Device, "ADCard", None),
            "Lyra": getattr(Device, "Lyra", None),
        }
        value = mapping.get(device_type)
        if value is None:
            raise InstrumentSelectionError(
                f"Unknown device type '{device_type}'.  "
                f"Valid types: {list(mapping.keys())}"
            )
        return value

    # ------------------------------------------------------------------
    # Instrument selection
    # ------------------------------------------------------------------

    def select_instrument(self, device_type: str, instance: int = 1) -> None:
        """
        Select an instrument device for subsequent data reads.

        Parameters
        ----------
        device_type:
            One of ``"MS"``, ``"UV"``, ``"PDA"``, ``"Analog"``, ``"MSAnalog"``.
        instance:
            1-based device instance number (usually 1).

        Raises
        ------
        InstrumentSelectionError
            If the device type is unknown or the instance does not exist.
        """
        self._check_open()
        device = self._get_device(device_type)
        try:
            self._raw_file.SelectInstrument(device, instance)
        except Exception as exc:
            raise InstrumentSelectionError(
                f"Cannot select {device_type} instance {instance}: {exc}"
            ) from exc

    def get_instrument_count(self) -> int:
        """Return the total number of instrument devices in the file."""
        self._check_open()
        return int(self._raw_file.InstrumentCount)

    def get_instrument_count_of_type(self, device_type: str) -> int:
        """Return the number of devices of the given *device_type*."""
        self._check_open()
        device = self._get_device(device_type)
        return int(self._raw_file.GetInstrumentCountOfType(device))

    def get_instrument_type(self, index: int) -> str:
        """Return the device-type string for the given 0-based *index*."""
        self._check_open()
        dtype = self._raw_file.GetInstrumentType(index)
        return str(dtype)

    def get_instrument_data(self) -> InstrumentInfo:
        """
        Return metadata for the currently selected instrument device.

        Returns
        -------
        InstrumentInfo
        """
        self._check_open()
        d = self._raw_file.GetInstrumentData()
        channel_labels: List[str] = []
        try:
            for label in d.ChannelLabels:
                channel_labels.append(str(label))
        except Exception:
            pass
        return InstrumentInfo(
            device_type=self._instrument_type,
            instance_number=self._instrument_instance,
            name=str(d.Name),
            model=str(d.Model),
            serial_number=str(d.SerialNumber),
            software_version=str(d.SoftwareVersion),
            hardware_version=str(d.HardwareVersion),
            units=str(d.Units),
            channel_labels=channel_labels,
        )

    # ------------------------------------------------------------------
    # File / run header
    # ------------------------------------------------------------------

    def get_file_info(self) -> FileInfo:
        """
        Return file-level metadata (operator, sample, instrument, …).

        Returns
        -------
        FileInfo
        """
        self._check_open()
        fh = self._raw_file.FileHeader
        si = self._raw_file.SampleInformation
        rh = self._raw_file.RunHeaderEx
        idata = self._raw_file.GetInstrumentData()

        return FileInfo(
            file_name=str(self._raw_file.FileName),
            creation_date=str(fh.CreationDate),
            operator=str(fh.WhoCreatedId),
            comment=str(si.Comment),
            sample_name=str(si.SampleName),
            sample_id=str(si.SampleId),
            sample_type=str(si.SampleType),
            vial=str(si.Vial),
            instrument_method=str(si.InstrumentMethod),
            tune_method=str(si.TuneMethod) if hasattr(si, "TuneMethod") else "",
            acquisition_software_version=str(fh.FileDescription) if hasattr(fh, "FileDescription") else "",
            instrument_name=str(idata.Name),
            instrument_serial_number=str(idata.SerialNumber),
            number_of_ms_orders=int(rh.MsOrderCount) if hasattr(rh, "MsOrderCount") else 0,
            has_ms_data=bool(rh.HasMsData) if hasattr(rh, "HasMsData") else True,
        )

    def get_scan_range(self) -> Tuple[int, int]:
        """
        Return ``(first_scan, last_scan)`` for the selected instrument.

        Returns
        -------
        tuple[int, int]
        """
        self._check_open()
        rh = self._raw_file.RunHeaderEx
        return int(rh.FirstSpectrum), int(rh.LastSpectrum)

    def get_start_time(self) -> float:
        """Return the acquisition start time in minutes."""
        self._check_open()
        return float(self._raw_file.RunHeaderEx.StartTime)

    def get_end_time(self) -> float:
        """Return the acquisition end time in minutes."""
        self._check_open()
        return float(self._raw_file.RunHeaderEx.EndTime)

    def get_instrument_method(self, index: int = 0) -> str:
        """
        Return the text of the instrument method at *index*.

        Parameters
        ----------
        index:
            0-based method index (most files have a single method at index 0).
        """
        self._check_open()
        return str(self._raw_file.GetInstrumentMethod(index))

    def get_all_instrument_names_from_method(self) -> List[str]:
        """Return the list of instrument names embedded in the method."""
        self._check_open()
        names = self._raw_file.GetAllInstrumentNamesFromInstrumentMethod()
        return [str(n) for n in names]

    # ------------------------------------------------------------------
    # Scan filters & events
    # ------------------------------------------------------------------

    def get_filters(self) -> List[str]:
        """Return all unique scan-filter strings present in the file."""
        self._check_open()
        return [str(f) for f in self._raw_file.GetFilters()]

    def get_filter_for_scan(self, scan_number: int) -> str:
        """Return the scan-filter string for *scan_number*."""
        self._check_open()
        self._check_scan(scan_number)
        return str(self._raw_file.GetFilterForScanNumber(scan_number))

    def get_scan_event_for_scan(self, scan_number: int) -> dict:
        """
        Return a dictionary of scan-event parameters for *scan_number*.

        Common keys: ``MSOrder``, ``Polarity``, ``ScanType``, ``Detector``,
        ``MassRangeCount``, ``Precursor*``.
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
            result["ScanEventNumber"] = int(ev.ScanEventNumber) if hasattr(ev, "ScanEventNumber") else None
        except Exception:
            pass
        return result

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
    # Retention time
    # ------------------------------------------------------------------

    def get_retention_time(self, scan_number: int) -> float:
        """Return the retention time in minutes for *scan_number*."""
        self._check_open()
        self._check_scan(scan_number)
        return float(self._raw_file.RetentionTimeFromScanNumber(scan_number))

    def scan_number_from_retention_time(self, retention_time: float) -> int:
        """Return the scan number closest to *retention_time* (minutes)."""
        self._check_open()
        return int(self._raw_file.ScanNumberFromRetentionTime(retention_time))

    # ------------------------------------------------------------------
    # Spectral data – centroid
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
            When ``True`` and profile data exist, the centroided view is still
            returned (the flag is forwarded to the .NET API as-is).
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
    # Spectral data – profile
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

        segments: List[Tuple[List[float], List[float]]] = []
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
        Return a consolidated :class:`ScanInfo` for *scan_number*, combining
        filter, event, stats, and trailer-extra data.

        Parameters
        ----------
        scan_number:
            1-based scan number.
        """
        self._check_open()
        self._check_scan(scan_number)

        filter_str = str(self._raw_file.GetFilterForScanNumber(scan_number))
        ev = self._raw_file.GetScanEventForScanNumber(scan_number)
        stats = self._raw_file.GetScanStatsForScanNumber(scan_number)
        rt = float(self._raw_file.RetentionTimeFromScanNumber(scan_number))

        ms_order = int(ev.MSOrder)
        is_centroid = "FTMS" in filter_str.upper() or "FT" in filter_str.upper()
        detector = str(ev.Detector) if hasattr(ev, "Detector") else ""
        activation = ""

        # Trailer extra for injection time, precursor info, etc.
        trailer = self._get_trailer_dict(scan_number)
        inj_time = float(trailer.get("Ion Injection Time (ms)", 0.0) or 0.0)
        precursor_mass: Optional[float] = None
        precursor_charge: Optional[int] = None
        collision_energy: Optional[float] = None
        isolation_width: Optional[float] = None
        monoisotopic_mass: Optional[float] = None

        if ms_order >= 2:
            try:
                precursor_mass = float(trailer.get("Monoisotopic M/Z:", 0.0) or 0.0) or None
                if precursor_mass is None:
                    # fall back to scan event precursor
                    pm = ev.GetReaction(0).PrecursorMass
                    precursor_mass = float(pm)
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
            activation_type=activation,
            precursor_mass=precursor_mass,
            precursor_charge=precursor_charge,
            collision_energy=collision_energy,
            isolation_width=isolation_width,
            monoisotopic_mass=monoisotopic_mass,
            ion_injection_time=inj_time or None,
        )

    # ------------------------------------------------------------------
    # Averaged spectra
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

        opts = self._raw_file.DefaultMassOptions()
        if filter_string:
            from ThermoFisher.CommonCore.Data.FilterEnums import MassAnalyzerType  # type: ignore
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

    def average_scans(self, scan_numbers: List[int]) -> AveragedScan:
        """
        Average the spectra for an arbitrary list of *scan_numbers*.

        Parameters
        ----------
        scan_numbers:
            List of 1-based scan numbers to average.
        """
        self._check_open()
        opts = self._raw_file.DefaultMassOptions()

        from System.Collections.Generic import List as DotNetList  # type: ignore
        from System import Int32  # type: ignore

        dn_list = DotNetList[Int32]()
        for s in scan_numbers:
            dn_list.Add(Int32(s))

        avg = self._raw_file.AverageScans(dn_list, opts)

        masses = [float(m) for m in avg.PreferredMasses] if avg.PreferredMasses else []
        intensities = [float(i) for i in avg.PreferredIntensities] if avg.PreferredIntensities else []

        first = min(scan_numbers)
        last = max(scan_numbers)
        return AveragedScan(first_scan=first, last_scan=last, masses=masses, intensities=intensities)

    # ------------------------------------------------------------------
    # Chromatograms
    # ------------------------------------------------------------------

    def get_chromatogram(
        self,
        trace_type: str = "BasePeak",
        mass_range: str = "",
        start_scan: int = -1,
        end_scan: int = -1,
    ) -> ChromatogramData:
        """
        Extract a chromatogram trace from the file.

        Parameters
        ----------
        trace_type:
            One of ``"BasePeak"``, ``"TIC"``, ``"MassRange"``,
            ``"EIC"`` (extracted ion), ``"NeutralLoss"``.
        mass_range:
            Mass range string for ``"MassRange"`` / ``"EIC"`` traces,
            e.g. ``"500.0-510.0"``.
        start_scan, end_scan:
            Scan range. Use ``-1`` for the full file range.
        """
        self._check_open()
        from ThermoFisher.CommonCore.Data.Business import (  # type: ignore
            ChromatogramTraceSettings,
            TraceType,
        )
        from ThermoFisher.CommonCore.Data.FilterEnums import ChromatogramFormat  # type: ignore
        from ThermoFisher.CommonCore.Data import Business  # type: ignore

        trace_map = {
            "BasePeak": TraceType.BasePeak,
            "TIC": TraceType.TIC,
            "MassRange": TraceType.MassRange,
            "EIC": TraceType.MassRange,
            "NeutralLoss": TraceType.NeutralLoss,
        }
        dn_trace = trace_map.get(trace_type, TraceType.BasePeak)

        settings = ChromatogramTraceSettings(dn_trace)
        if mass_range:
            settings.Filter = mass_range

        first, last = self.get_scan_range()
        s0 = start_scan if start_scan > 0 else first
        s1 = end_scan if end_scan > 0 else last

        from System import Array  # type: ignore
        settings_array = Array[ChromatogramTraceSettings]([settings])
        data = self._raw_file.GetChromatogramData(settings_array, s0, s1)

        from ThermoFisher.CommonCore.Data.Business import ChromatogramSignal  # type: ignore
        signals = ChromatogramSignal.FromChromatogramData(data)
        sig = signals[0]

        times = [float(t) for t in sig.Times] if sig.Times else []
        intensities = [float(i) for i in sig.Intensities] if sig.Intensities else []

        return ChromatogramData(
            trace_type=trace_type,
            mass_range=mass_range,
            times=times,
            intensities=intensities,
        )

    # ------------------------------------------------------------------
    # Trailer extra data
    # ------------------------------------------------------------------

    def _get_trailer_dict(self, scan_number: int) -> dict:
        """Return a raw key->value dict for trailer-extra data (internal)."""
        try:
            trailer = self._raw_file.GetTrailerExtraInformation(scan_number)
            result = {}
            for label, value in zip(trailer.Labels, trailer.Values):
                result[str(label)] = str(value)
            return result
        except Exception:
            return {}

    def get_trailer_data(self, scan_number: int) -> TrailerData:
        """
        Return trailer-extra (auxiliary) data for *scan_number*.

        Trailer data contains additional scan metadata such as ion injection
        time, charge state, monoisotopic mass, AGC, and more.

        Parameters
        ----------
        scan_number:
            1-based scan number.
        """
        self._check_open()
        self._check_scan(scan_number)
        fields = self._get_trailer_dict(scan_number)
        return TrailerData(scan_number=scan_number, fields=fields)

    def get_trailer_header_info(self) -> List[str]:
        """Return the list of all trailer-extra field labels defined in the file."""
        self._check_open()
        headers = self._raw_file.GetTrailerExtraHeaderInformation()
        return [str(h.Label) for h in headers]

    # ------------------------------------------------------------------
    # Status log
    # ------------------------------------------------------------------

    def get_status_log_header_info(self) -> List[str]:
        """Return all status-log field labels defined in the file."""
        self._check_open()
        headers = self._raw_file.GetStatusLogHeaderInformation()
        return [str(h.Label) for h in headers]

    def get_status_log_for_retention_time(self, retention_time: float) -> StatusLogEntry:
        """
        Return the status log entry closest to *retention_time* (minutes).

        Parameters
        ----------
        retention_time:
            Retention time in minutes.
        """
        self._check_open()
        log = self._raw_file.GetStatusLogForRetentionTime(retention_time)
        fields = {}
        try:
            for label, value in zip(log.Labels, log.Values):
                fields[str(label)] = str(value)
        except Exception:
            pass
        return StatusLogEntry(retention_time=retention_time, fields=fields)

    def get_status_log_for_scan(self, scan_number: int) -> StatusLogEntry:
        """Return the status log entry for *scan_number*."""
        rt = self.get_retention_time(scan_number)
        return self.get_status_log_for_retention_time(rt)

    # ------------------------------------------------------------------
    # Scan dependents
    # ------------------------------------------------------------------

    def get_scan_dependents(
        self, scan_number: int, depth: int = 1
    ) -> ScanDependent:
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
        Estimate mass precision (accuracy in ppm / mmu) for each peak in
        *scan_number*.

        Requires the ``ThermoFisher.CommonCore.MassPrecisionEstimator`` assembly.

        Parameters
        ----------
        scan_number:
            1-based scan number (must be an FTMS / Orbitrap scan).
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

        scan = self._raw_file.GetCentroidStream(scan_number, False)
        estimates = PrecisionEstimate.GetMassPrecisionEstimate(scan, self._raw_file, scan_number)

        result: List[MassPrecision] = []
        for e in estimates:
            result.append(
                MassPrecision(
                    mass=float(e.Mass),
                    intensity=float(e.Intensity),
                    resolution=float(e.Resolution),
                    mz_accuracy_mass=float(e.MZAccuracyInPPM),
                    mz_accuracy_mmu=float(e.MZAccuracyInMMU),
                )
            )
        return result

    # ------------------------------------------------------------------
    # Bulk scan iteration helpers
    # ------------------------------------------------------------------

    def iter_scan_info(self, ms_order: Optional[int] = None) -> Iterator[ScanInfo]:
        """
        Yield :class:`ScanInfo` for every scan in the file.

        Parameters
        ----------
        ms_order:
            When given, only scans of this MS order are yielded
            (e.g. ``1`` for MS1, ``2`` for MS2).
        """
        first, last = self.get_scan_range()
        for scan in range(first, last + 1):
            info = self.get_scan_info(scan)
            if ms_order is not None and info.ms_order != ms_order:
                continue
            yield info

    def iter_centroid_data(
        self, ms_order: Optional[int] = None
    ) -> Iterator[CentroidData]:
        """
        Yield :class:`CentroidData` for every (centroid) scan in the file.

        Parameters
        ----------
        ms_order:
            Filter by MS order if given.
        """
        first, last = self.get_scan_range()
        for scan in range(first, last + 1):
            filt = self.get_filter_for_scan(scan)
            ev = self._raw_file.GetScanEventForScanNumber(scan)
            if ms_order is not None and int(ev.MSOrder) != ms_order:
                continue
            yield self.get_centroid_stream(scan)

    def analyze_all_scans(self) -> Dict[str, int]:
        """
        Walk every scan and verify that masses within each scan are ordered
        (ascending).  Returns a summary dict with ``total``, ``centroid``,
        ``profile``, and ``out_of_order`` counts.
        """
        self._check_open()
        first, last = self.get_scan_range()
        total = centroid = profile = out_of_order = 0

        for scan in range(first, last + 1):
            total += 1
            stats = self._raw_file.GetScanStatsForScanNumber(scan)
            filt = str(self._raw_file.GetFilterForScanNumber(scan))
            is_ft = "FTMS" in filt.upper()

            if is_ft:
                centroid += 1
                cs = self._raw_file.GetCentroidStream(scan, False)
                masses = [float(m) for m in cs.Masses] if cs.Masses else []
            else:
                profile += 1
                seg = self._raw_file.GetSegmentedScanFromScanNumber(scan, stats)
                masses = [float(p) for p in seg.Positions] if seg and seg.Positions else []

            for i in range(1, len(masses)):
                if masses[i] < masses[i - 1]:
                    out_of_order += 1
                    break

        return {
            "total": total,
            "centroid": centroid,
            "profile": profile,
            "out_of_order": out_of_order,
        }

    # ------------------------------------------------------------------
    # Spectral subtraction
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
        Subtract the spectrum of *scan_b* from *scan_a* (A − B).

        Both scans must share the **same scan filter string** (same analyzer,
        polarity, MS order, and mass range).  Subtraction is performed in
        centroid space when either scan is a centroid scan, and in profile
        space when both are profile scans.

        Parameters
        ----------
        scan_a:
            1-based scan number of the minuend (the scan to subtract *from*).
        scan_b:
            1-based scan number of the subtrahend (the scan being subtracted).
        mass_range:
            Optional ``(low_mz, high_mz)`` tuple to restrict the output to a
            sub-range of the spectrum.  Peaks / data points outside this range
            are discarded before subtraction.
        mass_tolerance_ppm:
            Matching tolerance (in ppm) used when aligning centroid peaks from
            the two scans.  Ignored for profile subtraction.
        normalize:
            When ``True`` each spectrum is divided by its total ion current
            before subtraction, making the result relative rather than
            absolute.

        Returns
        -------
        SubtractedSpectrum
            Contains ``masses``, signed ``intensities`` (A − B), and
            ``intensities_clipped`` (negatives zeroed).  Use the ``peaks``
            property to iterate only the surviving (positive) peaks.

        Raises
        ------
        ScanNotFoundError
            If either scan number is outside the valid range.
        ValueError
            If the two scans have different scan filter strings.
        """
        self._check_open()
        self._check_scan(scan_a)
        self._check_scan(scan_b)

        filter_a = str(self._raw_file.GetFilterForScanNumber(scan_a))
        filter_b = str(self._raw_file.GetFilterForScanNumber(scan_b))
        if filter_a != filter_b:
            raise ValueError(
                f"Cannot subtract scans with different filters.\n"
                f"  scan {scan_a}: {filter_a!r}\n"
                f"  scan {scan_b}: {filter_b!r}"
            )

        is_centroid_a = "FTMS" in filter_a.upper()
        is_centroid_b = "FTMS" in filter_b.upper()
        use_centroid = is_centroid_a or is_centroid_b

        if use_centroid:
            result = self._subtract_centroid(
                scan_a, scan_b, mass_range, mass_tolerance_ppm, normalize
            )
        else:
            result = self._subtract_profile(
                scan_a, scan_b, mass_range, normalize
            )

        masses, intensities = result
        intensities_clipped = [max(0.0, v) for v in intensities]

        return SubtractedSpectrum(
            scan_a=scan_a,
            scan_b=scan_b,
            scan_filter=filter_a,
            mass_range=mass_range,
            is_centroid=use_centroid,
            masses=masses,
            intensities=intensities,
            intensities_clipped=intensities_clipped,
        )

    # --- centroid subtraction helpers ------------------------------------

    def _subtract_centroid(
        self,
        scan_a: int,
        scan_b: int,
        mass_range: Optional[Tuple[float, float]],
        tol_ppm: float,
        normalize: bool,
    ) -> Tuple[List[float], List[float]]:
        """Match peaks by m/z within *tol_ppm* and subtract intensities."""
        cs_a = self._raw_file.GetCentroidStream(scan_a, False)
        cs_b = self._raw_file.GetCentroidStream(scan_b, False)

        masses_a = [float(m) for m in cs_a.Masses] if cs_a.Masses else []
        inten_a  = [float(i) for i in cs_a.Intensities] if cs_a.Intensities else []
        masses_b = [float(m) for m in cs_b.Masses] if cs_b.Masses else []
        inten_b  = [float(i) for i in cs_b.Intensities] if cs_b.Intensities else []

        # Apply mass range filter
        masses_a, inten_a = _apply_mass_range(masses_a, inten_a, mass_range)
        masses_b, inten_b = _apply_mass_range(masses_b, inten_b, mass_range)

        # Optional TIC normalisation
        if normalize:
            inten_a = _normalize_to_tic(inten_a)
            inten_b = _normalize_to_tic(inten_b)

        # Build a fast lookup for scan_b peaks: mass -> intensity
        # For each scan_a peak, find the closest scan_b peak within tolerance.
        # Unmatched scan_b peaks are subtracted as stand-alone negative entries.
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

        # Peaks only in scan_b → appear as negative entries in the result
        for idx, (m_b, i_b) in enumerate(zip(masses_b, inten_b)):
            if not matched_b[idx]:
                out_masses.append(m_b)
                out_intensities.append(-i_b)

        # Re-sort by mass
        pairs = sorted(zip(out_masses, out_intensities), key=lambda x: x[0])
        if pairs:
            out_masses, out_intensities = zip(*pairs)
            return list(out_masses), list(out_intensities)
        return [], []

    # --- profile subtraction helpers -------------------------------------

    def _subtract_profile(
        self,
        scan_a: int,
        scan_b: int,
        mass_range: Optional[Tuple[float, float]],
        normalize: bool,
    ) -> Tuple[List[float], List[float]]:
        """
        Subtract profile spectra by interpolating scan_b onto scan_a's m/z grid.
        """
        stats_a = self._raw_file.GetScanStatsForScanNumber(scan_a)
        stats_b = self._raw_file.GetScanStatsForScanNumber(scan_b)
        seg_a = self._raw_file.GetSegmentedScanFromScanNumber(scan_a, stats_a)
        seg_b = self._raw_file.GetSegmentedScanFromScanNumber(scan_b, stats_b)

        masses_a  = [float(p) for p in seg_a.Positions]  if seg_a and seg_a.Positions  else []
        inten_a   = [float(i) for i in seg_a.Intensities] if seg_a and seg_a.Intensities else []
        masses_b  = [float(p) for p in seg_b.Positions]  if seg_b and seg_b.Positions  else []
        inten_b   = [float(i) for i in seg_b.Intensities] if seg_b and seg_b.Intensities else []

        masses_a, inten_a = _apply_mass_range(masses_a, inten_a, mass_range)
        masses_b, inten_b = _apply_mass_range(masses_b, inten_b, mass_range)

        if normalize:
            inten_a = _normalize_to_tic(inten_a)
            inten_b = _normalize_to_tic(inten_b)

        # Interpolate scan_b intensities at scan_a positions
        inten_b_interp = _linear_interp(masses_a, masses_b, inten_b)
        out_intensities = [a - b for a, b in zip(inten_a, inten_b_interp)]

        return masses_a, out_intensities

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        state = "open" if self.is_open() else "closed"
        return f"RawFileAdapter({os.path.basename(self._path)!r}, {state})"
