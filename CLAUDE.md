# CLAUDE.md — RawFileReaderPyAdapter

This file provides context for AI assistants working on this codebase.

---

## Project Overview

**RawFileReaderPyAdapter** is a Python wrapper around the Thermo Fisher Scientific RawFileReader .NET assemblies. It enables Python developers to read Thermo `.raw` mass spectrometry files without interacting with .NET objects directly. The bridge between Python and .NET is provided by `pythonnet` (the `clr` module).

- Package name (PyPI): `rawfilereader-python`
- Importable as: `rawfilereader`
- Version: `1.0.0`
- Python requirement: `>=3.8`
- Single Python dependency: `pythonnet>=3.0.3`

---

## Repository Structure

```
RawFileReaderPyAdapter/
├── rawfilereader/          # The Python package
│   ├── __init__.py         # Public API exports + __version__
│   ├── adapter.py          # Core RawFileAdapter class (~1250 lines)
│   ├── models.py           # All return-type dataclasses (~194 lines)
│   ├── loader.py           # .NET assembly discovery and loading (~129 lines)
│   └── exceptions.py       # Custom exception hierarchy (~26 lines)
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

All 13 public data models live in `rawfilereader/models.py`:

| Dataclass | Returned by |
|---|---|
| `FileInfo` | `get_file_info()` |
| `InstrumentInfo` | `get_instrument_data()` |
| `ScanStats` | `get_scan_stats()` |
| `CentroidData` | `get_centroid_stream()` |
| `ProfileData` | `get_profile_data()` |
| `ScanInfo` | `get_scan_info()`, `iter_scan_info()` |
| `ChromatogramData` | `get_chromatogram()` |
| `TrailerData` | `get_trailer_data()` |
| `StatusLogEntry` | `get_status_log_for_scan()` |
| `ScanDependent` | `get_scan_dependents()` |
| `MassPrecision` | `get_mass_precision()` |
| `AveragedScan` | `average_scans_in_range()`, `average_scans()` |
| `SubtractedSpectrum` | `subtract_spectra()` |

When adding a new method that returns structured data, add a new dataclass to `models.py` first, then implement the adapter method.

### 3. Convenience Properties on Dataclasses

Some dataclasses expose computed properties for ergonomics:
- `CentroidData.peaks` → `List[Tuple[float, float]]` (mass, intensity pairs)
- `ProfileData.masses` / `.intensities` → flattened from `segments`
- `SubtractedSpectrum.peaks` → clipped (non-negative) (mass, intensity) pairs

Follow this pattern when a derived view of the data is clearly useful.

### 4. Lazy .NET Imports

.NET types are never imported at module load time. They are imported inside `RawFileAdapter._import_dotnet_types()` and related helpers, which are called only after `load_assemblies()` has succeeded. This prevents `ImportError` at import time when DLLs are absent.

### 5. Exception Hierarchy

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

### 6. Assembly Loading (`loader.py`)

`load_assemblies()` is idempotent (guarded by `_loaded` module flag). DLL discovery priority:
1. Explicit `libs_dir` argument
2. `RAWFILEREADER_LIBS` environment variable
3. Auto-discovery: `../libs/`, `../Libs/`, `./libs/` relative to the package

Required DLLs:
- `ThermoFisher.CommonCore.Data.dll`
- `ThermoFisher.CommonCore.RawFileReader.dll`
- `ThermoFisher.CommonCore.MassPrecisionEstimator.dll`

Optional DLL (loaded silently if present):
- `ThermoFisher.CommonCore.BackgroundSubtraction.dll`

### 7. Context Manager

`RawFileAdapter` implements `__enter__` / `__exit__`. Always prefer using `with RawFileAdapter(...) as rf:` in examples and documentation.

---

## Adding New Adapter Methods

Follow this checklist:

1. **Define the return type** as a `@dataclass` in `rawfilereader/models.py`.
2. **Import the new dataclass** in `rawfilereader/adapter.py` (top-level import block).
3. **Implement the method** on `RawFileAdapter`:
   - Call `self._require_open()` at the top to guard against closed-file access.
   - Use `self._raw_file` (the `IRawDataPlus` .NET object) to call .NET API.
   - Convert all .NET values to Python primitives before building the dataclass.
   - Document parameters and raises in a NumPy-style docstring.
4. **Export the dataclass** from `rawfilereader/__init__.py` (both import and `__all__`).
5. **Update README.md** with an API reference entry and, if appropriate, a usage example.

---

## Pure-Python Helpers in `adapter.py`

Four module-level pure-Python helpers support the spectral subtraction feature (no .NET dependency):

| Helper | Purpose |
|---|---|
| `_apply_mass_range(masses, intensities, range)` | Filter lists to a m/z window |
| `_normalize_to_tic(intensities)` | Divide by sum (TIC normalisation) |
| `_find_closest(target, sorted_masses, tol_ppm)` | Binary-search with ppm tolerance |
| `_linear_interp(x_out, x_in, y_in)` | Linear interpolation for profile grids |

Keep these functions free of .NET imports. They are tested independently of any DLL.

---

## Public API Surface

Everything exported from `rawfilereader/__init__.py` is public. Adding or removing exports is a breaking change. The current public names are:

**Classes:** `RawFileAdapter`

**Models:** `ScanInfo`, `CentroidData`, `ProfileData`, `ChromatogramData`, `InstrumentInfo`, `FileInfo`, `ScanStats`, `TrailerData`, `StatusLogEntry`, `ScanDependent`, `MassPrecision`, `SubtractedSpectrum`

**Exceptions:** `RawFileError`, `RawFileNotOpenError`, `RawFileInAcquisitionError`, `InstrumentSelectionError`, `ScanNotFoundError`

Note: `AveragedScan` and `AssemblyLoadError` are defined internally but not currently exported via `__init__.py`.

---

## Development Setup

```bash
# Install in editable mode with pythonnet
pip install -e .

# Provide the RawFileReader DLLs (not included in repo)
# Option A: environment variable
export RAWFILEREADER_LIBS=/path/to/dlls

# Option B: place DLLs in libs/ next to the package
mkdir libs && cp *.dll libs/
```

DLLs must be the NetCore build from:
`https://github.com/thermofisherlsms/RawFileReader/tree/main/Libs/NetCore`

---

## Testing

There are currently no automated tests in this repository. When adding tests:
- Use `pytest` as the test runner.
- Place tests under a `tests/` directory.
- Tests that require real `.raw` files or the RawFileReader DLLs should be skipped when those resources are absent (use `pytest.importorskip` or a fixture that checks `RAWFILEREADER_LIBS`).
- The pure-Python helpers in `adapter.py` (`_apply_mass_range`, `_normalize_to_tic`, `_find_closest`, `_linear_interp`) can be tested without any DLLs.

---

## Git Workflow

- Active development branch: `claude/add-claude-documentation-Hs3Qi`
- Remote: `mzzzhunter/RawFileReaderPyAdapter`
- There are no protected branch rules or required CI checks currently.

---

## Key .NET Concepts (for context)

- `IRawDataPlus` — the main .NET interface representing an open RAW file.
- `Device` — a .NET enum for instrument device types (`MS`, `UV`, `PDA`, etc.). The string constants in `RawFileAdapter.DEVICE_TYPES` match these enum member names.
- `RawFileReaderAdapter.FileFactory(path)` — static factory that opens the file and returns an `IRawDataPlus`.
- Scan numbers in RawFileReader are **1-based**.
- Scan filters are human-readable strings like `"FTMS + p NSI Full ms [200.00-2000.00]"`.
