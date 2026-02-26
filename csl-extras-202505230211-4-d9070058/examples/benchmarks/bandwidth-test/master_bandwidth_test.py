#!/usr/bin/env python3
"""
Master script for bandwidth testing that iterates through different parameter combinations.
Compiles and runs tests for both H2D and D2H directions, capturing all output to log files.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path


def cleanup_build_artifacts():
    """Clean up build artifacts before each compile."""
    artifacts = [
        "cs_*.tar.gz",
        "latest",
        "hash.json",
        "wsjob*"
    ]
    for artifact in artifacts:
        if "*" in artifact:
            # Use glob for patterns
            import glob
            for file in glob.glob(artifact):
                if os.path.isfile(file):
                    os.remove(file)
                elif os.path.isdir(file):
                    import shutil
                    shutil.rmtree(file)
        else:
            if os.path.exists(artifact):
                if os.path.isfile(artifact):
                    os.remove(artifact)
                elif os.path.isdir(artifact):
                    import shutil
                    shutil.rmtree(artifact)


def run_command(cmd, log_file=None, description=""):
    """Run a command and optionally capture output to a log file."""
    if description:
        print(f"\n{'='*70}")
        print(f"{description}")
        print(f"{'='*70}")
    
    print(f"Running: {cmd}")
    
    if log_file:
        log_dir = os.path.dirname(log_file) if os.path.dirname(log_file) else "."
        os.makedirs(log_dir, exist_ok=True)
        with open(log_file, "w") as f:
            # Write command to log
            f.write(f"Command: {cmd}\n")
            f.write("=" * 70 + "\n\n")
            f.flush()
            # Run command and capture both stdout and stderr
            result = subprocess.run(
                cmd,
                shell=True,
                stdout=f,
                stderr=subprocess.STDOUT,
                text=True
            )
        return result.returncode == 0
    else:
        result = subprocess.run(cmd, shell=True)
        return result.returncode == 0


def generate_log_filename(m, n, k, buffer_size, channels, direction, loop_count, base_dir="logs"):
    """Generate log filename based on parameters."""
    filename = f"m{m}-n{n}-k{k}-buffer_size{buffer_size}-channels{channels}-{direction}-loop{loop_count}.txt"
    return os.path.join(base_dir, filename)


def main():
    parser = argparse.ArgumentParser(
        description="Master bandwidth test script that iterates through parameter combinations"
    )
    
    # Parameter ranges (can be overridden)
    parser.add_argument("--k-values", type=int, nargs="+", default=[512],
                       help="PE length values to test (default: 512)")
    parser.add_argument("--m-values", type=int, nargs="+", default=[720],
                       help="Height values to test (default: 720)")
    parser.add_argument("--n-values", type=int, nargs="+", default=[720],
                       help="Width values to test (default: 720)")
    parser.add_argument("--channels-values", type=int, nargs="+", default=[16, 4, 1],
                       help="Channel values to test (default: 16 4 1)")
    parser.add_argument("--buffer-sizes", type=int, nargs="+", default=[1, 2, 4, 8],
                       help="Buffer sizes to test (default: 1 2 4 8)")
    parser.add_argument("--directions", type=str, nargs="+", choices=["h2d", "d2h"], 
                       default=["h2d", "d2h"],
                       help="Directions to test (default: h2d d2h)")
    parser.add_argument("--loop-count", type=int, default=5,
                       help="Number of iterations per test (default: 5)")
    
    # Architecture
    parser.add_argument("--arch", type=str, default="wse3", help="Architecture (default: wse3)")
    
    # Fabric dimensions
    parser.add_argument("--fabric-dims", type=str, default="762,1172",
                       help="Fabric dimensions as 'width,height' (default: 762,1172)")
    
    # Log directory
    parser.add_argument("--log-dir", type=str, default="logs",
                       help="Directory for log files (default: logs)")
    
    # Script paths
    parser.add_argument("--compile-script", type=str, default="compile_launcher_param.py",
                       help="Path to compile script (default: compile_launcher_param.py)")
    parser.add_argument("--run-script", type=str, default="run_launcher_param.py",
                       help="Path to run script (default: run_launcher_param.py)")
    
    # Options
    parser.add_argument("--skip-compile", action="store_true",
                       help="Skip compilation (assume already compiled)")
    parser.add_argument("--compile-only", action="store_true",
                       help="Only compile, don't run tests")
    parser.add_argument("--cleanup", action="store_true", default=True,
                       help="Clean up build artifacts before each compile (default: True)")
    
    args = parser.parse_args()
    
    # Create log directory
    os.makedirs(args.log_dir, exist_ok=True)
    
    # Print configuration
    print("=" * 70)
    print("Bandwidth Test Configuration")
    print("=" * 70)
    print(f"k values: {args.k_values}")
    print(f"m values: {args.m_values}")
    print(f"n values: {args.n_values}")
    print(f"channels: {args.channels_values}")
    print(f"buffer sizes: {args.buffer_sizes}")
    print(f"directions: {args.directions}")
    print(f"loop count: {args.loop_count}")
    print(f"arch: {args.arch}")
    print(f"fabric-dims: {args.fabric_dims}")
    print(f"log directory: {args.log_dir}")
    print("=" * 70)
    
    # Calculate total tests
    if args.compile_only:
        total_tests = (
            len(args.k_values) * len(args.m_values) * len(args.n_values) *
            len(args.channels_values) * len(args.buffer_sizes)
        )
    else:
        total_tests = (
            len(args.k_values) * len(args.m_values) * len(args.n_values) *
            len(args.channels_values) * len(args.buffer_sizes) * len(args.directions)
        )
    print(f"\nTotal test combinations: {total_tests}")
    
    test_count = 0
    failed_tests = []
    
    # Iterate through all parameter combinations
    for k in args.k_values:
        for m in args.m_values:
            for n in args.n_values:
                for channels in args.channels_values:
                    for buffer_size in args.buffer_sizes:
                        # Compile once per (k, m, n, channels, buffer_size) combination
                        # (before testing different directions)
                        if not args.skip_compile:
                            if args.cleanup:
                                cleanup_build_artifacts()
                            
                            compile_cmd = (
                                f"python {args.compile_script} "
                                f"--m={m} --n={n} --k={k} "
                                f"--channels={channels} "
                                f"--width-west-buf={buffer_size} "
                                f"--width-east-buf={buffer_size} "
                                f"--arch={args.arch} "
                                f"--fabric-dims={args.fabric_dims}"
                            )
                            
                            compile_log = os.path.join(
                                args.log_dir,
                                f"compile-m{m}-n{n}-k{k}-buffer_size{buffer_size}-channels{channels}.txt"
                            )
                            
                            print(f"\n[{test_count+1}/{total_tests}] Compiling: "
                                  f"m={m}, n={n}, k={k}, channels={channels}, buffer_size={buffer_size}")
                            
                            if not run_command(
                                compile_cmd,
                                log_file=compile_log,
                                description=f"Compiling: m={m}, n={n}, k={k}, channels={channels}, buffer_size={buffer_size}"
                            ):
                                print(f"ERROR: Compilation failed for m={m}, n={n}, k={k}, "
                                      f"channels={channels}, buffer_size={buffer_size}")
                                failed_tests.append(f"COMPILE: m={m}, n={n}, k={k}, "
                                                   f"channels={channels}, buffer_size={buffer_size}")
                                # Skip running tests if compilation failed
                                if not args.compile_only:
                                    test_count += len(args.directions)
                                continue
                        
                        # Run tests for each direction (skip if compile-only)
                        if not args.compile_only:
                            for direction in args.directions:
                                test_count += 1
                                
                                log_file = generate_log_filename(
                                    m, n, k, buffer_size, channels, direction,
                                    args.loop_count, args.log_dir
                                )
                                
                                run_cmd = (
                                    f"python {args.run_script} "
                                    f"--m={m} --n={n} --k={k} "
                                    f"--channels={channels} "
                                    f"--width-west-buf={buffer_size} "
                                    f"--width-east-buf={buffer_size} "
                                    f"--direction={direction} "
                                    f"--loop-count={args.loop_count} "
                                    f"--arch={args.arch}"
                                )
                                
                                print(f"\n[{test_count}/{total_tests}] Running: "
                                      f"m={m}, n={n}, k={k}, channels={channels}, "
                                      f"buffer_size={buffer_size}, direction={direction}")
                                
                                if not run_command(
                                    run_cmd,
                                    log_file=log_file,
                                    description=f"Running: m={m}, n={n}, k={k}, channels={channels}, "
                                              f"buffer_size={buffer_size}, direction={direction}"
                                ):
                                    print(f"ERROR: Test failed for m={m}, n={n}, k={k}, "
                                          f"channels={channels}, buffer_size={buffer_size}, direction={direction}")
                                    failed_tests.append(f"RUN: m={m}, n={n}, k={k}, "
                                                       f"channels={channels}, buffer_size={buffer_size}, "
                                                       f"direction={direction}")
                        else:
                            # If compile-only, still count the tests but skip running
                            test_count += len(args.directions)
    
    # Print summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Total tests: {test_count}")
    print(f"Failed tests: {len(failed_tests)}")
    
    if failed_tests:
        print("\nFailed tests:")
        for test in failed_tests:
            print(f"  - {test}")
    else:
        print("\nAll tests completed successfully!")
    
    print(f"\nLog files saved in: {args.log_dir}")
    print("=" * 70)
    
    return 0 if len(failed_tests) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

