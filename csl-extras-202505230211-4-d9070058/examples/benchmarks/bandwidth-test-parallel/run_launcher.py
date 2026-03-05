#!/usr/bin/env python3
"""
Appliance launcher for the bandwidth-test-parallel benchmark.

Workflow (memcpy path, SdkCompiler):
  Step 1:  python compile_single.py --height H --pe-length N --arch wse3
           → SdkCompiler compiles src/layout.csl with --fabric-dims=762,1172
           → writes artifact hash to artifact_path.json

  Step 2:  python run_launcher.py --height H --pe-length N --arch wse3
           → SdkLauncher stages run_hw.py, ships compiled artifact to appliance
           → calls cs_python run_hw.py --cmaddr %CMADDR% on the worker

Note: The SdkLayout (direct-link) path in run_single.py is simulator-only.
SdkLayout programs cannot be compiled via SdkCompiler/cslc because they
require multi-region layout and create_input/output_stream(), which are
Python-API-only features.  For appliance runs, use the memcpy path above.
"""

import argparse
import json
import os

from cerebras.sdk.client import SdkLauncher


ARTIFACT_JSON = 'artifact_path.json'


def main():
    parser = argparse.ArgumentParser(
        description='Appliance launcher for bandwidth-test-parallel'
    )
    parser.add_argument(
        '--width', '-W', type=int, default=1,
        help='Number of PE columns (default: 1; must match compile step)'
    )
    parser.add_argument(
        '--height', '-H', type=int, default=4,
        help='Number of PE rows (default: 4; must match compile step)'
    )
    parser.add_argument(
        '--pe-length', '-N', type=int, default=1024,
        help='Number of f32 elements per PE (default: 1024; must match compile step)'
    )
    parser.add_argument(
        '--arch', choices=['wse2', 'wse3'], default='wse3',
        help='Target WSE architecture (default: wse3)'
    )
    parser.add_argument(
        '--loop-count', '-L', type=int, default=1,
        help='Number of back-to-back transfers (default: 1)'
    )
    parser.add_argument(
        '--d2h', action='store_true',
        help='Measure D2H bandwidth (default: H2D)'
    )
    parser.add_argument(
        '--sync', action='store_true',
        help='Use blocking (sync) memcpy transfers instead of async'
    )
    parser.add_argument(
        '--verify', action='store_true',
        help='Verify loopback: check received data matches sent data'
    )
    parser.add_argument(
        '--simulator', action='store_true',
        help='Run inside the appliance in simulator mode (default: real hardware)'
    )
    parser.add_argument(
        '--artifact-path', default=ARTIFACT_JSON,
        help=f'Path to artifact_path.json from compile step (default: {ARTIFACT_JSON})'
    )
    args = parser.parse_args()

    # ---- Read compiled artifact path ----
    if not os.path.exists(args.artifact_path):
        raise FileNotFoundError(
            f"Artifact path file not found: {args.artifact_path}\n"
            "Run compile step first:\n"
            f"  python compile_single.py "
            f"--height {args.height} --pe-length {args.pe_length} --arch {args.arch}"
        )
    with open(args.artifact_path, encoding='utf-8') as f:
        artifact_path = json.load(f)['artifact_path']

    print(f"=== Appliance Launcher: bandwidth-test-parallel ===")
    print(f"Artifact     : {artifact_path}")
    print(f"Width  (PEs) : {args.width}")
    print(f"Height (PEs) : {args.height}")
    print(f"PE length    : {args.pe_length} f32")
    print(f"Arch         : {args.arch.upper()}")
    print(f"Simulator    : {args.simulator}")
    print()

    verify_flag = '--verify' if args.verify else ''
    sync_flag   = '--sync'   if args.sync   else ''
    d2h_flag    = '--d2h'    if args.d2h    else ''

    run_cmd = (
        f"cs_python run_hw.py "
        f"--width {args.width} "
        f"--height {args.height} "
        f"--pe-length {args.pe_length} "
        f"--loop-count {args.loop_count} "
        f"--latestlink latest "
        f"{d2h_flag} "
        f"{sync_flag} "
        f"{verify_flag} "
        f"--cmaddr %CMADDR%"
    ).strip()

    print(f"Submitting to appliance ...")
    print(f"Run command: {run_cmd}")
    print()

    with SdkLauncher(artifact_path, simulator=args.simulator,
                     disable_version_check=True) as launcher:
        launcher.stage('run_hw.py')
        response = launcher.run(run_cmd)

    print("Appliance response:")
    print(response)


if __name__ == '__main__':
    main()
