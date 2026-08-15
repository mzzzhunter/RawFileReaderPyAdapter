import shutil
from pathlib import Path

import pytest

from rawfilereader import RawFileAdapter


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RAW = REPOSITORY_ROOT / "sample.raw"
ASSEMBLIES = REPOSITORY_ROOT / "libs" / "Net8" / "Assemblies"


@pytest.mark.integration
def test_open_bundled_sample_with_bundled_assemblies():
    """Exercise the real FileFactory/open/close path when .NET is available."""
    if shutil.which("dotnet") is None:
        pytest.skip("the .NET runtime is not installed")
    if not SAMPLE_RAW.is_file():
        pytest.skip("sample.raw is not available")

    adapter = RawFileAdapter(str(SAMPLE_RAW), libs_dir=str(ASSEMBLIES))

    with adapter:
        first_scan, last_scan = adapter.get_scan_range()
        assert adapter.is_open
        assert first_scan >= 1
        assert last_scan >= first_scan

    assert not adapter.is_open
