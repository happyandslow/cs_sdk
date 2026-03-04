#!/usr/bin/env cs_python
"""
Appliance-side runtime for the memcpy-based loopback benchmark.

This script is staged and executed by run_launcher.py when the artifact was
compiled with compile_single.py (SdkCompiler / memcpy path).

It uses the sdkruntimepybind memcpy API (available in cs_python on the
appliance) to perform H2D → loopback → D2H and report bandwidth.

Usage (called automatically by run_launcher.py, not directly by the user):
  cs_python run_hw.py --height H --pe-length N --cmaddr IP:PORT [--verify]
"""

import argparse
import time

import numpy as np
from cerebras.sdk.runtime.sdkruntimepybind import (  # pylint: disable=no-name-in-module
    MemcpyDataType,
    MemcpyOrder,
    SdkRuntime,
)


def main():
    parser = argparse.ArgumentParser(
        description="Appliance-side memcpy loopback runtime (compile_single.py path)"
    )
    parser.add_argument(
        "--height", "-H", type=int, required=True,
        help="Number of PEs in the column"
    )
    parser.add_argument(
        "--pe-length", "-N", type=int, required=True,
        help="Number of f32 elements per PE"
    )
    parser.add_argument(
        "--cmaddr", required=True,
        help="IP:port of the CS appliance"
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="Verify loopback: check received data matches sent data"
    )
    args = parser.parse_args()

    H         = args.height
    pe_length = args.pe_length
    total     = H * pe_length

    print(f"=== Direct-Link Loopback Bandwidth Test (memcpy path) ===")
    print(f"Height (PEs) : {H}")
    print(f"PE length    : {pe_length} f32")
    print(f"Total data   : {total} f32  ({total * 4 / 1024:.1f} KB per direction)")
    print()

    # Working directory ('.') is the extracted artifact directory on the appliance.
    runner = SdkRuntime(".", cmaddr=args.cmaddr)
    symbol_buf = runner.get_id("buf")

    runner.load()
    runner.run()

    data_h2d = np.arange(total, dtype=np.float32)
    data_d2h = np.zeros(total, dtype=np.float32)

    print("Running bandwidth measurement ...")
    t0 = time.perf_counter()
    runner.memcpy_h2d(
        symbol_buf, data_h2d,
        0, 0, 1, H, pe_length,
        streaming=False,
        data_type=MemcpyDataType.MEMCPY_32BIT,
        order=MemcpyOrder.ROW_MAJOR,
        nonblock=True,
    )
    runner.memcpy_d2h(
        data_d2h, symbol_buf,
        0, 0, 1, H, pe_length,
        streaming=False,
        data_type=MemcpyDataType.MEMCPY_32BIT,
        order=MemcpyOrder.ROW_MAJOR,
        nonblock=True,
    )
    runner.stop()
    t1 = time.perf_counter()

    elapsed_s   = t1 - t0
    elapsed_us  = elapsed_s * 1e6
    bytes_one   = total * 4
    bytes_rt    = bytes_one * 2
    bw_h2d_mbps = bytes_one / elapsed_s / 1e6
    bw_rt_mbps  = bytes_rt  / elapsed_s / 1e6
    bw_rt_gbps  = bytes_rt  / elapsed_s / 1e9

    print()
    print("--- Results ---")
    print(f"Elapsed time        : {elapsed_us:.1f} us  ({elapsed_s * 1e3:.3f} ms)")
    print(f"One-way bandwidth   : {bw_h2d_mbps:.2f} MB/s  (H2D or D2H)")
    print(f"Round-trip BW       : {bw_rt_mbps:.2f} MB/s  ({bw_rt_gbps:.4f} GB/s)")

    if args.verify:
        print()
        if np.array_equal(data_h2d, data_d2h):
            print("Verification: PASSED (loopback data matches exactly)")
        else:
            mismatches = np.sum(data_h2d != data_d2h)
            print(f"Verification: FAILED ({mismatches}/{total} elements differ)")
            bad = np.where(data_h2d != data_d2h)[0][:5]
            for i in bad:
                print(f"  [idx={i}] sent={data_h2d[i]:.4f}  recv={data_d2h[i]:.4f}")
            raise RuntimeError("Loopback verification failed")


if __name__ == "__main__":
    main()
