"""
LogsMixin
=========
Status log, trailer extra, tune data, and error log access.
"""

from __future__ import annotations

from typing import List

from .models import ErrorLogEntry, StatusLogEntry, TrailerData, TuneData


class LogsMixin:
    """Methods wrapping log and trailer-extra DLL calls on IRawDataPlus."""

    # ------------------------------------------------------------------
    # Trailer extra
    # ------------------------------------------------------------------

    def get_trailer_data(self, scan_number: int) -> TrailerData:
        """
        Return trailer-extra (auxiliary) data for *scan_number*.

        Trailer data contains additional scan metadata such as ion injection
        time, charge state, monoisotopic mass, AGC, and more.

        Parameters
        ----------
        scan_number:
            1-based scan number.
        """
        self._check_open()
        self._check_scan(scan_number)
        fields = self._get_trailer_dict(scan_number)
        return TrailerData(scan_number=scan_number, fields=fields)

    def get_trailer_header_info(self) -> List[str]:
        """Return the list of all trailer-extra field labels defined in the file."""
        self._check_open()
        headers = self._raw_file.GetTrailerExtraHeaderInformation()
        return [str(h.Label) for h in headers]

    # ------------------------------------------------------------------
    # Status log
    # ------------------------------------------------------------------

    def get_status_log_header_info(self) -> List[str]:
        """Return all status-log field labels defined in the file."""
        self._check_open()
        headers = self._raw_file.GetStatusLogHeaderInformation()
        return [str(h.Label) for h in headers]

    def get_status_log_for_retention_time(self, retention_time: float) -> StatusLogEntry:
        """
        Return the status log entry closest to *retention_time* (minutes).

        Parameters
        ----------
        retention_time:
            Retention time in minutes.
        """
        self._check_open()
        log = self._raw_file.GetStatusLogForRetentionTime(retention_time)
        fields: dict = {}
        try:
            for label, value in zip(log.Labels, log.Values):
                fields[str(label)] = str(value)
        except Exception:
            pass
        return StatusLogEntry(retention_time=retention_time, fields=fields)

    def get_status_log_for_scan(self, scan_number: int) -> StatusLogEntry:
        """Return the status log entry for *scan_number*."""
        rt = self.get_retention_time(scan_number)
        return self.get_status_log_for_retention_time(rt)

    def get_status_log_entries_count(self) -> int:
        """Return the total number of status log entries in the file."""
        self._check_open()
        return int(self._raw_file.GetStatusLogEntriesCount())

    def get_status_log_at_position(self, position: int) -> StatusLogEntry:
        """
        Return the status log entry at 0-based *position*.

        Parameters
        ----------
        position:
            0-based index into the status log.
        """
        self._check_open()
        log = self._raw_file.GetStatusLogAtPosition(position)
        fields: dict = {}
        rt = 0.0
        try:
            rt = float(log.RetentionTime) if hasattr(log, "RetentionTime") else 0.0
            for label, value in zip(log.Labels, log.Values):
                fields[str(label)] = str(value)
        except Exception:
            pass
        return StatusLogEntry(retention_time=rt, fields=fields)

    # ------------------------------------------------------------------
    # Tune data
    # ------------------------------------------------------------------

    def get_tune_data_count(self) -> int:
        """Return the number of tune segments stored in the file."""
        self._check_open()
        return int(self._raw_file.GetTuneDataCount())

    def get_tune_data(self, index: int = 0) -> TuneData:
        """
        Return instrument tune data for the segment at *index*.

        Parameters
        ----------
        index:
            0-based tune segment index.
        """
        self._check_open()
        tune = self._raw_file.GetTuneData(index)
        labels: List[str] = []
        values: List[str] = []
        try:
            for label in tune.Labels:
                labels.append(str(label))
            for value in tune.Values:
                values.append(str(value))
        except Exception:
            pass
        return TuneData(index=index, labels=labels, values=values)

    # ------------------------------------------------------------------
    # Error log
    # ------------------------------------------------------------------

    def get_error_log_count(self) -> int:
        """Return the number of error log entries in the file."""
        self._check_open()
        try:
            return int(self._raw_file.GetErrorLogItems())
        except Exception:
            return 0

    def get_error_log_entry(self, index: int) -> ErrorLogEntry:
        """
        Return one error log entry by 0-based *index*.

        Parameters
        ----------
        index:
            0-based index into the error log.
        """
        self._check_open()
        entry = self._raw_file.GetErrorLogItem(index)
        return ErrorLogEntry(
            index=index,
            retention_time=float(getattr(entry, "RetentionTime", 0.0) or 0.0),
            error_message=str(getattr(entry, "Message", getattr(entry, "Error", ""))),
        )
