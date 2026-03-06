#!/usr/bin/env cs_python
"""
Direct-link H2D bandwidth test with on-device timing.

Architecture (single PE, no demux/mux):

  host --[h2d_stream]--> core PE (1x1) --[d2h_stream]--> host (3 f32 timing)

The PE:
  1. Enables TSC at startup
  2. Records time_start (48-bit TSC)
  3. DMA-receives pe_length f32 wavelets from host
  4. Records time_end
  5. Packs {time_start, time_end} into 3 f32 and sends via d2h stream

Bandwidth is computed from on-device timestamps:
  cycles = time_end - time_start
  time_us = cycles / 0.85e3   (850 MHz clock)
  BW = (pe_length * 4 bytes) / time_us
"""

import argparse
import struct
import time

import numpy as np

from cerebras.sdk.runtime.sdkruntimepybind import (
    SdkLayout,
    SdkRuntime,
    SdkTarget,
    SimfabConfig,
    get_platform,
)

from core import get_direct_core


# ---------------------------------------------------------------------------
# Timestamp decoding (same as bandwidth-test/run.py)
# ---------------------------------------------------------------------------

def float_to_hex(f):
    return hex(struct.unpack("<I", struct.pack("<f", f))[0])


def make_u48(words):
    return words[0] + (words[1] << 16) + (words[2] << 32)


def decode_timestamps(time_buf_f32):
    """
    Decode 3 f32 words into (time_start, time_end) as 48-bit integers.

    Packing layout (from bw_direct_kernel.csl / bw_sync_kernel.csl):
      f32[0] = {tscStart[1], tscStart[0]}
      f32[1] = {tscEnd[0],   tscStart[2]}
      f32[2] = {tscEnd[2],   tscEnd[1]}
    """
    word = np.zeros(3, dtype=np.uint16)

    hex_t0 = int(float_to_hex(time_buf_f32[0]), base=16)
    hex_t1 = int(float_to_hex(time_buf_f32[1]), base=16)
    hex_t2 = int(float_to_hex(time_buf_f32[2]), base=16)

    word[0] = hex_t0 & 0x0000FFFF
    word[1] = (hex_t0 >> 16) & 0x0000FFFF
    word[2] = hex_t1 & 0x0000FFFF
    time_start = make_u48(word)

    word[0] = (hex_t1 >> 16) & 0x0000FFFF
    word[1] = hex_t2 & 0x0000FFFF
    word[2] = (hex_t2 >> 16) & 0x0000FFFF
    time_end = make_u48(word)

    return time_start, time_end


# ---------------------------------------------------------------------------
# Layout construction
# ---------------------------------------------------------------------------

def build_layout(platform, buf_size, num_batches):
    """Construct the SdkLayout with a single 1x1 direct core."""
    layout = SdkLayout(platform)

    (core_in_port, core_out_port, core) = get_direct_core(
        layout, 'core', buf_size, num_batches
    )
    core.place(1, 0)

    h2d_stream = layout.create_input_stream(core_in_port)
    d2h_stream = layout.create_output_stream(core_out_port)

    return layout, h2d_stream, d2h_stream


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Direct-link H2D bandwidth test with on-device timing'
    )
    parser.add_argument(
        '--buf-size', '-B', type=int, default=1024,
        help='Buffer size per batch in f32 elements (default: 1024)'
    )
    parser.add_argument(
        '--num-batches', '-K', type=int, default=1,
        help='Number of batches to receive (default: 1)'
    )
    parser.add_argument(
        '--cmaddr',
        help='IP:port for CS system (omit for simulator)'
    )
    parser.add_argument(
        '--arch', choices=['wse2', 'wse3'], default='wse3',
        help='Target WSE architecture (default: wse3)'
    )
    args = parser.parse_args()

    buf_size    = args.buf_size
    num_batches = args.num_batches
    total_elems = buf_size * num_batches

    print(f"=== Direct-Link H2D Bandwidth Test (on-device timing) ===")
    print(f"Architecture : {args.arch.upper()}")
    print(f"Buffer size  : {buf_size} f32  ({buf_size * 4 / 1024:.1f} KB)")
    print(f"Num batches  : {num_batches}")
    print(f"Total data   : {total_elems} f32  ({total_elems * 4 / 1024:.1f} KB)")
    print()

    # ---- Platform ----
    config = SimfabConfig(dump_core=True)
    target = SdkTarget.WSE3 if args.arch == 'wse3' else SdkTarget.WSE2
    platform = get_platform(args.cmaddr, config, target)

    # ---- Build and compile layout ----
    print("Building and compiling layout ...")
    layout, h2d_stream, d2h_stream = build_layout(platform, buf_size, num_batches)
    t_compile_start = time.perf_counter()
    compile_artifacts = layout.compile(out_prefix='out')
    t_compile_end = time.perf_counter()
    print(f"Compilation done in {(t_compile_end - t_compile_start):.1f} s")
    print()

    # ---- Runtime ----
    runtime = SdkRuntime(compile_artifacts, platform, memcpy_required=False)
    runtime.load()
    runtime.run()

    # ---- Data ----
    data_h2d = np.arange(total_elems, dtype=np.float32)
    # PE sends back 4 f32 of packed timestamps (3 data + 1 padding)
    time_buf = np.zeros(4, dtype=np.float32)

    # ---- Transfer ----
    print("Sending data and receiving timestamps ...")
    runtime.send(h2d_stream, data_h2d, nonblock=True)
    runtime.receive(d2h_stream, time_buf, 4, nonblock=True)
    runtime.stop()

    # ---- Decode on-device timestamps ----
    time_start, time_end = decode_timestamps(time_buf)
    cycles = time_end - time_start
    # 850 MHz clock: 1 cycle = (1/0.85) ns = (1/0.85)*1e-3 us
    time_us = (cycles / 0.85) * 1.0e-3
    # time_start is recorded after the first batch completes, so we measure
    # (num_batches - 1) batches of steady-state transfer.
    measured_batches = max(num_batches - 1, 1)
    data_bytes = measured_batches * buf_size * 4
    bw_mbps = data_bytes / time_us if time_us > 0 else 0.0
    bw_gbps = bw_mbps / 1000.0

    print()
    print(f"--- Results (on-device timing) ---")
    print(f"time_start          : {time_start}")
    print(f"time_end            : {time_end}")
    print(f"Elapsed cycles      : {cycles}")
    print(f"Elapsed time        : {time_us:.1f} us")
    print(f"Measured batches    : {measured_batches} of {num_batches}")
    print(f"Data transferred    : {data_bytes} bytes  ({data_bytes / 1024:.1f} KB)")
    print(f"H2D Bandwidth       : {bw_mbps:.2f} MB/s  ({bw_gbps:.4f} GB/s)")


if __name__ == '__main__':
    main()
