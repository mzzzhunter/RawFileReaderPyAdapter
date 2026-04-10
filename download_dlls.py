#!/usr/bin/env python3
"""
download_dlls.py
================
Download the Thermo Fisher RawFileReader .NET assemblies and configure
the RAWFILEREADER_LIBS environment variable so the adapter can find them.

Usage
-----
    python download_dlls.py
    python download_dlls.py --libs-dir /opt/thermo/libs
    python download_dlls.py --include-optional   # also downloads BackgroundSubtraction.dll
    python download_dlls.py --no-env             # skip environment variable setup
"""

import argparse
import os
import sys
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# DLL catalogue
# ---------------------------------------------------------------------------

_BASE_URL = (
    "https://raw.githubusercontent.com/thermofisherlsms/RawFileReader"
    "/main/Libs/NetCore/"
)

_REQUIRED_DLLS = [
    "ThermoFisher.CommonCore.Data.dll",
    "ThermoFisher.CommonCore.RawFileReader.dll",
    "ThermoFisher.CommonCore.MassPrecisionEstimator.dll",
]

_OPTIONAL_DLLS = [
    "ThermoFisher.CommonCore.BackgroundSubtraction.dll",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reporthook(count, block_size, total_size):
    """Print a simple download progress indicator."""
    if total_size <= 0:
        downloaded_kb = count * block_size // 1024
        print(f"\r  {downloaded_kb} KB downloaded...", end="", flush=True)
    else:
        pct = min(100, count * block_size * 100 // total_size)
        downloaded_kb = min(count * block_size, total_size) // 1024
        total_kb = total_size // 1024
        print(f"\r  {downloaded_kb}/{total_kb} KB ({pct}%)", end="", flush=True)


def _download(url: str, dest: Path) -> None:
    """Download *url* to *dest*, printing progress. Cleans up on failure."""
    print(f"  {dest.name}")
    try:
        urllib.request.urlretrieve(url, dest, reporthook=_reporthook)
        size_kb = dest.stat().st_size // 1024
        print(f"\r  {dest.name}: {size_kb} KB — OK               ")
    except Exception as exc:
        dest.unlink(missing_ok=True)
        print(f"\r  {dest.name}: FAILED — {exc}")
        raise


def _persist_env(libs_dir: Path) -> None:
    """
    Write ``export RAWFILEREADER_LIBS=<libs_dir>`` to the user's shell
    config file on Unix/macOS, or print ``setx`` instructions on Windows.
    """
    libs_str = str(libs_dir)
    export_line = f'export RAWFILEREADER_LIBS="{libs_str}"'
    marker = "RAWFILEREADER_LIBS"

    if sys.platform == "win32":
        print("\nTo set the environment variable permanently, run in Command Prompt:")
        print(f'  setx RAWFILEREADER_LIBS "{libs_str}"')
        print("Then restart your terminal for the change to take effect.")
        return

    # Determine which shell config to target
    shell_binary = os.environ.get("SHELL", "")
    if "zsh" in shell_binary:
        rc_path = Path.home() / ".zshrc"
    elif "bash" in shell_binary:
        rc_path = Path.home() / ".bashrc"
    else:
        rc_path = Path.home() / ".profile"

    if rc_path.exists() and marker in rc_path.read_text():
        # Update the existing line in-place
        updated = "\n".join(
            export_line if marker in line else line
            for line in rc_path.read_text().splitlines()
        )
        rc_path.write_text(updated + "\n")
        print(f"\nUpdated {marker} in {rc_path}")
    else:
        with rc_path.open("a") as fh:
            fh.write(f"\n# RawFileReader DLL directory (added by download_dlls.py)\n")
            fh.write(f"{export_line}\n")
        print(f"\nAdded {marker} to {rc_path}")

    print(f'Run:  source {rc_path}  (or open a new terminal) to apply.')


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Download Thermo Fisher RawFileReader .NET assemblies and "
            "configure the RAWFILEREADER_LIBS environment variable."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--libs-dir",
        default=str(Path(__file__).parent / "libs"),
        metavar="DIR",
        help="Directory to place the DLLs in (default: ./libs next to this script)",
    )
    parser.add_argument(
        "--include-optional",
        action="store_true",
        help=(
            "Also download optional DLLs "
            "(ThermoFisher.CommonCore.BackgroundSubtraction.dll)"
        ),
    )
    parser.add_argument(
        "--no-env",
        action="store_true",
        help="Skip writing RAWFILEREADER_LIBS to the shell config file",
    )
    args = parser.parse_args()

    libs_dir = Path(args.libs_dir).resolve()
    libs_dir.mkdir(parents=True, exist_ok=True)

    dlls_to_download = _REQUIRED_DLLS + (
        _OPTIONAL_DLLS if args.include_optional else []
    )

    print(f"Destination : {libs_dir}")
    print(f"DLLs        : {len(dlls_to_download)} "
          f"({'including optional' if args.include_optional else 'required only'})")
    print()

    failed = []
    for dll_name in dlls_to_download:
        dest = libs_dir / dll_name
        if dest.exists():
            print(f"  {dll_name}: already present, skipping.")
            continue
        url = _BASE_URL + dll_name
        try:
            _download(url, dest)
        except Exception:
            failed.append(dll_name)

    print()

    if failed:
        print(f"ERROR: The following DLL(s) could not be downloaded:")
        for name in failed:
            print(f"  - {name}")
        print(
            "\nYou can download them manually from:\n"
            "  https://github.com/thermofisherlsms/RawFileReader/tree/main/Libs/NetCore"
        )
        sys.exit(1)

    # Set for the current process
    os.environ["RAWFILEREADER_LIBS"] = str(libs_dir)
    print(f"RAWFILEREADER_LIBS={libs_dir}")

    if not args.no_env:
        _persist_env(libs_dir)

    print("\nAll done. You can now use the rawfilereader package:")
    print("  from rawfilereader import RawFileAdapter")
    print('  with RawFileAdapter("sample.raw") as rf:')
    print("      print(rf.get_file_info().instrument_name)")


if __name__ == "__main__":
    main()
