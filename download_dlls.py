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
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# DLL catalogue
# ---------------------------------------------------------------------------

_OWNER = "thermofisherlsms"
_REPO  = "RawFileReader"
_PATH  = "Libs/NetCore"

_REQUIRED_DLLS = [
    "ThermoFisher.CommonCore.Data.dll",
    "ThermoFisher.CommonCore.RawFileReader.dll",
    "ThermoFisher.CommonCore.MassPrecisionEstimator.dll",
]

_OPTIONAL_DLLS = [
    "ThermoFisher.CommonCore.BackgroundSubtraction.dll",
]

# Minimum plausible size for a real DLL (LFS pointer files are ~130 bytes)
_MIN_DLL_BYTES = 10_000

# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------

def _api_request(url: str) -> dict:
    """Perform a GitHub API GET and return the parsed JSON."""
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "rawfilereader-python-downloader",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def _default_branch() -> str:
    """Return the repo's default branch (e.g. 'main' or 'master')."""
    try:
        info = _api_request(
            f"https://api.github.com/repos/{_OWNER}/{_REPO}"
        )
        return info.get("default_branch", "main")
    except Exception:
        return "main"


def _dll_url(dll_name: str, branch: str) -> str:
    """
    Return the github.com/raw/ URL for a DLL.

    This endpoint follows Git LFS redirects to the actual object store.
    raw.githubusercontent.com does NOT follow LFS and returns the pointer
    text instead of the binary, which is why direct CDN URLs fail.
    """
    return (
        f"https://github.com/{_OWNER}/{_REPO}"
        f"/raw/{branch}/{_PATH}/{dll_name}"
    )

# ---------------------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------------------

_last_report: float = 0.0

def _reporthook(count, block_size, total_size):
    global _last_report
    now = time.monotonic()
    if count > 0 and now - _last_report < 1.0:
        return
    _last_report = now
    if total_size <= 0:
        kb = count * block_size // 1024
        print(f"    {kb} KB ...", flush=True)
    else:
        pct = min(100, count * block_size * 100 // total_size)
        kb = min(count * block_size, total_size) // 1024
        total_kb = total_size // 1024
        print(f"    {kb}/{total_kb} KB ({pct}%)", flush=True)


def _download(url: str, dest: Path) -> None:
    """Download *url* to *dest* with progress. Raises on failure or bad size."""
    try:
        urllib.request.urlretrieve(url, dest, reporthook=_reporthook)
    except Exception as exc:
        dest.unlink(missing_ok=True)
        print(f"\r  FAILED — {exc}")
        raise

    size = dest.stat().st_size
    if size < _MIN_DLL_BYTES:
        dest.unlink(missing_ok=True)
        raise RuntimeError(
            f"Downloaded file is only {size} bytes — "
            "likely an LFS pointer or an error page, not a real DLL."
        )

    print(f"  {dest.name}: {size // 1024} KB — OK")

# ---------------------------------------------------------------------------
# Environment variable persistence
# ---------------------------------------------------------------------------

def _persist_env(libs_dir: Path) -> None:
    libs_str = str(libs_dir)
    export_line = f'export RAWFILEREADER_LIBS="{libs_str}"'
    marker = "RAWFILEREADER_LIBS"

    if sys.platform == "win32":
        print("\nTo set the environment variable permanently, run in Command Prompt:")
        print(f'  setx RAWFILEREADER_LIBS "{libs_str}"')
        print("Then restart your terminal for the change to take effect.")
        return

    shell_binary = os.environ.get("SHELL", "")
    if "zsh" in shell_binary:
        rc_path = Path.home() / ".zshrc"
    elif "bash" in shell_binary:
        rc_path = Path.home() / ".bashrc"
    else:
        rc_path = Path.home() / ".profile"

    if rc_path.exists() and marker in rc_path.read_text():
        updated = "\n".join(
            export_line if marker in line else line
            for line in rc_path.read_text().splitlines()
        )
        rc_path.write_text(updated + "\n")
        print(f"\nUpdated {marker} in {rc_path}")
    else:
        with rc_path.open("a") as fh:
            fh.write("\n# RawFileReader DLL directory (added by download_dlls.py)\n")
            fh.write(f"{export_line}\n")
        print(f"\nAdded {marker} to {rc_path}")

    print(f"Run:  source {rc_path}  (or open a new terminal) to apply.")

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
        help="Also download ThermoFisher.CommonCore.BackgroundSubtraction.dll",
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

    # Discover the default branch once (avoids hardcoding 'main' vs 'master')
    print("Resolving repository branch...", end=" ", flush=True)
    branch = _default_branch()
    print(branch)

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
        url = _dll_url(dll_name, branch)
        print(f"  {dll_name}")
        try:
            _download(url, dest)
        except Exception as exc:
            print(f"  {dll_name}: FAILED — {exc}")
            failed.append(dll_name)

    print()

    if failed:
        print("ERROR: The following DLL(s) could not be downloaded:")
        for name in failed:
            print(f"  - {name}")
        print(
            "\nDownload them manually from:\n"
            f"  https://github.com/{_OWNER}/{_REPO}/tree/{branch}/{_PATH}"
        )
        sys.exit(1)

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
