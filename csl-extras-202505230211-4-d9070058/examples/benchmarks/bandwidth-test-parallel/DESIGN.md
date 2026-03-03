# Parallel Bandwidth Test — Design Document

**Goal:** Re-implement the host↔device bandwidth benchmark using the direct link
(SdkLayout point-to-point) API instead of the memcpy framework, then demonstrate
how multiple I/O streams can be partitioned across independent host processes.

---

## Background

### Two communication paradigms in the Cerebras SDK

The SDK offers two distinct host↔device data transfer mechanisms:

| | **Memcpy framework** | **Direct link (SdkLayout)** |
|---|---|---|
| **Compilation** | `cslc --memcpy --channels=N` | `SdkLayout.create_input/output_stream()` |
| **Routing** | Auto-inserted by compiler; 3 west cols + 2 east cols reserved | Explicit PE-to-PE wavelet streams |
| **Host API** | `runtime.memcpy_h2d()` / `memcpy_d2h()` | `runtime.send()` / `runtime.receive()` |
| **Data path** | Host → FPGA → PE memory (scatter/gather built-in) | Host → FPGA port PE → demux fabric → PE array |
| **Multi-host** | Single host (one CM connection) | Each host can own a separate FPGA link |
| **Channels** | 1–16 parallel I/O channels | One per `create_input/output_stream()` call |
| **Fabric overhead** | Fixed columns for memcpy infrastructure | No fixed overhead; ports placed explicitly |

**Critical constraint:** `create_input_stream()` / `create_output_stream()` each connect
to a **single PE on a physical FPGA port** on the wafer edge. Data fan-out to/from
multi-PE regions is the user's responsibility (demux/mux pattern).

---

## Key Findings from Reference Implementations

### From `sdklayout-05-gemv`

1. **Demux adaptor pattern**: A `1×1` region injects control wavelets every `batch_size`
   wavelets to trigger routing-switch advances in the downstream demux region
   (`SWITCH_ADV` opcode, `ctrl.encode_single_payload()`).

2. **Two-position routing switch**: Each PE's router holds a list of `RoutingPosition`s.
   The hardware advances from pos[0] → pos[1] upon receipt of a control wavelet.
   This enables one serial FPGA link to fan out to N PEs without any software loop.

3. **Edge routing override**: `get_edge_routing(Edge.RIGHT, [pos1])` pins the last PE
   in a chain to always stay at pos1 (RAMP only), preventing spurious eastward forwarding.

4. **Deadlock avoidance**: When two input streams have a dependency in the kernel
   (GEMV: x must be fully received before b can be added), both sends must be
   `nonblock=True` so the host does not block on x while the device is waiting for b.

5. **Port ↔ stream distinction**:
   - `create_input_port()` — region-level logical boundary; can be multi-PE;
     used with `layout.connect()` for PE-to-PE wiring.
   - `create_input_stream()` — wraps a port with a host I/O bridge; always 1-PE wide;
     returns a stream name for `runtime.send()`.

6. **`SdkLayout.compile()`** is the real compilation entry point. All `place()`,
   `paint_all()`, `connect()` calls are pre-compilation layout metadata.

### From `bandwidth-test`

1. **On-device timing**: TSC (48-bit timestamp counter) is read via
   `timestamp.get_timestamp()` exported from the sync module. Values are packed into
   f32 arrays for D2H retrieval. Reference clock (`f_sync`) removes per-PE clock skew.

2. **Propagation delay correction**: `time_ref[py, px] -= (px + py)` accounts for
   the mesh distance the sync signal travels before reaching each PE.

3. **Bandwidth formula**:
   ```
   cycles = max(time_end) - min(time_start)  # across all PEs
   time_us = cycles / 0.85e3                  # 850 MHz clock
   BW_MBps = (wavelets * 4 bytes) / time_us * loop_count
   ```

4. **Compile/run split**: `--compile-only` writes a `hash.json`; `--run-only` loads it.
   This is required for appliance mode where `SdkCompiler` and `SdkRuntime` run as
   separate jobs. `run_launcher.py` uses `SdkLauncher` to submit to the appliance.

5. **Buffer columns** (`--width-west-buf`, `--width-east-buf`): Each PE holds a 46 KB
   FIFO. Required buffer width = `ceil((pe_length * core_width * 4) / 46KB)`. These
   overlap compute and I/O but are not available in the direct link model.

6. **Channels** (`--channels=N`, max 16): Each channel is an independent FPGA link.
   Multiple channels are auto-managed by the memcpy framework; with direct link,
   multiple streams serve the same role but each must be explicitly wired.

### From Cerebras engineer (Slack conversation)

- `SdkRuntime` creates host↔FPGA links when initialized. Each `runtime.run()` call
  establishes connections for the streams the runtime "sees" in its compiled artifact.
- **Multi-host model**: One host calls `load()` to program the wafer; each host then
  calls `run()` independently and only accesses its own stream(s).
- **FPGA link conflict**: If two `SdkRuntime` instances try to access the same stream
  (same FPGA link), the FPGA will fail. The "config file" is the compiled artifact
  directory — each host needs an artifact that only declares its own stream(s).
