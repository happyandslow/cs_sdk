#!/usr/bin/env python3
"""
Appliance launcher for the distributed bandwidth test.

Stages run_distributed.py + worker.py + core.py + CSL source onto the
appliance worker via SdkLauncher, then runs cs_python run_distributed.py.

Usage:
    # 2 workers, 1024 f32 buffer, 100 batches
    python run_appliance_distributed.py -P 2 -B 1024 -K 100

    # 4 workers
    python run_appliance_distributed.py -P 4 -B 512 -K 50 --arch wse3

    # Appliance simulator
    python run_appliance_distributed.py -P 2 -B 256 --simulator
"""

import argparse
import os
import shutil

from cerebras.sdk.client import SdkLauncher


FILES_TO_STAGE = [
    'run_distributed.py',
    'worker.py',
    'core.py',
    'src/bw_direct_kernel.csl',
    'out/out_port_map.json',
]


def main():
    parser = argparse.ArgumentParser(
        description='Appliance launcher for distributed bandwidth test'
    )
    parser.add_argument(
        '--num-pipelines', '-P', type=int, default=2,
        help='Number of parallel worker pipelines (default: 2)'
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
            raise FileNotFoundError("Required file not found: %s" % f)

    staging_dir = 'bw_staging_distributed'
    if os.path.exists(staging_dir):
        shutil.rmtree(staging_dir)
    os.makedirs(staging_dir)
    os.makedirs(os.path.join(staging_dir, 'src'), exist_ok=True)
    os.makedirs(os.path.join(staging_dir, 'out'), exist_ok=True)
    for f in FILES_TO_STAGE:
        shutil.copy2(f, os.path.join(staging_dir, f))

    run_cmd = (
        "cs_python run_distributed.py "
        "--num-pipelines %d "
        "--buf-size %d "
        "--num-batches %d "
        "--arch %s "
        "--cmaddr %%CMADDR%%"
    ) % (args.num_pipelines, args.buf_size, args.num_batches, args.arch)

    pe_elems = args.buf_size * args.num_batches
    total = args.num_pipelines * pe_elems
    print("=== Distributed Bandwidth Test: Appliance Launcher ===")
    print("Architecture : %s" % args.arch.upper())
    print("Workers      : %d" % args.num_pipelines)
    print("Buffer size  : %d f32" % args.buf_size)
    print("Num batches  : %d" % args.num_batches)
    print("Per-worker   : %d f32  (%.1f KB)" % (pe_elems, pe_elems * 4 / 1024))
    print("Total data   : %d f32  (%.1f KB)" % (total, total * 4 / 1024))
    print("Simulator    : %s" % args.simulator)
    print("Run command  : %s" % run_cmd)
    print()

    with SdkLauncher(staging_dir, simulator=args.simulator,
                     disable_version_check=True) as launcher:
        response = launcher.run(run_cmd)

    print("Appliance response:")
    print(response)


if __name__ == '__main__':
    main()
