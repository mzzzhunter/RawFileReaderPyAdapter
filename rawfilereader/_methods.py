"""
MethodsMixin
============
Instrument method text access via IRawData / IRawDataPlus.
"""

from __future__ import annotations

from typing import List, Optional


class MethodsMixin:
    """Methods for reading embedded instrument method data."""

    def has_instrument_method(self) -> bool:
        """Return ``True`` if the RAW file contains an instrument method."""
        self._check_open()
        return bool(getattr(self._raw_file, "HasInstrumentMethod", False))

    def get_instrument_method_count(self) -> int:
        """Return the number of instrument method sections in the file."""
        self._check_open()
        return int(getattr(self._raw_file, "InstrumentMethodsCount", 0) or 0)

    def get_instrument_method_text(self, index: int = 0) -> str:
        """
        Return the raw text of instrument method section *index*.

        Parameters
        ----------
        index:
            0-based section index.  Use :meth:`get_instrument_method_count`
            to find the upper bound.
        """
        self._check_open()
        text = self._raw_file.GetInstrumentMethod(index)
        return str(text) if text is not None else ""

    def get_instrument_method_device_names(self) -> List[str]:
        """
        Return the device names embedded in the instrument method.

        Wraps ``GetAllInstrumentNamesFromInstrumentMethod``.
        """
        self._check_open()
        try:
            names = self._raw_file.GetAllInstrumentNamesFromInstrumentMethod()
            return [str(n) for n in names] if names else []
        except Exception:
            return []

    def get_instrument_method_friendly_names(self) -> List[str]:
        """
        Return human-readable device names from the instrument method.

        Wraps ``GetAllInstrumentFriendlyNamesFromInstrumentMethod``
        (IRawDataPlus only).
        """
        self._check_open()
        try:
            names = self._raw_file.GetAllInstrumentFriendlyNamesFromInstrumentMethod()
            return [str(n) for n in names] if names else []
        except Exception:
            return []

    def export_instrument_method(self, destination_path: str, include_user_text: bool = True) -> None:
        """
        Export the instrument method to a file on disk.

        Wraps ``IRawDataPlus.ExportInstrumentMethod``.

        Parameters
        ----------
        destination_path:
            Full path of the output file (usually ``*.meth`` or ``*.xml``).
        include_user_text:
            Whether to include user-text sections in the export.
        """
        self._check_open()
        self._raw_file.ExportInstrumentMethod(destination_path, include_user_text)
