"""
Assembly loader for the Thermo Fisher RawFileReader .NET libraries.

Supported layouts
-----------------
1. Assemblies alongside this package or source checkout.
2. Assemblies installed as wheel data under ``sys.prefix/libs``.
3. User-supplied directory via the ``RAWFILEREADER_LIBS`` environment variable.
4. Explicit path passed to :func:`load_assemblies`.
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import Dict, Optional

from .exceptions import AssemblyLoadError

_REQUIRED_DLLS = [
    "OpenMcdf",
    "OpenMcdf.Extensions",
    "ThermoFisher.CommonCore.Data",
    "ThermoFisher.CommonCore.RawFileReader",
    "ThermoFisher.CommonCore.BackgroundSubtraction",
]

_load_lock = threading.Lock()
_loaded_from: Optional[Path] = None


def _normalise_path(path: Path) -> Path:
    """Expand, resolve, and normalise a candidate assembly directory."""
    return path.expanduser().resolve()


def _contains_required_dlls(path: Path) -> bool:
    """Return ``True`` when *path* contains every required assembly."""
    return path.is_dir() and all((path / f"{name}.dll").is_file() for name in _REQUIRED_DLLS)


def _candidate_libs_dirs() -> list[Path]:
    """Return candidate assembly directories in search-priority order."""
    candidates: list[Path] = []

    env = os.environ.get("RAWFILEREADER_LIBS")
    if env:
        candidates.append(Path(env))

    package_root = Path(__file__).parent
    project_root = package_root.parent
    candidates.extend(
        [
            project_root / "lib" / "Net8" / "Assemblies",
            project_root / "libs" / "Net8" / "Assemblies",
            project_root / "libs",
            project_root / "Libs",
            package_root / "libs" / "Net8" / "Assemblies",
            package_root / "libs",
            Path(sys.prefix) / "libs" / "Net8" / "Assemblies",
        ]
    )

    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = _normalise_path(candidate)
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return unique


def _find_libs_dir() -> Optional[Path]:
    """Return the first candidate containing all required assemblies."""
    for candidate in _candidate_libs_dirs():
        if _contains_required_dlls(candidate):
            return candidate
    return None


def assembly_diagnostics(libs_dir: Optional[str] = None) -> Dict[str, object]:
    """Return environment and DLL-discovery information for troubleshooting."""
    requested = _normalise_path(Path(libs_dir)) if libs_dir else None
    selected = requested or _find_libs_dir()
    dlls = {
        name: bool(selected and (selected / f"{name}.dll").is_file())
        for name in _REQUIRED_DLLS
    }
    return {
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "prefix": sys.prefix,
        "requested_libs_dir": str(requested) if requested else None,
        "selected_libs_dir": str(selected) if selected else None,
        "loaded_from": str(_loaded_from) if _loaded_from else None,
        "dlls": dlls,
    }


def load_assemblies(libs_dir: Optional[str] = None) -> None:
    """Load the RawFileReader .NET assemblies into the current process.

    Raises
    ------
    AssemblyLoadError
        If pythonnet cannot initialise CoreCLR, the DLL directory cannot be
        located, a conflicting directory is requested after initialisation, or
        a required assembly cannot be loaded.
    """
    global _loaded_from

    with _load_lock:
        requested = _normalise_path(Path(libs_dir)) if libs_dir else None

        if _loaded_from is not None:
            if requested is not None and requested != _loaded_from:
                raise AssemblyLoadError(
                    "RawFileReader assemblies are already loaded from "
                    f"'{_loaded_from}', so they cannot be reloaded from '{requested}' "
                    "in the same Python process."
                )
            return

        search_dir = requested or _find_libs_dir()
        if search_dir is None or not _contains_required_dlls(search_dir):
            checked = "\n".join(f"  - {path}" for path in _candidate_libs_dirs())
            raise AssemblyLoadError(
                "Cannot locate a complete RawFileReader DLL directory. Set "
                "RAWFILEREADER_LIBS or pass libs_dir= with a directory containing "
                "all required assemblies. Checked:\n" + checked
            )

        runtime_error: Optional[Exception] = None
        try:
            from pythonnet import load as load_runtime

            load_runtime("coreclr")
        except ImportError:
            # The import of clr below produces the clearest missing-dependency error.
            pass
        except RuntimeError as exc:
            # RuntimeError can mean the runtime was already initialised. Retain it
            # so an assembly-load failure can report the original context.
            runtime_error = exc
        except Exception as exc:
            raise AssemblyLoadError(f"Failed to initialise the .NET Core runtime: {exc}") from exc

        try:
            import clr  # type: ignore
        except ImportError as exc:
            raise AssemblyLoadError(
                "pythonnet is not installed. Install it with: pip install pythonnet"
            ) from exc

        search_path = str(search_dir)
        if search_path not in sys.path:
            sys.path.insert(0, search_path)

        for name in _REQUIRED_DLLS:
            try:
                clr.AddReference(name)
            except Exception as exc:
                context = f" Runtime initialisation also reported: {runtime_error}" if runtime_error else ""
                raise AssemblyLoadError(
                    f"Failed to load assembly '{name}' from '{search_dir}': {exc}.{context}"
                ) from exc

        _loaded_from = search_dir
