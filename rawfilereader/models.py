"""
Data models (plain Python dataclasses) returned by the RawFileAdapter.
All values are converted from .NET types to native Python types here so
callers never need to touch pythonnet objects directly.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class FileInfo:
    """File-header-level metadata about the RAW file."""
    file_name: str
    creation_date: str
    operator: str
    comment: str
    acquisition_software_version: str
    instrument_name: str
    instrument_serial_number: str
    number_of_ms_orders: int
    has_ms_data: bool
    # Optional extended fields from IFileHeader / IRawDataProperties
    file_description: Optional[str] = None
    file_type: Optional[str] = None
    revision: Optional[int] = None
    modified_date: Optional[str] = None
    computer_name: Optional[str] = None
    path: Optional[str] = None
    who_created_logon: Optional[str] = None
    who_modified_logon: Optional[str] = None
    number_of_times_calibrated: Optional[int] = None
    number_of_times_modified: Optional[int] = None


@dataclass
class SampleInfo:
    """Full sample information record (SampleInformation in the .NET API)."""
    sample_name: str
    sample_id: str
    sample_type: str
    vial: str
    comment: str
    barcode: str
    barcode_status: str
    calibration_level: str
    calibration_file: str
    dilution_factor: float
    injection_volume: float
    istd_amount: float
    row_number: int
    sample_volume: float
    sample_weight: float
    path: str
    processing_method_file: str
    instrument_method_file: str
    raw_file_name: str
    user_text: List[str] = field(default_factory=list)


@dataclass
class AutoSamplerInfo:
    """Autosampler tray and vial geometry (IAutoSamplerInformation in the .NET API)."""
    tray_index: int
    vial_index: int
    vials_per_tray: int
    vials_per_tray_x: int
    vials_per_tray_y: int
    tray_shape: str
    tray_name: str


@dataclass
class InstrumentInfo:
    """Per-device instrument metadata."""
    device_type: str
    instance_number: int
    name: str
    model: str
    serial_number: str
    software_version: str
    hardware_version: str
    units: str
    channel_labels: List[str] = field(default_factory=list)


@dataclass
class ScanStats:
    """Statistics for a single scan."""
    scan_number: int
    start_time: float
    low_mass: float
    high_mass: float
    tic: float
    base_peak_mass: float
    base_peak_intensity: float
    packet_count: int
    scan_event_number: int
    master_index: int
    is_centroid_scan: bool


@dataclass
class CentroidData:
    """Centroid (peak-picked) mass spectrum data."""
    scan_number: int
    masses: List[float]
    intensities: List[float]
    charges: List[float]
    baselines: List[float]
    noises: List[float]
    resolutions: List[float]
    is_exceptional: bool
    is_reference: bool

    @property
    def peaks(self) -> List[Tuple[float, float]]:
        """Return (mass, intensity) tuples for all peaks."""
        return list(zip(self.masses, self.intensities))


@dataclass
class ProfileData:
    """Profile (raw) mass spectrum data, as segmented arrays."""
    scan_number: int
    segments: List[Tuple[List[float], List[float]]] = field(default_factory=list)

    @property
    def masses(self) -> List[float]:
        """Flatten all segment positions into a single list."""
        result: List[float] = []
        for pos, _ in self.segments:
            result.extend(pos)
        return result

    @property
    def intensities(self) -> List[float]:
        """Flatten all segment intensities into a single list."""
        result: List[float] = []
        for _, inten in self.segments:
            result.extend(inten)
        return result


@dataclass
class ScanInfo:
    """High-level metadata about a single scan."""
    scan_number: int
    scan_filter: str
    ms_order: int
    retention_time: float
    injection_time: float
    is_centroid: bool
    detector_type: str
    activation_type: str
    precursor_mass: Optional[float] = None
    precursor_charge: Optional[int] = None
    collision_energy: Optional[float] = None
    isolation_width: Optional[float] = None
    monoisotopic_mass: Optional[float] = None
    ion_injection_time: Optional[float] = None


@dataclass
class ChromatogramData:
    """A single chromatogram trace."""
    trace_type: str
    mass_range: str
    times: List[float]
    intensities: List[float]


@dataclass
class TrailerData:
    """Trailer-extra (auxiliary) data appended to a scan."""
    scan_number: int
    fields: dict


@dataclass
class StatusLogEntry:
    """One row from the instrument status log."""
    retention_time: float
    fields: dict


@dataclass
class ScanDependent:
    """Relationship between a parent scan and its dependent (MS^n) scans."""
    scan_number: int
    dependent_scan_numbers: List[int]


@dataclass
class MassPrecision:
    """Mass accuracy / precision estimate for a single peak."""
    mass: float
    intensity: float
    resolution: float
    mz_accuracy_ppm: float
    mz_accuracy_mmu: float


@dataclass
class AveragedScan:
    """Result from averaging multiple scans."""
    first_scan: int
    last_scan: int
    masses: List[float]
    intensities: List[float]
    time_range: Optional[Tuple[float, float]] = None


@dataclass
class BackgroundSubtractedSpectrum:
    """
    Result of background subtraction using the Thermo Fisher BackgroundSubtractor.

    Requires ``ThermoFisher.CommonCore.BackgroundSubtraction.dll``.
    """
    scan_number: int
    background_scans: List[int]
    scan_filter: str
    masses: List[float]
    intensities: List[float]

    @property
    def peaks(self) -> List[Tuple[float, float]]:
        """Return ``(mass, intensity)`` tuples for all peaks."""
        return list(zip(self.masses, self.intensities))


@dataclass
class TuneData:
    """Instrument tune data for one tune segment."""
    index: int
    labels: List[str]
    values: List[str]


@dataclass
class ErrorLogEntry:
    """One entry from the instrument error log."""
    index: int
    retention_time: float
    error_message: str


@dataclass
class RunHeaderInfo:
    """
    Extended run-header metadata (IRunHeader / IRunHeaderAccess).

    Returned by :meth:`~rawfilereader.RawFileAdapter.get_run_header_info`.
    """
    first_scan: int
    last_scan: int
    start_time: float
    end_time: float
    low_mass: float
    high_mass: float
    mass_resolution: float
    max_intensity: float
    max_integrated_intensity: float
    spectra_count: int
    status_log_count: int
    error_log_count: int
    trailer_extra_count: int
    tune_data_count: int
    expected_run_time: float
    comment1: str
    comment2: str
    in_acquisition: bool
    tolerance_unit: str
    filter_mass_precision: Optional[int] = None
    writer_protocol: Optional[int] = None


@dataclass
class RawFileError:
    """
    Detailed error information from IRawDataPlus.FileError.

    Returned by :meth:`~rawfilereader.RawFileAdapter.get_file_error`.
    """
    has_error: bool
    error_code: int
    error_message: str
