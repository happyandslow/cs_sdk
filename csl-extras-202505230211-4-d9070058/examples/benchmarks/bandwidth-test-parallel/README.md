# bandwidth-test-parallel

A host↔device bandwidth benchmark using the **SdkLayout direct-link** API
(point-to-point wavelet streams) instead of the memcpy framework.

Demonstrates:
- Direct-link H2D + D2H loopback measurement on a single host
- Demux/mux fan-out/fan-in pattern from `sdklayout-05-gemv`
- Foundation for multi-host partitioned I/O streams (see `DESIGN.md`)

---

## Architecture

```
host ──[h2d_stream]──► in_adaptor(1×1)
                              │ SWITCH_ADV every pe_length wavelets
                              ▼
                       in_demux(1×H)      ← distributes data vertically
                              │ pe_length wavelets per PE
                              ▼
                       core(1×H)          ← loopback kernel: recv → buf → send
                              │
                              ▼
                       out_mux(1×H)       ← serialises results northward
                              │
                       ◄──[d2h_stream]──── host
```

Each column has **H** PEs. PE `i` receives exactly `pe_length` f32 wavelets,
stores them in a local buffer, and echoes them back.  The timing measures the
full round-trip (H2D + D2H) wall-clock time.

---

## Requirements

- Cerebras SDK v1.4.0+  (`SdkLayout`, `SdkRuntime`)
- `cs_python` on PATH

---

## Quick Start

```bash
cd examples/benchmarks/bandwidth-test-parallel

# Smoke test (H=2, 4 elements/PE, with loopback verification)
cs_python run_single.py --height 2 --pe-length 4 --verify

# Larger test
cs_python run_single.py --height 8 --pe-length 1024

# Run the full test suite
bash bandwidth_test.sh
```

For hardware (CS system):
```bash
cs_python run_single.py --height 8 --pe-length 2048 --cmaddr <IP:PORT>
bash bandwidth_test.sh --cmaddr <IP:PORT>
```

---

## Files

```
bandwidth-test-parallel/
├── DESIGN.md                  Design document and architecture notes
├── README.md                  This file
├── run_single.py              Single-host run script
├── demux.py                   Demux helper (get_demux_adaptor, get_b_demux)
├── mux.py                     Mux helper (get_mux)
├── core.py                    Loopback core helper (get_loopback_core)
├── bandwidth_test.sh          Test suite script
└── src/
    ├── bw_loopback_kernel.csl Per-PE loopback: recv pe_length wavelets → send
    ├── demux_adaptor.csl      1×1 adaptor: forward + inject SWITCH_ADV
    ├── demux.csl              Demux PE: receive batch and optionally forward
    └── mux.csl                Mux PE: forward batch northward, then switch
```

---

## Parameters

| Flag | Default | Description |
|------|---------|-------------|
| `--height` / `-H` | 4 | Number of PEs in the column |
| `--pe-length` / `-N` | 1024 | f32 elements per PE (max ~4096) |
| `--arch` | `wse3` | Target architecture (`wse2` or `wse3`) |
| `--cmaddr` | *(simulator)* | `IP:port` for CS system |
| `--verify` | off | Check loopback correctness after run |
| `--name` | `out` | Compiled artifact directory prefix |

---

## Output Example

```
=== Direct-Link Loopback Bandwidth Test ===
Architecture : WSE3
Height (PEs) : 8
PE length    : 1024 f32
Total data   : 8192 f32  (32.0 KB per direction)

Building and compiling layout ...
Compilation done in 12.3 s  ->  out/

Running bandwidth measurement ...

--- Results ---
Elapsed time        : 850.2 us  (0.850 ms)
One-way bandwidth   : 37.64 MB/s  (H2D or D2H, half of round-trip)
Round-trip BW       : 75.28 MB/s  (0.0000 GB/s)
```

---

## Key Differences vs `bandwidth-test` (memcpy)

| | `bandwidth-test` (memcpy) | `bandwidth-test-parallel` (direct link) |
|---|---|---|
| Compilation | `cslc --memcpy --channels=N` | `SdkLayout.compile()` |
| Host API | `runtime.memcpy_h2d()` / `memcpy_d2h()` | `runtime.send()` / `runtime.receive()` |
| Multi-host | Single host only | Each host can own a separate stream |
| Timing | On-device TSC via memcpy_d2h | Host-side wall clock |
| Loop count | Built-in CSL loop | One pass per `runtime.run()` |
| Reserved cols | 3 west + 2 east for memcpy | None |

---

## Design Notes

- **Router state**: The demux/mux routing switches are consumed after one pass.
  Multiple iterations require multiple `runtime.run()` calls (each restarts the
  device program from initial state).
- **Deadlock prevention**: Both `runtime.send()` and `runtime.receive()` use
  `nonblock=True`.  If `send()` were blocking, the host would stall waiting for
  H2D completion while the device waits for the host to register `receive()`.
- **Multi-host extension**: See `DESIGN.md` for the proposed architecture where
  separate host processes each own one stream (H2D sender, D2H receiver, timing
  receiver).

---

## See Also

- `sdklayout-05-gemv/` — tutorial showing the demux/mux pattern
- `bandwidth-test/` — original memcpy-based benchmark
- `DESIGN.md` — detailed design notes and open questions
