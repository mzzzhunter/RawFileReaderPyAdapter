# RawFileReader Python Adapter — API Reference

Complete reference for all data models and adapter methods exposed by
`rawfilereader` v2.0.0.  Every method is a thin Python wrapper around a
specific Thermo Fisher RawFileReader .NET DLL call.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Exception Hierarchy](#exception-hierarchy)
3. [Data Models](#data-models)
4. [RawFileAdapter Methods](#rawfileadapter-methods)
   - [Lifecycle](#lifecycle)
   - [Instrument Selection](#instrument-selection)
   - [File & Run Headers](#file--run-headers)
   - [Sample & Autosampler Info](#sample--autosampler-info)
   - [Scan Data](#scan-data)
   - [Scan Filters & Enumerators](#scan-filters--enumerators)
   - [Chromatograms](#chromatograms)
   - [Logs & Diagnostics](#logs--diagnostics)
   - [Scan Averaging & Background Subtraction](#scan-averaging--background-subtraction)
5. [RawFileThreadManager](#rawfilethreadmanager)

---

## Quick Start

```python
from rawfilereader import RawFileAdapter

with RawFileAdapter("sample.raw") as rf:
    fi = rf.get_file_info()
    first, last = rf.get_scan_range()
    centroid = rf.get_centroid_stream(1)
    tic = rf.get_chromatogram(trace_type="TIC")
```

---

## Exception Hierarchy

All exceptions inherit from `RawFileError`.

| Exception | Raised when |
|---|---|
| `RawFileError` | Base class |
| `RawFileNotOpenError` | Method called on a closed file, or file cannot be opened |
| `RawFileInAcquisitionError` | File is still being written by the instrument |
| `InstrumentSelectionError` | Requested device type or instance does not exist |
| `ScanNotFoundError` | Scan number is outside `[first_scan, last_scan]` |
| `AssemblyLoadError` | DLL not found or pythonnet not installed |

---

## Data Models

All public methods return plain Python dataclasses — no .NET objects are
exposed to the caller.

---

### `FileInfo`

Returned by `get_file_info()`.  File-header-level metadata.

| Field | Type | Description |
|---|---|---|
| `file_name` | `str` | Full path to the RAW file |
| `creation_date` | `str` | Acquisition timestamp |
| `operator` | `str` | Operator / analyst name |
| `comment` | `str` | Free-text comment |
| `acquisition_software_version` | `str` | Xcalibur / Tune software version |
| `instrument_name` | `str` | Instrument display name |
| `instrument_serial_number` | `str` | Instrument serial number |
| `number_of_ms_orders` | `int` | Highest MS order present |
| `has_ms_data` | `bool` | Whether the file contains MS scans |

---

### `SampleInfo`

Returned by `get_sample_info()`.  Full `SampleInformation` record.

| Field | Type | Description |
|---|---|---|
| `sample_name` | `str` | Sample name |
| `sample_id` | `str` | Sample identifier |
| `sample_type` | `str` | Sample type string |
| `vial` | `str` | Vial position |
| `comment` | `str` | Sample comment |
| `barcode` | `str` | Barcode string |
| `barcode_status` | `str` | Barcode read status |
| `calibration_level` | `str` | Calibration level |
| `calibration_file` | `str` | Path to calibration file |
| `dilution_factor` | `float` | Dilution factor |
| `injection_volume` | `float` | Injection volume (µL) |
| `istd_amount` | `float` | Internal standard amount |
| `row_number` | `int` | Sample row number in the sequence |
| `sample_volume` | `float` | Sample volume |
| `sample_weight` | `float` | Sample weight |
| `path` | `str` | Data path |
| `processing_method_file` | `str` | Processing method file path |
| `instrument_method_file` | `str` | Instrument method file path |
| `raw_file_name` | `str` | RAW file name (from header) |
| `user_text` | `List[str]` | User-defined text fields |

---

### `AutoSamplerInfo`

Returned by `get_autosampler_info()`.  Autosampler tray geometry.

| Field | Type | Description |
|---|---|---|
| `tray_index` | `int` | Tray index |
| `vial_index` | `int` | Vial index within the tray |
| `vials_per_tray` | `int` | Total vials per tray |
| `vials_per_tray_x` | `int` | Tray columns |
| `vials_per_tray_y` | `int` | Tray rows |
| `tray_shape` | `str` | Tray shape descriptor |
| `tray_name` | `str` | Tray name |

---

### `InstrumentInfo`

Returned by `get_instrument_data()`.  Per-device metadata.

| Field | Type | Description |
|---|---|---|
| `device_type` | `str` | Device type string (e.g. `"MS"`, `"UV"`) |
| `instance_number` | `int` | 1-based instance number |
| `name` | `str` | Instrument name |
| `model` | `str` | Instrument model |
| `serial_number` | `str` | Serial number |
| `software_version` | `str` | Firmware / software version |
| `hardware_version` | `str` | Hardware revision |
| `units` | `str` | Signal units |
| `channel_labels` | `List[str]` | Channel label strings |

---

### `ScanStats`

Returned by `get_scan_stats()`.  Per-scan statistics from `GetScanStatsForScanNumber`.

| Field | Type | Description |
|---|---|---|
| `scan_number` | `int` | 1-based scan number |
| `start_time` | `float` | Retention time of the scan (min) |
| `low_mass` | `float` | Low m/z boundary |
| `high_mass` | `float` | High m/z boundary |
| `tic` | `float` | Total ion current |
| `base_peak_mass` | `float` | m/z of the base peak |
| `base_peak_intensity` | `float` | Intensity of the base peak |
| `packet_count` | `int` | Number of data packets |
| `scan_event_number` | `int` | Scan event index |
| `master_index` | `int` | Master scan index |
| `is_centroid_scan` | `bool` | Whether the scan is centroid mode |

---

### `CentroidData`

Returned by `get_centroid_stream()`.  Peak-picked mass spectrum from `GetCentroidStream`.

| Field | Type | Description |
|---|---|---|
| `scan_number` | `int` | 1-based scan number |
| `masses` | `List[float]` | Peak m/z values |
| `intensities` | `List[float]` | Peak intensities |
| `charges` | `List[float]` | Per-peak charge states |
| `baselines` | `List[float]` | Per-peak baseline values |
| `noises` | `List[float]` | Per-peak noise values |
| `resolutions` | `List[float]` | Per-peak resolution values |
| `is_exceptional` | `bool` | Exceptional scan flag |
| `is_reference` | `bool` | Reference scan flag |

**Convenience property**

| Property | Returns | Description |
|---|---|---|
| `.peaks` | `List[Tuple[float, float]]` | `(mass, intensity)` pairs |

---

### `ProfileData`

Returned by `get_profile_data()`.  Raw (continuous) spectrum from `GetSegmentedScanFromScanNumber`.

| Field | Type | Description |
|---|---|---|
| `scan_number` | `int` | 1-based scan number |
| `segments` | `List[Tuple[List[float], List[float]]]` | List of `(positions, intensities)` segment pairs |

**Convenience properties**

| Property | Returns | Description |
|---|---|---|
| `.masses` | `List[float]` | All segment positions flattened |
| `.intensities` | `List[float]` | All segment intensities flattened |

---

### `ScanInfo`

Returned by `get_scan_info()`.  Consolidated scan metadata from filter, event, stats, and trailer.

| Field | Type | Description |
|---|---|---|
| `scan_number` | `int` | 1-based scan number |
| `scan_filter` | `str` | Full scan filter string |
| `ms_order` | `int` | MS order (1 = MS1, 2 = MS2, …) |
| `retention_time` | `float` | Retention time (min) |
| `injection_time` | `float` | Ion injection time (ms) |
| `is_centroid` | `bool` | Whether the scan is centroid mode |
| `detector_type` | `str` | Detector type string |
| `activation_type` | `str` | Fragmentation type |
| `precursor_mass` | `Optional[float]` | Precursor m/z (MS2+) |
| `precursor_charge` | `Optional[int]` | Precursor charge state (MS2+) |
| `collision_energy` | `Optional[float]` | Collision energy in eV (MS2+) |
| `isolation_width` | `Optional[float]` | Isolation window width (MS2+) |
| `monoisotopic_mass` | `Optional[float]` | Monoisotopic precursor m/z (MS2+) |
| `ion_injection_time` | `Optional[float]` | Ion injection time from trailer (ms) |

---

### `ChromatogramData`

Returned by `get_chromatogram()` and `get_chromatogram_ex()`.

| Field | Type | Description |
|---|---|---|
| `trace_type` | `str` | Trace type string (e.g. `"TIC"`, `"BasePeak"`, `"MassRange"`) |
| `mass_range` | `str` | Mass range string used (e.g. `"500.0-510.0"`) |
| `times` | `List[float]` | Retention time axis (min) |
| `intensities` | `List[float]` | Intensity axis |

---

### `TrailerData`

Returned by `get_trailer_data()`.  Auxiliary scan metadata from `GetTrailerExtraInformation`.

| Field | Type | Description |
|---|---|---|
| `scan_number` | `int` | 1-based scan number |
| `fields` | `dict` | Key-value pairs of all trailer-extra labels and values |

Common trailer keys: `"Ion Injection Time (ms)"`, `"Charge State:"`,
`"Monoisotopic M/Z:"`, `"AGC:"`.

---

### `StatusLogEntry`

Returned by `get_status_log_for_scan()`, `get_status_log_for_retention_time()`, and `get_status_log_at_position()`.

| Field | Type | Description |
|---|---|---|
| `retention_time` | `float` | Retention time of the log entry (min) |
| `fields` | `dict` | Key-value pairs of instrument status values |

---

### `ScanDependent`

Returned by `get_scan_dependents()`.  MS^n parent–child scan relationship.

| Field | Type | Description |
|---|---|---|
| `scan_number` | `int` | Parent scan number |
| `dependent_scan_numbers` | `List[int]` | Direct child scan numbers |

---

### `MassPrecision`

Returned (as a list) by `get_mass_precision()`.  Per-peak accuracy estimate from
`PrecisionEstimate.GetMassPrecisionEstimate`.

| Field | Type | Description |
|---|---|---|
| `mass` | `float` | Peak m/z |
| `intensity` | `float` | Peak intensity |
| `resolution` | `float` | Peak resolution |
| `mz_accuracy_mass` | `float` | m/z accuracy in ppm |
| `mz_accuracy_mmu` | `float` | m/z accuracy in mmu |

---

### `AveragedScan`

Returned by `average_scans_in_range()`, `average_scans()`, and
`average_scans_in_time_range()`.

| Field | Type | Description |
|---|---|---|
| `first_scan` | `int` | First scan in the averaged range |
| `last_scan` | `int` | Last scan in the averaged range |
| `masses` | `List[float]` | Averaged m/z values |
| `intensities` | `List[float]` | Averaged intensities |
| `time_range` | `Optional[Tuple[float, float]]` | `(start_time, end_time)` in min — set by `average_scans_in_time_range` only |

---

### `BackgroundSubtractedSpectrum`

Returned by `subtract_background()`.  Requires `ThermoFisher.CommonCore.BackgroundSubtraction.dll`.

| Field | Type | Description |
|---|---|---|
| `scan_number` | `int` | Foreground scan number |
| `background_scans` | `List[int]` | Background scan numbers used |
| `scan_filter` | `str` | Filter string of the foreground scan |
| `masses` | `List[float]` | Resulting m/z values |
| `intensities` | `List[float]` | Resulting intensities |

**Convenience property**

| Property | Returns | Description |
|---|---|---|
| `.peaks` | `List[Tuple[float, float]]` | `(mass, intensity)` pairs |

---

### `TuneData`

Returned by `get_tune_data()`.  Instrument tune data for one segment.

| Field | Type | Description |
|---|---|---|
| `index` | `int` | 0-based tune segment index |
| `labels` | `List[str]` | Tune parameter names |
| `values` | `List[str]` | Tune parameter values (as strings) |

---

### `ErrorLogEntry`

Returned by `get_error_log_entry()`.  One entry from the instrument error log.

| Field | Type | Description |
|---|---|---|
| `index` | `int` | 0-based index |
| `retention_time` | `float` | Retention time when the error occurred (min) |
| `error_message` | `str` | Error message text |

---

## RawFileAdapter Methods

### Lifecycle

#### `RawFileAdapter(raw_file_path, libs_dir=None)`

Open a RAW file.  Prefer the context-manager form:

```python
with RawFileAdapter("sample.raw") as rf:
    ...
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `raw_file_path` | `str` | — | Path to the `.raw` file |
| `libs_dir` | `str \| None` | `None` | Override DLL search directory |

#### `open()` / `close()`

Explicit open/close.  `open()` is called automatically by `__enter__`.

#### `is_open` *(property)*

Returns `True` if the file is currently open.

---

### Instrument Selection

#### `select_instrument(device_type, instance=1)`

Select an instrument device for subsequent calls.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `device_type` | `str` | — | `"MS"`, `"UV"`, `"PDA"`, `"Analog"`, `"MSAnalog"` |
| `instance` | `int` | `1` | 1-based device instance |

.NET call: `SelectInstrument`

#### `get_instrument_count() → int`

Total number of instrument devices in the file.
.NET call: `InstrumentCount`

#### `get_instrument_count_of_type(device_type) → int`

Number of devices of a specific type.
.NET call: `GetInstrumentCountOfType`

#### `get_instrument_type(index) → str`

Device-type string for the 0-based `index`.
.NET call: `GetInstrumentType`

---

### File & Run Headers

#### `get_file_info() → FileInfo`

File-header metadata (operator, creation date, instrument name/serial).
.NET calls: `FileHeader`, `RunHeaderEx`, `GetInstrumentData`

#### `get_scan_range() → Tuple[int, int]`

Returns `(first_scan, last_scan)` for the selected instrument.
.NET call: `RunHeaderEx.FirstSpectrum / LastSpectrum`

#### `get_start_time() → float`

Acquisition start time in minutes.
.NET call: `RunHeaderEx.StartTime`

#### `get_end_time() → float`

Acquisition end time in minutes.
.NET call: `RunHeaderEx.EndTime`

#### `get_instrument_method(index=0) → str`

Text of the embedded instrument method at `index`.
.NET call: `GetInstrumentMethod`

#### `get_instrument_method_count() → int`

Number of embedded instrument methods.
.NET call: `InstrumentMethodsCount`

#### `get_all_instrument_names_from_method() → List[str]`

Instrument names listed in the embedded method.
.NET call: `GetAllInstrumentNamesFromInstrumentMethod`

#### `get_instrument_data() → InstrumentInfo`

Metadata for the currently selected device.
.NET call: `GetInstrumentData`

---

### Sample & Autosampler Info

#### `get_sample_info() → SampleInfo`

Full `SampleInformation` record — name, vial, injection volume, barcode, etc.
.NET call: `SampleInformation`

#### `get_autosampler_info() → AutoSamplerInfo`

Tray index, vial index, and tray dimensions.
.NET call: `AutoSamplerInformation`

---

### Scan Data

#### `get_retention_time(scan_number) → float`

Retention time in minutes for a scan.
.NET call: `RetentionTimeFromScanNumber`

#### `scan_number_from_retention_time(retention_time) → int`

Nearest scan number to a given retention time.
.NET call: `ScanNumberFromRetentionTime`

#### `get_scan_stats(scan_number) → ScanStats`

TIC, base peak, mass range, and other per-scan statistics.
.NET call: `GetScanStatsForScanNumber`

#### `get_centroid_stream(scan_number, prefer_profile_data=False) → CentroidData`

Peak-picked mass spectrum with per-peak charge, noise, baseline, and resolution.
.NET call: `GetCentroidStream`

#### `get_profile_data(scan_number) → ProfileData`

Raw (continuous) profile data as segmented arrays.
.NET call: `GetSegmentedScanFromScanNumber`

#### `get_scan_info(scan_number) → ScanInfo`

Consolidated scan metadata combining filter string, scan event, stats, RT,
and trailer extra.
.NET calls: `GetFilterForScanNumber`, `GetScanEventForScanNumber`,
`RetentionTimeFromScanNumber`, `GetTrailerExtraInformation`

#### `get_scan_event_for_scan(scan_number) → dict`

Raw scan-event fields: `MSOrder`, `Polarity`, `ScanType`, `Detector`,
`MassRangeCount`, `ScanEventNumber`.
.NET call: `GetScanEventForScanNumber`

#### `get_scan_event_string(scan_number) → str`

Human-readable scan-event string.
.NET call: `GetScanEventStringForScanNumber`

#### `test_scan(scan_number, filter_string) → bool`

`True` if the scan matches the given filter string.
.NET call: `TestScan`

#### `get_scan_dependents(scan_number, depth=1) → ScanDependent`

MS^n parent–child scan relationships.
.NET call: `GetScanDependents`

#### `get_mass_precision(scan_number) → List[MassPrecision]`

Per-peak mass accuracy and resolution estimates.
Requires `ThermoFisher.CommonCore.MassPrecisionEstimator.dll`.
.NET call: `PrecisionEstimate.GetMassPrecisionEstimate`

---

### Scan Filters & Enumerators

#### `get_filters() → List[str]`

All unique scan-filter strings present in the file.
.NET call: `GetFilters`

#### `get_auto_filters() → List[str]`

Auto-generated filter strings covering all scan types.
.NET call: `GetAutoFilters`

#### `get_filter_for_scan(scan_number) → str`

Filter string for a specific scan.
.NET call: `GetFilterForScanNumber`

#### `get_filter_from_string(filter_string) → str`

Normalise and round-trip a filter string through the .NET parser.
.NET call: `GetFilterFromString`

#### `get_filtered_scan_numbers(filter_string) → List[int]`

All scan numbers matching a filter string.
.NET call: `GetFilteredScanEnumerator`

#### `get_filtered_scan_numbers_over_time(filter_string, start_time, end_time) → List[int]`

Scan numbers matching a filter within a retention-time window.
.NET call: `GetFilteredScanEnumeratorOverTime`

---

### Chromatograms

#### `get_chromatogram(trace_type="BasePeak", mass_range="", start_scan=-1, end_scan=-1, filter_string="") → ChromatogramData`

Extract a single chromatogram trace.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `trace_type` | `str` | `"BasePeak"` | `"BasePeak"`, `"TIC"`, `"MassRange"` / `"EIC"`, `"NeutralLoss"`, `"UV"`, `"PDA"`, `"Analog"` |
| `mass_range` | `str` | `""` | Mass range for EIC, e.g. `"500.0-510.0"` |
| `start_scan` | `int` | `-1` | Start scan (`-1` = first scan) |
| `end_scan` | `int` | `-1` | End scan (`-1` = last scan) |
| `filter_string` | `str` | `""` | Restrict to scans matching this filter (see `get_filters()`) |

.NET call: `GetChromatogramData`

#### `get_chromatogram_ex(trace_type="BasePeak", mass_ranges=None, filter_string="", start_scan=-1, end_scan=-1) → ChromatogramData`

Extended chromatogram with multiple mass ranges.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `trace_type` | `str` | `"BasePeak"` | Same values as `get_chromatogram` |
| `mass_ranges` | `List[Tuple[float, float]] \| None` | `None` | List of `(low_mz, high_mz)` tuples |
| `filter_string` | `str` | `""` | Scan filter restriction |
| `start_scan` | `int` | `-1` | Start scan |
| `end_scan` | `int` | `-1` | End scan |

.NET call: `GetChromatogramDataEx`

---

### Logs & Diagnostics

#### `get_trailer_data(scan_number) → TrailerData`

All trailer-extra key-value pairs for a scan.
.NET call: `GetTrailerExtraInformation`

#### `get_trailer_header_info() → List[str]`

Names of all trailer-extra fields defined in the file.
.NET call: `GetTrailerExtraHeaderInformation`

#### `get_status_log_header_info() → List[str]`

Names of all status-log fields defined in the file.
.NET call: `GetStatusLogHeaderInformation`

#### `get_status_log_for_retention_time(retention_time) → StatusLogEntry`

Status log entry closest to a given retention time.
.NET call: `GetStatusLogForRetentionTime`

#### `get_status_log_for_scan(scan_number) → StatusLogEntry`

Status log entry for a scan (looks up RT then calls above).

#### `get_status_log_entries_count() → int`

Total number of status log entries.
.NET call: `GetStatusLogEntriesCount`

#### `get_status_log_at_position(position) → StatusLogEntry`

Status log entry by 0-based position.
.NET call: `GetStatusLogAtPosition`

#### `get_tune_data_count() → int`

Number of tune segments stored in the file.
.NET call: `GetTuneDataCount`

#### `get_tune_data(index=0) → TuneData`

Tune parameter labels and values for one segment.
.NET call: `GetTuneData`

#### `get_error_log_count() → int`

Number of error log entries.
.NET call: `GetErrorLogItems`

#### `get_error_log_entry(index) → ErrorLogEntry`

One error log entry by 0-based index.
.NET call: `GetErrorLogItem`

---

### Scan Averaging & Background Subtraction

#### `average_scans_in_range(first_scan, last_scan, filter_string=None) → AveragedScan`

Average all scans in an inclusive scan-number range.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `first_scan` | `int` | — | First scan (inclusive) |
| `last_scan` | `int` | — | Last scan (inclusive) |
| `filter_string` | `str \| None` | `None` | Restrict to matching scans |

.NET call: `AverageScansInScanRange`

#### `average_scans(scan_numbers) → AveragedScan`

Average an arbitrary list of scans.
.NET call: `AverageScans`

#### `average_scans_in_time_range(start_time, end_time, filter_string=None) → AveragedScan`

Average scans within a retention-time window.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `start_time` | `float` | — | Start time in minutes |
| `end_time` | `float` | — | End time in minutes |
| `filter_string` | `str \| None` | `None` | Restrict to matching scans |

.NET call: `AverageScansInTimeRange`

#### `subtract_background(scan_number, background_scan_numbers, mass_range=None) → BackgroundSubtractedSpectrum`

Remove background from a scan using the Thermo Fisher `BackgroundSubtractor`.

Requires `ThermoFisher.CommonCore.BackgroundSubtraction.dll`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `scan_number` | `int` | — | Foreground scan |
| `background_scan_numbers` | `int \| List[int]` | — | One or more background scans |
| `mass_range` | `Tuple[float, float] \| None` | `None` | Optional `(low_mz, high_mz)` window |

.NET call: `BackgroundSubtractor.Subtract`

---

## RawFileThreadManager

Thread-safe wrapper around `IRawFileThreadManager` for concurrent reads of a
single RAW file from multiple threads.

```python
from rawfilereader import RawFileThreadManager
import concurrent.futures

with RawFileThreadManager("sample.raw") as mgr:
    def read_scan(n):
        acc = mgr.create_accessor()
        result = acc.get_centroid_stream(n)
        acc.close()
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        spectra = list(pool.map(read_scan, range(1, 101)))
```

### `RawFileThreadManager(raw_file_path, libs_dir=None)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `raw_file_path` | `str` | — | Path to the `.raw` file |
| `libs_dir` | `str \| None` | `None` | Override DLL directory |

### `open()` / `close()`

Explicit lifecycle.  `open()` is called automatically by `__enter__`.

### `create_accessor() → RawFileAdapter`

Return a new, already-open `RawFileAdapter` backed by an independent .NET
accessor from `CreateThreadAccessor()`.  Each accessor is safe for one thread
at a time.  Call `accessor.close()` when done.

---

## DLL Requirements

| DLL | Required | Used for |
|---|---|---|
| `ThermoFisher.CommonCore.Data.dll` | Yes | Core data types and interfaces |
| `ThermoFisher.CommonCore.RawFileReader.dll` | Yes | `IRawDataPlus`, file factory |
| `ThermoFisher.CommonCore.MassPrecisionEstimator.dll` | Yes | `get_mass_precision()` |
| `ThermoFisher.CommonCore.BackgroundSubtraction.dll` | Optional | `subtract_background()` |

DLLs must be the **NetCore** build from the
[Thermo Fisher RawFileReader GitHub](https://github.com/thermofisherlsms/RawFileReader/tree/main/Libs/NetCore).
