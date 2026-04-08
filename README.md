# TraceHunter

A comprehensive Python adapter for the [Thermo Fisher Scientific RawFileReader](https://github.com/thermofisherlsms/RawFileReader) .NET assemblies.  It uses [pythonnet](https://github.com/pythonnet/pythonnet) to bridge Python and .NET so you can read Thermo `.raw` mass-spectrometry files without leaving Python.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
  - [Opening and Closing Files](#opening-and-closing-files)
  - [Instrument Selection](#instrument-selection)
  - [File / Run Header Metadata](#file--run-header-metadata)
  - [Scan Range & Retention Time](#scan-range--retention-time)
  - [Scan Filters & Events](#scan-filters--events)
  - [Scan Statistics](#scan-statistics)
  - [Spectral Data – Centroid](#spectral-data--centroid)
  - [Spectral Data – Profile](#spectral-data--profile)
  - [High-level Scan Info](#high-level-scan-info)
  - [Averaged Spectra](#averaged-spectra)
  - [Chromatograms](#chromatograms)
  - [Trailer Extra Data](#trailer-extra-data)
  - [Status Log](#status-log)
  - [Scan Dependents (MS^n)](#scan-dependents-msn)
  - [Mass Precision Estimation](#mass-precision-estimation)
  - [Bulk Iteration Helpers](#bulk-iteration-helpers)
  - [Scan Quality Analysis](#scan-quality-analysis)
- [Data Models](#data-models)
- [Exceptions](#exceptions)
- [Environment Variables](#environment-variables)
- [Examples](#examples)

---

## Requirements

| Requirement | Version |
|---|---|
| Python | ≥ 3.8 |
| pythonnet | ≥ 3.0.3 |
| .NET Runtime | ≥ 6.0 (for `NetCore` DLLs) or .NET Framework ≥ 4.5.1 |
| RawFileReader DLLs | Latest from [thermofisherlsms/RawFileReader](https://github.com/thermofisherlsms/RawFileReader/tree/main/Libs) |

### Required DLLs

Download the DLLs from the `Libs/NetCore` folder of the upstream repository and place them in a `libs/` directory next to this package (or point to them with the `RAWFILEREADER_LIBS` environment variable):

```
libs/
  ThermoFisher.CommonCore.Data.dll
  ThermoFisher.CommonCore.RawFileReader.dll
  ThermoFisher.CommonCore.MassPrecisionEstimator.dll
  ThermoFisher.CommonCore.BackgroundSubtraction.dll   # optional
```

---

## Installation

```bash
# Install Python dependencies
pip install pythonnet

# Clone / install this package
pip install .
```

Or directly from source:

```bash
git clone https://github.com/mzzzhunter/tracehunter.git
cd tracehunter
pip install -r requirements.txt
```

Set the DLL directory:

```bash
export RAWFILEREADER_LIBS=/path/to/libs
```

---

## Quick Start

```python
from tracehunter import TraceHunter

with TraceHunter("sample.raw") as th:
    info = th.get_file_info()
    print(f"Instrument : {info.instrument_name}")
    print(f"Operator   : {info.operator}")

    first, last = th.get_scan_range()
    print(f"Scans      : {first} – {last}")

    # Read first scan as centroid data
    centroid = th.get_centroid_stream(first)
    for mass, intensity in centroid.peaks[:5]:
        print(f"  m/z={mass:.4f}  I={intensity:.0f}")
```

---

## API Reference

### Opening and Closing Files

#### `TraceHunter(raw_file_path, libs_dir=None, instrument_type="MS", instrument_instance=1)`

Create a new adapter instance.

| Parameter | Type | Description |
|---|---|---|
| `raw_file_path` | `str` | Path to the `.raw` file |
| `libs_dir` | `str \| None` | Override path to the DLL directory |
| `instrument_type` | `str` | Device type to select on open (`"MS"`, `"UV"`, `"PDA"`, `"Analog"`, `"MSAnalog"`) |
| `instrument_instance` | `int` | 1-based device instance number |

```python
# Explicit open/close
th = TraceHunter("sample.raw")
th.open()
# ... work ...
th.close()

# Preferred: context manager
with TraceHunter("sample.raw") as th:
    pass
```

#### `open()` / `close()` / `is_open() -> bool`

```python
th = TraceHunter("sample.raw")
th.open()
print(th.is_open())   # True
th.close()
print(th.is_open())   # False
```

---

### Instrument Selection

#### `select_instrument(device_type, instance=1)`

Select a specific device for subsequent reads.

```python
with TraceHunter("sample.raw") as th:
    th.select_instrument("UV", 1)   # switch to UV detector
    th.select_instrument("MS", 1)   # switch back to MS
```

#### `get_instrument_count() -> int`

```python
count = th.get_instrument_count()
print(f"Total devices: {count}")
```

#### `get_instrument_count_of_type(device_type) -> int`

```python
ms_count = th.get_instrument_count_of_type("MS")
uv_count = th.get_instrument_count_of_type("UV")
```

#### `get_instrument_type(index) -> str`

```python
for i in range(th.get_instrument_count()):
    print(f"  Device {i}: {th.get_instrument_type(i)}")
```

#### `get_instrument_data() -> InstrumentInfo`

```python
info = th.get_instrument_data()
print(info.name, info.model, info.serial_number)
```

---

### File / Run Header Metadata

#### `get_file_info() -> FileInfo`

```python
fi = th.get_file_info()
print(fi.file_name)
print(fi.creation_date)
print(fi.operator)
print(fi.sample_name)
print(fi.sample_id)
print(fi.instrument_name)
print(fi.instrument_serial_number)
```

#### `get_instrument_method(index=0) -> str`

```python
method_text = th.get_instrument_method(0)
print(method_text[:200])
```

#### `get_all_instrument_names_from_method() -> List[str]`

```python
names = th.get_all_instrument_names_from_method()
for name in names:
    print(name)
```

---

### Scan Range & Retention Time

#### `get_scan_range() -> Tuple[int, int]`

```python
first, last = th.get_scan_range()
print(f"Scans: {first} to {last}")
```

#### `get_start_time() -> float` / `get_end_time() -> float`

```python
print(f"Run time: {th.get_start_time():.2f} – {th.get_end_time():.2f} min")
```

#### `get_retention_time(scan_number) -> float`

```python
rt = th.get_retention_time(100)
print(f"Scan 100 @ {rt:.3f} min")
```

#### `scan_number_from_retention_time(retention_time) -> int`

```python
scan = th.scan_number_from_retention_time(5.0)
print(f"Closest scan to 5.0 min: {scan}")
```

---

### Scan Filters & Events

#### `get_filters() -> List[str]`

```python
for filt in th.get_filters():
    print(filt)
# e.g. "FTMS + p NSI Full ms [200.00-2000.00]"
```

#### `get_filter_for_scan(scan_number) -> str`

```python
filt = th.get_filter_for_scan(1)
print(filt)
```

#### `get_scan_event_for_scan(scan_number) -> dict`

```python
ev = th.get_scan_event_for_scan(1)
print(ev["MSOrder"])   # 1
print(ev["Polarity"])  # "Positive"
print(ev["Detector"])  # "FTMS"
```

---

### Scan Statistics

#### `get_scan_stats(scan_number) -> ScanStats`

```python
stats = th.get_scan_stats(1)
print(f"TIC         : {stats.tic:.2e}")
print(f"Base peak   : m/z={stats.base_peak_mass:.4f}  I={stats.base_peak_intensity:.2e}")
print(f"Mass range  : {stats.low_mass:.1f}–{stats.high_mass:.1f}")
print(f"RT          : {stats.start_time:.3f} min")
print(f"Is centroid : {stats.is_centroid_scan}")
```

---

### Spectral Data – Centroid

#### `get_centroid_stream(scan_number, prefer_profile_data=False) -> CentroidData`

```python
centroid = th.get_centroid_stream(1)
print(f"Peaks: {len(centroid.masses)}")

# Iterate (mass, intensity) pairs
for mass, intensity in centroid.peaks:
    print(f"  {mass:.4f}  {intensity:.0f}")

# With noise and resolution
for m, i, n, r in zip(centroid.masses, centroid.intensities,
                       centroid.noises, centroid.resolutions):
    snr = i / n if n else float("inf")
    print(f"  m/z={m:.4f}  SNR={snr:.1f}  R={r:.0f}")
```

---

### Spectral Data – Profile

#### `get_profile_data(scan_number) -> ProfileData`

```python
profile = th.get_profile_data(1)

# Access flattened arrays
masses = profile.masses
intensities = profile.intensities

# Or iterate segments (each segment is a (positions, intensities) tuple)
for pos, inten in profile.segments:
    print(f"  Segment: {len(pos)} data points")
```

---

### High-level Scan Info

#### `get_scan_info(scan_number) -> ScanInfo`

Combines filter, event, stats, and trailer-extra into a single object.

```python
info = th.get_scan_info(500)
print(f"MS order        : {info.ms_order}")
print(f"RT              : {info.retention_time:.3f} min")
print(f"Filter          : {info.scan_filter}")
print(f"Injection time  : {info.injection_time:.2f} ms")
print(f"Is centroid     : {info.is_centroid}")

# For MS2+:
if info.ms_order >= 2:
    print(f"Precursor m/z   : {info.precursor_mass:.4f}")
    print(f"Charge state    : {info.precursor_charge}")
    print(f"Collision energy: {info.collision_energy:.1f} eV")
    print(f"Isolation width : {info.isolation_width:.2f} Th")
```

---

### Averaged Spectra

#### `average_scans_in_range(first_scan, last_scan, filter_string=None) -> AveragedScan`

```python
avg = th.average_scans_in_range(1, 50)
print(f"Averaged {avg.first_scan}–{avg.last_scan}: {len(avg.masses)} peaks")
```

#### `average_scans(scan_numbers) -> AveragedScan`

```python
# Average specific scans (e.g. all MS1 scans at a given retention time)
scan_list = [10, 20, 30, 40, 50]
avg = th.average_scans(scan_list)
```

---

### Chromatograms

#### `get_chromatogram(trace_type, mass_range, start_scan, end_scan) -> ChromatogramData`

```python
# Total ion chromatogram (TIC)
tic = th.get_chromatogram(trace_type="TIC")
for t, i in zip(tic.times, tic.intensities):
    print(f"  {t:.3f} min  {i:.2e}")

# Base peak chromatogram
bpc = th.get_chromatogram(trace_type="BasePeak")

# Extracted ion chromatogram (EIC) for a mass range
eic = th.get_chromatogram(
    trace_type="MassRange",
    mass_range="524.27-524.29",
)

# Restrict to a scan range
partial = th.get_chromatogram(
    trace_type="TIC",
    start_scan=100,
    end_scan=500,
)
```

---

### Trailer Extra Data

#### `get_trailer_data(scan_number) -> TrailerData`

```python
trailer = th.get_trailer_data(1)
for label, value in trailer.fields.items():
    print(f"  {label}: {value}")

# Common fields:
print(trailer.fields.get("Ion Injection Time (ms)"))
print(trailer.fields.get("Charge State:"))
print(trailer.fields.get("Monoisotopic M/Z:"))
print(trailer.fields.get("AGC:"))
```

#### `get_trailer_header_info() -> List[str]`

```python
labels = th.get_trailer_header_info()
print(labels)
```

---

### Status Log

#### `get_status_log_header_info() -> List[str]`

```python
log_labels = th.get_status_log_header_info()
```

#### `get_status_log_for_retention_time(retention_time) -> StatusLogEntry`

```python
entry = th.get_status_log_for_retention_time(5.0)
for label, value in entry.fields.items():
    print(f"  {label}: {value}")
```

#### `get_status_log_for_scan(scan_number) -> StatusLogEntry`

```python
entry = th.get_status_log_for_scan(200)
```

---

### Scan Dependents (MS^n)

#### `get_scan_dependents(scan_number, depth=1) -> ScanDependent`

```python
dep = th.get_scan_dependents(scan_number=10, depth=1)
print(f"Scan {dep.scan_number} triggered: {dep.dependent_scan_numbers}")
```

---

### Mass Precision Estimation

#### `get_mass_precision(scan_number) -> List[MassPrecision]`

Works on Orbitrap / FTMS scans only.

```python
estimates = th.get_mass_precision(1)
for e in estimates[:10]:
    print(
        f"  m/z={e.mass:.5f}  "
        f"ppm={e.mz_accuracy_mass:.3f}  "
        f"mmu={e.mz_accuracy_mmu:.3f}  "
        f"R={e.resolution:.0f}"
    )
```

---

### Bulk Iteration Helpers

#### `iter_scan_info(ms_order=None) -> Iterator[ScanInfo]`

```python
# All MS2 scan metadata
for info in th.iter_scan_info(ms_order=2):
    print(f"Scan {info.scan_number}  precursor={info.precursor_mass}")
```

#### `iter_centroid_data(ms_order=None) -> Iterator[CentroidData]`

```python
# Collect all MS1 centroids
ms1_spectra = list(th.iter_centroid_data(ms_order=1))
```

---

### Scan Quality Analysis

#### `analyze_all_scans() -> dict`

Walks every scan and checks for out-of-order masses (data integrity check).

```python
summary = th.analyze_all_scans()
print(f"Total scans       : {summary['total']}")
print(f"Centroid scans    : {summary['centroid']}")
print(f"Profile scans     : {summary['profile']}")
print(f"Out-of-order scans: {summary['out_of_order']}")
```

---

## Data Models

All methods return plain Python dataclasses — no .NET objects leak through.

| Class | Key Fields |
|---|---|
| `FileInfo` | `file_name`, `creation_date`, `operator`, `sample_name`, `instrument_name`, `instrument_serial_number` |
| `InstrumentInfo` | `device_type`, `name`, `model`, `serial_number`, `software_version`, `channel_labels` |
| `ScanStats` | `scan_number`, `start_time`, `tic`, `base_peak_mass`, `base_peak_intensity`, `low_mass`, `high_mass` |
| `CentroidData` | `masses`, `intensities`, `charges`, `noises`, `resolutions`, `peaks` (property) |
| `ProfileData` | `segments`, `masses` (property), `intensities` (property) |
| `ScanInfo` | `ms_order`, `retention_time`, `scan_filter`, `precursor_mass`, `collision_energy`, `isolation_width` |
| `ChromatogramData` | `trace_type`, `mass_range`, `times`, `intensities` |
| `TrailerData` | `scan_number`, `fields` (dict) |
| `StatusLogEntry` | `retention_time`, `fields` (dict) |
| `ScanDependent` | `scan_number`, `dependent_scan_numbers` |
| `MassPrecision` | `mass`, `mz_accuracy_mass` (ppm), `mz_accuracy_mmu`, `resolution` |
| `AveragedScan` | `first_scan`, `last_scan`, `masses`, `intensities` |

---

## Exceptions

| Exception | When raised |
|---|---|
| `RawFileError` | Base class for all adapter errors |
| `RawFileNotOpenError` | File could not be opened or is not open |
| `RawFileInAcquisitionError` | File is still being written by the instrument |
| `InstrumentSelectionError` | Requested device type / instance not available |
| `ScanNotFoundError` | Scan number outside the valid range |
| `AssemblyLoadError` | DLLs not found or pythonnet not installed |

```python
from tracehunter.exceptions import ScanNotFoundError, RawFileNotOpenError

try:
    centroid = th.get_centroid_stream(99999)
except ScanNotFoundError as e:
    print(f"Bad scan: {e}")
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `RAWFILEREADER_LIBS` | Path to the folder containing the RawFileReader `.dll` files |

```bash
export RAWFILEREADER_LIBS=/opt/thermo/libs
python my_script.py
```

---

## Examples

### Example 1 – Print file summary

```python
from tracehunter import TraceHunter

with TraceHunter("sample.raw") as th:
    fi = th.get_file_info()
    first, last = th.get_scan_range()

    print(f"File    : {fi.file_name}")
    print(f"Date    : {fi.creation_date}")
    print(f"Operator: {fi.operator}")
    print(f"Sample  : {fi.sample_name}")
    print(f"Instrument: {fi.instrument_name} ({fi.instrument_serial_number})")
    print(f"Scans   : {first}–{last}")
    print(f"RT range: {th.get_start_time():.2f}–{th.get_end_time():.2f} min")
```

### Example 2 – Extract all MS1 spectra to a list of dicts

```python
from tracehunter import TraceHunter

results = []
with TraceHunter("sample.raw") as th:
    for info in th.iter_scan_info(ms_order=1):
        centroid = th.get_centroid_stream(info.scan_number)
        results.append({
            "scan": info.scan_number,
            "rt": info.retention_time,
            "peaks": centroid.peaks,
        })

print(f"Collected {len(results)} MS1 scans")
```

### Example 3 – Build a TIC and export to CSV

```python
import csv
from tracehunter import TraceHunter

with TraceHunter("sample.raw") as th:
    tic = th.get_chromatogram(trace_type="TIC")

with open("tic.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["retention_time_min", "intensity"])
    writer.writerows(zip(tic.times, tic.intensities))

print("TIC exported to tic.csv")
```

### Example 4 – Dump MS2 scan info with precursor details

```python
from tracehunter import TraceHunter

with TraceHunter("sample.raw") as th:
    for info in th.iter_scan_info(ms_order=2):
        print(
            f"Scan {info.scan_number:5d} "
            f"RT={info.retention_time:.3f} min  "
            f"precursor={info.precursor_mass or 'N/A':.4f}  "
            f"z={info.precursor_charge}  "
            f"CE={info.collision_energy:.1f} eV"
        )
```

### Example 5 – Average MS1 scans in a retention-time window

```python
from tracehunter import TraceHunter

with TraceHunter("sample.raw") as th:
    t_start, t_end = 5.0, 5.5   # minutes
    s_start = th.scan_number_from_retention_time(t_start)
    s_end   = th.scan_number_from_retention_time(t_end)

    avg = th.average_scans_in_range(s_start, s_end)
    print(f"Averaged {avg.first_scan}–{avg.last_scan} ({len(avg.masses)} peaks)")
    for m, i in zip(avg.masses[:10], avg.intensities[:10]):
        print(f"  {m:.4f}  {i:.2e}")
```

### Example 6 – Inspect trailer-extra and status log for a scan

```python
from tracehunter import TraceHunter

with TraceHunter("sample.raw") as th:
    scan = 42
    trailer = th.get_trailer_data(scan)
    print("Trailer extra:")
    for k, v in trailer.fields.items():
        print(f"  {k}: {v}")

    log = th.get_status_log_for_scan(scan)
    print("\nStatus log @ RT={log.retention_time:.3f} min:")
    for k, v in log.fields.items():
        print(f"  {k}: {v}")
```

### Example 7 – Mass precision for an Orbitrap scan

```python
from tracehunter import TraceHunter

with TraceHunter("sample.raw") as th:
    estimates = th.get_mass_precision(1)
    print(f"{'m/z':>12}  {'ppm':>8}  {'mmu':>8}  {'Resolution':>12}")
    for e in estimates[:20]:
        print(f"{e.mass:12.5f}  {e.mz_accuracy_mass:8.3f}  "
              f"{e.mz_accuracy_mmu:8.4f}  {e.resolution:12.0f}")
```

### Example 8 – List all instruments and their types

```python
from tracehunter import TraceHunter

with TraceHunter("sample.raw") as th:
    n = th.get_instrument_count()
    print(f"Found {n} instrument device(s):")
    for i in range(n):
        dtype = th.get_instrument_type(i)
        print(f"  [{i}] {dtype}")

    # Try selecting each MS device
    ms_count = th.get_instrument_count_of_type("MS")
    for instance in range(1, ms_count + 1):
        th.select_instrument("MS", instance)
        idata = th.get_instrument_data()
        print(f"MS instance {instance}: {idata.name} ({idata.serial_number})")
```

### Example 9 – Find MS^n scan tree

```python
from tracehunter import TraceHunter

with TraceHunter("sample.raw") as th:
    first, last = th.get_scan_range()
    for scan in range(first, min(first + 200, last + 1)):
        info = th.get_scan_info(scan)
        if info.ms_order == 1:
            deps = th.get_scan_dependents(scan)
            if deps.dependent_scan_numbers:
                print(f"MS1 scan {scan} -> MS2 scans: {deps.dependent_scan_numbers}")
```

### Example 10 – Run data-integrity check

```python
from tracehunter import TraceHunter

with TraceHunter("sample.raw") as th:
    summary = th.analyze_all_scans()
    print(f"Total          : {summary['total']}")
    print(f"Centroid scans : {summary['centroid']}")
    print(f"Profile scans  : {summary['profile']}")
    print(f"Out-of-order   : {summary['out_of_order']}")
    if summary["out_of_order"] == 0:
        print("All scans passed mass-ordering check.")
    else:
        print(f"WARNING: {summary['out_of_order']} scan(s) have out-of-order masses!")
```

---

## License

The Python adapter code in this repository is released under the MIT License.

The Thermo Fisher Scientific RawFileReader assemblies are distributed under a separate [End User License Agreement](https://github.com/thermofisherlsms/RawFileReader/blob/main/License.doc).  You must accept that agreement before using those assemblies.
