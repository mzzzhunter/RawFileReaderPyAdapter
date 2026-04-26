# CLAUDE.md — RawFileReaderPyAdapter

This file provides context for AI assistants working on this codebase.

---

## Project Overview

**RawFileReaderPyAdapter** is a Python wrapper around the Thermo Fisher Scientific RawFileReader .NET assemblies. It enables Python developers to read Thermo `.raw` mass spectrometry files without interacting with .NET objects directly. The bridge between Python and .NET is provided by `pythonnet` (the `clr` module).

- Package name (PyPI): `rawfilereader-python`
- Importable as: `rawfilereader`
- Version: `2.0.0`
- Python requirement: `>=3.8`
- Single Python dependency: `pythonnet>=3.0.3`

---

## Repository Structure

```
RawFileReaderPyAdapter/
├── rawfilereader/              # The Python package
│   ├── __init__.py             # Public API exports + __version__
│   ├── adapter.py              # RawFileAdapter class (mixin composition)
│   ├── models.py               # All return-type dataclasses
│   ├── loader.py               # .NET assembly discovery and loading
│   ├── exceptions.py           # Custom exception hierarchy
│   ├── _base.py                # RawFileBase — open/close/guards
│   ├── _headers.py             # HeadersMixin — file info, sample, run header
│   ├── _scans.py               # ScansMixin — centroid, profile, stats, filters
│   ├── _chromatograms.py       # ChromatogramsMixin — chromatograms
│   ├── _logs.py                # LogsMixin — trailer/status/tune/error logs
│   ├── _averaging.py           # AveragingMixin — averaging + subtraction
│   ├── _methods.py             # MethodsMixin — instrument method text
│   └── _threading.py           # RawFileThreadManager — threaded access
├── libs/Net8/Assemblies/       # Bundled RawFileReader DLLs (Net8 build)
├── colab_demo.ipynb            # Google Colab demo notebook
├── sample.raw                  # Demo RAW file for Colab
├── README.md                   # User-facing documentation
├── setup.py                    # Package metadata (setuptools)
└── requirements.txt            # pythonnet>=3.0.3
```

There are no automated tests, no CI configuration, and no `pyproject.toml`.

---

## Key Architectural Conventions

### 1. Mixin Architecture

`RawFileAdapter` (in `adapter.py`) is a thin class that inherits from multiple focused mixins:

```python
class RawFileAdapter(
    RawFileBase,       # open/close, _check_open, _check_scan
    HeadersMixin,      # get_file_info, get_run_header_info, get_sample_info, …
    ScansMixin,        # get_centroid_stream, get_scan_info, iter_scan_info, …
    ChromatogramsMixin,# get_chromatogram, get_chromatogram_by_time, …
    LogsMixin,         # get_trailer_data, get_status_log_for_scan, …
    AveragingMixin,    # average_scans, subtract_spectra, subtract_background, …
    MethodsMixin,      # has_instrument_method, get_instrument_method_text, …
):
```

Add new functionality to the appropriate mixin file, not to `adapter.py`.

### 2. No .NET Objects Leak to Callers

Every public method converts .NET objects to plain Python dataclasses before returning. Callers never receive a `pythonnet` proxy object.

### 3. All Return Types Are Dataclasses Defined in `models.py`

| Dataclass | Returned by |
|---|---|
| `FileInfo` | `get_file_info()` |
| `RunHeaderInfo` | `get_run_header_info()` |
| `RawFileError` | `get_file_error()` |
| `InstrumentInfo` | `get_instrument_data()` |
| `SampleInfo` | `get_sample_info()` |
| `AutoSamplerInfo` | `get_autosampler_info()` |
| `ScanStats` | `get_scan_stats()` |
| `CentroidData` | `get_centroid_stream()`, `iter_centroid_data()` |
| `ProfileData` | `get_profile_data()` |
| `ScanInfo` | `get_scan_info()`, `iter_scan_info()` |
| `ScanDependent` | `get_scan_dependents()` |
| `MassPrecision` | `get_mass_precision()` |
| `ChromatogramData` | `get_chromatogram()`, `get_chromatogram_by_time()`, `get_chromatogram_ex()` |
| `TrailerData` | `get_trailer_data()` |
| `StatusLogEntry` | `get_status_log_for_scan()`, `get_status_log_for_retention_time()` |
| `TuneData` | `get_tune_data()` |
| `ErrorLogEntry` | `get_error_log_entry()` |
| `AveragedScan` | `average_scans_in_range()`, `average_scans()`, `average_scans_in_time_range()` |
| `SubtractedSpectrum` | `subtract_spectra()` |
| `BackgroundSubtractedSpectrum` | `subtract_background()`, `subtract_scans()` |

### 4. Convenience Properties on Dataclasses

- `CentroidData.peaks` → `List[Tuple[float, float]]` (mass, intensity pairs)
- `ProfileData.masses` / `.intensities` → flattened from `segments`
- `SubtractedSpectrum.peaks` → clipped (non-negative) (mass, intensity) pairs
- `BackgroundSubtractedSpectrum.peaks` → (mass, intensity) pairs

### 5. Reflection Helper (`_reflect_call` in `_averaging.py`)

pythonnet 3.x interface proxies only expose methods declared on the interface type. `RawFileAccess` concrete methods (averaging, subtraction) require reflection to call. `_reflect_call(obj, method_name, *args)` does a 2-pass search: public methods first, then non-public with name-suffix matching for explicit interface implementations.