- **MPI** can be used on top for host-side synchronization across processes.
- **Cycle-count variability** (~466K–536K): Caused by I/O path timing variation (host
  TCP aggregation, FPGA latency), not by the compute kernel itself. Pure compute with
  no I/O is very stable.

---

## Design Proposal

### Objectives

1. **Replace memcpy** with SdkLayout direct link streams for data transfer.
2. **On-device timing** retained (f_tic, f_toc, f_sync) but timing readback happens
   via a dedicated output stream rather than memcpy.
3. **Multiple independent streams** that can be assigned to separate host processes.
4. **Appliance-compatible**: compile/run split, `SdkLauncher` workflow preserved.

---

### Architecture Overview

```
                    H2D direction
  ┌──────────┐     ┌──────────────┐     ┌─────────────────────────────┐
  │  Host A  │────▶│ in_adaptor   │────▶│                             │
  │ send(s0) │     │ (1×1) + demux│     │   core region  (W × H)      │
  └──────────┘     └──────────────┘     │                             │
                                        │  - receive data via fabin   │
  ┌──────────┐     ┌──────────────┐     │  - f_tic / f_toc / f_sync   │
  │  Host B  │────▶│ in_adaptor   │────▶│  - loopback or discard      │
  │ send(s1) │     │ (1×1) + demux│     │                             │
  └──────────┘     └──────────────┘     └──────────┬──────────────────┘
                                                   │
                    D2H direction                   │
  ┌──────────┐     ┌──────────────┐                │
  │  Host C  │◀────│  mux + out_  │◀───────────────┘
  │ recv(s2) │     │  adaptor(1×1)│   data loopback
  └──────────┘     └──────────────┘
                    ┌──────────────┐
  ┌──────────┐     │  timing_mux  │◀── timing data (TSC values)
  │  Host D  │◀────│  + adaptor   │
  │ recv(t)  │     └──────────────┘
  └──────────┘
```

**Note on timing stream**: The memcpy approach reads timing via `memcpy_d2h()` after
the fact. With direct link we have two options:
- **Option A (Recommended)**: Add a dedicated `timing_out` stream: after `f_toc()` the
  kernel sends packed TSC values out through a separate output color. The host reads
  this stream like any other.
- **Option B**: Keep a small separate memcpy artifact just for timing readback (hybrid).
  Simpler to implement but requires memcpy infrastructure alongside.

---

### CSL Kernel Design (`bw_dl_kernel.csl`)

Replace `@import_module("<memcpy/memcpy>")` with direct fabric DSDs:

```
// Inputs
param in_color: color;      // H2D data stream
param out_color: color;     // D2H data stream
param timing_color: color;  // timing output stream

const in_dsd  = @get_dsd(fabin_dsd,  .{.extent = pe_length, .fabric_color = in_color,  .input_queue  = @get_input_queue(0)});
const out_dsd = @get_dsd(fabout_dsd, .{.extent = pe_length, .fabric_color = out_color, .output_queue = @get_output_queue(0)});
```

Key difference from memcpy kernel:
- No `memcpy.csl` import; no queue 0 reservation for memcpy.
- Data arrives via wavelet-triggered task (WTT) or synchronous `@mov32`.
- Timing still uses `timestamp.get_timestamp()` from the sync module.
- **Timing export**: Kernel sends packed TSC values via `timing_color` fabout_dsd
  after `f_toc()` completes.

---

### Python Layout Design (`run.py`)

```python
layout = SdkLayout(platform)

# --- Core compute region ---
core = layout.create_code_region('./src/bw_dl_kernel.csl', 'core', W, H)
core.set_param_all('pe_length', pe_length)
in_color   = core.color('in_color')
out_color  = core.color('out_color')
timing_color = core.color('timing_color')
# ... paint routing for in_color, out_color, timing_color ...
core.place(CORE_X, CORE_Y)

# --- Input demux chain (reuse from sdklayout-05-gemv pattern) ---
(h2d_port, adaptor_out_port, adaptor) = get_demux_adaptor(layout, ...)
adaptor.place(ADAPTOR_X, CORE_Y)
(demux_in_port, demux_out_port, demux) = get_demux(layout, ..., W, H)
demux.place(DEMUX_X, CORE_Y)
layout.connect(adaptor_out_port, demux_in_port)
layout.connect(demux_out_port, core_in_port)

# --- Output mux chain ---
(mux_in_port, mux_out_port, mux) = get_mux(layout, ..., W, H)
mux.place(MUX_X, CORE_Y)
layout.connect(core_out_port, mux_in_port)
(d2h_port, _, d2h_adaptor) = get_mux_adaptor(layout, ...)
layout.connect(mux_out_port, d2h_adaptor_in_port)

# --- Timing output stream (single PE, top-left of core or dedicated region) ---
timing_region = layout.create_code_region('./src/bw_timing_out.csl', 'timing_out', 1, 1)
timing_region.place(TIMING_X, TIMING_Y)
timing_out_port = timing_region.create_output_port(...)

# --- Host I/O streams ---
h2d_stream  = layout.create_input_stream(h2d_port)
d2h_stream  = layout.create_output_stream(d2h_port)
timing_stream = layout.create_output_stream(timing_out_port)

# --- Compile ---
artifacts = layout.compile(out_prefix='out')
```

