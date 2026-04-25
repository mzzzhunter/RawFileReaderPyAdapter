# RawFileReaderPyAdapter — Function Tree & Dependency Map

Source material: `UsingRawFileReader.docx` (Thermo Fisher, Rev. Dec 7 2015) and the four
IntelliSense XML schemas shipped with the DLLs.

---

## 1. .NET Interface Hierarchy

```
ThermoFisher.CommonCore.Data.dll
│
├── IRawDataProperties  ← base for all raw-data interfaces
│   ├── .Path               string   path where file was originally created
│   ├── .FileName           string   acquired file name (no path)
│   ├── .CreationDate       DateTime
│   ├── .CreatorId          string
│   ├── .SampleInformation  SampleInformation
│   ├── .IsError            bool
│   ├── .InAcquisition      bool     file still being written
│   └── .IsOpen             bool
│
├── IRawData  (extends IRawDataProperties)
│   ├── .RunHeader                     RunHeader
│   ├── .InstrumentCount               int
│   ├── .InstrumentMethodsCount        int
│   ├── .IncludeReferenceAndExceptionData  bool (get/set)
│   ├── .SelectedInstrument            IInstrumentSelectionAccess
│   ├── SelectInstrument(Device, int)
│   ├── GetInstrumentCountOfType(Device)  → int
│   ├── GetInstrumentType(int)            → Device
│   ├── GetAllInstrumentNamesFromInstrumentMethod()  → string[]
│   ├── GetInstrumentMethod(int)           → string
│   └── RefreshViewOfFile()                (live-acquisition reload)
│
├── IRawDataPlus  (extends IRawData)
│   ├── .FileHeader            IFileHeader
│   ├── .FileError             IFileError
│   ├── .AutoSamplerInformation  IAutoSamplerInformation
│   ├── .HasInstrumentMethod   bool
│   ├── .HasMsData             bool
│   ├── .ComputerName          string
│   ├── .UserLabel             string[]
│   ├── .RunHeaderEx           IRunHeaderEx
│   │       ├── .FirstSpectrumNumber   int   (1-based)
│   │       ├── .LastSpectrumNumber    int
│   │       ├── .StartTime             double  (minutes)
│   │       ├── .EndTime               double
│   │       ├── .ErrorLogCount         int
│   │       └── .TrailerExtraCount     int
│   ├── .ScanEvents            IScanEvents
│   │
│   ├── — Instrument —
│   ├── GetInstrumentData()   → InstrumentData
│   ├── GetAllInstrumentFriendlyNamesFromInstrumentMethod()  → string[]
│   └── ExportInstrumentMethod(string path, bool forceOverwrite)  → bool
│
│   ├── — Scan access —
│   ├── GetScanStatsForScanNumber(int)               → ScanStatistics
│   ├── GetSegmentedScanFromScanNumber(int, ScanStatistics?)  → SegmentedScan
│   │       ├── .SegmentCount          int
│   │       ├── .SegmentLengths        ReadOnlyCollection<int>
│   │       ├── .Intensities           double[]
│   │       ├── .Positions             double[]   (m/z or wavelength)
│   │       ├── .Flags                 PeakOptions[]
│   │       └── .MassRanges            ReadOnlyCollection<IRangeAccess>
│   ├── GetCentroidStream(int, bool preferProfileData)  → CentroidStream
│   ├── RetentionTimeFromScanNumber(int)   → double
│   └── ScanNumberFromRetentionTime(double) → int
│
│   ├── — Filters & Events —
│   ├── GetFilters()                         → ReadOnlyCollection<IScanFilter>
│   ├── GetFilterForScanNumber(int)          → IScanFilter
│   ├── GetFilterFromString(string)          → IScanFilter
│   ├── GetFilterFromString(string, int precision) → IScanFilter
│   ├── GetScanEventForScanNumber(int)       → IScanEvent
│   ├── GetScanEventStringForScanNumber(int) → string
│   ├── GetFilteredScanEnumerator(IScanFilter)  → IEnumerable<int>
│   ├── GetFilteredScanEnumeratorOverTime(IScanFilter, double, double) → IEnumerable<int>
│   ├── GetFilteredScanIterator(IScanFilter) → IFilteredScanIterator
│   └── TestScan(int, string)               → bool
│
│   ├── — Chromatogram —
│   ├── GetChromatogramData(IChromatogramSettings[], int, int)  → IChromatogramData
│   ├── GetChromatogramData(IChromatogramSettings[], int, int, MassOptions)
│   ├── GetChromatogramDataEx(IChromatogramSettingsEx[], int, int)  → IChromatogramDataPlus
│   └── GetChromatogramDataEx(IChromatogramSettingsEx[], int, int, MassOptions)
│
│   ├── — Logs —
│   ├── GetTrailerExtraHeaderInformation()   → HeaderItem[]
│   ├── GetTrailerExtraInformation(int)      → LogEntry
│   ├── GetTrailerExtraValues(int, bool)     → string[]
│   ├── GetTrailerExtraValue(int, int)       → object
│   ├── GetStatusLogHeaderInformation()      → HeaderItem[]
│   ├── GetStatusLogForRetentionTime(double) → LogEntry
│   ├── GetStatusLogEntriesCount()           → int
│   ├── GetStatusLogValues(int, bool)        → StatusLogValues
│   ├── GetStatusLogAtPosition(int)          → ISingleValueStatusLog
│   ├── GetErrorLogItem(int)                 → IErrorLogEntry
│   ├── GetTuneDataHeaderInformation()       → HeaderItem[]
│   ├── GetTuneData(int)                     → LogEntry
│   └── GetTuneDataCount()                   → int
│
│   └── — Scan dependents —
│       └── GetScanDependents(int scanNumber, int filterPrecisionDecimals)  → IScanDependents
│
├── IRawDataExtended  (extends IRawDataPlus)  ← what FileFactory() actually returns
│   ├── GetDetectorReader(IInstrumentSelectionAccess, bool)  → IDetectorReader
│   ├── GetAdditionalScanData(int)   → byte[]
│   ├── GetExtendedScanData(int)     → IReadOnlyList<IDataBlock>
│   └── GetSortedStatusLogEntry(int) → LogEntry
│
└── IRawFileThreadManager / IRawFileThreadAccessor
    └── CreateThreadAccessor()  → IRawDataPlus   (one per thread)

ThermoFisher.CommonCore.RawFileReader.dll
└── RawFileReaderAdapter  [static factory class]
    ├── FileFactory(string path)                          → IRawDataExtended
    ├── ThreadedFileFactory(string path)                  → IRawFileThreadAccessor
    ├── DelegatedAccessFileFactory(string, IViewCollectionManager)
    ├── RandomAccessThreadedFileFactory(string, IViewCollectionManager)
    ├── DelegatedRandomAccessThreadedFileFactory(string, IViewCollectionManager)
    ├── FileHeaderFactory(string path)                    → IFileHeader  (file closed after)
    └── ScanDecoderFactory(byte[], IMsScanIndexAccess, int)

ThermoFisher.CommonCore.BackgroundSubtraction.dll
└── Extension methods on IRawDataPlus  (via BackgroundSubtractor / ScanAverager)
    ├── AverageScans(List<int> scanNumbers, MassOptions)           → Scan
    ├── AverageScans(List<ScanStatistics>, MassOptions)            → Scan
    ├── AverageScansInScanRange(int first, int last, string filter, MassOptions) → Scan
    ├── AverageScansInScanRange(int, int, IScanFilter, MassOptions)
    ├── AverageScansInTimeRange(double, double, string, MassOptions)
    ├── AverageScansInTimeRange(double, double, IScanFilter, MassOptions)
    └── SubtractScans(Scan foreground, Scan background)            → Scan

ThermoFisher.CommonCore.MassPrecisionEstimator.dll
└── PrecisionEstimate  (implements IPrecisionEstimate)
    ├── .Rawfile      IRawData   (set before calling)
    ├── .ScanNumber   int        (set before calling)
    ├── GetIonTime(MassAnalyzerType, Scan, List<string>, List<string>)  → double
    ├── GetMassPrecisionEstimate(Scan, MassAnalyzerType, double, double)  → List<EstimatorResults>
    └── GetMassPrecisionEstimate()                                         → List<EstimatorResults>
        └── EstimatorResults fields:
            ├── .Mass               double
            ├── .Intensity          double
            ├── .Resolution         double
            ├── .MassAccuracyInPpm  double
            └── .MassAccuracyInMmu  double

OpenMcdf.dll / OpenMcdf.Extensions.dll
└── Compound Document (OLE/COM structured storage) reader — used internally
    by RawFileReader to navigate the binary .raw file format
```