### 6. Lazy .NET Imports

.NET types are imported inside mixin methods (or via `_base.py` helpers), never at module load time. This prevents `ImportError` when DLLs are absent at import time.

### 7. Pure-Python Spectral Helpers (in `_averaging.py`)

Four module-level pure-Python helpers support `subtract_spectra` (no .NET dependency):

| Helper | Purpose |
|---|---|
| `_apply_mass_range(masses, intensities, range)` | Filter lists to a m/z window |
| `_normalize_to_tic(intensities)` | Divide by sum (TIC normalisation) |
| `_find_closest(target, sorted_masses, tol_ppm)` | Binary-search with ppm tolerance |
| `_linear_interp(x_out, x_in, y_in)` | Linear interpolation for profile grids |

### 8. Exception Hierarchy

All custom exceptions inherit from `RawFileError` (defined in `exceptions.py`):

```
RawFileError
├── RawFileNotOpenError        — file not open / open failed
├── RawFileInAcquisitionError  — file still being written by instrument
├── InstrumentSelectionError   — device type/instance not available
├── ScanNotFoundError          — scan number out of range
└── AssemblyLoadError          — pythonnet or DLL missing
```

### 9. Assembly Loading (`loader.py`)

`load_assemblies()` is idempotent (guarded by `_loaded` module flag). DLL discovery priority:
1. Explicit `libs_dir` argument
2. `RAWFILEREADER_LIBS` environment variable
3. Auto-discovery: `libs/Net8/Assemblies/` next to the repo root, then `./libs/`

DLLs bundled in `libs/Net8/Assemblies/`:
- `ThermoFisher.CommonCore.Data.dll` (required)
- `ThermoFisher.CommonCore.RawFileReader.dll` (required)
- `ThermoFisher.CommonCore.MassPrecisionEstimator.dll` (required)
- `ThermoFisher.CommonCore.BackgroundSubtraction.dll` (optional — loaded silently if present)
- `OpenMcdf.dll`, `OpenMcdf.Extensions.dll` (required)

### 10. Context Manager

`RawFileAdapter` implements `__enter__` / `__exit__`. Always prefer `with RawFileAdapter(...) as rf:` in examples.

---

## Adding New Adapter Methods

1. **Define the return type** as a `@dataclass` in `rawfilereader/models.py`.
2. **Implement the method** in the appropriate mixin (`_headers.py`, `_scans.py`, `_logs.py`, `_averaging.py`, `_methods.py`, etc.).
   - Call `self._check_open()` at the top.
   - Use `self._raw_file` (the `IRawDataPlus` .NET proxy) to call .NET API.
   - Convert all .NET values to Python primitives before building the dataclass.
   - Document parameters and raises in a NumPy-style docstring.
3. **Export the dataclass** from `rawfilereader/__init__.py` (both import and `__all__`).
4. **Update README.md** with an API reference entry and, if appropriate, a usage example.

---

## Public API Surface

Everything exported from `rawfilereader/__init__.py` is public. Adding or removing exports is a breaking change.

**Classes:** `RawFileAdapter`, `RawFileThreadManager`

**Models:** `AveragedScan`, `AutoSamplerInfo`, `BackgroundSubtractedSpectrum`, `CentroidData`, `ChromatogramData`, `ErrorLogEntry`, `FileInfo`, `InstrumentInfo`, `MassPrecision`, `ProfileData`, `RawFileError`, `RunHeaderInfo`, `SampleInfo`, `ScanDependent`, `ScanInfo`, `ScanStats`, `StatusLogEntry`, `SubtractedSpectrum`, `TrailerData`, `TuneData`

**Exceptions:** `AssemblyLoadError`, `InstrumentSelectionError`, `RawFileError`, `RawFileInAcquisitionError`, `RawFileNotOpenError`, `ScanNotFoundError`

---

## Development Setup

```bash
pip install -e .
# DLLs are bundled in libs/Net8/Assemblies/ — no separate download needed.
# To use DLLs from a different location:
export RAWFILEREADER_LIBS=/path/to/dlls
```

---

## Testing

There are currently no automated tests. When adding tests:
- Use `pytest` as the test runner under a `tests/` directory.
- Skip tests that need real `.raw` files or DLLs when those are absent (`pytest.importorskip` or a fixture that checks `RAWFILEREADER_LIBS`).
- The pure-Python helpers in `_averaging.py` (`_apply_mass_range`, `_normalize_to_tic`, `_find_closest`, `_linear_interp`) can be tested without any DLLs.

---

## Git Workflow

- Active development branch: `claude/add-claude-documentation-Hs3Qi`
- Remote: `mzzzhunter/RawFileReaderPyAdapter`
- There are no protected branch rules or required CI checks currently.

---

## Key .NET Concepts (for context)

- `IRawDataPlus` — the main .NET interface representing an open RAW file.
- `IScanAveragePlus` — interface with `AverageScans`, `AverageScansInScanRange`, `AverageScansInTimeRange`, `SubtractScans`.
- `Device` — .NET enum for instrument device types (`MS`, `UV`, `PDA`, etc.).
- `RawFileReaderAdapter.FileFactory(path)` — static factory that opens the file and returns an `IRawDataPlus`.
- Scan numbers in RawFileReader are **1-based**.
- Scan filters are human-readable strings like `"FTMS + p NSI Full ms [200.00-2000.00]"`.
