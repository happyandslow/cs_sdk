#!/usr/bin/env cs_python
"""
Distributed H2D bandwidth test with on-device timing.

Spawns N independent worker subprocesses, each with its own SdkRuntime
instance and filtered port map. A master process handles lifecycle
(load/run/stop) with no data streams.
"""

import argparse
import json
import multiprocessing
import os
import struct
import time

import numpy as np

from cerebras.sdk.runtime.sdkruntimepybind import (
    SdkCompileArtifacts,
    SdkLayout,
    SdkRuntime,
    SdkTarget,
    SimfabConfig,
    get_platform,
)

from core import get_direct_core
from worker import worker_main


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
        core.place(1, i * 16)

        h2d_stream = layout.create_input_stream(core_in_port, io_buffer_size=8192)
        d2h_stream = layout.create_output_stream(core_out_port, io_buffer_size=8192)
        streams.append((h2d_stream, d2h_stream))

    return layout, streams


# ---------------------------------------------------------------------------
# Port map handling
# ---------------------------------------------------------------------------
# NOTE: The SdkLayout creates a single mux/adaptor for all streams, so the
# port map only has 1 IN + 1 OUT physical bus regardless of pipeline count.
# We cannot split by logical stream name. Instead, all runtimes (master +
# workers) share the full port map. The SDK routes send()/receive() to the
# correct pipeline internally via the logical stream name.


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Distributed H2D bandwidth test with on-device timing'
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

    print(f"=== Distributed H2D Bandwidth Test (on-device timing) ===")
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

    # ---- Port map and stream names ----
    port_map_path = os.path.join('out', 'out_port_map.json')
    with open(port_map_path) as f:
        print(f"Port map ({f.name}):")
        print(f.read())

    stream_names = []
    for h2d_stream, d2h_stream in streams:
        stream_names.append((h2d_stream, d2h_stream))
    print(f"Logical stream names: {stream_names}")
    print()

    # ---- Master runtime (lifecycle only, full port map) ----
    artifacts = SdkCompileArtifacts('out')
    artifacts.add_port_mapping(port_map_path)
    runtime = SdkRuntime(artifacts, platform, memcpy_required=False)
    runtime.load()
    runtime.run()

    # ---- Spawn worker subprocesses ----
    load_done_event = multiprocessing.Event()
    result_queue = multiprocessing.Queue()

    # Signal that master is ready
    load_done_event.set()

    workers = []
    for i in range(P):
        h2d_name, d2h_name = stream_names[i]
        p = multiprocessing.Process(
            target=worker_main,
            args=(
                i,
                'out',
                port_map_path,
                h2d_name,
                d2h_name,
                buf_size,
                num_batches,
                args.cmaddr,
                args.arch,
                load_done_event,
                result_queue,
            ),
        )
        p.start()
        workers.append(p)

    # ---- Collect results ----
    results = []
    for _ in range(P):
        results.append(result_queue.get())

    for w in workers:
        w.join()

    # ---- Stop master runtime ----
    runtime.stop()

    # ---- Check for errors ----
    for r in results:
        if r['error'] is not None:
            print(f"ERROR in worker {r['rank']}: {r['error']}")
            raise RuntimeError(f"Worker {r['rank']} failed: {r['error']}")

    # ---- Decode on-device timestamps per pipeline ----
    # Sort results by rank for consistent output
    results.sort(key=lambda r: r['rank'])

    print()
    print(f"--- Results ({P} pipelines, on-device timing) ---")

    measured_batches = max(num_batches - 1, 1)
    data_bytes_per = measured_batches * buf_size * 4
    all_starts = []
    all_ends = []

    for r in results:
        i = r['rank']
        time_buf = np.array(r['time_buf'], dtype=np.float32)
        ts, te = decode_timestamps(time_buf)
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
