#!/usr/bin/env cs_python
"""
Single-host loopback bandwidth test using the SdkLayout direct-link API.

Architecture (single column of H PEs):

  host ──[h2d_stream]──> in_adaptor(1×1) ──> in_demux(1×H) ──> core(1×H) ──> out_mux(1×H) ──[d2h_stream]──> host

  * in_adaptor  : injects SWITCH_ADV after every pe_length wavelets
  * in_demux    : vertical demux; PE[i] receives pe_length wavelets each
  * core        : each PE buffers pe_length wavelets, then echoes them back
  * out_mux     : serialises results; PE[0] sends first, PE[1] next, etc.

Host-side wall-clock timing measures round-trip (H2D + D2H) bandwidth.
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


# ---------------------------------------------------------------------------
# Layout construction
# ---------------------------------------------------------------------------

def build_layout(platform, height, pe_length):
    """Construct the SdkLayout and return (layout, h2d_stream, d2h_stream)."""
    layout = SdkLayout(platform)

    # ---- Input adaptor (1×1) ----
    # Receives the full H*pe_length wavelet stream from the host and injects
    # SWITCH_ADV control wavelets between each pe_length-sized batch.
    (h2d_port, adaptor_out_port, adaptor) = get_demux_adaptor(
        layout, 'in_adaptor', pe_length, height
    )
    adaptor.place(1, 0)

    # ---- Vertical demux (1×height) ----
    # Distributes batches: PE[0] gets first pe_length, PE[1] next, etc.
    (demux_in_port, demux_out_port, demux) = get_b_demux(
        layout, 'in_demux', pe_length, 1, height
    )
    demux.place(2, 0)
    layout.connect(adaptor_out_port, demux_in_port)

    # ---- Loopback core (1×height) ----
    # Each PE receives pe_length wavelets, stores them, sends them back.
    (core_in_port, core_out_port, core) = get_loopback_core(
        layout, 'core', pe_length, height
    )
    core.place(3, 0)
    layout.connect(demux_out_port, core_in_port)

    # ---- Mux (1×height) ----
    # Serialises results from all PEs into a single output stream.
    (mux_in_port, d2h_port, mux) = get_mux(
        layout, 'out_mux', pe_length, 1, height
    )
    mux.place(4, 0)
    layout.connect(core_out_port, mux_in_port)

    # ---- Host I/O streams ----
    h2d_stream = layout.create_input_stream(h2d_port)
    d2h_stream = layout.create_output_stream(d2h_port)

    return layout, h2d_stream, d2h_stream


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Direct-link loopback bandwidth test (single-host)'
    )
    parser.add_argument(
        '--height', '-H', type=int, default=4,
        help='Number of PEs in the column (default: 4)'
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
    parser.add_argument(
        '--name', default='out',
        help='Output artifact prefix (default: out)'
    )
    args = parser.parse_args()

    H         = args.height
    pe_length = args.pe_length
    total     = H * pe_length

    print(f"=== Direct-Link Loopback Bandwidth Test ===")
    print(f"Architecture : {args.arch.upper()}")
    print(f"Height (PEs) : {H}")
    print(f"PE length    : {pe_length} f32")
    print(f"Total data   : {total} f32  ({total * 4 / 1024:.1f} KB per direction)")
    print()

    # ---- Platform ----
    config   = SimfabConfig(dump_core=True)
    target   = SdkTarget.WSE3 if args.arch == 'wse3' else SdkTarget.WSE2
    platform = get_platform(args.cmaddr, config, target)

    # ---- Compile ----
    print("Building and compiling layout ...")
    layout, h2d_stream, d2h_stream = build_layout(platform, H, pe_length)
    t_compile_start = time.perf_counter()
    artifacts = layout.compile(out_prefix=args.name)
    t_compile_end = time.perf_counter()
    print(f"Compilation done in {(t_compile_end - t_compile_start):.1f} s  ->  {artifacts}")
    print()

    # ---- Runtime ----
    runtime = SdkRuntime(artifacts, platform, memcpy_required=False)
    runtime.load()
    runtime.run()

    # ---- Data ----
    data_h2d = np.arange(total, dtype=np.float32)
    data_d2h = np.empty(total, dtype=np.float32)

    # ---- Timed round-trip ----
    print("Running bandwidth measurement ...")
    t0 = time.perf_counter()
    runtime.send(h2d_stream,  data_h2d, nonblock=True)
    runtime.receive(d2h_stream, data_d2h, total, nonblock=True)
    runtime.stop()           # blocks until all async ops complete
    t1 = time.perf_counter()

    # ---- Report ----
    elapsed_s   = t1 - t0
    elapsed_us  = elapsed_s * 1e6
    bytes_one   = total * 4                  # one-way: H2D or D2H
    bytes_rt    = bytes_one * 2              # round-trip total
    bw_h2d_mbps = bytes_one / elapsed_s / 1e6
    bw_rt_mbps  = bytes_rt  / elapsed_s / 1e6
    bw_rt_gbps  = bytes_rt  / elapsed_s / 1e9

    print()
    print(f"--- Results ---")
    print(f"Elapsed time        : {elapsed_us:.1f} us  ({elapsed_s * 1e3:.3f} ms)")
    print(f"One-way bandwidth   : {bw_h2d_mbps:.2f} MB/s  (H2D or D2H, half of round-trip)")
    print(f"Round-trip BW       : {bw_rt_mbps:.2f} MB/s  ({bw_rt_gbps:.4f} GB/s)")

    # ---- Optional verification ----
    if args.verify:
        print()
        if np.array_equal(data_h2d, data_d2h):
            print("Verification: PASSED (loopback data matches exactly)")
        else:
            mismatches = np.sum(data_h2d != data_d2h)
            print(f"Verification: FAILED ({mismatches}/{total} elements differ)")
            # Show first few mismatches
            bad = np.where(data_h2d != data_d2h)[0][:5]
            for i in bad:
                print(f"  [idx={i}] sent={data_h2d[i]:.4f}  recv={data_d2h[i]:.4f}")
            raise RuntimeError("Loopback verification failed")


if __name__ == '__main__':
    main()
