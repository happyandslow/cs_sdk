#!/usr/bin/env python3
"""
Compile script for the bandwidth-test-parallel benchmark.

Uses SdkCompiler (regular Python, no cs_python required) to compile the
memcpy-based loopback layout (src/layout.csl) on the appliance.

Workflow (appliance host — no cs_python available):
  Step 1: python compile_single.py --height H --pe-length N --arch wse3
  Step 2: python run_launcher.py  --height H --pe-length N --arch wse3

run_launcher.py detects that artifact_path.json holds an appliance artifact
hash (not a local directory) and automatically stages run_hw.py for the
appliance-side execution.

This is the appliance-host analogue of:
    cs_python run_single.py --compile-only ...   (which requires cs_python)

Compilation topology
--------------------
  1 column × height rows of loopback PEs (src/layout.csl + src/bw_kernel.csl)
  Host I/O via the memcpy framework (--memcpy --channels=1)
  Fabric: width=8 (4 west memcpy + 1 core + 2 east memcpy + 1)
          height=H+2 (1 fabric-offset + H core rows + 1 guard)
"""

import argparse
import json

from cerebras.sdk.client import SdkCompiler  # pylint: disable=import-error


# Artifact path JSON written by this script and read by run_launcher.py.
ARTIFACT_JSON = "artifact_path.json"

# Full WSE-3 fabric dimensions (required for real hardware runs).
WSE3_FABRIC_DIMS = "762,1172"
WSE2_FABRIC_DIMS = "757,996"


def main():
    parser = argparse.ArgumentParser(
        description="Compile bandwidth-test-parallel (memcpy path) using SdkCompiler"
    )
    parser.add_argument(
        "--height", "-H", type=int, default=4,
        help="Number of PEs in the column (default: 4)"
    )
    parser.add_argument(
        "--pe-length", "-N", type=int, default=1024,
        help="Number of f32 elements per PE (default: 1024)"
    )
    parser.add_argument(
        "--arch", choices=["wse2", "wse3"], default="wse3",
        help="Target WSE architecture (default: wse3)"
    )
    parser.add_argument(
        "--output-dir", default=".",
        help="Directory where artifact_path.json is written (default: .)"
    )
    args = parser.parse_args()

    H = args.height
    N = args.pe_length

    # Fabric dimensions and offsets for the memcpy framework.
    # core_fabric_offset_x = fabric_offset_x(1) + 3 west memcpy columns = 4
    # core_fabric_offset_y = fabric_offset_y(1)
    # min_fabric_width  = 4 + 1 (core width) + 2 (east memcpy) + 1 = 8
    # min_fabric_height = 1 + H + 1 = H + 2
    fabric_offset_x = 4   # 1 base + 3 west memcpy
    fabric_offset_y = 1
    fabric_dims = WSE3_FABRIC_DIMS if args.arch == "wse3" else WSE2_FABRIC_DIMS

    compile_args = (
        f"--arch {args.arch} "
        f"--fabric-dims={fabric_dims} "
        f"--fabric-offsets={fabric_offset_x},{fabric_offset_y} "
        f"--params=height:{H},pe_length:{N} "
        f"-o=latest "
        f"--memcpy "
        f"--channels=1"
    )

    print(f"=== bandwidth-test-parallel: SdkCompiler Compile ===")
    print(f"Architecture : {args.arch.upper()}")
    print(f"Height (PEs) : {H}")
    print(f"PE length    : {N} f32")
    print(f"Fabric dims  : {fabric_dims}")
    print(f"Compile args : {compile_args}")
    print()

    # Disable version check to tolerate client/server version differences.
    with SdkCompiler(disable_version_check=True) as compiler:
        artifact_path = compiler.compile(
            "./src",       # source directory
            "layout.csl",  # top-level CSL file
            compile_args,
            args.output_dir,
        )

    # Save the artifact path for run_launcher.py.
    import os
    artifact_json = os.path.join(args.output_dir, ARTIFACT_JSON)
    with open(artifact_json, "w", encoding="utf-8") as f:
        json.dump({"artifact_path": artifact_path}, f)

    print(f"Compilation successful.")
    print(f"Artifact path : {artifact_path}")
    print(f"Saved to      : {artifact_json}")


if __name__ == "__main__":
    main()
