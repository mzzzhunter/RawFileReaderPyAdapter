import runpy
import sys
from types import ModuleType

import rawfilereader


def test_distribution_and_runtime_versions_match(monkeypatch):
    setup_arguments = {}
    setuptools = ModuleType("setuptools")
    setuptools.find_packages = lambda **kwargs: ["rawfilereader"]
    setuptools.setup = lambda **kwargs: setup_arguments.update(kwargs)
    monkeypatch.setitem(sys.modules, "setuptools", setuptools)

    runpy.run_path("setup.py", run_name="__main__")

    assert setup_arguments["version"] == rawfilereader.__version__
