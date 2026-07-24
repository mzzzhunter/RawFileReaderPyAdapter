from glob import glob
from pathlib import Path

from setuptools import find_packages, setup

ROOT = Path(__file__).parent
VERSION = "2.0.0"
DLL_DIR = ROOT / "libs" / "Net8" / "Assemblies"

setup(
    name="rawfilereader-python",
    version=VERSION,
    description="Python adapter for Thermo Fisher Scientific RawFileReader .NET assemblies",
    long_description=(ROOT / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["tests*", "examples*"]),
    data_files=[
        (
            "libs/Net8/Assemblies",
            glob(str(DLL_DIR / "*.dll")),
        )
    ],
    python_requires=">=3.8",
    install_requires=[
        "pythonnet>=3.0.3",
    ],
    extras_require={
        "test": ["pytest>=7", "pytest-cov>=4"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],
)
