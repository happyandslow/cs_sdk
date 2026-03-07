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

from cerebras.geometry.geometry import IntVector
from cerebras.sdk.runtime.sdkruntimepybind import (
    Route,
    RoutingPosition,
    SdkCompileArtifacts,
    SdkLayout,
    SdkRuntime,
    SdkTarget,
    SimfabConfig,
    get_platform,
)

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

    Uses create_input_stream_from_loc / create_output_stream_from_loc to
    bypass the SDK's adaptor/mux merging. Each pipeline's PE is placed at
    a valid LVDS position so it gets its own direct LVDS port pair.

    Returns: (layout, [(h2d_stream, d2h_stream), ...])
    """
    # Valid I/O port Y positions on WSE-3 WEST edge (discovered empirically):
    # [0, 144, 288, 432, 576, 720, 864, 1008] — spaced 144 rows apart.
    VALID_IO_Y = [i * 144 for i in range(8)]
    MAX_PIPELINES = len(VALID_IO_Y)

    if num_pipelines > MAX_PIPELINES:
        raise ValueError(
            f"num_pipelines={num_pipelines} exceeds max {MAX_PIPELINES} "
            f"(limited by valid I/O port locations on WSE-3)"
        )

    layout = SdkLayout(platform)
    streams = []

    for i in range(num_pipelines):
        io_y = VALID_IO_Y[i]

        # Create 1x1 core region with in/out colors
        core = layout.create_code_region(
            './src/bw_direct_kernel.csl', f'core_{i}', 1, 1)
        core.set_param_all('buf_size', buf_size)
        core.set_param_all('num_batches', num_batches)

        in_color = core.color('in_color')
        out_color = core.color('out_color')
        core.set_param_all(in_color)
        core.set_param_all(out_color)

        # Route in_color: WEST -> RAMP (receive from host)
        core.paint_all(in_color,
            [RoutingPosition().set_input([Route.WEST]).set_output([Route.RAMP])])
        # Route out_color: RAMP -> EAST (send to host)
        core.paint_all(out_color,
            [RoutingPosition().set_input([Route.RAMP]).set_output([Route.EAST])])

        # Place core at valid LVDS position (column 0 = WEST edge)
        core.place(0, io_y)

        # Direct LVDS connection — bypasses adaptor/mux merging.
        # Each call creates its own LVDS port entry in the port map.
        h2d_name = layout.create_input_stream_from_loc(
            IntVector(0, io_y), in_color, prefix=f'h2d_{i}')
        d2h_name = layout.create_output_stream_from_loc(
            IntVector(0, io_y), out_color, prefix=f'd2h_{i}')
        streams.append((h2d_name, d2h_name))

    return layout, streams


# ---------------------------------------------------------------------------
# Port map splitting
# ---------------------------------------------------------------------------

def split_port_map(full_port_map, stream_names, out_dir):
    """Split a full port map into master (empty) and per-worker port maps.

    With explicit io_loc, each pipeline should have its own LVDS port pair
    in the port map. Each worker gets a port map with only its buses.
    The master gets all buses for lifecycle (load/run/stop).
    """
    os.makedirs(out_dir, exist_ok=True)
    all_buses = full_port_map['buses']

    # Master: needs all buses for load/stop but won't send/receive
    master_path = os.path.join(out_dir, 'port_map_master.json')
    with open(master_path, 'w') as f:
        json.dump(full_port_map, f, indent=2)

    # Per-worker: filter buses by port_name matching the stream names
    worker_paths = []
    for i, (h2d_name, d2h_name) in enumerate(stream_names):
        worker_buses = [
            bus for bus in all_buses
            if bus['port_name'] in (h2d_name, d2h_name)
        ]
        if not worker_buses:
            print(f"  WARNING: No buses matched for worker {i} "
                  f"(h2d={h2d_name}, d2h={d2h_name})")
            print(f"  Available port_names: "
                  f"{[b['port_name'] for b in all_buses]}")
        worker_map = {**full_port_map, 'buses': worker_buses}
        path = os.path.join(out_dir, f'port_map_worker_{i}.json')
        with open(path, 'w') as f:
            json.dump(worker_map, f, indent=2)
        worker_paths.append(path)

    return master_path, worker_paths


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
        port_map_content = f.read()
        print(f"Port map ({f.name}):")
        print(port_map_content)

    full_port_map = json.loads(port_map_content)

    stream_names = streams  # already (h2d_name, d2h_name) string tuples
    print(f"Logical stream names: {stream_names}")
    print()

    # Split port map: master gets all buses, each worker gets its own
    master_map_path, worker_map_paths = split_port_map(
        full_port_map, stream_names, 'out'
    )

    # ---- Master runtime (lifecycle, full port map) ----
    artifacts = SdkCompileArtifacts('out')
    artifacts.add_port_mapping(master_map_path)
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
                worker_map_paths[i],
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
