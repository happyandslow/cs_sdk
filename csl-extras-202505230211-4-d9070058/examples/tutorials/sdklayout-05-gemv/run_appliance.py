#!/usr/bin/env python3
"""
Appliance launcher for the sdklayout-05-gemv tutorial.

Creates a staging directory with run.py + helper scripts + CSL source files,
passes it to SdkLauncher (which tars and uploads it), then runs:
    cs_python run.py --cmaddr %CMADDR% --arch <arch>

On the worker, get_platform(cmaddr) connects to the CS system and
provides the full fabric dimensions (762x1172 for WSE-3) that
SdkLayout.compile() needs.

Usage:
    python run_appliance.py                     # defaults: wse3
    python run_appliance.py --arch wse3
    python run_appliance.py --simulator         # appliance simulator mode
"""

import argparse
import os
import shutil

from cerebras.sdk.client import SdkLauncher


def main():
    parser = argparse.ArgumentParser(
        description='Appliance launcher for sdklayout-05-gemv'
    )
    parser.add_argument(
        '--arch', choices=['wse2', 'wse3'], default='wse3',
        help='Target WSE architecture (default: wse3)'
    )
    parser.add_argument(
        '--simulator', action='store_true',
        help='Run in appliance simulator mode (default: real hardware)'
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Files to stage: run.py + Python helpers + CSL sources
    files_to_stage = [
        'run.py',
        'demux.py',
        'mux.py',
        'gemv.py',
        'demux_adaptor.csl',
        'demux.csl',
        'gemv.csl',
        'mux.csl',
    ]

    for f in files_to_stage:
        if not os.path.exists(f):
            raise FileNotFoundError(f"Required file not found: {f}")

    # Create a staging directory with all files.
    # SdkLauncher(dir) tars up the directory contents and extracts them
    # on the worker — the worker's working directory will contain the files.
    staging_dir = 'gemv_staging'
    if os.path.exists(staging_dir):
        shutil.rmtree(staging_dir)
    os.makedirs(staging_dir)
    for f in files_to_stage:
        shutil.copy2(f, staging_dir)

    run_cmd = (
        f"cs_python run.py "
        f"--cmaddr %CMADDR% "
        f"--arch {args.arch}"
    )

    print(f"=== sdklayout-05-gemv: Appliance Launcher ===")
    print(f"Architecture : {args.arch.upper()}")
    print(f"Simulator    : {args.simulator}")
    print(f"Staged files : {', '.join(files_to_stage)}")
    print(f"Run command  : {run_cmd}")
    print()

    with SdkLauncher(staging_dir, simulator=args.simulator,
                     disable_version_check=True) as launcher:
        response = launcher.run("ls -la")
        print("Appliance response:")
        print(response)
        response = launcher.run(run_cmd)

    print("Appliance response:")
    print(response)


if __name__ == '__main__':
    main()