---

### Multi-Host Partitioning

Each host needs its own compiled artifact containing only its stream(s). This is
achieved by compiling separate layouts per host role, each containing a subset of
the `create_input/output_stream()` calls.

**Proposed host roles:**

| Host | Streams owned | Artifact |
|------|--------------|---------|
| Loader | (none; calls load() only) | full artifact |
| H2D sender | `h2d_stream` | artifact with h2d stream only |
| D2H receiver | `d2h_stream` | artifact with d2h stream only |
| Timing receiver | `timing_stream` | artifact with timing stream only |

**Compile strategy:**

```
Compile variant A (h2d_only):  layout includes only h2d stream
Compile variant B (d2h_only):  layout includes only d2h stream
Compile variant C (timing):    layout includes only timing stream
Compile variant FULL:          all streams (for single-host testing)
```

The CSL kernel is the same for all variants; only the host-side layout differs.

**Host synchronization** (MPI or barrier):
```
Host (Loader): load() → signal others
Host (Sender):               wait → run() → send(h2d_stream) → done
Host (Receiver):             wait → run() → receive(d2h_stream) → compute BW
Host (Timing):               wait → run() → receive(timing_stream) → decode TSC
```

---

### Timing Without Memcpy

The original benchmark reads timing via `memcpy_d2h()` after `f_toc()`. With direct
link, we need an alternative. Proposed approach:

1. **Root PE** (e.g., PE at (0,0)) collects aggregated timing: after f_toc, it runs
   a reduction across all PEs to find `max(time_end)` and `min(time_start)`.
   (This requires a separate on-chip reduction, similar to `comm_lib` in WaferLLM.)
2. Root PE packs these two 48-bit values and sends via `timing_color` output stream.
3. Host receives 2 × 3 × 4 bytes = 24 bytes, decodes as before.

**Simpler alternative (single PE timing)**: If W=H=1, no reduction needed. Single
PE sends its own `(time_start, time_end)` directly. Useful for latency measurement
but not bandwidth (need large transfers across many PEs for accurate BW).

---

### Fabric Layout

With direct link, no reserved memcpy columns. Layout is more compact:

```
Fabric X:  [ adaptor | demux (W cols) | core (W cols) | mux (W cols) | d2h_adaptor ]
Fabric offset: (4, 1) same as WSE-3 convention
Core offset X: 4 + 1 (adaptor) + W (demux) = 5 + W
Minimum fabric width: 4 + 1 + W + W + W + 1 = 4 + 3W + 2
```

Compare to memcpy: `4 + 3 (west) + W + 2 (east) = 9 + W`

For W=448 (full width test): direct link needs ~1350 cols vs memcpy 460 cols.
→ For large W, the demux/mux columns dominate. This is a key trade-off.

**Mitigation**: For pure bandwidth measurement, W=1 (single column of H PEs) suffices.
The demux distributes vertically. This keeps fabric width small.

---

### Files to Implement

```
bandwidth-test-parallel/
├── DESIGN.md                  ← this file
├── src/
│   ├── bw_dl_layout.csl       ← CSL layout (no memcpy import)
│   ├── bw_dl_kernel.csl       ← per-PE kernel (fabin/fabout instead of memcpy)
│   ├── bw_timing_out.csl      ← timing aggregation and output PE
│   └── sync/                  ← copy from bandwidth-test (unchanged)
│       ├── layout.csl
│       └── pe.csl
├── demux.py                   ← reuse/adapt from sdklayout-05-gemv
├── mux.py                     ← reuse/adapt from sdklayout-05-gemv
├── layout.py                  ← SdkLayout construction (new)
├── run_single.py              ← single-host run (all streams on one runtime)
├── run_multihost.py           ← multi-host run (each process owns subset of streams)
├── bw_cmd_parser.py           ← adapted from bandwidth-test
├── compile.py                 ← compile-only step (for appliance)
├── run_launcher.py            ← SdkLauncher wrapper (adapted from bandwidth-test)
└── commands_wse3.sh           ← example invocations
```

---

## Open Questions

1. **Timing reduction**: Is there an existing on-chip reduction primitive usable here
   (like WaferLLM's `comm_lib`), or must we implement our own?

2. **Per-host artifact compilation**: Does `SdkLayout` support "partial compilation"
   where only a subset of streams is included? Or must we compile N separate full
   layouts, each with only one stream declared?

3. **`runtime.run()` semantics**: Can a runtime call `run()` on an already-loaded
   device without conflicting with another runtime's `run()`? The engineer implied yes
   but this is not documented.

4. **Demux/mux overhead**: The demux pattern introduces PE columns that consume
   routing resources. For pure bandwidth measurement (no compute), we may want a
   simpler single-column design with no fan-out.

5. **Loopback vs absorb**: Should the kernel loopback data (H2D → D2H) for round-trip
   measurement, or just absorb H2D? Loopback is simpler for single-stream BW but
   requires the output stream to be initialized even during H2D-only test.
