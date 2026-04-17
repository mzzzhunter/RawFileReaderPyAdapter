"""
RawFileBase
===========
Base class providing file open/close, guard helpers, and lazy .NET type
imports.  All mixin classes inherit from this via RawFileAdapter.
"""

from __future__ import annotations

import os
from typing import Optional

from .exceptions import (
    AssemblyLoadError,
    InstrumentSelectionError,
    RawFileInAcquisitionError,
    RawFileNotOpenError,
    ScanNotFoundError,
)
from .loader import load_assemblies


class RawFileBase:
    """
    Manages the lifecycle of a Thermo RAW file handle.

    Parameters
    ----------
    raw_file_path:
        Absolute or relative path to the ``.raw`` file.
    libs_dir:
        Directory containing the RawFileReader DLLs.  When *None* the loader
        uses the ``RAWFILEREADER_LIBS`` environment variable or auto-discovery.
    instrument_type:
        Device type to select on open.  Defaults to ``"MS"``.
    instrument_instance:
        1-based instance number for the selected device.
    """

    DEVICE_TYPES = ("MS", "MSAnalog", "UV", "PDA", "Analog", "ADCard", "Lyra")

    def __init__(
        self,
        raw_file_path: str,
        libs_dir: Optional[str] = None,
        instrument_type: str = "MS",
        instrument_instance: int = 1,
    ) -> None:
        self._path = os.path.abspath(raw_file_path)
        self._libs_dir = libs_dir
        self._instrument_type = instrument_type
        self._instrument_instance = instrument_instance
        self._raw_file = None
        self._device_enum = None

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "RawFileBase":
        self.open()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def __repr__(self) -> str:
        state = "open" if self.is_open() else "closed"
        return f"{type(self).__name__}({os.path.basename(self._path)!r}, {state})"

    # ------------------------------------------------------------------
    # .NET assembly loading
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        load_assemblies(self._libs_dir)

    def _import_dotnet_types(self):
        """Return (RawFileReaderAdapter, Device) after assemblies are loaded."""
        from ThermoFisher.CommonCore.RawFileReader import RawFileReaderAdapter  # type: ignore
        from ThermoFisher.CommonCore.Data.Business import Device  # type: ignore
        return RawFileReaderAdapter, Device

    # ------------------------------------------------------------------
    # File open / close
    # ------------------------------------------------------------------

    def open(self) -> None:
        """
        Open the RAW file and select the default instrument device.

        Raises
        ------
        FileNotFoundError
            If the ``.raw`` file does not exist.
        RawFileInAcquisitionError
            If the file is still being acquired.
        InstrumentSelectionError
            If the requested device type/instance cannot be selected.
        AssemblyLoadError
            If the RawFileReader DLLs cannot be located.
        """
        if not os.path.exists(self._path):
            raise FileNotFoundError(f"RAW file not found: {self._path}")

        self._ensure_loaded()
        RawFileReaderAdapter, Device = self._import_dotnet_types()

        raw = RawFileReaderAdapter.FileFactory(self._path)

        if not raw.IsOpen:
            raise RawFileNotOpenError(
                f"RawFileReader could not open: {self._path}"
            )
        if raw.IsError:
            raise RawFileNotOpenError(
                f"RawFileReader reported an error on: {self._path}"
            )
        if raw.InAcquisition:
            raise RawFileInAcquisitionError(
                f"File is still being acquired: {self._path}"
            )

        self._raw_file = raw
        self._device_enum = Device
        self.select_instrument(self._instrument_type, self._instrument_instance)

    def close(self) -> None:
        """Close the RAW file and release .NET resources."""
        if self._raw_file is not None:
            self._raw_file.Dispose()
            self._raw_file = None

    def is_open(self) -> bool:
        """Return ``True`` if the file is currently open."""
        return self._raw_file is not None and self._raw_file.IsOpen

    # ------------------------------------------------------------------
    # Internal guards
    # ------------------------------------------------------------------

    def _check_open(self) -> None:
        if self._raw_file is None or not self._raw_file.IsOpen:
            raise RawFileNotOpenError("File is not open.  Call open() first.")

    def _check_scan(self, scan_number: int) -> None:
        first, last = self.get_scan_range()
        if not (first <= scan_number <= last):
            raise ScanNotFoundError(
                f"Scan {scan_number} is outside the valid range [{first}, {last}]."
            )

    # ------------------------------------------------------------------
    # Device enum helper
    # ------------------------------------------------------------------

    def _get_device(self, device_type: str):
        """Return the .NET Device enum value for *device_type* string."""
        Device = self._device_enum
        mapping = {
            name: getattr(Device, name, None)
            for name in self.DEVICE_TYPES
        }
        value = mapping.get(device_type)
        if value is None:
            raise InstrumentSelectionError(
                f"Unknown device type '{device_type}'.  "
                f"Valid types: {list(mapping.keys())}"
            )
        return value

    # ------------------------------------------------------------------
    # Trailer dict helper (used by _scans.py get_scan_info)
    # ------------------------------------------------------------------

    def _get_trailer_dict(self, scan_number: int) -> dict:
        """Return a label->value dict for trailer-extra data (internal use)."""
        try:
            trailer = self._raw_file.GetTrailerExtraInformation(scan_number)
            return {str(label): str(value)
                    for label, value in zip(trailer.Labels, trailer.Values)}
        except Exception:
            return {}
