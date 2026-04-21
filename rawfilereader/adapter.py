"""
RawFileAdapter
==============
High-level Python wrapper around the Thermo Fisher Scientific RawFileReader
.NET assemblies.  All public methods return plain Python dataclasses defined
in :mod:`rawfilereader.models`; callers never touch .NET objects directly.

The adapter is composed from focused mixin classes:

- :class:`~rawfilereader._base.RawFileBase` — file open/close/guards
- :class:`~rawfilereader._headers.HeadersMixin` — file info, sample, instrument
- :class:`~rawfilereader._scans.ScansMixin` — centroid, profile, stats, filters
- :class:`~rawfilereader._chromatograms.ChromatogramsMixin` — chromatograms
- :class:`~rawfilereader._logs.LogsMixin` — status/tune/error logs, trailer
- :class:`~rawfilereader._averaging.AveragingMixin` — scan averaging/subtraction
- :class:`~rawfilereader._methods.MethodsMixin` — instrument method text

Usage
-----
>>> from rawfilereader import RawFileAdapter
>>> with RawFileAdapter("sample.raw") as rf:
...     info = rf.get_file_info()
...     print(info.instrument_name)
"""

from ._averaging import AveragingMixin
from ._base import RawFileBase
from ._chromatograms import ChromatogramsMixin
from ._headers import HeadersMixin
from ._logs import LogsMixin
from ._methods import MethodsMixin
from ._scans import ScansMixin


class RawFileAdapter(
    RawFileBase,
    HeadersMixin,
    ScansMixin,
    ChromatogramsMixin,
    LogsMixin,
    AveragingMixin,
    MethodsMixin,
):
    """
    Python adapter for reading Thermo Scientific RAW files via RawFileReader.

    Parameters
    ----------
    raw_file_path:
        Absolute or relative path to the ``.raw`` file.
    libs_dir:
        Directory containing the RawFileReader DLLs.  When *None* the loader
        uses the ``RAWFILEREADER_LIBS`` environment variable or searches for a
        ``libs/`` directory next to the package.
    instrument_type:
        The device type to select on open.  Defaults to ``"MS"``.
    instrument_instance:
        1-based instance number for the selected device.

    Examples
    --------
    Open as a context manager (recommended):

    >>> with RawFileAdapter("sample.raw") as rf:
    ...     print(rf.get_file_info().instrument_name)
    ...     print(rf.get_sample_info().sample_name)

    Manual open/close:

    >>> adapter = RawFileAdapter("sample.raw")
    >>> adapter.open()
    >>> first, last = adapter.get_scan_range()
    >>> adapter.close()
    """
