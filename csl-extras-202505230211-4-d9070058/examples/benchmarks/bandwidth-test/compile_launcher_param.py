#!/usr/bin/env python3
"""
Parameterized compile launcher script for bandwidth testing.
Accepts command-line arguments for all compile parameters.
Uses the same compilation pattern as compile_launcher.py
"""
import argparse
import json
from cerebras.sdk.client import SdkCompiler


def calculate_fabric_offsets(width_west_buf, width_east_buf):
    """Calculate fabric offsets based on buffer sizes."""
    fabric_offset_x = 1
    fabric_offset_y = 1
    # memcpy framework requires 3 columns at the west of the core rectangle
    # memcpy framework requires 2 columns at the east of the core rectangle
    core_fabric_offset_x = fabric_offset_x + 3 + width_west_buf
    core_fabric_offset_y = fabric_offset_y + width_east_buf
    return core_fabric_offset_x, core_fabric_offset_y


def main():
    parser = argparse.ArgumentParser(description="Parameterized compile launcher for bandwidth testing")
    
    # Matrix dimensions
    parser.add_argument("--m", type=int, required=True, help="Height dimension")
    parser.add_argument("--n", type=int, required=True, help="Width dimension")
    parser.add_argument("--k", type=int, required=True, help="PE length dimension")
    
    # Buffer sizes
    parser.add_argument("--width-west-buf", type=int, required=True, help="West buffer width")
    parser.add_argument("--width-east-buf", type=int, required=True, help="East buffer width")
    
    # Channels
    parser.add_argument("--channels", type=int, required=True, help="Number of I/O channels")
    
    # Architecture
    parser.add_argument("--arch", type=str, default="wse3", help="Architecture (default: wse3)")
    
    # Fabric dimensions (optional, will use defaults if not provided)
    parser.add_argument("--fabric-dims", type=str, default="762,1172", 
                       help="Fabric dimensions as 'width,height' (default: 762,1172)")
    
    # Fabric offsets (optional, will be calculated if not provided)
    parser.add_argument("--fabric-offsets", type=str, default=None,
                       help="Fabric offsets as 'x,y' (will be calculated if not provided)")
    
    # Output directory
    parser.add_argument("--output-dir", type=str, default=".", help="Output directory (default: .)")
    parser.add_argument("--output-name", type=str, default="latest", help="Output name (default: latest)")
    
    # C IDs (usually fixed)
    parser.add_argument("--C0_ID", type=int, default=0, help="C0_ID (default: 0)")
    parser.add_argument("--C1_ID", type=int, default=1, help="C1_ID (default: 1)")
    parser.add_argument("--C2_ID", type=int, default=2, help="C2_ID (default: 2)")
    parser.add_argument("--C3_ID", type=int, default=3, help="C3_ID (default: 3)")
    parser.add_argument("--C4_ID", type=int, default=4, help="C4_ID (default: 4)")
    
    # Source path
    parser.add_argument("--src-path", type=str, default="./src", help="Source path (default: ./src)")
    parser.add_argument("--csl-file", type=str, default="bw_sync_layout.csl", 
                       help="CSL file name (default: bw_sync_layout.csl)")
    
    args = parser.parse_args()
    
    # Parse fabric dimensions
    fabric_width, fabric_height = map(int, args.fabric_dims.split(","))
    
    # Calculate or use provided fabric offsets
    if args.fabric_offsets:
        fabric_offset_x, fabric_offset_y = map(int, args.fabric_offsets.split(","))
    else:
        fabric_offset_x, fabric_offset_y = calculate_fabric_offsets(
            args.width_west_buf, args.width_east_buf
        )
    
    # Build compile command string (same format as compile_launcher.py)
    compile_args = (
        f"--arch {args.arch} "
        f"--fabric-dims={fabric_width},{fabric_height} "
        f"--fabric-offsets={fabric_offset_x},{fabric_offset_y} "
        f"--params=width:{args.n},height:{args.m},pe_length:{args.k} "
        f"--params=C0_ID:{args.C0_ID} "
        f"--params=C1_ID:{args.C1_ID} "
        f"--params=C2_ID:{args.C2_ID} "
        f"--params=C3_ID:{args.C3_ID} "
        f"--params=C4_ID:{args.C4_ID} "
        f"-o={args.output_name} "
        f"--memcpy "
        f"--channels={args.channels} "
        f"--width-west-buf={args.width_west_buf} "
        f"--width-east-buf={args.width_east_buf}"
    )
    
    print(f"Compiling with parameters:")
    print(f"  m={args.m}, n={args.n}, k={args.k}")
    print(f"  channels={args.channels}")
    print(f"  width-west-buf={args.width_west_buf}, width-east-buf={args.width_east_buf}")
    print(f"  fabric-dims={fabric_width},{fabric_height}")
    print(f"  fabric-offsets={fabric_offset_x},{fabric_offset_y}")
    print(f"  Compile args: {compile_args}")
    
    # Instantiate compiler using a context manager (same as compile_launcher.py)
    # Disable version check to ignore appliance client and server version differences.
    with SdkCompiler(disable_version_check=True) as compiler:
        # Launch compile job (same invocation pattern as compile_launcher.py)
        artifact_path = compiler.compile(
            args.src_path,
            args.csl_file,
            compile_args,
            args.output_dir
        )
        
        # Write the artifact_path to a JSON file (same as compile_launcher.py)
        artifact_json_path = f"{args.output_dir}/artifact_path.json"
        with open(artifact_json_path, "w", encoding="utf8") as f:
            json.dump({"artifact_path": artifact_path}, f)
        
        print(f"Compilation successful. Artifact path saved to {artifact_json_path}")
        print(f"Artifact path: {artifact_path}")


if __name__ == "__main__":
    main()
