"""
TraceHunter
===========
A Python adapter for Thermo Fisher Scientific RawFileReader .NET assemblies.
Uses pythonnet (clr) to bridge Python and .NET.
"""

from .adapter import TraceHunter
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
    MassPrecision,
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
    "TraceHunter",
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
    "MassPrecision",
    "RawFileError",
    "RawFileNotOpenError",
    "RawFileInAcquisitionError",
    "InstrumentSelectionError",
    "ScanNotFoundError",
]
