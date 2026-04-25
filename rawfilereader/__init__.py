"""
RawFileReader Python Adapter
============================
A Python wrapper around the Thermo Fisher Scientific RawFileReader .NET assemblies.
Uses pythonnet (clr) to bridge Python and .NET.
"""

from .adapter import RawFileAdapter
from .models import (
    ScanInfo,
    CentroidData,
    ProfileData,
    ChromatogramData,
    InstrumentInfo,
    FileInfo,
    ScanStats,
    TrailerData,
    StatusLogEntry,
    ScanDependent,
    SubtractedSpectrum,
    BackgroundSubtractedSpectrum,
)
from .exceptions import (
    RawFileError,
    RawFileNotOpenError,
    RawFileInAcquisitionError,
    InstrumentSelectionError,
    ScanNotFoundError,
)

__version__ = "1.0.0"
__all__ = [
    "RawFileAdapter",
    "ScanInfo",
    "CentroidData",
    "ProfileData",
    "ChromatogramData",
    "InstrumentInfo",
    "FileInfo",
    "ScanStats",
    "TrailerData",
    "StatusLogEntry",
    "ScanDependent",
    "SubtractedSpectrum",
    "BackgroundSubtractedSpectrum",
    "RawFileError",
    "RawFileNotOpenError",
    "RawFileInAcquisitionError",
    "InstrumentSelectionError",
    "ScanNotFoundError",
]
