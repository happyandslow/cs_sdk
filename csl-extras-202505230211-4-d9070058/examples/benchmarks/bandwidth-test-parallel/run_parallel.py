#!/usr/bin/env cs_python
"""
Parallel-stream H2D bandwidth test with on-device timing.

Creates N independent pipelines, each a single PE connected directly to
its own h2d/d2h stream pair (no demux/mux).

Fabric layout (N pipelines stacked vertically):

  Y=0:   [core_0]    <- pipeline 0
  Y=1:   [core_1]    <- pipeline 1
  Y=2:   [core_2]    <- pipeline 2
  ...

Each PE:
  1. Enables TSC at startup
  2. Records time_start, DMA-receives pe_length f32 from host
  3. Records time_end, sends 3 f32 packed timestamps via d2h stream

Bandwidth is computed per-pipeline from on-device timestamps, then aggregated.
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
    """Decode 3 f32 words into (time_start, time_end) as 48-bit integers."""
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

def build_layout(platform, num_pipelines, buf_size, num_batches):
    """
    Construct an SdkLayout with num_pipelines independent direct-core PEs.

    Returns: (layout, [(h2d_stream, d2h_stream), ...])
    """
    layout = SdkLayout(platform)
    streams = []

    for i in range(num_pipelines):
        (core_in_port, core_out_port, core) = get_direct_core(
            layout, f'core_{i}', buf_size, num_batches
        )
        core.place(1, i)

        h2d_stream = layout.create_input_stream(core_in_port)
        d2h_stream = layout.create_output_stream(core_out_port)
        streams.append((h2d_stream, d2h_stream))

    return layout, streams


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Parallel-stream H2D bandwidth test with on-device timing'
    )
    parser.add_argument(
        '--num-pipelines', '-P', type=int, default=2,
        help='Number of parallel pipelines (default: 2)'
    )
    parser.add_argument(
        '--buf-size', '-B', type=int, default=1024,
        help='Buffer size per batch in f32 elements (default: 1024)'
    )
    parser.add_argument(
        '--num-batches', '-K', type=int, default=1,
        help='Number of batches per PE (default: 1)'
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

    P           = args.num_pipelines
    buf_size    = args.buf_size
    num_batches = args.num_batches
    pe_elems    = buf_size * num_batches   # total f32 per PE
    total       = P * pe_elems

    print(f"=== Parallel H2D Bandwidth Test (on-device timing) ===")
    print(f"Architecture : {args.arch.upper()}")
    print(f"Pipelines    : {P}")
    print(f"Buffer size  : {buf_size} f32  ({buf_size * 4 / 1024:.1f} KB)")
    print(f"Num batches  : {num_batches}")
    print(f"Per-PE data  : {pe_elems} f32  ({pe_elems * 4 / 1024:.1f} KB)")
    print(f"Total data   : {total} f32  ({total * 4 / 1024:.1f} KB)")
    print()

    # ---- Platform ----
    config = SimfabConfig(dump_core=True)
    target = SdkTarget.WSE3 if args.arch == 'wse3' else SdkTarget.WSE2
    platform = get_platform(args.cmaddr, config, target)

    # ---- Build and compile layout ----
    print("Building and compiling layout ...")
    layout, streams = build_layout(platform, P, buf_size, num_batches)
    t_compile_start = time.perf_counter()
    compile_artifacts = layout.compile(out_prefix='out')
    t_compile_end = time.perf_counter()
    print(f"Compilation done in {(t_compile_end - t_compile_start):.1f} s")
    print()

    # ---- Runtime ----
    runtime = SdkRuntime(compile_artifacts, platform, memcpy_required=False)
    runtime.load()
    runtime.run()

    # ---- Data (per pipeline) ----
    data_h2d = []
    time_bufs = []
    for i in range(P):
        data_h2d.append(np.arange(i * pe_elems, (i + 1) * pe_elems, dtype=np.float32))
        time_bufs.append(np.zeros(4, dtype=np.float32))

    # ---- Transfer (all pipelines concurrent) ----
    print("Sending data and receiving timestamps ...")
    for i in range(P):
        h2d_stream, d2h_stream = streams[i]
        runtime.send(h2d_stream, data_h2d[i], nonblock=True)
        runtime.receive(d2h_stream, time_bufs[i], 4, nonblock=True)
    runtime.stop()

    # ---- Decode on-device timestamps per pipeline ----
    print()
    print(f"--- Results ({P} pipelines, on-device timing) ---")

    # time_start is recorded after the first batch completes, so we measure
    # (num_batches - 1) batches of steady-state transfer.
    measured_batches = max(num_batches - 1, 1)
    data_bytes_per = measured_batches * buf_size * 4
    all_starts = []
    all_ends = []

    for i in range(P):
        ts, te = decode_timestamps(time_bufs[i])
        all_starts.append(ts)
        all_ends.append(te)
        cycles = te - ts
        time_us = (cycles / 0.85) * 1.0e-3
        bw_mbps = data_bytes_per / time_us if time_us > 0 else 0.0
        print(f"  Pipeline {i}: {cycles} cycles, {time_us:.1f} us, {bw_mbps:.2f} MB/s")

    # Aggregate: use earliest start, latest end across all pipelines
    global_start = min(all_starts)
    global_end   = max(all_ends)
    global_cycles = global_end - global_start
    global_time_us = (global_cycles / 0.85) * 1.0e-3
    total_measured_bytes = P * data_bytes_per
    agg_bw_mbps = total_measured_bytes / global_time_us if global_time_us > 0 else 0.0
    agg_bw_gbps = agg_bw_mbps / 1000.0

    print()
    print(f"  Aggregate ({measured_batches} of {num_batches} batches measured):")
    print(f"    Elapsed cycles      : {global_cycles}")
    print(f"    Elapsed time        : {global_time_us:.1f} us")
    print(f"    Total data          : {total_measured_bytes} bytes  ({total_measured_bytes / 1024:.1f} KB)")
    print(f"    Aggregate H2D BW    : {agg_bw_mbps:.2f} MB/s  ({agg_bw_gbps:.4f} GB/s)")


if __name__ == '__main__':
    main()
