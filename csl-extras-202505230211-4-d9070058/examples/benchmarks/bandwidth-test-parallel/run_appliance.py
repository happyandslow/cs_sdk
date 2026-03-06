#!/usr/bin/env python3
"""
Appliance launcher for the bandwidth-test-parallel benchmark.

Stages run scripts + helper scripts + CSL source files into a directory,
passes it to SdkLauncher (which tars and uploads it), then runs either
run.py (single pipeline) or run_parallel.py (multiple pipelines).

Usage:
    # Single pipeline (default)
    python run_appliance.py --height 8 --pe-length 1024 --arch wse3

    # Parallel pipelines
    python run_appliance.py --num-pipelines 4 --height 8 --pe-length 1024

    # With verification
    python run_appliance.py --num-pipelines 2 --height 4 --pe-length 256 --verify
"""

import argparse
import os
import shutil

from cerebras.sdk.client import SdkLauncher


# Files to stage on the appliance worker.
FILES_TO_STAGE = [
    'run.py',
    'run_parallel.py',
    'core.py',
    'demux.py',
    'mux.py',
    'src/bw_loopback_kernel.csl',
    'src/demux_adaptor.csl',
    'src/demux.csl',
    'src/mux.csl',
]


def main():
    parser = argparse.ArgumentParser(
        description='Appliance launcher for bandwidth-test-parallel (direct-link)'
    )
    parser.add_argument(
        '--num-pipelines', '-P', type=int, default=1,
        help='Number of parallel pipelines (default: 1 = single pipeline via run.py)'
    )
    parser.add_argument(
        '--width', '-W', type=int, default=1,
        help='Number of PE columns (default: 1, only used with single pipeline)'
    )
    parser.add_argument(
        '--height', '-H', type=int, default=4,
        help='Number of PE rows per pipeline (default: 4)'
    )
    parser.add_argument(
        '--pe-length', '-N', type=int, default=1024,
        help='Number of f32 elements per PE (default: 1024)'
    )
    parser.add_argument(
        '--arch', choices=['wse2', 'wse3'], default='wse3',
        help='Target WSE architecture (default: wse3)'
    )
    parser.add_argument(
        '--verify', action='store_true',
        help='Verify loopback: check received data matches sent data'
    )
    parser.add_argument(
        '--simulator', action='store_true',
        help='Run in appliance simulator mode (default: real hardware)'
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    for f in FILES_TO_STAGE:
        if not os.path.exists(f):
            raise FileNotFoundError(f"Required file not found: {f}")

    # Create staging directory with all files.
    staging_dir = 'bw_staging'
    if os.path.exists(staging_dir):
        shutil.rmtree(staging_dir)
    os.makedirs(staging_dir)
    os.makedirs(os.path.join(staging_dir, 'src'), exist_ok=True)
    for f in FILES_TO_STAGE:
        shutil.copy2(f, os.path.join(staging_dir, f))

    verify_flag = '--verify' if args.verify else ''

    if args.num_pipelines > 1:
        run_cmd = (
            f"cs_python run_parallel.py "
            f"--num-pipelines {args.num_pipelines} "
            f"--height {args.height} "
            f"--pe-length {args.pe_length} "
            f"--arch {args.arch} "
            f"{verify_flag} "
            f"--cmaddr %CMADDR%"
        ).strip()
    else:
        run_cmd = (
            f"cs_python run.py "
            f"--width {args.width} "
            f"--height {args.height} "
            f"--pe-length {args.pe_length} "
            f"--arch {args.arch} "
            f"{verify_flag} "
            f"--cmaddr %CMADDR%"
        ).strip()

    print(f"=== bandwidth-test-parallel: Appliance Launcher ===")
    print(f"Architecture : {args.arch.upper()}")
    print(f"Pipelines    : {args.num_pipelines}")
    print(f"Height (PEs) : {args.height}")
    print(f"PE length    : {args.pe_length} f32")
    print(f"Simulator    : {args.simulator}")
    print(f"Run command  : {run_cmd}")
    print()

    with SdkLauncher(staging_dir, simulator=args.simulator,
                     disable_version_check=True) as launcher:
        response = launcher.run(run_cmd)

    print("Appliance response:")
    print(response)


if __name__ == '__main__':
    main()
