from types import SimpleNamespace

import pytest

import rawfilereader.adapter as adapter_module
from rawfilereader import RawFileAdapter, ScanNotFoundError


class FakeRawFile:
    IsOpen = True

    def __init__(self, first=1, last=3):
        self.RunHeaderEx = SimpleNamespace(FirstSpectrum=first, LastSpectrum=last)


def make_adapter():
    adapter = RawFileAdapter("sample.raw")
    adapter._raw_file = FakeRawFile()
    adapter._MassOptions = object
    return adapter


def test_average_scans_rejects_empty_input():
    with pytest.raises(ValueError, match="at least one"):
        make_adapter().average_scans([])


def test_average_scans_validates_every_scan_before_native_call(monkeypatch):
    native_called = False

    def native_call(*args):
        nonlocal native_called
        native_called = True

    monkeypatch.setattr(adapter_module, "_reflect_call", native_call)

    with pytest.raises(ScanNotFoundError, match="Scan 4"):
        make_adapter().average_scans([1, 4])

    assert native_called is False


def test_average_range_rejects_reversed_bounds():
    with pytest.raises(ValueError, match="less than or equal"):
        make_adapter().average_scans_in_range(3, 1)


def test_average_range_propagates_native_failures(monkeypatch):
    def native_call(*args):
        raise RuntimeError("native averaging failed")

    monkeypatch.setattr(adapter_module, "_reflect_call", native_call)

    with pytest.raises(RuntimeError, match="native averaging failed"):
        make_adapter().average_scans_in_range(1, 3)


def test_average_range_fallback_propagates_scan_read_failures(monkeypatch):
    adapter = make_adapter()
    monkeypatch.setattr(
        adapter_module,
        "_reflect_call",
        lambda *args: (_ for _ in ()).throw(AttributeError("method unavailable")),
    )
    monkeypatch.setattr(
        adapter,
        "get_centroid_stream",
        lambda scan: (_ for _ in ()).throw(RuntimeError(f"cannot read scan {scan}")),
    )

    with pytest.raises(RuntimeError, match="cannot read scan 1"):
        adapter.average_scans_in_range(1, 3)
