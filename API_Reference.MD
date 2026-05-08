# RawFileReaderPyAdapter API Reference

This document lists the public Python API implemented by `rawfilereader`: adapter methods, data models, data-model convenience properties, and package exceptions. The adapter wraps Thermo Fisher RawFileReader .NET objects and returns native Python values or dataclasses.

## Hyperlink Index

### Adapter API

- [RawFileAdapter](#rawfileadapter)
  - [Constructor and lifecycle](#constructor-and-lifecycle)
    - [`RawFileAdapter(raw_file_path, libs_dir=None, instrument_type="MS", instrument_instance=1)`](#rawfileadapterraw_file_path-libs_dirnone-instrument_typems-instrument_instance1)
    - [`__enter__()`](#__enter__)
    - [`__exit__(*_)`](#__exit__)
    - [`__repr__()`](#__repr__)
    - [`open()`](#open)
    - [`close()`](#close)
    - [`is_open`](#is_open)
  - [Instrument selection and instrument metadata](#instrument-selection-and-instrument-metadata)
    - [`select_instrument(device_type, instance=1)`](#select_instrumentdevice_type-instance1)
    - [`get_instrument_count()`](#get_instrument_count)
    - [`get_instrument_count_of_type(device_type)`](#get_instrument_count_of_typedevice_type)
    - [`get_instrument_type(index)`](#get_instrument_typeindex)
    - [`get_instrument_data()`](#get_instrument_data)
  - [File and run metadata](#file-and-run-metadata)
    - [`get_file_info()`](#get_file_info)
    - [`get_scan_range()`](#get_scan_range)
    - [`get_start_time()`](#get_start_time)
    - [`get_end_time()`](#get_end_time)
    - [`get_instrument_method(index=0)`](#get_instrument_methodindex0)
    - [`get_all_instrument_names_from_method()`](#get_all_instrument_names_from_method)
    - [`get_run_header_info()`](#get_run_header_info)
    - [`get_file_error()`](#get_file_error)
  - [Filters, events, and scan lookup](#filters-events-and-scan-lookup)
    - [`get_filters()`](#get_filters)
    - [`get_filter_for_scan(scan_number)`](#get_filter_for_scanscan_number)
    - [`get_scan_event_for_scan(scan_number)`](#get_scan_event_for_scanscan_number)
    - [`get_retention_time(scan_number)`](#get_retention_timescan_number)
    - [`scan_number_from_retention_time(retention_time)`](#scan_number_from_retention_timeretention_time)
    - [`get_filtered_scan_numbers(filter_string, start_scan=None, end_scan=None)`](#get_filtered_scan_numbersfilter_string-start_scannone-end_scannone)
    - [`iterate_filtered_scans(filter_string, start_time=None, end_time=None)`](#iterate_filtered_scansfilter_string-start_timenone-end_timenone)
  - [Scan data and scan summaries](#scan-data-and-scan-summaries)
    - [`get_scan_stats(scan_number)`](#get_scan_statsscan_number)
    - [`get_centroid_stream(scan_number, prefer_profile_data=False)`](#get_centroid_streamscan_number-prefer_profile_datafalse)
    - [`get_profile_data(scan_number)`](#get_profile_datascan_number)
    - [`get_scan_info(scan_number)`](#get_scan_infoscan_number)
    - [`get_mass_precision(scan_number)`](#get_mass_precisionscan_number)
    - [`iter_scan_info(ms_order=None)`](#iter_scan_infoms_ordernone)
    - [`iter_centroid_data(ms_order=None)`](#iter_centroid_datams_ordernone)
    - [`analyze_all_scans()`](#analyze_all_scans)
  - [Averaging, chromatograms, trailer data, status logs, and dependents](#averaging-chromatograms-trailer-data-status-logs-and-dependents)
    - [`average_scans_in_range(first_scan, last_scan, filter_string=None)`](#average_scans_in_rangefirst_scan-last_scan-filter_stringnone)
    - [`average_scans(scan_numbers)`](#average_scansscan_numbers)
    - [`get_chromatogram(trace_type="BasePeak", mass_range="", start_scan=-1, end_scan=-1)`](#get_chromatogramtrace_typebasepeak-mass_range-start_scan-1-end_scan-1)
    - [`get_trailer_data(scan_number)`](#get_trailer_datascan_number)
    - [`get_trailer_header_info()`](#get_trailer_header_info)
    - [`get_status_log_header_info()`](#get_status_log_header_info)
    - [`get_status_log_for_retention_time(retention_time)`](#get_status_log_for_retention_timeretention_time)
    - [`get_status_log_for_scan(scan_number)`](#get_status_log_for_scanscan_number)
    - [`get_scan_dependents(scan_number, depth=1)`](#get_scan_dependentsscan_number-depth1)
  - [Subtraction APIs](#subtraction-apis)
    - [`subtract_spectra(scan_a, scan_b, mass_range=None, mass_tolerance_ppm=5.0, normalize=False)`](#subtract_spectrascan_a-scan_b-mass_rangenone-mass_tolerance_ppm50-normalizefalse)
    - [`subtract_background(scan_number, background_scan_numbers, mass_range=None)`](#subtract_backgroundscan_number-background_scan_numbers-mass_rangenone)

### Data Model API

- [Data models](#data-models)
  - [`FileInfo`](#fileinfo)
  - [`InstrumentInfo`](#instrumentinfo)
  - [`ScanStats`](#scanstats)
  - [`CentroidData`](#centroiddata)
  - [`ProfileData`](#profiledata)
  - [`ScanInfo`](#scaninfo)
  - [`ChromatogramData`](#chromatogramdata)
  - [`TrailerData`](#trailerdata)
  - [`StatusLogEntry`](#statuslogentry)
  - [`ScanDependent`](#scandependent)
  - [`AveragedScan`](#averagedscan)
  - [`BackgroundSubtractedSpectrum`](#backgroundsubtractedspectrum)
  - [`SubtractedSpectrum`](#subtractedspectrum)
  - [`MassPrecision`](#massprecision)
  - [`RunHeaderInfo`](#runheaderinfo)
  - [`FileError`](#fileerror)
- [Exceptions](#exceptions)

## Type Conventions

- Scan numbers are 1-based Thermo RAW scan numbers unless a method explicitly states otherwise.
- Retention times are in minutes.
- Mass ranges are normally `(low_mz, high_mz)` tuples and are inclusive when applied in Python.
- Most adapter methods require `open()` to have been called. Using `with RawFileAdapter(...) as rf:` opens and closes automatically.
- `device_type` strings are parsed into Thermo `Device` enum values. Common values are `"MS"`, `"UV"`, `"PDA"`, `"Analog"`, and `"MSAnalog"`.

## RawFileAdapter

Main high-level wrapper class exported as `rawfilereader.RawFileAdapter`.

### Constructor and lifecycle

#### `RawFileAdapter(raw_file_path, libs_dir=None, instrument_type="MS", instrument_instance=1)`

Creates a new adapter instance. This does not open the RAW file until `open()` or the context manager is used.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `raw_file_path` | `str` | required | Path to the `.raw` file. Stored internally as an absolute path. |
| `libs_dir` | `Optional[str]` | `None` | Optional override path containing the Thermo Fisher .NET DLLs. |
| `instrument_type` | `str` | `"MS"` | Device type selected when opening the file. |
| `instrument_instance` | `int` | `1` | 1-based instance number for the selected device type. |

| Output | Description |
|---|---|
| `RawFileAdapter` | Adapter object. |

#### `__enter__()`

Opens the RAW file and returns the adapter for use in a `with` block.

| Input | Type | Default | Description |
|---|---:|---:|---|
| none | — | — | — |

| Output | Description |
|---|---|
| `RawFileAdapter` | The opened adapter instance. |

#### `__exit__(*_)`

Closes the RAW file when a context manager exits.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `*_` | variadic | — | Context-manager exception arguments; ignored. |

| Output | Description |
|---|---|
| `None` | Releases .NET resources by calling `close()`. |

#### `__repr__()`

Returns a debugging representation containing the RAW filename and open/closed state.

| Input | Type | Default | Description |
|---|---:|---:|---|
| none | — | — | — |

| Output | Description |
|---|---|
| `str` | String like `RawFileAdapter('sample.raw', open)`. |

#### `open()`

Loads .NET assemblies, creates the Thermo RawFileReader object, checks file state, and selects the configured default instrument.

| Input | Type | Default | Description |
|---|---:|---:|---|
| none | — | — | Uses constructor parameters. |

| Output | Description |
|---|---|
| `None` | Opens the file in place. |

| Raises |
|---|
| `FileNotFoundError` if the RAW file path does not exist. |
| `RawFileNotOpenError` if RawFileReader cannot open the file or reports an error state. |
| `RawFileInAcquisitionError` if the file is still being acquired. |
| `InstrumentSelectionError` if the requested instrument cannot be selected. |
| `AssemblyLoadError` if pythonnet or Thermo DLLs cannot be loaded. |

#### `close()`

Closes the RAW file and disposes the underlying .NET object.

| Input | Type | Default | Description |
|---|---:|---:|---|
| none | — | — | — |

| Output | Description |
|---|---|
| `None` | The adapter becomes closed. |

#### `is_open`

Boolean property showing whether the underlying RAW file object exists and is open.

| Input | Type | Default | Description |
|---|---:|---:|---|
| none | — | — | — |

| Output | Description |
|---|---|
| `bool` | `True` when currently open, otherwise `False`. |

### Instrument selection and instrument metadata

#### `select_instrument(device_type, instance=1)`

Selects an instrument device for subsequent reads.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `device_type` | `str` | required | Device type name parsed to the Thermo `Device` enum. |
| `instance` | `int` | `1` | 1-based device instance number. |

| Output | Description |
|---|---|
| `None` | Updates the selected instrument on the open RAW file. |

#### `get_instrument_count()`

Returns the total number of instrument devices in the file.

| Input | Type | Default | Description |
|---|---:|---:|---|
| none | — | — | — |

| Output | Description |
|---|---|
| `int` | Total instrument/device count. |

#### `get_instrument_count_of_type(device_type)`

Returns how many devices of a given type are present.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `device_type` | `str` | required | Device type name such as `"MS"` or `"UV"`. |

| Output | Description |
|---|---|
| `int` | Number of matching devices. |

#### `get_instrument_type(index)`

Returns the device type for a 0-based instrument index.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `index` | `int` | required | 0-based instrument index. |

| Output | Description |
|---|---|
| `str` | Device type string. |

#### `get_instrument_data()`

Returns metadata for the currently selected instrument.

| Input | Type | Default | Description |
|---|---:|---:|---|
| none | — | — | Uses the selected instrument. |

| Output | Description |
|---|---|
| [`InstrumentInfo`](#instrumentinfo) | Device metadata such as name, model, serial number, versions, units, and channel labels. |

### File and run metadata

#### `get_file_info()`

Returns file-level metadata, sample information, instrument information, and extended header fields when available.

| Input | Type | Default | Description |
|---|---:|---:|---|
| none | — | — | — |

| Output | Description |
|---|---|
| [`FileInfo`](#fileinfo) | Header-level metadata for the RAW file. |

#### `get_scan_range()`

Returns the first and last scan numbers for the selected instrument.

| Input | Type | Default | Description |
|---|---:|---:|---|
| none | — | — | — |

| Output | Description |
|---|---|
| `Tuple[int, int]` | `(first_scan, last_scan)`. |

#### `get_start_time()`

Returns the acquisition start time.

| Input | Type | Default | Description |
|---|---:|---:|---|
| none | — | — | — |

| Output | Description |
|---|---|
| `float` | Start time in minutes. |

#### `get_end_time()`

Returns the acquisition end time.

| Input | Type | Default | Description |
|---|---:|---:|---|
| none | — | — | — |

| Output | Description |
|---|---|
| `float` | End time in minutes. |

#### `get_instrument_method(index=0)`

Returns the instrument method text at the requested method index.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `index` | `int` | `0` | Instrument method index. |

| Output | Description |
|---|---|
| `str` | Instrument method text. |

#### `get_all_instrument_names_from_method()`

Returns all instrument names embedded in the instrument method.

| Input | Type | Default | Description |
|---|---:|---:|---|
| none | — | — | — |

| Output | Description |
|---|---|
| `List[str]` | Instrument names. |

#### `get_run_header_info()`

Returns extended run-header metadata from `IRawData.RunHeaderEx`.

| Input | Type | Default | Description |
|---|---:|---:|---|
| none | — | — | — |

| Output | Description |
|---|---|
| [`RunHeaderInfo`](#runheaderinfo) | Extended scan-range, time-range, count, intensity, and metadata values. |

#### `get_file_error()`

Returns diagnostic file-error state from `IRawDataPlus.FileError`.

| Input | Type | Default | Description |
|---|---:|---:|---|
| none | — | — | — |

| Output | Description |
|---|---|
| [`FileError`](#fileerror) | Error flag, code, and message. |

### Filters, events, and scan lookup

#### `get_filters()`

Returns all unique scan-filter strings in the file.

| Input | Type | Default | Description |
|---|---:|---:|---|
| none | — | — | — |

| Output | Description |
|---|---|
| `List[str]` | Scan-filter strings. |

#### `get_filter_for_scan(scan_number)`

Returns the filter string for one scan.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `scan_number` | `int` | required | 1-based scan number. |

| Output | Description |
|---|---|
| `str` | Scan-filter string. |

#### `get_scan_event_for_scan(scan_number)`

Returns scan-event parameters for one scan.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `scan_number` | `int` | required | 1-based scan number. |

| Output | Description |
|---|---|
| `dict` | Scan-event fields including MS order, detector/activation information, isolation data, and precursor data where available. |

#### `get_retention_time(scan_number)`

Returns the retention time for a scan.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `scan_number` | `int` | required | 1-based scan number. |

| Output | Description |
|---|---|
| `float` | Retention time in minutes. |

#### `scan_number_from_retention_time(retention_time)`

Returns the scan number nearest to a retention time.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `retention_time` | `float` | required | Retention time in minutes. |

| Output | Description |
|---|---|
| `int` | Nearest scan number. |

#### `get_filtered_scan_numbers(filter_string, start_scan=None, end_scan=None)`

Returns scan numbers whose scan-filter string exactly matches `filter_string` within an optional scan range.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `filter_string` | `str` | required | Filter string to match. |
| `start_scan` | `Optional[int]` | `None` | First scan to inspect; defaults to the file's first scan. |
| `end_scan` | `Optional[int]` | `None` | Last scan to inspect; defaults to the file's last scan. |

| Output | Description |
|---|---|
| `List[int]` | Matching scan numbers. |

#### `iterate_filtered_scans(filter_string, start_time=None, end_time=None)`

Lazily yields scan numbers whose scan-filter string matches `filter_string` over an optional retention-time range.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `filter_string` | `str` | required | Filter string to match. |
| `start_time` | `Optional[float]` | `None` | Start retention time in minutes; defaults to file start. |
| `end_time` | `Optional[float]` | `None` | End retention time in minutes; defaults to file end. |

| Output | Description |
|---|---|
| `Iterator[int]` | Lazy iterator of matching scan numbers. |

### Scan data and scan summaries

#### `get_scan_stats(scan_number)`

Returns per-scan statistics.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `scan_number` | `int` | required | 1-based scan number. |

| Output | Description |
|---|---|
| [`ScanStats`](#scanstats) | TIC, base peak, scan event, packet count, scan mode, and scan time metadata. |

#### `get_centroid_stream(scan_number, prefer_profile_data=False)`

Returns centroided peak data for a scan.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `scan_number` | `int` | required | 1-based scan number. |
| `prefer_profile_data` | `bool` | `False` | Passed to Thermo `GetCentroidStream`; requests centroid generation from profile data where supported. |

| Output | Description |
|---|---|
| [`CentroidData`](#centroiddata) | Peak masses, intensities, charges, baselines, noise values, resolutions, and flags. |

#### `get_profile_data(scan_number)`

Returns segmented raw profile data for a scan.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `scan_number` | `int` | required | 1-based scan number. |

| Output | Description |
|---|---|
| [`ProfileData`](#profiledata) | Segment pairs of position/mass arrays and intensity arrays. |

#### `get_scan_info(scan_number)`

Returns a consolidated high-level scan summary combining filter, event, stats, trailer, and retention-time data.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `scan_number` | `int` | required | 1-based scan number. |

| Output | Description |
|---|---|
| [`ScanInfo`](#scaninfo) | High-level scan metadata. |

#### `get_mass_precision(scan_number)`

Returns per-peak mass accuracy and precision estimates for a scan.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `scan_number` | `int` | required | 1-based scan number. |

| Output | Description |
|---|---|
| `List[`[`MassPrecision`](#massprecision)`]` | One mass-precision estimate per returned peak. |

#### `iter_scan_info(ms_order=None)`

Yields scan summaries for every scan, optionally filtered by MS order.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `ms_order` | `Optional[int]` | `None` | If provided, only yields scans where `ScanInfo.ms_order == ms_order`. |

| Output | Description |
|---|---|
| `Iterator[`[`ScanInfo`](#scaninfo)`]` | Lazy iterator of scan summaries. |

#### `iter_centroid_data(ms_order=None)`

Yields centroid data for each scan, optionally filtered by MS order.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `ms_order` | `Optional[int]` | `None` | If provided, only yields centroid data for scans with the matching MS order. |

| Output | Description |
|---|---|
| `Iterator[`[`CentroidData`](#centroiddata)`]` | Lazy iterator of centroid spectra. |

#### `analyze_all_scans()`

Walks every scan and performs basic scan-quality analysis.

| Input | Type | Default | Description |
|---|---:|---:|---|
| none | — | — | — |

| Output | Description |
|---|---|
| `Dict[str, int]` | Summary counts such as `total_scans`, `centroid_scans`, `profile_scans`, `empty_scans`, `bad_mass_order`, and `errors`. |

### Averaging, chromatograms, trailer data, status logs, and dependents

#### `average_scans_in_range(first_scan, last_scan, filter_string=None)`

Averages scans between two scan numbers, inclusive.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `first_scan` | `int` | required | First scan in the range. |
| `last_scan` | `int` | required | Last scan in the range. |
| `filter_string` | `Optional[str]` | `None` | Optional scan-filter string; if omitted, the first scan's filter is used. |

| Output | Description |
|---|---|
| [`AveragedScan`](#averagedscan) | Averaged m/z and intensity arrays for the range. |

#### `average_scans(scan_numbers)`

Averages an arbitrary list of scan numbers.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `scan_numbers` | `List[int]` | required | Scan numbers to average. Must not be empty. |

| Output | Description |
|---|---|
| [`AveragedScan`](#averagedscan) | Averaged m/z and intensity arrays. `first_scan` and `last_scan` reflect the min/max input scan number. |

#### `get_chromatogram(trace_type="BasePeak", mass_range="", start_scan=-1, end_scan=-1)`

Extracts a chromatogram trace.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `trace_type` | `str` | `"BasePeak"` | Thermo trace type name, such as `"BasePeak"`, `"TIC"`, or another available `TraceType`. |
| `mass_range` | `str` | `""` | Optional mass range string used for traces that need a range. |
| `start_scan` | `int` | `-1` | Start scan. `-1` means use the first scan in the file. |
| `end_scan` | `int` | `-1` | End scan. `-1` means use the last scan in the file. |

| Output | Description |
|---|---|
| [`ChromatogramData`](#chromatogramdata) | Times and intensities for the requested trace. |

#### `get_trailer_data(scan_number)`

Returns trailer-extra data for one scan.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `scan_number` | `int` | required | 1-based scan number. |

| Output | Description |
|---|---|
| [`TrailerData`](#trailerdata) | Scan number and a label-to-value dictionary. |

#### `get_trailer_header_info()`

Returns all trailer-extra field labels defined in the file.

| Input | Type | Default | Description |
|---|---:|---:|---|
| none | — | — | — |

| Output | Description |
|---|---|
| `List[str]` | Trailer-extra labels. |

#### `get_status_log_header_info()`

Returns all status-log field labels defined in the file.

| Input | Type | Default | Description |
|---|---:|---:|---|
| none | — | — | — |

| Output | Description |
|---|---|
| `List[str]` | Status-log labels. |

#### `get_status_log_for_retention_time(retention_time)`

Returns the status-log row nearest to a retention time.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `retention_time` | `float` | required | Retention time in minutes. |

| Output | Description |
|---|---|
| [`StatusLogEntry`](#statuslogentry) | Retention time and label-to-value dictionary. |

#### `get_status_log_for_scan(scan_number)`

Returns the status-log row associated with a scan by first converting the scan number to retention time.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `scan_number` | `int` | required | 1-based scan number. |

| Output | Description |
|---|---|
| [`StatusLogEntry`](#statuslogentry) | Retention time and label-to-value dictionary. |

#### `get_scan_dependents(scan_number, depth=1)`

Returns MS<sup>n</sup> dependent scan relationships for one scan.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `scan_number` | `int` | required | Parent scan number. |
| `depth` | `int` | `1` | Dependency depth to request from RawFileReader. |

| Output | Description |
|---|---|
| [`ScanDependent`](#scandependent) | Parent scan number and dependent scan numbers. |

### Subtraction APIs

#### `subtract_spectra(scan_a, scan_b, mass_range=None, mass_tolerance_ppm=5.0, normalize=False)`

Subtracts scan B from scan A. Both scans must have the same scan-filter string.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `scan_a` | `int` | required | Foreground scan number. |
| `scan_b` | `int` | required | Background/comparison scan number to subtract. |
| `mass_range` | `Optional[Tuple[float, float]]` | `None` | Optional inclusive m/z range applied before subtraction. |
| `mass_tolerance_ppm` | `float` | `5.0` | Matching tolerance for centroid subtraction. |
| `normalize` | `bool` | `False` | If `True`, normalizes each spectrum to total ion current before subtraction. |

| Output | Description |
|---|---|
| [`SubtractedSpectrum`](#subtractedspectrum) | Signed and clipped intensity differences. |

#### `subtract_background(scan_number, background_scan_numbers, mass_range=None)`

Removes background from a scan using Thermo Fisher's `BackgroundSubtractor`. If multiple background scans are supplied, they are averaged first where the .NET API supports it; the implementation contains a pure-Python fallback for background peak subtraction.

| Input | Type | Default | Description |
|---|---:|---:|---|
| `scan_number` | `int` | required | Foreground scan number. |
| `background_scan_numbers` | `Union[int, List[int]]` | required | One background scan number or a list of background scans. |
| `mass_range` | `Optional[Tuple[float, float]]` | `None` | Optional inclusive m/z range applied to the result. |

| Output | Description |
|---|---|
| [`BackgroundSubtractedSpectrum`](#backgroundsubtractedspectrum) | Background-subtracted masses and intensities. |

## Data Models

All data models are Python `dataclass` classes exported from `rawfilereader.models` and re-exported from `rawfilereader`.

### `FileInfo`

Header-level metadata about the RAW file.

| Field / property | Type | Default | Description |
|---|---:|---:|---|
| `file_name` | `str` | required | File name. |
| `creation_date` | `str` | required | Creation date as a string. |
| `operator` | `str` | required | Operator/creator identifier. |
| `comment` | `str` | required | File or sample comment. |
| `sample_name` | `str` | required | Sample name. |
| `sample_id` | `str` | required | Sample ID. |
| `sample_type` | `str` | required | Sample type. |
| `vial` | `str` | required | Autosampler vial identifier. |
| `instrument_method` | `str` | required | Instrument method summary/name. |
| `tune_method` | `str` | required | Tune method summary/name. |
| `acquisition_software_version` | `str` | required | Acquisition software version. |
| `instrument_name` | `str` | required | Instrument name. |
| `instrument_serial_number` | `str` | required | Instrument serial number. |
| `number_of_ms_orders` | `int` | required | Number of MS orders. |
| `has_ms_data` | `bool` | required | Whether the file has MS data. |
| `file_description` | `str` | `""` | Extended file description when available. |
| `file_type` | `str` | `""` | Extended file type when available. |
| `revision` | `int` | `0` | Extended file revision. |
| `modified_date` | `str` | `""` | Extended modified date. |
| `computer_name` | `str` | `""` | Computer name. |
| `path` | `str` | `""` | Original file path. |
| `who_created_logon` | `str` | `""` | Creator logon. |
| `who_modified_logon` | `str` | `""` | Last modifier logon. |
| `number_of_times_calibrated` | `int` | `0` | Calibration count. |
| `number_of_times_modified` | `int` | `0` | Modification count. |

### `InstrumentInfo`

Per-device instrument metadata.

| Field / property | Type | Default | Description |
|---|---:|---:|---|
| `device_type` | `str` | required | Device type such as `"MS"`, `"UV"`, `"PDA"`, or `"Analog"`. |
| `instance_number` | `int` | required | 1-based device instance number. |
| `name` | `str` | required | Instrument/device name. |
| `model` | `str` | required | Instrument model. |
| `serial_number` | `str` | required | Serial number. |
| `software_version` | `str` | required | Software version. |
| `hardware_version` | `str` | required | Hardware version. |
| `units` | `str` | required | Native units for the detector/device. |
| `channel_labels` | `List[str]` | `[]` | Channel labels. |

### `ScanStats`

Statistics for a single scan.

| Field / property | Type | Default | Description |
|---|---:|---:|---|
| `scan_number` | `int` | required | Scan number. |
| `start_time` | `float` | required | Scan start/retention time in minutes. |
| `low_mass` | `float` | required | Low m/z bound. |
| `high_mass` | `float` | required | High m/z bound. |
| `tic` | `float` | required | Total ion current. |
| `base_peak_mass` | `float` | required | Base-peak m/z. |
| `base_peak_intensity` | `float` | required | Base-peak intensity. |
| `packet_count` | `int` | required | Packet count. |
| `scan_event_number` | `int` | required | Scan event number. |
| `master_index` | `int` | required | Master index. |
| `is_centroid_scan` | `bool` | required | Whether the scan is centroid data. |

### `CentroidData`

Centroid (peak-picked) mass-spectrum data.

| Field / property | Type | Default | Description |
|---|---:|---:|---|
| `scan_number` | `int` | required | Scan number. |
| `masses` | `List[float]` | required | Peak m/z values. |
| `intensities` | `List[float]` | required | Peak intensities. |
| `charges` | `List[float]` | required | Peak charge values. |
| `baselines` | `List[float]` | required | Baseline values. |
| `noises` | `List[float]` | required | Noise estimates. |
| `resolutions` | `List[float]` | required | Resolution estimates. |
| `is_exceptional` | `bool` | required | Thermo exceptional-data flag. |
| `is_reference` | `bool` | required | Thermo reference-data flag. |
| `peaks` | `List[Tuple[float, float]]` | computed property | `(mass, intensity)` tuples from `masses` and `intensities`. |

### `ProfileData`

Profile (raw, continuous) mass-spectrum data represented as segmented arrays.

| Field / property | Type | Default | Description |
|---|---:|---:|---|
| `scan_number` | `int` | required | Scan number. |
| `segments` | `List[Tuple[List[float], List[float]]]` | `[]` | Segment list. Each item is `(positions, intensities)`. |
| `masses` | `List[float]` | computed property | All segment positions flattened into one list. |
| `intensities` | `List[float]` | computed property | All segment intensities flattened into one list. |

### `ScanInfo`

High-level metadata about a single scan.

| Field / property | Type | Default | Description |
|---|---:|---:|---|
| `scan_number` | `int` | required | Scan number. |
| `scan_filter` | `str` | required | Thermo scan-filter string. |
| `ms_order` | `int` | required | MS order, for example `1` for MS1 or `2` for MS2. |
| `retention_time` | `float` | required | Retention time in minutes. |
| `injection_time` | `float` | required | Injection time in milliseconds. |
| `is_centroid` | `bool` | required | Whether the scan is centroid data. |
| `detector_type` | `str` | required | Detector type. |
| `activation_type` | `str` | required | Activation type. |
| `precursor_mass` | `Optional[float]` | `None` | Precursor m/z when available. |
| `precursor_charge` | `Optional[int]` | `None` | Precursor charge when available. |
| `collision_energy` | `Optional[float]` | `None` | Collision energy when available. |
| `isolation_width` | `Optional[float]` | `None` | Isolation width when available. |
| `monoisotopic_mass` | `Optional[float]` | `None` | Monoisotopic mass when available. |
| `ion_injection_time` | `Optional[float]` | `None` | Ion injection time when available. |

### `ChromatogramData`

A single chromatogram trace.

| Field / property | Type | Default | Description |
|---|---:|---:|---|
| `trace_type` | `str` | required | Trace type, such as `"BasePeak"`, `"TIC"`, or `"MassRange"`. |
| `mass_range` | `str` | required | Mass range string associated with the trace. |
| `times` | `List[float]` | required | Retention-time points in minutes. |
| `intensities` | `List[float]` | required | Trace intensities. |

### `TrailerData`

Trailer-extra auxiliary data appended to a scan.

| Field / property | Type | Default | Description |
|---|---:|---:|---|
| `scan_number` | `int` | required | Scan number. |
| `fields` | `dict` | required | Mapping of trailer labels to values. |

### `StatusLogEntry`

One row from the instrument status log.

| Field / property | Type | Default | Description |
|---|---:|---:|---|
| `retention_time` | `float` | required | Status-log retention time in minutes. |
| `fields` | `dict` | required | Mapping of status-log labels to values. |

### `ScanDependent`

Relationship between a parent scan and dependent MS<sup>n</sup> scans.

| Field / property | Type | Default | Description |
|---|---:|---:|---|
| `scan_number` | `int` | required | Parent scan number. |
| `dependent_scan_numbers` | `List[int]` | required | Dependent scan numbers. |

### `AveragedScan`

Result from averaging multiple scans.

| Field / property | Type | Default | Description |
|---|---:|---:|---|
| `first_scan` | `int` | required | First scan included in the average, or minimum input scan for arbitrary-list averaging. |
| `last_scan` | `int` | required | Last scan included in the average, or maximum input scan for arbitrary-list averaging. |
| `masses` | `List[float]` | required | Averaged m/z values. |
| `intensities` | `List[float]` | required | Averaged intensities. |

### `BackgroundSubtractedSpectrum`

Result of background subtraction using Thermo Fisher background-removal logic.

| Field / property | Type | Default | Description |
|---|---:|---:|---|
| `scan_number` | `int` | required | Foreground scan number. |
| `background_scans` | `List[int]` | required | Background scan numbers used. |
| `scan_filter` | `str` | required | Scan-filter string for the foreground scan. |
| `masses` | `List[float]` | required | Background-subtracted m/z values. |
| `intensities` | `List[float]` | required | Background-subtracted intensities. |
| `peaks` | `List[Tuple[float, float]]` | computed property | `(mass, intensity)` tuples from `masses` and `intensities`. |

### `SubtractedSpectrum`

Result of subtracting one mass spectrum from another (`scan_a - scan_b`).

| Field / property | Type | Default | Description |
|---|---:|---:|---|
| `scan_a` | `int` | required | Foreground scan number. |
| `scan_b` | `int` | required | Scan number subtracted from `scan_a`. |
| `scan_filter` | `str` | required | Common scan-filter string for both scans. |
| `mass_range` | `Optional[Tuple[float, float]]` | required | m/z range used, or `None` for full range. |
| `is_centroid` | `bool` | required | Whether centroid subtraction was used. |
| `masses` | `List[float]` | required | Output m/z values. |
| `intensities` | `List[float]` | required | Signed intensity differences. |
| `intensities_clipped` | `List[float]` | required | Negative values clipped to zero. |
| `peaks` | `List[Tuple[float, float]]` | computed property | Positive `(mass, clipped_intensity)` pairs only. |

### `MassPrecision`

Mass accuracy / precision estimate for one peak.

| Field / property | Type | Default | Description |
|---|---:|---:|---|
| `mass` | `float` | required | Peak m/z. |
| `intensity` | `float` | required | Peak intensity. |
| `resolution` | `float` | required | Peak resolution. |
| `mz_accuracy_ppm` | `float` | required | Mass accuracy in ppm. |
| `mz_accuracy_mmu` | `float` | required | Mass accuracy in millimass units. |

### `RunHeaderInfo`

Extended run-header metadata from `IRawData.RunHeaderEx`.

| Field / property | Type | Default | Description |
|---|---:|---:|---|
| `first_scan` | `int` | required | First scan number. |
| `last_scan` | `int` | required | Last scan number. |
| `start_time` | `float` | required | Run start time in minutes. |
| `end_time` | `float` | required | Run end time in minutes. |
| `low_mass` | `float` | required | Lowest mass in the run header. |
| `high_mass` | `float` | required | Highest mass in the run header. |
| `mass_resolution` | `float` | required | Run-header mass resolution. |
| `max_intensity` | `float` | required | Maximum intensity. |
| `max_integrated_intensity` | `float` | required | Maximum integrated intensity. |
| `spectra_count` | `int` | required | Number of spectra. |
| `status_log_count` | `int` | required | Number of status-log entries. |
| `error_log_count` | `int` | required | Number of error-log entries. |
| `trailer_extra_count` | `int` | required | Number of trailer-extra entries. |
| `tune_data_count` | `int` | required | Number of tune-data entries. |
| `expected_run_time` | `float` | required | Expected run time. |
| `comment1` | `str` | required | Run comment 1. |
| `comment2` | `str` | required | Run comment 2. |
| `in_acquisition` | `bool` | required | Whether the file is in acquisition. |
| `tolerance_unit` | `str` | required | Tolerance unit. |
| `filter_mass_precision` | `int` | required | Filter mass precision. |
| `writer_protocol` | `int` | required | Writer protocol identifier. |

### `FileError`

Diagnostic error state from `IRawDataPlus.FileError`.

| Field / property | Type | Default | Description |
|---|---:|---:|---|
| `has_error` | `bool` | required | Whether an error is reported. |
| `error_code` | `int` | required | Error code. |
| `error_message` | `str` | required | Error message. |

## Exceptions

All package-specific exceptions inherit from `RawFileError`.

| Exception | Base | Description |
|---|---|---|
| `RawFileError` | `Exception` | Base exception for package errors. |
| `RawFileNotOpenError` | `RawFileError` | Raised when an operation requires an open file, or when RawFileReader fails to open a file. |
| `RawFileInAcquisitionError` | `RawFileError` | Raised when the RAW file is still being acquired. |
| `InstrumentSelectionError` | `RawFileError` | Raised when an instrument device type or instance cannot be selected. |
| `ScanNotFoundError` | `RawFileError` | Raised when a requested scan number is outside the valid scan range. |
| `AssemblyLoadError` | `RawFileError` | Raised when pythonnet or Thermo Fisher RawFileReader assemblies cannot be loaded. |
