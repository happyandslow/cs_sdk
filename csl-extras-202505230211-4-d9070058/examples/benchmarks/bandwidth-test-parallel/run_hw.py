#!/usr/bin/env cs_python
"""
Appliance-side runtime for the memcpy-based loopback benchmark.

This script is staged and executed by run_launcher.py when the artifact was
compiled with compile_single.py (SdkCompiler / memcpy path).

It uses the sdkruntimepybind memcpy API (available in cs_python on the
appliance) to perform H2D → loopback → D2H and report bandwidth.

Usage (called automatically by run_launcher.py, not directly by the user):
  cs_python run_hw.py --height H --pe-length N --latestlink latest --cmaddr IP:PORT [--verify]
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
        "--width", "-W", type=int, default=1,
        help="Number of PE columns (default: 1)"
    )
    parser.add_argument(
        "--height", "-H", type=int, required=True,
        help="Number of PE rows"
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
        "--latestlink", default="latest",
        help="Directory (or symlink) containing the compiled ELF files. "
             "SdkLauncher creates a 'latest' symlink on the appliance pointing "
             "to the extracted artifact directory. (default: latest)"
    )
    parser.add_argument(
        "--loop-count", "-L", type=int, default=1,
        help="Number of back-to-back transfers to amortize overhead (default: 1)"
    )
    parser.add_argument(
        "--d2h", action="store_true",
        help="Measure D2H bandwidth (default: H2D)"
    )
    parser.add_argument(
        "--sync", action="store_true",
        help="Use blocking (sync) memcpy transfers instead of nonblocking (async). "
             "Async allows the runtime to aggregate multiple requests into fewer TCP "
             "transactions, amortizing the ~200us TCP overhead."
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="Verify loopback: check received data matches sent data"
    )
    args = parser.parse_args()

    W         = args.width
    H         = args.height
    pe_length = args.pe_length
    total     = W * H * pe_length
    artifact_dir = args.latestlink

    loop_count = args.loop_count
    direction  = "D2H" if args.d2h else "H2D"

    print(f"=== Memcpy Bandwidth Test ===")
    print(f"Width  (PEs) : {W}")
    print(f"Height (PEs) : {H}")
    print(f"PE length    : {pe_length} f32")
    print(f"Total data   : {total} f32  ({total * 4 / 1024:.1f} KB per transfer)")
    print(f"Direction    : {direction}")
    print(f"Loop count   : {loop_count}")
    print(f"Transfer     : {'sync (blocking)' if args.sync else 'async (nonblocking)'}")
    print()

    # SdkLauncher extracts the compiled artifact and creates a symlink named
    # `latest` (or whatever --latestlink specifies) pointing to the ELF directory.
    runner = SdkRuntime(artifact_dir, cmaddr=args.cmaddr)
    symbol_buf = runner.get_id("buf")

    runner.load()
    runner.run()

    data_h2d = np.arange(total, dtype=np.float32)
    data_d2h = np.zeros(total, dtype=np.float32)

    nonblock = not args.sync

    print("Running bandwidth measurement ...")
    t0 = time.perf_counter()

    for j in range(loop_count):
        if args.d2h:
            runner.memcpy_d2h(
                data_d2h, symbol_buf,
                0, 0, W, H, pe_length,
                streaming=False,
                data_type=MemcpyDataType.MEMCPY_32BIT,
                order=MemcpyOrder.ROW_MAJOR,
                nonblock=nonblock,
            )
        else:
            runner.memcpy_h2d(
                symbol_buf, data_h2d,
                0, 0, W, H, pe_length,
                streaming=False,
                data_type=MemcpyDataType.MEMCPY_32BIT,
                order=MemcpyOrder.ROW_MAJOR,
                nonblock=nonblock,
            )

    runner.stop()
    t1 = time.perf_counter()

    elapsed_s    = t1 - t0
    elapsed_us   = elapsed_s * 1e6
    bytes_total  = total * 4 * loop_count
    bw_mbps      = bytes_total / elapsed_s / 1e6
    bw_gbps      = bytes_total / elapsed_s / 1e9

    print()
    print("--- Results ---")
    print(f"Elapsed time        : {elapsed_us:.1f} us  ({elapsed_s * 1e3:.3f} ms)")
    print(f"Total transferred   : {bytes_total / 1024:.1f} KB  ({loop_count} × {total * 4 / 1024:.1f} KB)")
    print(f"Bandwidth ({direction:3s})    : {bw_mbps:.2f} MB/s  ({bw_gbps:.4f} GB/s)")

    if args.verify:
        print()
        print("Note: --verify requires a separate round-trip run (H2D+D2H).")
        print("      Re-launching runtime for verification ...")
        runner_v = SdkRuntime(artifact_dir, cmaddr=args.cmaddr)
        sym_v = runner_v.get_id("buf")
        runner_v.load()
        runner_v.run()
        runner_v.memcpy_h2d(
            sym_v, data_h2d, 0, 0, W, H, pe_length,
            streaming=False, data_type=MemcpyDataType.MEMCPY_32BIT,
            order=MemcpyOrder.ROW_MAJOR, nonblock=True,
        )
        runner_v.memcpy_d2h(
            data_d2h, sym_v, 0, 0, W, H, pe_length,
            streaming=False, data_type=MemcpyDataType.MEMCPY_32BIT,
            order=MemcpyOrder.ROW_MAJOR, nonblock=True,
        )
        runner_v.stop()
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