---

## 2. Python Package Function Tree

```
rawfilereader/  (importable as `rawfilereader`, PyPI: rawfilereader-python)
│
├── exceptions.py
│   └── RawFileError(Exception)                   ← base for all package errors
│       ├── RawFileNotOpenError                   file not open / open failed
│       ├── RawFileInAcquisitionError             file still being acquired
│       ├── InstrumentSelectionError              device type / instance unavailable
│       ├── ScanNotFoundError                     scan number out of range
│       └── AssemblyLoadError                     pythonnet or DLL missing
│
├── models.py  (plain dataclasses; no .NET dependency)
│   ├── FileInfo
│   │   fields: file_name, creation_date, operator, comment, sample_name,
│   │           sample_id, sample_type, vial, instrument_method, tune_method,
│   │           acquisition_software_version, instrument_name,
│   │           instrument_serial_number, number_of_ms_orders, has_ms_data
│   │
│   ├── InstrumentInfo
│   │   fields: device_type, instance_number, name, model, serial_number,
│   │           software_version, hardware_version, units, channel_labels
│   │
│   ├── ScanStats
│   │   fields: scan_number, start_time, low_mass, high_mass, tic,
│   │           base_peak_mass, base_peak_intensity, packet_count,
│   │           scan_event_number, master_index, is_centroid_scan
│   │
│   ├── CentroidData
│   │   fields: scan_number, masses, intensities, charges, baselines,
│   │           noises, resolutions, is_exceptional, is_reference
│   │   └── .peaks  [property] → List[Tuple[float, float]]
│   │       zip(masses, intensities)
│   │
│   ├── ProfileData
│   │   fields: scan_number, segments: List[Tuple[positions, intensities]]
│   │   ├── .masses      [property] → List[float]   (flattened segments)
│   │   └── .intensities [property] → List[float]   (flattened segments)
│   │
│   ├── ScanInfo
│   │   fields: scan_number, scan_filter, ms_order, retention_time,
│   │           injection_time, is_centroid, detector_type, activation_type,
│   │           precursor_mass?, precursor_charge?, collision_energy?,
│   │           isolation_width?, monoisotopic_mass?, ion_injection_time?
│   │
│   ├── ChromatogramData
│   │   fields: trace_type, mass_range, times, intensities
│   │
│   ├── TrailerData
│   │   fields: scan_number, fields: dict[label → value]
│   │
│   ├── StatusLogEntry
│   │   fields: retention_time, fields: dict[label → value]
│   │
│   ├── ScanDependent
│   │   fields: scan_number, dependent_scan_numbers: List[int]
│   │
│   ├── MassPrecision
│   │   fields: mass, intensity, resolution, mz_accuracy_mass (ppm),
│   │           mz_accuracy_mmu (mmu)
│   │
│   ├── AveragedScan
│   │   fields: first_scan, last_scan, masses, intensities
│   │
│   ├── BackgroundSubtractedSpectrum
│   │   fields: scan_number, background_scans, scan_filter, masses, intensities
│   │   └── .peaks  [property] → List[Tuple[float, float]]
│   │       zip(masses, intensities)
│   │
│   └── SubtractedSpectrum
│       fields: scan_a, scan_b, scan_filter, mass_range?, is_centroid,
│               masses, intensities (signed), intensities_clipped (≥0)
│       └── .peaks  [property] → List[Tuple[float, float]]
│           [(m, i) for m, i in zip(masses, intensities_clipped) if i > 0]
│
├── loader.py
│   ├── _find_libs_dir() → Optional[Path]
│   │   Priority order:
│   │   1. RAWFILEREADER_LIBS environment variable
│   │   2. <package_root>/lib/Net8/Assemblies/
│   │   3. <package_root>/libs/Net8/Assemblies/       ← actual location
│   │   4. <package_root>/libs/
│   │   5. <package_root>/Libs/
│   │   6. <package_dir>/libs/
│   │
│   └── load_assemblies(libs_dir: Optional[str] = None) → None
│       (idempotent — guarded by module-level _loaded flag)
│       ├── calls _find_libs_dir() when libs_dir is None
│       ├── import clr  (pythonnet ≥ 3.0.3)
│       ├── sys.path.append(search_dir)
│       └── clr.AddReference(dll_path) for each of 6 required DLLs:
│           ├── OpenMcdf.dll
│           ├── OpenMcdf.Extensions.dll
│           ├── ThermoFisher.CommonCore.Data.dll
│           ├── ThermoFisher.CommonCore.RawFileReader.dll
│           ├── ThermoFisher.CommonCore.MassPrecisionEstimator.dll
│           └── ThermoFisher.CommonCore.BackgroundSubtraction.dll
│
├── adapter.py
│   │
│   ├── Module-level pure-Python helpers  (no .NET dependency)
│   │   │
│   │   ├── _apply_mass_range(masses, intensities, mass_range)
│   │   │       → Tuple[List[float], List[float]]
│   │   │   Filters both lists to keep only entries where
│   │   │   mass_range[0] ≤ mass ≤ mass_range[1].
│   │   │
│   │   ├── _normalize_to_tic(intensities)
│   │   │       → List[float]
│   │   │   Divides each intensity by sum(intensities) (TIC normalisation).
│   │   │   Returns original list unchanged if sum is zero.
│   │   │
│   │   ├── _find_closest(target, sorted_masses, tol_ppm)
│   │   │       → Optional[int]
│   │   │   Binary search into sorted_masses; returns index of closest mass
│   │   │   within tol_ppm, or None if no match.
│   │   │
│   │   └── _linear_interp(x_out, x_in, y_in)
│   │           → List[float]
│   │       Linear interpolation of (x_in, y_in) evaluated at each x_out.
│   │       Used to align two profile grids before subtraction.
│   │
│   └── class RawFileAdapter
│       │   DEVICE_TYPES dict: "MS" | "UV" | "PDA" | "Analog" | "Other"
│       │                      → .NET Device enum member name
│       │
│       ├── ── Lifecycle ──────────────────────────────────────────────────
│       │
│       ├── __init__(raw_file_path, libs_dir=None,
│       │            instrument_type="MS", instrument_instance=1)
│       │   Stores arguments; does NOT open or load assemblies yet.
│       │
│       ├── __enter__() → self
│       │   Calls open(); returns self for use in `with` statement.
│       │
│       ├── __exit__(*_) → None
│       │   Calls close().
│       │
│       ├── __repr__() → str
│       │   Returns a human-readable string with path and open state.
│       │
│       ├── open() → None
│       │   ├── _ensure_loaded()
│       │   ├── _import_dotnet_types()
│       │   └── .NET: RawFileReaderAdapter.FileFactory(path)
│       │           then validates IsOpen / IsError / InAcquisition
│       │           then SelectInstrument(Device, instance)
│       │
│       ├── close() → None
│       │   └── .NET: _raw_file.Dispose()
│       │
│       └── is_open  [property] → bool
│           └── .NET: _raw_file.IsOpen
│
│       ├── ── Private helpers ────────────────────────────────────────────
│       │
│       ├── _ensure_loaded() → None
│       │   └── load_assemblies(self._libs_dir)   [loader.py]
│       │
│       ├── _import_dotnet_types() → (RawFileReaderAdapter, Device)
│       │   Lazy import from clr after assemblies are loaded.
│       │
│       ├── _check_open() → None
│       │   Raises RawFileNotOpenError if file is not open.
│       │
│       ├── _check_scan(scan_number) → None
│       │   ├── get_scan_range()
│       │   └── Raises ScanNotFoundError if out of [first, last].
│       │
│       ├── _get_device(device_type: str) → .NET Device enum value
│       │   Looks up device_type string in DEVICE_TYPES, then resolves
│       │   against the .NET Device enum. Raises InstrumentSelectionError
│       │   if the enum member is absent in this DLL version.
│       │
│       └── _get_trailer_dict(scan_number) → dict
│           └── .NET: _raw_file.GetTrailerExtraInformation(scan_number)
│               Converts LogEntry label/value pairs → plain Python dict.
│
│       ├── ── Instrument selection ───────────────────────────────────────
│       │
│       ├── select_instrument(device_type, instance=1) → None
│       │   ├── _check_open()
│       │   ├── _get_device(device_type)
│       │   └── .NET: _raw_file.SelectInstrument(Device, instance)
│       │
│       ├── get_instrument_count() → int
│       │   └── .NET: _raw_file.InstrumentCount
│       │
│       ├── get_instrument_count_of_type(device_type) → int
│       │   ├── _check_open()
│       │   ├── _get_device(device_type)
│       │   └── .NET: _raw_file.GetInstrumentCountOfType(Device)
│       │
│       └── get_instrument_type(index) → str
│           └── .NET: _raw_file.GetInstrumentType(index)  → Device enum → str
│
│       ├── ── File / Run metadata ────────────────────────────────────────
│       │
│       ├── get_instrument_data() → InstrumentInfo
│       │   └── .NET: _raw_file.GetInstrumentData()
│       │
│       ├── get_file_info() → FileInfo
│       │   └── .NET: _raw_file.FileHeader
│       │           _raw_file.SampleInformation
│       │           _raw_file.RunHeaderEx
│       │           _raw_file.GetInstrumentData()
│       │           _raw_file.FileName
│       │
│       ├── get_scan_range() → Tuple[int, int]
│       │   └── .NET: _raw_file.RunHeaderEx.FirstSpectrumNumber
│       │           _raw_file.RunHeaderEx.LastSpectrumNumber
│       │
│       ├── get_start_time() → float
│       │   └── .NET: _raw_file.RunHeaderEx.StartTime
│       │
│       ├── get_end_time() → float
│       │   └── .NET: _raw_file.RunHeaderEx.EndTime
│       │
│       ├── get_instrument_method(index=0) → str
│       │   └── .NET: _raw_file.GetInstrumentMethod(index)
│       │
│       └── get_all_instrument_names_from_method() → List[str]
│           └── .NET: _raw_file.GetAllInstrumentNamesFromInstrumentMethod()
│
│       ├── ── Scan filters & events ──────────────────────────────────────
│       │
│       ├── get_filters() → List[str]
│       │   └── .NET: _raw_file.GetFilters()  → list of IScanFilter → ToString()
│       │
│       ├── get_filter_for_scan(scan_number) → str
│       │   ├── _check_open(), _check_scan(scan_number)
│       │   └── .NET: _raw_file.GetFilterForScanNumber(scan_number) → ToString()
│       │
│       └── get_scan_event_for_scan(scan_number) → dict
│           ├── _check_open(), _check_scan(scan_number)
│           └── .NET: _raw_file.GetScanEventForScanNumber(scan_number)
│               Converts IScanEvent properties → plain Python dict.
│
│       ├── ── Scan statistics & retention time ───────────────────────────
│       │
│       ├── get_scan_stats(scan_number) → ScanStats
│       │   ├── _check_open(), _check_scan(scan_number)
│       │   └── .NET: _raw_file.GetScanStatsForScanNumber(scan_number)
│       │           _raw_file.GetFilterForScanNumber(scan_number)
│       │
│       ├── get_retention_time(scan_number) → float
│       │   ├── _check_open(), _check_scan(scan_number)
│       │   └── .NET: _raw_file.RetentionTimeFromScanNumber(scan_number)
│       │
│       └── scan_number_from_retention_time(retention_time) → int
│           ├── _check_open()
│           └── .NET: _raw_file.RunHeaderEx  (clamp to valid range)
│                   _raw_file.ScanNumberFromRetentionTime(retention_time)
│
│       ├── ── Spectral data ──────────────────────────────────────────────
│       │
│       ├── get_centroid_stream(scan_number, prefer_profile_data=False)
│       │       → CentroidData
│       │   ├── _check_open(), _check_scan(scan_number)
│       │   └── .NET: _raw_file.GetCentroidStream(scan_number, prefer_profile_data)
│       │
│       └── get_profile_data(scan_number) → ProfileData
│           ├── _check_open(), _check_scan(scan_number)
│           └── .NET: _raw_file.GetScanStatsForScanNumber(scan_number)
│                   _raw_file.GetSegmentedScanFromScanNumber(scan_number, stats)
│
│       ├── ── Comprehensive scan info ────────────────────────────────────
│       │
│       └── get_scan_info(scan_number) → ScanInfo
│           ├── _check_open(), _check_scan(scan_number)
│           ├── _get_trailer_dict(scan_number)
│           └── .NET: _raw_file.GetFilterForScanNumber(scan_number)
│                   _raw_file.GetScanEventForScanNumber(scan_number)
│                   _raw_file.GetScanStatsForScanNumber(scan_number)
│                   _raw_file.RetentionTimeFromScanNumber(scan_number)
│                   _raw_file.GetReaction(scan_number, 0)  (MS/MS precursor)
│
│       ├── ── Scan averaging ─────────────────────────────────────────────
│       │
│       ├── average_scans_in_range(first_scan, last_scan, filter_string=None)
│       │       → AveragedScan
│       │   ├── _check_open(), get_scan_range()
│       │   └── .NET: _raw_file.DefaultMassOptions()
│       │           _raw_file.GetFilterForScanNumber(first_scan)
│       │           _raw_file.AverageScansInScanRange(first, last, filter, opts)
│       │               ↑ BackgroundSubtraction extension method
│       │
│       └── average_scans(scan_numbers) → AveragedScan
│           ├── _check_open()
│           └── .NET: _raw_file.DefaultMassOptions()
│                   _raw_file.AverageScans(scan_numbers, opts)
│                       ↑ BackgroundSubtraction extension method
│
│       ├── ── Chromatogram ───────────────────────────────────────────────
│       │
│       └── get_chromatogram(trace_type="BasePeak", mass_range="",
│                            start_scan=-1, end_scan=-1) → ChromatogramData
│           ├── _check_open(), get_scan_range()
│           └── .NET: _raw_file.GetScanRange()          (clamp scan args)
│                   _raw_file.GetChromatogramData(settings[], start, end)
│
│       ├── ── Trailer / Status logs ──────────────────────────────────────
│       │
│       ├── get_trailer_data(scan_number) → TrailerData
│       │   ├── _check_open(), _check_scan(scan_number)
│       │   └── _get_trailer_dict(scan_number)
│       │
│       ├── get_trailer_header_info() → List[str]
│       │   └── .NET: _raw_file.GetTrailerExtraHeaderInformation()
│       │
│       ├── get_status_log_header_info() → List[str]
│       │   └── .NET: _raw_file.GetStatusLogHeaderInformation()
│       │
│       ├── get_status_log_for_retention_time(retention_time) → StatusLogEntry
│       │   └── .NET: _raw_file.GetStatusLogForRetentionTime(retention_time)
│       │
│       └── get_status_log_for_scan(scan_number) → StatusLogEntry
│           ├── get_retention_time(scan_number)
│           └── get_status_log_for_retention_time(rt)
│
│       ├── ── Scan dependents & mass precision ───────────────────────────
│       │
│       ├── get_scan_dependents(scan_number, depth=1) → ScanDependent
│       │   ├── _check_open(), _check_scan(scan_number)
│       │   └── .NET: _raw_file.GetScanDependents(scan_number, depth)
│       │
│       └── get_mass_precision(scan_number) → List[MassPrecision]
│           ├── _check_open(), _check_scan(scan_number)
│           └── .NET: _raw_file.GetCentroidStream(scan_number, False)
│                   PrecisionEstimate { .Rawfile, .ScanNumber }
│                   .GetMassPrecisionEstimate(scan, analyzerType, tic, bpi)
│                       ↑ MassPrecisionEstimator assembly
│
│       ├── ── Iteration helpers ──────────────────────────────────────────
│       │
│       ├── iter_scan_info(ms_order=None) → Iterator[ScanInfo]
│       │   ├── get_scan_range()
│       │   └── get_scan_info(n)  for each n in range
│       │       (skips scans where ms_order doesn't match)
│       │
│       ├── iter_centroid_data(ms_order=None) → Iterator[CentroidData]
│       │   ├── get_scan_range()
│       │   ├── .NET: _raw_file.GetFilterForScanNumber(n)
│       │   ├── .NET: _raw_file.GetScanEventForScanNumber(n)
│       │   └── get_centroid_stream(n)  per qualifying scan
│       │
│       └── analyze_all_scans() → Dict[str, int]
│           ├── _check_open(), get_scan_range()
│           └── .NET: _raw_file.RunHeaderEx
│                   _raw_file.GetScanStatsForScanNumber(n)
│                   _raw_file.GetFilterForScanNumber(n)
│                   _raw_file.GetCentroidStream(n, False)
│                   _raw_file.GetSegmentedScanFromScanNumber(n, stats)
│
│       └── ── Spectral subtraction ───────────────────────────────────────
│
│           ├── subtract_spectra(scan_a, scan_b, mass_range=None,
│           │                   mass_tolerance_ppm=5.0, normalize=False)
│           │       → SubtractedSpectrum
│           │   ├── _check_open()
│           │   ├── _check_scan(scan_a), _check_scan(scan_b)
│           │   ├── [centroid path] → _subtract_centroid(...)
│           │   └── [profile path]  → _subtract_profile(...)
│           │
│           ├── _subtract_centroid(scan_a, scan_b, mass_range, tol_ppm, normalize)
│           │       → Tuple[List[float], List[float]]
│           │   ├── .NET: _raw_file.GetCentroidStream(scan_a, False)
│           │   ├── .NET: _raw_file.GetCentroidStream(scan_b, False)
│           │   ├── _apply_mass_range(masses_a, intensities_a, mass_range)
│           │   ├── _apply_mass_range(masses_b, intensities_b, mass_range)
│           │   ├── [if normalize] _normalize_to_tic(intensities_a)
│           │   ├── [if normalize] _normalize_to_tic(intensities_b)
│           │   └── _find_closest(m, masses_b, tol_ppm)  for each m in masses_a
│           │
│           ├── _subtract_profile(scan_a, scan_b, mass_range, normalize)
│           │       → Tuple[List[float], List[float]]
│           │   ├── .NET: _raw_file.GetScanStatsForScanNumber(scan_a)
│           │   ├── .NET: _raw_file.GetSegmentedScanFromScanNumber(scan_a, stats_a)
│           │   ├── .NET: _raw_file.GetScanStatsForScanNumber(scan_b)
│           │   ├── .NET: _raw_file.GetSegmentedScanFromScanNumber(scan_b, stats_b)
│           │   ├── _apply_mass_range(pos_a, int_a, mass_range)
│           │   ├── _apply_mass_range(pos_b, int_b, mass_range)
│           │   ├── [if normalize] _normalize_to_tic(int_a)
│           │   ├── [if normalize] _normalize_to_tic(int_b)
│           │   └── _linear_interp(pos_a, pos_b, int_b)  → resampled_b
│           │
│           └── subtract_background(scan_number, background_scan_numbers,
│                                   mass_range=None)
│                   → BackgroundSubtractedSpectrum
│               ├── _check_open(), _check_scan(scan_number)
│               └── .NET: _raw_file.GetFilterForScanNumber(scan_number)
│                       _raw_file.GetCentroidStream(scan_number, False)
│                       _raw_file.DefaultMassOptions()
│                       _raw_file.AverageScans(background_scan_numbers, opts)
│                           ↑ BackgroundSubtraction extension method
│
└── __init__.py  — Public API surface
    ├── Classes:   RawFileAdapter
    ├── Models:    FileInfo, InstrumentInfo, ScanStats, CentroidData,
    │              ProfileData, ScanInfo, ChromatogramData, TrailerData,
    │              StatusLogEntry, ScanDependent, MassPrecision,
    │              SubtractedSpectrum, BackgroundSubtractedSpectrum
    └── Exceptions: RawFileError, RawFileNotOpenError,
                    RawFileInAcquisitionError, InstrumentSelectionError,
                    ScanNotFoundError
    (note: AveragedScan and AssemblyLoadError are defined but not exported)
```

