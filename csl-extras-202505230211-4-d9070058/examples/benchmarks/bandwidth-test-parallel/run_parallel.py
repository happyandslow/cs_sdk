#!/usr/bin/env cs_python
"""
Parallel-stream loopback bandwidth test using the SdkLayout direct-link API.

Creates N independent pipelines, each with its own:
  adaptor(1x1) -> demux(1xH) -> core(1xH) -> mux(1xH)
and its own h2d/d2h stream pair.

Fabric layout (N pipelines, each H rows tall, stacked vertically):

  Y=0:     [adaptor_0] [demux_0] [core_0] [mux_0]    <- pipeline 0
  Y=H:     [adaptor_1] [demux_1] [core_1] [mux_1]    <- pipeline 1
  Y=2H:    [adaptor_2] [demux_2] [core_2] [mux_2]    <- pipeline 2
  ...

All streams are sent/received concurrently (nonblock=True) from a single host.
This tests whether the SDK can handle multiple independent FPGA links in parallel.
"""

import argparse
import time

import numpy as np

from cerebras.sdk.runtime.sdkruntimepybind import (
    SdkLayout,
    SdkRuntime,
    SdkTarget,
    SimfabConfig,
    get_platform,
)

from core  import get_loopback_core
from demux import get_demux_adaptor, get_b_demux
from mux   import get_mux


def build_layout(platform, num_pipelines, height, pe_length):
    """
    Construct an SdkLayout with num_pipelines independent loopback pipelines.

    Returns: (layout, [(h2d_stream, d2h_stream), ...])
    """
    layout = SdkLayout(platform)
    streams = []
    width = 1  # each pipeline is a single column

    for i in range(num_pipelines):
        y_offset = i * height
        suffix = f'_{i}'

        # ---- Input adaptor (1x1) ----
        (h2d_port, adaptor_out_port, adaptor) = get_demux_adaptor(
            layout, f'in_adaptor{suffix}', pe_length, width * height
        )
        adaptor.place(1, y_offset)

        # ---- Vertical demux (1 x height) ----
        (demux_in_port, demux_out_port, demux) = get_b_demux(
            layout, f'in_demux{suffix}', pe_length, width, height
        )
        demux.place(2, y_offset)
        layout.connect(adaptor_out_port, demux_in_port)

        # ---- Loopback core (1 x height) ----
        (core_in_port, core_out_port, core) = get_loopback_core(
            layout, f'core{suffix}', pe_length, width, height
        )
        core.place(2 + width, y_offset)
        layout.connect(demux_out_port, core_in_port)

        # ---- Mux (1 x height) ----
        (mux_in_port, d2h_port, mux) = get_mux(
            layout, f'out_mux{suffix}', pe_length, width, height
        )
        mux.place(2 + 2 * width, y_offset)
        layout.connect(core_out_port, mux_in_port)

        # ---- Host I/O streams ----
        h2d_stream = layout.create_input_stream(h2d_port)
        d2h_stream = layout.create_output_stream(d2h_port)
        streams.append((h2d_stream, d2h_stream))

    return layout, streams


def main():
    parser = argparse.ArgumentParser(
        description='Parallel-stream direct-link loopback bandwidth test'
    )
    parser.add_argument(
        '--num-pipelines', '-P', type=int, default=2,
        help='Number of parallel pipelines (default: 2)'
    )
    parser.add_argument(
        '--height', '-H', type=int, default=4,
        help='Number of PE rows per pipeline (default: 4)'
    )
    parser.add_argument(
        '--pe-length', '-N', type=int, default=1024,
        help='Number of f32 elements per PE (default: 1024, max: ~4096)'
    )
    parser.add_argument(
        '--cmaddr',
        help='IP:port for CS system (omit for simulator)'
    )
    parser.add_argument(
        '--arch', choices=['wse2', 'wse3'], default='wse3',
        help='Target WSE architecture (default: wse3)'
    )
    parser.add_argument(
        '--verify', action='store_true',
        help='Verify loopback: check that received data matches sent data'
    )
    args = parser.parse_args()

    P         = args.num_pipelines
    H         = args.height
    pe_length = args.pe_length
    per_pipe  = H * pe_length       # f32 elements per pipeline
    total     = P * per_pipe        # f32 elements across all pipelines

    print(f"=== Parallel Direct-Link Loopback Bandwidth Test ===")
    print(f"Architecture : {args.arch.upper()}")
    print(f"Pipelines    : {P}")
    print(f"Height/pipe  : {H} PEs")
    print(f"PE length    : {pe_length} f32")
    print(f"Per pipeline : {per_pipe} f32  ({per_pipe * 4 / 1024:.1f} KB)")
    print(f"Total data   : {total} f32  ({total * 4 / 1024:.1f} KB per direction)")
    print()

    # ---- Platform ----
    config = SimfabConfig(dump_core=True)
    target = SdkTarget.WSE3 if args.arch == 'wse3' else SdkTarget.WSE2
    platform = get_platform(args.cmaddr, config, target)

    # ---- Build and compile layout ----
    print("Building and compiling layout ...")
    layout, streams = build_layout(platform, P, H, pe_length)
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
    data_d2h = []
    for i in range(P):
        data_h2d.append(np.arange(i * per_pipe, (i + 1) * per_pipe, dtype=np.float32))
        data_d2h.append(np.empty(per_pipe, dtype=np.float32))

    # ---- Timed round-trip (all pipelines concurrent) ----
    print("Running bandwidth measurement ...")
    t0 = time.perf_counter()
    for i in range(P):
        h2d_stream, d2h_stream = streams[i]
        runtime.send(h2d_stream, data_h2d[i], nonblock=True)
        runtime.receive(d2h_stream, data_d2h[i], per_pipe, nonblock=True)
    runtime.stop()
    t1 = time.perf_counter()

    # ---- Report ----
    elapsed_s   = t1 - t0
    elapsed_us  = elapsed_s * 1e6
    bytes_one   = total * 4
    bytes_rt    = bytes_one * 2
    bw_h2d_mbps = bytes_one / elapsed_s / 1e6
    bw_rt_mbps  = bytes_rt  / elapsed_s / 1e6
    bw_rt_gbps  = bytes_rt  / elapsed_s / 1e9

    print()
    print(f"--- Results ({P} pipelines) ---")
    print(f"Elapsed time        : {elapsed_us:.1f} us  ({elapsed_s * 1e3:.3f} ms)")
    print(f"Total data (1-way)  : {bytes_one / 1024:.1f} KB  ({P} x {per_pipe * 4 / 1024:.1f} KB)")
    print(f"Aggregate one-way   : {bw_h2d_mbps:.2f} MB/s")
    print(f"Aggregate round-trip: {bw_rt_mbps:.2f} MB/s  ({bw_rt_gbps:.4f} GB/s)")

    # ---- Optional verification ----
    if args.verify:
        print()
        all_pass = True
        for i in range(P):
            if np.array_equal(data_h2d[i], data_d2h[i]):
                print(f"Pipeline {i}: PASSED")
            else:
                mismatches = np.sum(data_h2d[i] != data_d2h[i])
                print(f"Pipeline {i}: FAILED ({mismatches}/{per_pipe} elements differ)")
                bad = np.where(data_h2d[i] != data_d2h[i])[0][:3]
                for j in bad:
                    print(f"  [idx={j}] sent={data_h2d[i][j]:.4f}  recv={data_d2h[i][j]:.4f}")
                all_pass = False
        if not all_pass:
            raise RuntimeError("Loopback verification failed")
        print("All pipelines: PASSED")


if __name__ == '__main__':
    main()
