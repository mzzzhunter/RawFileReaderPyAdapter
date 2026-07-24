from pathlib import Path

from rawfilereader import loader


def _write_required_dlls(directory: Path) -> None:
    directory.mkdir(parents=True)
    for name in loader._REQUIRED_DLLS:
        (directory / f"{name}.dll").write_bytes(b"")


def test_contains_required_dlls_rejects_incomplete_directory(tmp_path):
    (tmp_path / "ThermoFisher.CommonCore.Data.dll").write_bytes(b"")
    assert not loader._contains_required_dlls(tmp_path)


def test_find_libs_dir_skips_incomplete_candidates(monkeypatch, tmp_path):
    incomplete = tmp_path / "incomplete"
    complete = tmp_path / "complete"
    incomplete.mkdir()
    _write_required_dlls(complete)

    monkeypatch.setattr(loader, "_candidate_libs_dirs", lambda: [incomplete, complete])

    assert loader._find_libs_dir() == complete.resolve()


def test_assembly_diagnostics_reports_discovered_dlls(tmp_path):
    _write_required_dlls(tmp_path)

    diagnostics = loader.assembly_diagnostics(str(tmp_path))

    assert diagnostics["selected_libs_dir"] == str(tmp_path.resolve())
    assert all(diagnostics["dlls"].values())
