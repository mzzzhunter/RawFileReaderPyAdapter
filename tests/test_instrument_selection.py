from types import SimpleNamespace

import pytest

from rawfilereader import InstrumentSelectionError, RawFileAdapter


class FakeRawFile:
    IsOpen = True

    def __init__(self, selection_error=None):
        self.selection_error = selection_error
        self.selected = None

    def SelectInstrument(self, device, instance):
        if self.selection_error is not None:
            raise self.selection_error
        self.selected = (device, instance)

    def GetInstrumentData(self):
        return SimpleNamespace(
            Name="Instrument",
            Model="Model",
            SerialNumber="123",
            SoftwareVersion="1.0",
            HardwareVersion="1.0",
            Units="counts",
            ChannelLabels=[],
        )


def make_open_adapter(raw_file):
    adapter = RawFileAdapter(
        "sample.raw", instrument_type="MS", instrument_instance=1
    )
    adapter._raw_file = raw_file
    adapter._Device = object()
    adapter._DotNetEnum = SimpleNamespace(Parse=lambda enum_type, value: value)
    return adapter


def test_select_instrument_updates_active_selection():
    raw_file = FakeRawFile()
    adapter = make_open_adapter(raw_file)

    adapter.select_instrument("UV", 2)
    instrument = adapter.get_instrument_data()

    assert raw_file.selected == ("UV", 2)
    assert instrument.device_type == "UV"
    assert instrument.instance_number == 2


def test_select_instrument_keeps_previous_selection_when_dotnet_call_fails():
    raw_file = FakeRawFile(selection_error=RuntimeError("device unavailable"))
    adapter = make_open_adapter(raw_file)

    with pytest.raises(InstrumentSelectionError, match="device unavailable"):
        adapter.select_instrument("UV", 2)

    assert adapter._instrument_type == "MS"
    assert adapter._instrument_instance == 1
