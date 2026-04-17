"""
ChromatogramsMixin
==================
Chromatogram extraction: standard (GetChromatogramData) and extended
(GetChromatogramDataEx with mass tolerance and base-peak values).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from .models import ChromatogramData


class ChromatogramsMixin:
    """Methods wrapping chromatogram DLL calls on IRawDataPlus."""

    # ------------------------------------------------------------------
    # Standard chromatogram
    # ------------------------------------------------------------------

    def get_chromatogram(
        self,
        trace_type: str = "BasePeak",
        mass_range: str = "",
        start_scan: int = -1,
        end_scan: int = -1,
    ) -> ChromatogramData:
        """
        Extract a chromatogram trace from the file.

        Parameters
        ----------
        trace_type:
            One of ``"BasePeak"``, ``"TIC"``, ``"MassRange"``, ``"EIC"``,
            ``"NeutralLoss"``, ``"UV"``, ``"PDA"``, ``"Analog"``.
        mass_range:
            Mass range filter string for ``"MassRange"`` / ``"EIC"`` traces,
            e.g. ``"500.0-510.0"``.
        start_scan, end_scan:
            Scan range.  Use ``-1`` for the full file range.

        Returns
        -------
        ChromatogramData
        """
        self._check_open()
        from ThermoFisher.CommonCore.Data.Business import (  # type: ignore
            ChromatogramTraceSettings,
            TraceType,
        )
        from ThermoFisher.CommonCore.Data import Range as DotNetRange  # type: ignore
        from System import Array  # type: ignore

        trace_map = {
            name: getattr(TraceType, name, None)
            for name in ("BasePeak", "TIC", "MassRange", "NeutralLoss",
                         "UV", "PDA", "Analog", "ADCard")
        }
        trace_map["EIC"] = trace_map.get("MassRange")
        dn_trace = trace_map.get(trace_type) or TraceType.BasePeak

        settings = ChromatogramTraceSettings(dn_trace)
        if mass_range:
            lo_str, hi_str = mass_range.split("-", 1)
            settings.MassRanges = Array[DotNetRange](
                [DotNetRange(float(lo_str), float(hi_str))]
            )

        first, last = self.get_scan_range()
        s0 = start_scan if start_scan > 0 else first
        s1 = end_scan if end_scan > 0 else last

        settings_array = Array[ChromatogramTraceSettings]([settings])
        data = self._raw_file.GetChromatogramData(settings_array, s0, s1)

        from ThermoFisher.CommonCore.Data.Business import ChromatogramSignal  # type: ignore
        sig = ChromatogramSignal.FromChromatogramData(data)[0]

        times = [float(t) for t in sig.Times] if sig.Times else []
        intensities = [float(i) for i in sig.Intensities] if sig.Intensities else []

        return ChromatogramData(
            trace_type=trace_type,
            mass_range=mass_range,
            times=times,
            intensities=intensities,
        )

    # ------------------------------------------------------------------
    # Extended chromatogram (GetChromatogramDataEx)
    # ------------------------------------------------------------------

    def get_chromatogram_ex(
        self,
        trace_type: str = "BasePeak",
        mass_ranges: Optional[List[Tuple[float, float]]] = None,
        filter_string: str = "",
        start_scan: int = -1,
        end_scan: int = -1,
    ) -> ChromatogramData:
        """
        Extract an extended chromatogram trace using ``GetChromatogramDataEx``.

        This method exposes additional options compared to
        :meth:`get_chromatogram`: multiple mass ranges can be specified and
        the underlying ``ChromatogramTraceSettings`` filter is set from
        *filter_string*.

        Parameters
        ----------
        trace_type:
            Trace type string (same values as :meth:`get_chromatogram`).
        mass_ranges:
            List of ``(low_mz, high_mz)`` tuples.  Converted to a .NET
            ``Range[]`` array internally.  Pass ``None`` for no mass
            restriction.
        filter_string:
            Scan filter string to restrict which scans contribute to the
            chromatogram.
        start_scan, end_scan:
            Scan range.  Use ``-1`` for the full file range.

        Returns
        -------
        ChromatogramData
        """
        self._check_open()
        from ThermoFisher.CommonCore.Data.Business import (  # type: ignore
            ChromatogramTraceSettings,
            TraceType,
        )
        from ThermoFisher.CommonCore.Data import Range as DotNetRange  # type: ignore
        from System import Array  # type: ignore

        trace_map = {
            name: getattr(TraceType, name, None)
            for name in ("BasePeak", "TIC", "MassRange", "NeutralLoss",
                         "UV", "PDA", "Analog", "ADCard")
        }
        trace_map["EIC"] = trace_map.get("MassRange")
        dn_trace = trace_map.get(trace_type) or TraceType.BasePeak

        settings = ChromatogramTraceSettings(dn_trace)
        if filter_string:
            settings.Filter = filter_string
        if mass_ranges:
            dn_ranges = Array[DotNetRange](
                [DotNetRange(lo, hi) for lo, hi in mass_ranges]
            )
            settings.MassRanges = dn_ranges

        first, last = self.get_scan_range()
        s0 = start_scan if start_scan > 0 else first
        s1 = end_scan if end_scan > 0 else last

        settings_array = Array[ChromatogramTraceSettings]([settings])
        data = self._raw_file.GetChromatogramDataEx(settings_array, s0, s1)

        from ThermoFisher.CommonCore.Data.Business import ChromatogramSignal  # type: ignore
        sig = ChromatogramSignal.FromChromatogramData(data)[0]

        times = [float(t) for t in sig.Times] if sig.Times else []
        intensities = [float(i) for i in sig.Intensities] if sig.Intensities else []

        mass_range_str = (
            ",".join(f"{lo}-{hi}" for lo, hi in mass_ranges)
            if mass_ranges else ""
        )

        return ChromatogramData(
            trace_type=trace_type,
            mass_range=mass_range_str,
            times=times,
            intensities=intensities,
        )
