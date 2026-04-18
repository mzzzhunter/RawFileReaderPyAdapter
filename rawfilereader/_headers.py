"""
HeadersMixin
============
File/run header, sample information, autosampler, and instrument selection.
"""

from __future__ import annotations

from typing import List, Tuple

from .models import AutoSamplerInfo, FileInfo, InstrumentInfo, SampleInfo
from .exceptions import InstrumentSelectionError


class HeadersMixin:
    """Methods wrapping file/run header, sample, and instrument DLL calls."""

    # ------------------------------------------------------------------
    # Instrument selection
    # ------------------------------------------------------------------

    def select_instrument(self, device_type: str, instance: int = 1) -> None:
        """
        Select an instrument device for subsequent data reads.

        Parameters
        ----------
        device_type:
            One of ``"MS"``, ``"UV"``, ``"PDA"``, ``"Analog"``, ``"MSAnalog"``.
        instance:
            1-based device instance number (usually 1).

        Raises
        ------
        InstrumentSelectionError
            If the device type is unknown or the instance does not exist.
        """
        self._check_open()
        device = self._get_device(device_type)
        try:
            self._raw_file.SelectInstrument(device, instance)
            self._instrument_type = device_type
            self._instrument_instance = instance
        except InstrumentSelectionError:
            raise
        except Exception as exc:
            raise InstrumentSelectionError(
                f"Cannot select {device_type} instance {instance}: {exc}"
            ) from exc

    def get_instrument_count(self) -> int:
        """Return the total number of instrument devices in the file."""
        self._check_open()
        return int(self._raw_file.InstrumentCount)

    def get_instrument_count_of_type(self, device_type: str) -> int:
        """Return the number of devices of the given *device_type*."""
        self._check_open()
        device = self._get_device(device_type)
        return int(self._raw_file.GetInstrumentCountOfType(device))

    def get_instrument_type(self, index: int) -> str:
        """Return the device-type string for the given 0-based *index*."""
        self._check_open()
        return str(self._raw_file.GetInstrumentType(index))

    # ------------------------------------------------------------------
    # Run header
    # ------------------------------------------------------------------

    def get_scan_range(self) -> Tuple[int, int]:
        """Return ``(first_scan, last_scan)`` for the selected instrument."""
        self._check_open()
        rh = self._raw_file.RunHeaderEx
        return int(rh.FirstSpectrum), int(rh.LastSpectrum)

    def get_start_time(self) -> float:
        """Return the acquisition start time in minutes."""
        self._check_open()
        return float(self._raw_file.RunHeaderEx.StartTime)

    def get_end_time(self) -> float:
        """Return the acquisition end time in minutes."""
        self._check_open()
        return float(self._raw_file.RunHeaderEx.EndTime)

    # ------------------------------------------------------------------
    # File header
    # ------------------------------------------------------------------

    def get_file_info(self) -> FileInfo:
        """
        Return file-header-level metadata.

        Returns
        -------
        FileInfo
            Contains operator, creation date, instrument name/serial, etc.
            For sample-specific fields use :meth:`get_sample_info`.
        """
        self._check_open()
        fh = self._raw_file.FileHeader
        rh = self._raw_file.RunHeaderEx
        idata = self._raw_file.GetInstrumentData()

        return FileInfo(
            file_name=str(self._raw_file.FileName),
            creation_date=str(fh.CreationDate),
            operator=str(getattr(fh, "WhoCreatedId", "")),
            comment=str(getattr(fh, "Comment", "")),
            acquisition_software_version=str(getattr(fh, "FileDescription", "")),
            instrument_name=str(idata.Name),
            instrument_serial_number=str(idata.SerialNumber),
            number_of_ms_orders=int(rh.MsOrderCount) if hasattr(rh, "MsOrderCount") else 0,
            has_ms_data=bool(rh.HasMsData) if hasattr(rh, "HasMsData") else True,
        )

    # ------------------------------------------------------------------
    # Sample information
    # ------------------------------------------------------------------

    def get_sample_info(self) -> SampleInfo:
        """
        Return full sample information from the RAW file header.

        Returns
        -------
        SampleInfo
            Contains sample name/ID/type, vial, barcode, injection volume,
            dilution factor, and all other SampleInformation fields.
        """
        self._check_open()
        si = self._raw_file.SampleInformation

        user_text: List[str] = []
        try:
            for t in si.UserText:
                user_text.append(str(t))
        except Exception:
            pass

        return SampleInfo(
            sample_name=str(getattr(si, "SampleName", "")),
            sample_id=str(getattr(si, "SampleId", "")),
            sample_type=str(getattr(si, "SampleType", "")),
            vial=str(getattr(si, "Vial", "")),
            comment=str(getattr(si, "Comment", "")),
            barcode=str(getattr(si, "Barcode", "")),
            barcode_status=str(getattr(si, "BarcodeStatus", "")),
            calibration_level=str(getattr(si, "CalibrationLevel", "")),
            calibration_file=str(getattr(si, "CalibrationFile", "")),
            dilution_factor=float(getattr(si, "DilutionFactor", 0.0) or 0.0),
            injection_volume=float(getattr(si, "InjectionVolume", 0.0) or 0.0),
            istd_amount=float(getattr(si, "IstdAmount", 0.0) or 0.0),
            row_number=int(getattr(si, "RowNumber", 0) or 0),
            sample_volume=float(getattr(si, "SampleVolume", 0.0) or 0.0),
            sample_weight=float(getattr(si, "SampleWeight", 0.0) or 0.0),
            path=str(getattr(si, "Path", "")),
            processing_method_file=str(getattr(si, "ProcessingMethodFile", "")),
            instrument_method_file=str(getattr(si, "InstrumentMethodFile", "")),
            raw_file_name=str(getattr(si, "RawFileName", "")),
            user_text=user_text,
        )

    # ------------------------------------------------------------------
    # Autosampler
    # ------------------------------------------------------------------

    def get_autosampler_info(self) -> AutoSamplerInfo:
        """
        Return autosampler tray and vial geometry.

        Returns
        -------
        AutoSamplerInfo
            Tray index, vial index, tray dimensions, and tray shape.
        """
        self._check_open()
        asi = self._raw_file.AutoSamplerInformation

        return AutoSamplerInfo(
            tray_index=int(getattr(asi, "TrayIndex", -1) or -1),
            vial_index=int(getattr(asi, "VialIndex", -1) or -1),
            vials_per_tray=int(getattr(asi, "VialsPerTray", 0) or 0),
            vials_per_tray_x=int(getattr(asi, "VialsPerTrayX", 0) or 0),
            vials_per_tray_y=int(getattr(asi, "VialsPerTrayY", 0) or 0),
            tray_shape=str(getattr(asi, "TrayShapeAsString", getattr(asi, "TrayShape", ""))),
            tray_name=str(getattr(asi, "TrayName", "")),
        )

    # ------------------------------------------------------------------
    # Instrument data
    # ------------------------------------------------------------------

    def get_instrument_data(self) -> InstrumentInfo:
        """
        Return metadata for the currently selected instrument device.

        Returns
        -------
        InstrumentInfo
        """
        self._check_open()
        d = self._raw_file.GetInstrumentData()
        channel_labels: List[str] = []
        try:
            for label in d.ChannelLabels:
                channel_labels.append(str(label))
        except Exception:
            pass
        return InstrumentInfo(
            device_type=self._instrument_type,
            instance_number=self._instrument_instance,
            name=str(d.Name),
            model=str(d.Model),
            serial_number=str(d.SerialNumber),
            software_version=str(d.SoftwareVersion),
            hardware_version=str(d.HardwareVersion),
            units=str(d.Units),
            channel_labels=channel_labels,
        )
