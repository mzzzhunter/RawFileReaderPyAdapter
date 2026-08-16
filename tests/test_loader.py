import sys
from types import ModuleType

import pytest

import rawfilereader.loader as loader
from rawfilereader import AssemblyLoadError


@pytest.fixture(autouse=True)
def reset_loader_state(monkeypatch):
    monkeypatch.setattr(loader, "_loaded", False)


def make_assembly_directory(tmp_path, *, omit=None):
    for name in loader._REQUIRED_DLLS:
        if name != omit:
            (tmp_path / f"{name}.dll").touch()
    return tmp_path


def install_fake_runtime(monkeypatch, add_reference):
    pythonnet = ModuleType("pythonnet")
    pythonnet.load = lambda runtime: None
    clr = ModuleType("clr")
    clr.AddReference = add_reference
    monkeypatch.setitem(sys.modules, "pythonnet", pythonnet)
    monkeypatch.setitem(sys.modules, "clr", clr)


def test_missing_dlls_are_reported_before_process_state_changes(tmp_path):
    assemblies = make_assembly_directory(
        tmp_path, omit="ThermoFisher.CommonCore.RawFileReader"
    )
    original_path = list(sys.path)

    with pytest.raises(AssemblyLoadError, match="RawFileReader.dll"):
        loader.load_assemblies(str(assemblies))

    assert sys.path == original_path
    assert loader._loaded is False


def test_failed_assembly_load_removes_added_search_path(monkeypatch, tmp_path):
    assemblies = make_assembly_directory(tmp_path)

    def add_reference(name):
        if name == "ThermoFisher.CommonCore.Data":
            raise RuntimeError("bad image")

    install_fake_runtime(monkeypatch, add_reference)

    with pytest.raises(AssemblyLoadError, match="CommonCore.Data"):
        loader.load_assemblies(str(assemblies))

    assert str(assemblies) not in sys.path
    assert loader._loaded is False


def test_successful_load_does_not_duplicate_existing_search_path(
    monkeypatch, tmp_path
):
    assemblies = make_assembly_directory(tmp_path)
    references = []
    install_fake_runtime(monkeypatch, references.append)
    monkeypatch.syspath_prepend(str(assemblies))

    loader.load_assemblies(str(assemblies))

    assert sys.path.count(str(assemblies)) == 1
    assert references == loader._REQUIRED_DLLS
    assert loader._loaded is True
