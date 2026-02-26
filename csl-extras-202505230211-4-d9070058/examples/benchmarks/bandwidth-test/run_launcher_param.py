#!/usr/bin/env python3
"""
Parameterized run launcher script for bandwidth testing.
Accepts command-line arguments for all run parameters.
Uses the same launcher pattern as run_launcher.py
"""
import argparse
import json
import os
from cerebras.sdk.client import SdkLauncher


def main():
    parser = argparse.ArgumentParser(description="Parameterized run launcher for bandwidth testing")
    
    # Matrix dimensions
    parser.add_argument("--m", type=int, required=True, help="Height dimension")
    parser.add_argument("--n", type=int, required=True, help="Width dimension")
    parser.add_argument("--k", type=int, required=True, help="PE length dimension")
    
    # Buffer sizes
    parser.add_argument("--width-west-buf", type=int, required=True, help="West buffer width")
    parser.add_argument("--width-east-buf", type=int, required=True, help="East buffer width")
    
    # Channels
    parser.add_argument("--channels", type=int, required=True, help="Number of I/O channels")
    
    # Direction
    parser.add_argument("--direction", type=str, choices=["h2d", "d2h"], required=True,
                       help="Transfer direction: h2d (host-to-device) or d2h (device-to-host)")
    
    # Loop count
    parser.add_argument("--loop-count", type=int, default=5, help="Number of iterations (default: 5)")
    
    # Architecture
    parser.add_argument("--arch", type=str, default="wse3", help="Architecture (default: wse3)")
    
    # Artifact path (optional, will read from artifact_path.json if not provided)
    parser.add_argument("--artifact-path", type=str, default=None,
                       help="Path to artifact JSON file (default: artifact_path.json)")
    
    # Simulator flag
    parser.add_argument("--simulator", action="store_true", help="Run in simulator mode")
    
    args = parser.parse_args()
    
    # Read artifact path (same as run_launcher.py)
    artifact_json_path = args.artifact_path or "artifact_path.json"
    if not os.path.exists(artifact_json_path):
        raise FileNotFoundError(f"Artifact path file not found: {artifact_json_path}")
    
    artifact_path = ""
    with open(artifact_json_path, "r", encoding="utf8") as f:
        data = json.load(f)
        artifact_path = data["artifact_path"]
    
    print(f"Running with parameters:")
    print(f"  m={args.m}, n={args.n}, k={args.k}")
    print(f"  channels={args.channels}")
    print(f"  width-west-buf={args.width_west_buf}, width-east-buf={args.width_east_buf}")
    print(f"  direction={args.direction}")
    print(f"  loop_count={args.loop_count}")
    print(f"  arch={args.arch}")
    print(f"  simulator={args.simulator}")
    
    # Build run command string (same format as run_launcher.py)
    # For d2h, add --d2h flag; for h2d, no flag needed (default)
    direction_flag = f"--{args.direction} " if args.direction == "d2h" else ""
    run_cmd = (
        f"cs_python run.py "
        f"-m={args.m} -n={args.n} -k={args.k} "
        f"--latestlink latest "
        f"--channels={args.channels} "
        f"--width-west-buf={args.width_west_buf} "
        f"--width-east-buf={args.width_east_buf} "
        f"--arch={args.arch} "
        f"{direction_flag}"
        f"--run-only "
        f"--loop_count={args.loop_count} "
        f"--cmaddr %CMADDR%"
    )
    
    # artifact_path contains the path to the compiled artifact.
    # It will be transferred and extracted in the appliance.
    # The extracted directory will be the working directory.
    # Set simulator=False if running on CS system within appliance.
    # Disable version check to ignore appliance client and server version differences.
    # (Same invocation pattern as run_launcher.py)
    with SdkLauncher(artifact_path, simulator=args.simulator, disable_version_check=True) as launcher:
        # Transfer additional files to the appliance (same as run_launcher.py)
        launcher.stage("run.py")
        launcher.stage("bw_cmd_parser.py")
        
        # Run the command (same invocation pattern as run_launcher.py)
        print(f"Executing: {run_cmd}")
        response = launcher.run(run_cmd)
        
        print("Host code execution response: ", response)
        
        return response


if __name__ == "__main__":
    main()
