import sys
from types import ModuleType, SimpleNamespace

import pytest

from rawfilereader import (
    InstrumentSelectionError,
    RawFileAdapter,
    RawFileInAcquisitionError,
    RawFileNotOpenError,
)


class FakeRawFile:
    def __init__(self, *, is_open=True, is_error=False, in_acquisition=False):
        self.IsOpen = is_open
        self.IsError = is_error
        self.InAcquisition = in_acquisition
        self.disposed = False

    def Dispose(self):
        self.disposed = True
        self.IsOpen = False


def install_fake_dotnet_modules(monkeypatch, raw):
    raw_reader = ModuleType("ThermoFisher.CommonCore.RawFileReader")
    raw_reader.RawFileReaderAdapter = SimpleNamespace(FileFactory=lambda path: raw)

    business = ModuleType("ThermoFisher.CommonCore.Data.Business")
    for name in (
        "Device",
        "ChromatogramTraceSettings",
        "MassOptions",
        "Range",
        "Scan",
        "TraceType",
        "ChromatogramSignal",
    ):
        setattr(business, name, type(name, (), {}))

    background = ModuleType("ThermoFisher.CommonCore.BackgroundSubtraction")
    background.BackgroundSubtractor = type("BackgroundSubtractor", (), {})
    background.ScanAveragerPlus = type("ScanAveragerPlus", (), {})

    generic = ModuleType("System.Collections.Generic")
    generic.List = type("List", (), {})

    system = ModuleType("System")
    system.Int32 = int
    system.Array = type("Array", (), {})
    system.Enum = type("Enum", (), {})

    modules = {
        "ThermoFisher.CommonCore.RawFileReader": raw_reader,
        "ThermoFisher.CommonCore.Data.Business": business,
        "ThermoFisher.CommonCore.BackgroundSubtraction": background,
        "System.Collections.Generic": generic,
        "System": system,
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)


@pytest.mark.parametrize(
    ("raw", "error_type"),
    [
        (FakeRawFile(is_open=False), RawFileNotOpenError),
        (FakeRawFile(is_error=True), RawFileNotOpenError),
        (FakeRawFile(in_acquisition=True), RawFileInAcquisitionError),
    ],
)
def test_open_disposes_file_when_validation_fails(
    monkeypatch, tmp_path, raw, error_type
):
    raw_path = tmp_path / "sample.raw"
    raw_path.touch()
    install_fake_dotnet_modules(monkeypatch, raw)
    monkeypatch.setattr("rawfilereader.adapter.load_assemblies", lambda _: None)
    adapter = RawFileAdapter(str(raw_path))

    with pytest.raises(error_type):
        adapter.open()

    assert raw.disposed is True
    assert adapter._raw_file is None


def test_open_disposes_file_when_instrument_selection_fails(monkeypatch, tmp_path):
    raw = FakeRawFile()
    raw_path = tmp_path / "sample.raw"
    raw_path.touch()
    install_fake_dotnet_modules(monkeypatch, raw)
    monkeypatch.setattr("rawfilereader.adapter.load_assemblies", lambda _: None)
    monkeypatch.setattr(
        RawFileAdapter,
        "select_instrument",
        lambda *args: (_ for _ in ()).throw(InstrumentSelectionError("bad device")),
    )
    adapter = RawFileAdapter(str(raw_path))

    with pytest.raises(InstrumentSelectionError, match="bad device"):
        adapter.open()

    assert raw.disposed is True
    assert adapter._raw_file is None
