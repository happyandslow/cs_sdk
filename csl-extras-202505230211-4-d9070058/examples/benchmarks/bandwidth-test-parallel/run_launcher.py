#!/usr/bin/env python3
"""
Appliance launcher for the bandwidth-test-parallel benchmark.

Two paths:

  Path A — SdkLayout (direct-link):
    python run_launcher.py --direct-link --height H --pe-length N --arch wse3
    → stages src/ + Python scripts to the appliance worker; runs
      cs_python run_single.py --cmaddr %CMADDR% (compile+run in one step).
    Compilation MUST happen on the appliance because SdkLayout gets fabric
    dimensions (762×1172 for WSE-3) from the platform object, which requires
    get_system(cmaddr).  Local compilation with get_simulator() produces
    minimal-fabric ELFs that fail on hardware.

  Path B — SdkCompiler (memcpy):
    Compile:  python compile_single.py --height H --pe-length N --arch wse3
    Launch:   python run_launcher.py   --height H --pe-length N --arch wse3
    → stages run_hw.py; calls cs_python run_hw.py on appliance.
    SdkCompiler passes --fabric-dims=762,1172 explicitly to cslc, so
    compilation happens remotely with correct fabric dimensions.

Detection (when --direct-link is not used):
  Reads artifact_path.json from a prior compile step.
  If artifact_path is an appliance hash → Path B.
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
        '--direct-link', action='store_true',
        help='Use SdkLayout direct-link path (Path A). '
             'Stages source + scripts to the appliance; compiles and runs there. '
             'No artifact_path.json needed.'
    )
    parser.add_argument(
        '--artifact-path', default=ARTIFACT_JSON,
        help=f'Path to artifact_path.json from compile step (default: {ARTIFACT_JSON}). '
             'Only used for Path B (SdkCompiler/memcpy). Ignored with --direct-link.'
    )
    args = parser.parse_args()

    # ---- Determine path ----
    if args.direct_link:
        is_sdklayout = True
        artifact_path = None
    else:
        if not os.path.exists(args.artifact_path):
            raise FileNotFoundError(
                f"Artifact path file not found: {args.artifact_path}\n"
                "Options:\n"
                f"  Path A (direct-link): python run_launcher.py --direct-link "
                f"--height {args.height} --pe-length {args.pe_length} --arch {args.arch}\n"
                f"  Path B (SdkCompiler): python compile_single.py "
                f"--height {args.height} --pe-length {args.pe_length} --arch {args.arch}\n"
                f"                        python run_launcher.py "
                f"--height {args.height} --pe-length {args.pe_length} --arch {args.arch}"
            )
        with open(args.artifact_path, encoding='utf-8') as f:
            artifact_path = json.load(f)['artifact_path']

    path_label = "SdkLayout (direct-link)" if is_sdklayout else "SdkCompiler (memcpy)"

    print(f"=== Appliance Launcher: bandwidth-test-parallel ===")
    print(f"Compile path : {path_label}")
    if artifact_path is not None:
        print(f"Artifact     : {artifact_path}")
    else:
        print(f"Artifact     : (compile+run on appliance worker)")
    print(f"Width  (PEs) : {args.width}")
    print(f"Height (PEs) : {args.height}")
    print(f"PE length    : {args.pe_length} f32")
    print(f"Arch         : {args.arch.upper()}")
    print(f"Simulator    : {args.simulator}")
    print()

    verify_flag = '--verify' if args.verify else ''
    sync_flag   = '--sync'   if args.sync   else ''

    if is_sdklayout:
        # Path A: SdkLayout (direct-link).
        # Compile AND run on the appliance worker in one step.
        # SdkLayout.compile() gets fabric dims from the platform object;
        # get_system(%CMADDR%) on the appliance provides the full WSE-3
        # fabric (762×1172).  Local compilation with get_simulator() would
        # produce a minimal-fabric ELF that fails on hardware.
        #
        # Stage source files + Python scripts for the appliance worker.
        import tarfile
        staging_tar = 'dl_staging.tar.gz'
        with tarfile.open(staging_tar, 'w:gz') as tar:
            tar.add('src')
            tar.add('run_single.py')
            tar.add('demux.py')
            tar.add('mux.py')
            tar.add('core.py')

        run_cmd = (
            f"cs_python run_single.py "
            f"--width {args.width} "
            f"--height {args.height} "
            f"--pe-length {args.pe_length} "
            f"--arch {args.arch} "
            f"{sync_flag} "
            f"{verify_flag} "
            f"--cmaddr %CMADDR%"
        ).strip()

        print(f"Staging source + scripts to appliance (compile+run) ...")
        print(f"Run command: {run_cmd}")
        print()

        with SdkLauncher(staging_tar, simulator=args.simulator,
                         disable_version_check=True) as launcher:
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