---

## 3. Python Method → .NET Call Mapping

| Python method | Direct .NET calls on `_raw_file` |
|---|---|
| `open()` | `RawFileReaderAdapter.FileFactory()`, `.IsOpen`, `.IsError`, `.InAcquisition`, `SelectInstrument()` |
| `close()` | `.Dispose()` |
| `is_open` | `.IsOpen` |
| `select_instrument()` | `SelectInstrument(Device, int)` |
| `get_instrument_count()` | `.InstrumentCount` |
| `get_instrument_count_of_type()` | `GetInstrumentCountOfType(Device)` |
| `get_instrument_type()` | `GetInstrumentType(int)` |
| `get_instrument_data()` | `GetInstrumentData()` |
| `get_file_info()` | `.FileHeader`, `.SampleInformation`, `.RunHeaderEx`, `GetInstrumentData()`, `.FileName` |
| `get_scan_range()` | `.RunHeaderEx.FirstSpectrumNumber`, `.RunHeaderEx.LastSpectrumNumber` |
| `get_start_time()` | `.RunHeaderEx.StartTime` |
| `get_end_time()` | `.RunHeaderEx.EndTime` |
| `get_instrument_method()` | `GetInstrumentMethod(int)` |
| `get_all_instrument_names_from_method()` | `GetAllInstrumentNamesFromInstrumentMethod()` |
| `get_filters()` | `GetFilters()` |
| `get_filter_for_scan()` | `GetFilterForScanNumber(int)` |
| `get_scan_event_for_scan()` | `GetScanEventForScanNumber(int)` |
| `get_scan_stats()` | `GetScanStatsForScanNumber(int)`, `GetFilterForScanNumber(int)` |
| `get_retention_time()` | `RetentionTimeFromScanNumber(int)` |
| `scan_number_from_retention_time()` | `.RunHeaderEx`, `ScanNumberFromRetentionTime(double)` |
| `get_centroid_stream()` | `GetCentroidStream(int, bool)` |
| `get_profile_data()` | `GetScanStatsForScanNumber(int)`, `GetSegmentedScanFromScanNumber(int, stats)` |
| `get_scan_info()` | `GetFilterForScanNumber()`, `GetScanEventForScanNumber()`, `GetScanStatsForScanNumber()`, `RetentionTimeFromScanNumber()`, `GetReaction()` |
| `average_scans_in_range()` | `DefaultMassOptions()`, `GetFilterForScanNumber()`, `AverageScansInScanRange()` ¹ |
| `average_scans()` | `DefaultMassOptions()`, `AverageScans()` ¹ |
| `get_chromatogram()` | `GetScanRange()`, `GetChromatogramData()` |
| `_get_trailer_dict()` | `GetTrailerExtraInformation(int)` |
| `get_trailer_data()` | *(via `_get_trailer_dict`)* |
| `get_trailer_header_info()` | `GetTrailerExtraHeaderInformation()` |
| `get_status_log_header_info()` | `GetStatusLogHeaderInformation()` |
| `get_status_log_for_retention_time()` | `GetStatusLogForRetentionTime(double)` |
| `get_status_log_for_scan()` | *(via `get_retention_time` + `get_status_log_for_retention_time`)* |
| `get_scan_dependents()` | `GetScanDependents(int, int)` |
| `get_mass_precision()` | `GetCentroidStream()` + `PrecisionEstimate.GetMassPrecisionEstimate()` ² |
| `iter_scan_info()` | *(via `get_scan_range` + `get_scan_info` per scan)* |
| `iter_centroid_data()` | `GetFilterForScanNumber()`, `GetScanEventForScanNumber()` + *(via `get_centroid_stream`)* |
| `analyze_all_scans()` | `.RunHeaderEx`, `GetScanStatsForScanNumber()`, `GetFilterForScanNumber()`, `GetCentroidStream()`, `GetSegmentedScanFromScanNumber()` |
| `subtract_spectra()` | *(dispatches to `_subtract_centroid` or `_subtract_profile`)* |
| `_subtract_centroid()` | `GetCentroidStream()` ×2 |
| `_subtract_profile()` | `GetScanStatsForScanNumber()` ×2, `GetSegmentedScanFromScanNumber()` ×2 |
| `subtract_background()` | `GetFilterForScanNumber()`, `GetCentroidStream()`, `DefaultMassOptions()`, `AverageScans()` ¹ |

¹ Extension method from `ThermoFisher.CommonCore.BackgroundSubtraction.dll`
² Class from `ThermoFisher.CommonCore.MassPrecisionEstimator.dll`
