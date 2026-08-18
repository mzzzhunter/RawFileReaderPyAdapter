from pathlib import Path

from setuptools import find_packages, setup


PACKAGE_ROOT = Path(__file__).parent
version_namespace = {}
exec((PACKAGE_ROOT / "rawfilereader" / "_version.py").read_text(), version_namespace)

setup(
    name="rawfilereader-python",
    version=version_namespace["__version__"],
    description="Python adapter for Thermo Fisher Scientific RawFileReader .NET assemblies",
    long_description=(PACKAGE_ROOT / "README.md").read_text(),
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["tests*", "examples*"]),
    package_data={"rawfilereader": ["runtimeconfig.json"]},
    python_requires=">=3.8",
    install_requires=[
        "pythonnet>=3.0.3",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],
)
