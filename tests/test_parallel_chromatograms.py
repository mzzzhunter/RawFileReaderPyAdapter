from types import SimpleNamespace

import pytest

from rawfilereader import RawFileAdapter


class FakeArray:
    def __class_getitem__(cls, _item_type):
        return lambda values: list(values)


class FakeRange:
    def __init__(self, low, high):
        self.Low = low
        self.High = high


class FakeSettings:
    def __init__(self, trace):
        self.Trace = trace
        self.Filter = ""
        self.MassRanges = []


class FakePointRequest:
    @staticmethod
    def MassRangeRequest(low, high):
        return SimpleNamespace(low=low, high=high)


class FakePointBuilderFactory:
    calls = []

    @classmethod
    def CreatePointBuilder(cls, rt_range, selector, point_requests):
        cls.calls.append((rt_range, selector, list(point_requests)))
        return SimpleNamespace(
            rt_range=rt_range,
            selector=selector,
            point_request=point_requests[0],
        )


class FakeRawFile:
    IsOpen = True

    def GetFilterFromString(self, text):
        return SimpleNamespace(text=text)


class FakeScanSelect:
    @staticmethod
    def SelectByFilter(scan_filter):
        return SimpleNamespace(scan_filter=scan_filter)

    @staticmethod
    def SelectAll():
        return SimpleNamespace(scan_filter=None)


class FakeDelivery:
    def __init__(self, request):
        self.Request = request
        point = request.point_request
        self.DeliveredSignal = SimpleNamespace(
            Times=[request.rt_range.Low, request.rt_range.High],
            Intensities=[point.low, point.high],
        )


class FakeBatchGenerator:
    generated = []

    def GenerateChromatograms(self, deliveries):
        self.generated.append(list(deliveries))
        return [object() for _ in deliveries]


class FakeParallelFactory:
    attached = []

    @classmethod
    def FromRawData(cls, generator, raw_file):
        cls.attached.append((generator, raw_file))


class FakeTask:
    waited = []

    @classmethod
    def WaitAll(cls, tasks):
        cls.waited.append(list(tasks))


def make_adapter():
    FakePointBuilderFactory.calls = []
    FakeBatchGenerator.generated = []
    FakeParallelFactory.attached = []
    FakeTask.waited = []

    adapter = RawFileAdapter("unused.raw")
    adapter._raw_file = FakeRawFile()
    adapter._Array = FakeArray
    adapter._MassRange = FakeRange
    adapter._ChromatogramPointRequest = FakePointRequest
    adapter._ChromatogramPointBuilderFactory = FakePointBuilderFactory
    adapter._ScanSelect = FakeScanSelect
    adapter._ChromatogramDelivery = FakeDelivery
    adapter._IChromatogramDelivery = object
    adapter._IChromatogramPointRequest = object
    adapter._ChromatogramBatchGenerator = FakeBatchGenerator
    adapter._ParallelChromatogramFactory = FakeParallelFactory
    adapter._Task = FakeTask
    return adapter


def test_parallel_extraction_returns_one_ordered_result_per_mass_range():
    adapter = make_adapter()

    results = adapter.get_extracted_chromatograms(
        rt_range=(2.0, 8.5),
        scan_filter="FTMS + p ESI Full ms",
        mass_ranges=[(500.0, 510.0), (600.0, 610.0)],
    )

    assert [result.mass_range for result in results] == [
        "500.0-510.0",
        "600.0-610.0",
    ]
    assert [result.times for result in results] == [[2.0, 8.5], [2.0, 8.5]]
    assert [result.intensities for result in results] == [
        [500.0, 510.0],
        [600.0, 610.0],
    ]
    assert all(result.trace_type == "EIC" for result in results)
    assert [call[1].scan_filter.text for call in FakePointBuilderFactory.calls] == [
        "FTMS + p ESI Full ms",
        "FTMS + p ESI Full ms",
    ]
    assert len(FakeBatchGenerator.generated[0]) == 2
    assert len(FakeTask.waited[0]) == 2
    assert FakeParallelFactory.attached[0][1] is adapter._raw_file


def test_parallel_extraction_accepts_one_mass_range_tuple():
    adapter = make_adapter()

    results = adapter.get_extracted_chromatograms(
        rt_range=(0.0, 1.0),
        scan_filter="",
        mass_ranges=(100.0, 101.0),
    )

    assert len(results) == 1
    assert results[0].mass_range == "100.0-101.0"


@pytest.mark.parametrize(
    ("rt_range", "mass_ranges", "message"),
    [
        ((5.0, 2.0), (100.0, 101.0), "rt_range"),
        ((0.0, 2.0), (101.0, 100.0), "mass range"),
        ((0.0, 2.0), [], "mass_ranges"),
    ],
)
def test_parallel_extraction_rejects_invalid_ranges(rt_range, mass_ranges, message):
    adapter = make_adapter()

    with pytest.raises(ValueError, match=message):
        adapter.get_extracted_chromatograms(rt_range, "", mass_ranges)
