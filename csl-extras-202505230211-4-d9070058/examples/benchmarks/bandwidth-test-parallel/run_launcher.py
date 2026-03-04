#!/usr/bin/env python3
"""
Appliance launcher for the bandwidth-test-parallel benchmark.

Supports two compile paths, auto-detected from artifact_path.json:

  Path A — SdkLayout (direct-link, cs_python required for compilation):
    Compile:  cs_python run_single.py --compile-only --height H --pe-length N --arch wse3
    Launch:   python run_launcher.py  --height H --pe-length N --arch wse3
    → stages run_single.py + helpers; calls cs_python run_single.py --run-only on appliance

  Path B — SdkCompiler (memcpy, no cs_python required for compilation):
    Compile:  python compile_single.py --height H --pe-length N --arch wse3
    Launch:   python run_launcher.py   --height H --pe-length N --arch wse3
    → stages run_hw.py; calls cs_python run_hw.py on appliance

Detection:
  If artifact_path from artifact_path.json is an existing local directory
  → Path A (SdkLayout artifact, local directory uploaded by SdkLauncher).
  Otherwise (appliance artifact hash from SdkCompiler)
  → Path B (memcpy artifact, hash resolved by SdkLauncher on appliance).
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
            "Run a compile step first:\n"
            f"  Path A (SdkLayout):   cs_python run_single.py --compile-only "
            f"--height {args.height} --pe-length {args.pe_length} --arch {args.arch}\n"
            f"  Path B (SdkCompiler): python compile_single.py "
            f"--height {args.height} --pe-length {args.pe_length} --arch {args.arch}"
        )
    with open(args.artifact_path, encoding='utf-8') as f:
        artifact_path = json.load(f)['artifact_path']

    # ---- Auto-detect compile path ----
    # Path A: artifact_path is a local directory (SdkLayout produced it locally).
    # Path B: artifact_path is an appliance hash (SdkCompiler produced it remotely).
    is_sdklayout = os.path.isdir(artifact_path)
    path_label = "SdkLayout (direct-link)" if is_sdklayout else "SdkCompiler (memcpy)"

    print(f"=== Appliance Launcher: bandwidth-test-parallel ===")
    print(f"Compile path : {path_label}")
    print(f"Artifact     : {artifact_path}")
    print(f"Width  (PEs) : {args.width}")
    print(f"Height (PEs) : {args.height}")
    print(f"PE length    : {args.pe_length} f32")
    print(f"Arch         : {args.arch.upper()}")
    print(f"Simulator    : {args.simulator}")
    print()

    verify_flag = '--verify' if args.verify else ''
    sync_flag   = '--sync'   if args.sync   else ''

    if is_sdklayout:
        # Path A: SdkLayout artifact (local directory).
        # The appliance side uses run_single.py --run-only with the SdkLayout stream API.
        # SdkLauncher uploads the entire artifact directory to the appliance.
        run_cmd = (
            f"cs_python run_single.py "
            f"--run-only "
            f"--name . "
            f"--width {args.width} "
            f"--height {args.height} "
            f"--pe-length {args.pe_length} "
            f"--arch {args.arch} "
            f"{verify_flag} "
            f"--cmaddr %CMADDR%"
        ).strip()

        print(f"Staging files and submitting to appliance ...")
        print(f"Run command: {run_cmd}")
        print()

        with SdkLauncher(artifact_path, simulator=args.simulator,
                         disable_version_check=True) as launcher:
            launcher.stage('run_single.py')
            launcher.stage('demux.py')
            launcher.stage('mux.py')
            launcher.stage('core.py')
            response = launcher.run(run_cmd)

    else:
        # Path B: SdkCompiler artifact (appliance hash).
        # The appliance side uses run_hw.py with the memcpy API.
        # SdkLauncher resolves the hash and runs the artifact on the appliance.
        run_cmd = (
            f"cs_python run_hw.py "
            f"--width {args.width} "
            f"--height {args.height} "
            f"--pe-length {args.pe_length} "
            f"--latestlink latest "
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
