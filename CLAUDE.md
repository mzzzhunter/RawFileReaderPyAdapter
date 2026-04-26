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
├── rawfilereader/          # The Python package
│   ├── __init__.py         # Public API exports + __version__
│   ├── adapter.py          # Monolithic RawFileAdapter class (~1400 lines)
│   ├── models.py           # All return-type dataclasses
│   ├── loader.py           # .NET assembly discovery and loading
│   └── exceptions.py       # Custom exception hierarchy
├── libs/                   # RawFileReader DLLs (Net8/Assemblies/)
├── colab_demo.ipynb        # Google Colab demo notebook
├── sample.raw              # Sample file for the demo (gitignored)
├── README.md               # User-facing documentation
├── setup.py                # Package metadata (setuptools)
└── requirements.txt        # pythonnet>=3.0.3
```

There are no tests, no CI configuration, no `pyproject.toml`, and no `Makefile`.

---

## Key Architectural Conventions

### 1. No .NET Objects Leak to Callers

Every public method on `RawFileAdapter` converts .NET objects to plain Python dataclasses before returning. Callers never receive a `pythonnet` proxy object. This is the most important design rule — always convert at the boundary.

### 2. All Return Types Are Dataclasses Defined in `models.py`

All public data models live in `rawfilereader/models.py`:

| Dataclass | Returned by |
|---|---|
| `FileInfo` | `get_file_info()` |
| `RunHeaderInfo` | `get_run_header_info()` |
| `FileError` | `get_file_error()` |
| `InstrumentInfo` | `get_instrument_data()` |
| `ScanStats` | `get_scan_stats()` |
| `CentroidData` | `get_centroid_stream()`, `iter_centroid_data()` |
| `ProfileData` | `get_profile_data()` |
| `ScanInfo` | `get_scan_info()`, `iter_scan_info()` |
| `ChromatogramData` | `get_chromatogram()` |
| `TrailerData` | `get_trailer_data()` |
| `StatusLogEntry` | `get_status_log_for_scan()`, `get_status_log_for_retention_time()` |
| `ScanDependent` | `get_scan_dependents()` |
| `MassPrecision` | `get_mass_precision()` (list) |
| `AveragedScan` | `average_scans_in_range()`, `average_scans()` |
| `SubtractedSpectrum` | `subtract_spectra()` |
| `BackgroundSubtractedSpectrum` | `subtract_background()` |

When adding a new method that returns structured data, add a new dataclass to `models.py` first, then implement the adapter method.

### 3. Convenience Properties on Dataclasses

Some dataclasses expose computed properties for ergonomics:
- `CentroidData.peaks` → `List[Tuple[float, float]]` (mass, intensity pairs)
- `ProfileData.masses` / `.intensities` → flattened from `segments`
- `SubtractedSpectrum.peaks` → clipped (non-negative) (mass, intensity) pairs
- `BackgroundSubtractedSpectrum.peaks` → (mass, intensity) pairs

Follow this pattern when a derived view of the data is clearly useful.

### 4. .NET Imports Are Deferred to `open()`

All .NET types are imported in a single block inside `RawFileAdapter.open()` and stored as instance attributes (`self._Device`, `self._MassOptions`, etc.). No method body ever performs its own `import`. This prevents `ImportError` at import time when DLLs are absent.

### 5. Reflection Helper for Hidden Interface Methods

Some .NET methods live on the concrete `RawFileAccess` class rather than on the `IRawDataPlus` interface proxy. The module-level `_reflect_call(obj, method_name, *args)` helper in `adapter.py` uses .NET reflection to locate and invoke these methods. It searches public methods first, then widens to non-public + name-suffix matching for explicit interface implementations.

Used by: `average_scans_in_range()`, `average_scans()`.

### 6. Exception Hierarchy

All custom exceptions inherit from `RawFileError` (defined in `exceptions.py`):

```
RawFileError
├── RawFileNotOpenError        — file not open / open failed
├── RawFileInAcquisitionError  — file still being written by instrument
├── InstrumentSelectionError   — device type/instance not available
├── ScanNotFoundError          — scan number out of range
└── AssemblyLoadError          — pythonnet or DLL missing
```

Use the most specific exception. Never raise bare `Exception` or `RuntimeError`.

Note: `FileError` is a **dataclass** (returned by `get_file_error()`), not an exception.

### 7. Assembly Loading (`loader.py`)

`load_assemblies()` is idempotent (guarded by `_loaded` module flag). DLL discovery priority:
1. Explicit `libs_dir` argument
2. `RAWFILEREADER_LIBS` environment variable
3. Auto-discovery: `../libs/Net8/Assemblies/`, `../libs/`, `../Libs/`, `./libs/` relative to the package

Required DLLs (Net8 build):
- `ThermoFisher.CommonCore.Data.dll`
- `ThermoFisher.CommonCore.RawFileReader.dll`
- `ThermoFisher.CommonCore.BackgroundSubtraction.dll`
- `OpenMcdf.dll`, `OpenMcdf.Extensions.dll`

### 8. Context Manager

`RawFileAdapter` implements `__enter__` / `__exit__`. Always prefer using `with RawFileAdapter(...) as rf:` in examples and documentation.

---

## Pure-Python Helpers in `adapter.py`

Module-level helpers in `adapter.py` support spectral subtraction and averaging (no .NET dependency):

| Helper | Purpose |
|---|---|
| `_reflect_call(obj, name, *args)` | .NET reflection — invoke hidden interface methods |
| `_apply_mass_range(masses, intensities, range)` | Filter lists to a m/z window |
| `_normalize_to_tic(intensities)` | Divide by sum (TIC normalisation) |
| `_find_closest(target, sorted_masses, tol_ppm)` | Binary-search with ppm tolerance |
| `_linear_interp(x_out, x_in, y_in)` | Linear interpolation for profile grids |
| `_py_subtract_peaks(fg_m, fg_i, bg_m, bg_i, tol_ppm)` | Subtract background peaks (fallback) |
| `_average_centroid_peaks(masses_list, intensities_list)` | Merge + average centroid peaks (fallback) |

Keep these functions free of .NET imports.

---

## Adding New Adapter Methods

Follow this checklist:

1. **Define the return type** as a `@dataclass` in `rawfilereader/models.py`.
2. **Import the new dataclass** in `rawfilereader/adapter.py` (top-level import block).
3. **Implement the method** on `RawFileAdapter`:
   - Call `self._check_open()` at the top to guard against closed-file access.
   - Use `self._raw_file` (the `IRawDataPlus` .NET object) to call .NET API.
   - Convert all .NET values to Python primitives before building the dataclass.
   - Document parameters and raises in a NumPy-style docstring.
4. **Export the dataclass** from `rawfilereader/__init__.py` (both import and `__all__`).
5. **Update README.md** with an API reference entry and, if appropriate, a usage example.

---

## Scope

Every public method on `RawFileAdapter` is a thin wrapper around one or more RawFileReader DLL calls. **Do not add pure-Python algorithms** unless they are needed to support a DLL-backed feature (e.g. the subtraction math in `subtract_spectra` or the averaging fallback). If a feature is not implemented by the underlying DLL or its pure-Python fallback, it does not belong in this adapter.

---

## Public API Surface

Everything exported from `rawfilereader/__init__.py` is public. Adding or removing exports is a breaking change. The current public names are:

**Classes:** `RawFileAdapter`

**Models:** `AveragedScan`, `BackgroundSubtractedSpectrum`, `CentroidData`, `ChromatogramData`, `FileError`, `FileInfo`, `InstrumentInfo`, `MassPrecision`, `ProfileData`, `RunHeaderInfo`, `ScanDependent`, `ScanInfo`, `ScanStats`, `StatusLogEntry`, `SubtractedSpectrum`, `TrailerData`

**Exceptions:** `AssemblyLoadError`, `RawFileError`, `RawFileNotOpenError`, `RawFileInAcquisitionError`, `InstrumentSelectionError`, `ScanNotFoundError`

---

## Development Setup

```bash
# Install in editable mode with pythonnet
pip install -e .
```

The RawFileReader DLLs are shipped in `libs/Net8/Assemblies/` and discovered automatically.
To override, set `RAWFILEREADER_LIBS` to the folder containing the `.dll` files.

---

## Testing

There are currently no automated tests in this repository. When adding tests:
- Use `pytest` as the test runner.
- Place tests under a `tests/` directory.
- Tests that require real `.raw` files or the RawFileReader DLLs should be skipped when those resources are absent (use `pytest.importorskip` or a fixture that checks `RAWFILEREADER_LIBS`).
- The pure-Python helpers in `adapter.py` (`_apply_mass_range`, `_normalize_to_tic`, `_find_closest`, `_linear_interp`) can be tested without any DLLs.

---

## Git Workflow

- Active development branch: `main`
- Remote: `mzzzhunter/RawFileReaderPyAdapter`
- There are no protected branch rules or required CI checks currently.

---

## Key .NET Concepts (for context)

- `IRawDataPlus` — the main .NET interface representing an open RAW file.
- `Device` — a .NET enum for instrument device types (`MS`, `UV`, `PDA`, etc.). The string constants in `RawFileAdapter.DEVICE_TYPES` match these enum member names.
- `RawFileReaderAdapter.FileFactory(path)` — static factory that opens the file and returns an `IRawDataPlus`.
- Scan numbers in RawFileReader are **1-based**.
- Scan filters are human-readable strings like `"FTMS + p NSI Full ms [200.00-2000.00]"`.
- `IScanAveragePlus` — interface on the concrete class (not the proxy) that provides `AverageScansInScanRange`, `AverageScansInTimeRange`, `AverageScans`, and `SubtractScans`. Reached via `_reflect_call`.
