"""
RawFileReader Python Adapter
============================
A Python wrapper around the Thermo Fisher Scientific RawFileReader .NET
assemblies.  Uses pythonnet (clr) to bridge Python and .NET.
"""

from .adapter import RawFileAdapter
from ._threading import RawFileThreadManager
from .models import (
    AveragedScan,
    AutoSamplerInfo,
    BackgroundSubtractedSpectrum,
    CentroidData,
    ChromatogramData,
    ErrorLogEntry,
    FileInfo,
    InstrumentInfo,
    MassPrecision,
    ProfileData,
    RawFileError,
    RunHeaderInfo,
    SampleInfo,
    ScanDependent,
    ScanInfo,
    ScanStats,
    StatusLogEntry,
    TrailerData,
    TuneData,
)
from .exceptions import (
    AssemblyLoadError,
    InstrumentSelectionError,
    RawFileError,
    RawFileInAcquisitionError,
    RawFileNotOpenError,
    ScanNotFoundError,
)

__version__ = "2.0.0"
__all__ = [
    # Classes
    "RawFileAdapter",
    "RawFileThreadManager",
    # Models
    "AveragedScan",
    "AutoSamplerInfo",
    "BackgroundSubtractedSpectrum",
    "CentroidData",
    "ChromatogramData",
    "ErrorLogEntry",
    "FileInfo",
    "InstrumentInfo",
    "MassPrecision",
    "ProfileData",
    "RawFileError",
    "RunHeaderInfo",
    "SampleInfo",
    "ScanDependent",
    "ScanInfo",
    "ScanStats",
    "StatusLogEntry",
    "TrailerData",
    "TuneData",
    # Exceptions
    "AssemblyLoadError",
    "InstrumentSelectionError",
    "RawFileError",
    "RawFileInAcquisitionError",
    "RawFileNotOpenError",
    "ScanNotFoundError",
]
