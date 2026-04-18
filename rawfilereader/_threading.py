"""
RawFileThreadManager
====================
Thread-safe parallel reader wrapping IRawFileThreadManager.

Each call to :meth:`create_accessor` returns an independent
:class:`~rawfilereader.adapter.RawFileAdapter` backed by a separate
.NET ``IRawDataPlus`` accessor — safe for use in one thread at a time.
"""

from __future__ import annotations

import os
from typing import Optional, TYPE_CHECKING

from .exceptions import AssemblyLoadError, RawFileNotOpenError
from .loader import load_assemblies

if TYPE_CHECKING:
    from .adapter import RawFileAdapter


class RawFileThreadManager:
    """
    Opens a RAW file via the thread-manager factory and vends per-thread
    reader instances.

    Parameters
    ----------
    raw_file_path:
        Absolute or relative path to the ``.raw`` file.
    libs_dir:
        Directory containing the RawFileReader DLLs.

    Examples
    --------
    >>> with RawFileThreadManager("sample.raw") as mgr:
    ...     accessor = mgr.create_accessor()
    ...     print(accessor.get_file_info())
    """

    def __init__(
        self,
        raw_file_path: str,
        libs_dir: Optional[str] = None,
    ) -> None:
        self._path = os.path.abspath(raw_file_path)
        self._libs_dir = libs_dir
        self._thread_manager = None

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "RawFileThreadManager":
        self.open()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def __repr__(self) -> str:
        state = "open" if self._thread_manager is not None else "closed"
        return f"RawFileThreadManager({os.path.basename(self._path)!r}, {state})"

    # ------------------------------------------------------------------
    # Open / close
    # ------------------------------------------------------------------

    def open(self) -> None:
        """
        Open the RAW file via the thread-manager factory.

        Raises
        ------
        FileNotFoundError
            If the ``.raw`` file does not exist.
        AssemblyLoadError
            If the RawFileReader DLLs cannot be located.
        RawFileNotOpenError
            If the thread manager could not open the file.
        """
        if not os.path.exists(self._path):
            raise FileNotFoundError(f"RAW file not found: {self._path}")

        load_assemblies(self._libs_dir)

        try:
            from ThermoFisher.CommonCore.RawFileReader import RawFileReaderAdapter  # type: ignore
        except ImportError as exc:
            raise AssemblyLoadError(
                "RawFileReader assembly not loaded."
            ) from exc

        thread_mgr = RawFileReaderAdapter.ThreadedFileFactory(self._path)
        if not thread_mgr.IsOpen:
            raise RawFileNotOpenError(
                f"RawFileReader could not open: {self._path}"
            )
        self._thread_manager = thread_mgr

    def close(self) -> None:
        """Close the thread manager and release .NET resources."""
        if self._thread_manager is not None:
            self._thread_manager.Dispose()
            self._thread_manager = None

    # ------------------------------------------------------------------
    # Accessor factory
    # ------------------------------------------------------------------

    def create_accessor(self) -> "RawFileAdapter":
        """
        Create a thread-safe reader for one thread.

        Each returned :class:`~rawfilereader.adapter.RawFileAdapter` wraps
        an independent ``IRawDataPlus`` accessor obtained via
        ``CreateThreadAccessor()``, cast to ``IRawDataPlus`` so all API
        methods are available.  Only one thread should use a given accessor
        at a time.

        Returns
        -------
        RawFileAdapter
            An already-open adapter; do **not** call ``.open()`` on it.
            Call ``.close()`` when done, or use it as a context manager.

        Raises
        ------
        RawFileNotOpenError
            If the thread manager has not been opened.
        """
        if self._thread_manager is None:
            raise RawFileNotOpenError(
                "Thread manager is not open.  Call open() first."
            )

        from .adapter import RawFileAdapter  # local import to avoid circular
        from ThermoFisher.CommonCore.Data.Interfaces import IRawDataPlus  # type: ignore
        from ThermoFisher.CommonCore.Data.Business import Device  # type: ignore

        accessor_raw = IRawDataPlus(self._thread_manager.CreateThreadAccessor())

        adapter = RawFileAdapter.__new__(RawFileAdapter)
        adapter._path = self._path
        adapter._libs_dir = self._libs_dir
        adapter._instrument_type = "MS"
        adapter._instrument_instance = 1
        adapter._raw_file = accessor_raw
        adapter._device_enum = Device

        # Select default MS instrument on the accessor
        try:
            adapter.select_instrument("MS", 1)
        except Exception:
            pass

        return adapter
