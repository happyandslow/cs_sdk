#!/usr/bin/env python3
"""
Appliance launcher for the bandwidth-test-parallel benchmark.

Workflow:
  1. Compile locally (no hardware needed):
       cs_python run_single.py --compile-only --height H --pe-length N --arch wse3
     This creates the compiled artifact directory and artifact_path.json.

  2. Launch on appliance:
       python run_launcher.py --height H --pe-length N --arch wse3

     SdkLauncher:
       - Transfers the compiled artifact to the appliance
       - Stages run_single.py + helper Python files alongside the artifact
       - Runs: cs_python run_single.py --run-only --name . --height H --pe-length N
                   --arch A [--verify] --cmaddr %CMADDR%

     On the appliance, the working directory is the extracted artifact directory,
     so --name . resolves correctly to the artifact.

Key difference from the memcpy-based workflow (bandwidth-test):
  - Compilation uses SdkLayout.compile() locally (no SdkCompiler needed).
  - The artifact is a directory (e.g., 'out/') not a hash string.
  - SdkRuntime on the appliance uses get_platform(cmaddr, ...) to connect.
"""

import argparse
import json
import os

from cerebras.sdk.client import SdkLauncher


ARTIFACT_JSON = 'artifact_path.json'


def main():
    parser = argparse.ArgumentParser(
        description='Appliance launcher for bandwidth-test-parallel (direct-link loopback)'
    )
    parser.add_argument(
        '--height', '-H', type=int, default=4,
        help='Number of PEs in the column (default: 4; must match --compile-only run)'
    )
    parser.add_argument(
        '--pe-length', '-N', type=int, default=1024,
        help='Number of f32 elements per PE (default: 1024; must match --compile-only run)'
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
        help='Run inside the appliance in simulator mode (default: real hardware)'
    )
    parser.add_argument(
        '--artifact-path', default=ARTIFACT_JSON,
        help=f'Path to artifact_path.json written by --compile-only (default: {ARTIFACT_JSON})'
    )
    args = parser.parse_args()

    # ---- Read compiled artifact path ----
    if not os.path.exists(args.artifact_path):
        raise FileNotFoundError(
            f"Artifact path file not found: {args.artifact_path}\n"
            f"Run first:  cs_python run_single.py --compile-only "
            f"--height {args.height} --pe-length {args.pe_length} --arch {args.arch}"
        )
    with open(args.artifact_path, encoding='utf-8') as f:
        artifact_path = json.load(f)['artifact_path']

    print(f"=== Appliance Launcher: bandwidth-test-parallel ===")
    print(f"Artifact     : {artifact_path}")
    print(f"Height (PEs) : {args.height}")
    print(f"PE length    : {args.pe_length} f32")
    print(f"Arch         : {args.arch.upper()}")
    print(f"Simulator    : {args.simulator}")
    print()

    # ---- Build the run command ----
    # --name . : on the appliance the working directory IS the extracted artifact,
    #            so "." is the correct artifact path for SdkRuntime.
    verify_flag = '--verify' if args.verify else ''
    run_cmd = (
        f"cs_python run_single.py "
        f"--run-only "
        f"--name . "
        f"--height {args.height} "
        f"--pe-length {args.pe_length} "
        f"--arch {args.arch} "
        f"{verify_flag} "
        f"--cmaddr %CMADDR%"
    ).strip()

    # ---- Launch on appliance ----
    print(f"Staging files and submitting to appliance ...")
    print(f"Run command: {run_cmd}")
    print()

    with SdkLauncher(artifact_path, simulator=args.simulator, disable_version_check=True) as launcher:
        # Stage all Python helper files needed on the appliance side.
        launcher.stage('run_single.py')
        launcher.stage('demux.py')
        launcher.stage('mux.py')
        launcher.stage('core.py')

        response = launcher.run(run_cmd)
        print("Appliance response:")
        print(response)


if __name__ == '__main__':
    main()
