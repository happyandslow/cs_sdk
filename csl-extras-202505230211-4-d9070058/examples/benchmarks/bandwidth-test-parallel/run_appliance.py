#!/usr/bin/env python3
"""
Appliance launcher for the bandwidth-test-parallel benchmark.

Stages run scripts + helper scripts + CSL source files into a directory,
passes it to SdkLauncher (which tars and uploads it), then runs either
run.py (single pipeline) or run_parallel.py (multiple pipelines).

Usage:
    # Single pipeline (default)
    python run_appliance.py --buf-size 1024 --arch wse3

    # Large transfer with batching
    python run_appliance.py --buf-size 1024 --num-batches 100

    # Parallel pipelines
    python run_appliance.py --num-pipelines 4 --buf-size 1024 --num-batches 10

    # Appliance simulator
    python run_appliance.py --num-pipelines 2 --buf-size 256 --simulator
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
    'src/bw_direct_kernel.csl',
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
        '--buf-size', '-B', type=int, default=1024,
        help='Buffer size per batch in f32 elements (default: 1024)'
    )
    parser.add_argument(
        '--num-batches', '-K', type=int, default=1,
        help='Number of batches per PE (default: 1)'
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

    buf_args = f"--buf-size {args.buf_size} --num-batches {args.num_batches}"

    if args.num_pipelines > 1:
        run_cmd = (
            f"cs_python run_parallel.py "
            f"--num-pipelines {args.num_pipelines} "
            f"{buf_args} "
            f"--arch {args.arch} "
            f"--cmaddr %CMADDR%"
        )
    else:
        run_cmd = (
            f"cs_python run.py "
            f"{buf_args} "
            f"--arch {args.arch} "
            f"--cmaddr %CMADDR%"
        )

    pe_elems = args.buf_size * args.num_batches
    print(f"=== bandwidth-test-parallel: Appliance Launcher ===")
    print(f"Architecture : {args.arch.upper()}")
    print(f"Pipelines    : {args.num_pipelines}")
    print(f"Buffer size  : {args.buf_size} f32")
    print(f"Num batches  : {args.num_batches}")
    print(f"Per-PE data  : {pe_elems} f32  ({pe_elems * 4 / 1024:.1f} KB)")
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
