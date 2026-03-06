# bandwidth-test-parallel

A host-to-device bandwidth benchmark using the **SdkLayout direct-link** API
with **on-device timing** (TSC timestamps on the PE itself).

## Architecture

Each pipeline is a single PE connected directly to the host via input/output streams
(no demux/mux overhead):

```
host --[h2d_stream]--> core PE (1x1) --[d2h_stream]--> host (3 f32 timing)
```

The PE:
1. Enables TSC at startup
2. Records `time_start` (48-bit timestamp)
3. DMA-receives `pe_length` f32 wavelets from the host
4. Records `time_end`
5. Packs `{time_start, time_end}` into 3 f32 and sends via d2h stream

Bandwidth is computed from on-device timestamps:
```
cycles = time_end - time_start
time_us = cycles / 850e3          # 850 MHz clock
BW = (pe_length * 4) / time_us   # MB/s
```

For parallel mode, N independent pipelines are stacked vertically, each with
its own stream pair. Aggregate bandwidth uses `min(start)` to `max(end)` across
all PEs.

## Quick Start

### Simulator

```bash
cd examples/benchmarks/bandwidth-test-parallel

# Single PE, 1024 elements
cs_python run.py --pe-length 1024

# Single PE, larger transfer
cs_python run.py --pe-length 4096

# 2 parallel pipelines
cs_python run_parallel.py --num-pipelines 2 --pe-length 1024

# 4 parallel pipelines
cs_python run_parallel.py --num-pipelines 4 --pe-length 1024

# Run the full test suite
bash bandwidth_test.sh
```

### CS Appliance

```bash
# Single pipeline
python run_appliance.py --pe-length 1024 --arch wse3

# 4 parallel pipelines
python run_appliance.py --num-pipelines 4 --pe-length 1024 --arch wse3

# Appliance simulator mode
python run_appliance.py --num-pipelines 2 --pe-length 256 --simulator
```

## Files

```
bandwidth-test-parallel/
├── DESIGN.md                   Design document and architecture notes
├── README.md                   This file
├── run.py                      Single-pipeline: compile + run + report BW
├── run_parallel.py             Multi-pipeline: N parallel streams
├── run_appliance.py            Appliance launcher (SdkLauncher)
├── core.py                     Core helpers (get_direct_core, get_loopback_core)
├── bandwidth_test.sh           Simulator test suite
└── src/
    └── bw_direct_kernel.csl    Per-PE kernel: recv + timestamp + send timing
```

## Parameters

### `run.py`

| Flag | Default | Description |
|------|---------|-------------|
| `--pe-length` / `-N` | 1024 | Number of f32 elements to send to the PE |
| `--arch` | `wse3` | Target architecture (`wse2` or `wse3`) |
| `--cmaddr` | *(simulator)* | `IP:port` for CS system |

### `run_parallel.py`

| Flag | Default | Description |
|------|---------|-------------|
| `--num-pipelines` / `-P` | 2 | Number of parallel pipelines |
| `--pe-length` / `-N` | 1024 | f32 elements per PE |
| `--arch` | `wse3` | Target architecture |
| `--cmaddr` | *(simulator)* | `IP:port` for CS system |

### `run_appliance.py`

| Flag | Default | Description |
|------|---------|-------------|
| `--num-pipelines` / `-P` | 1 | 1 = run.py, >1 = run_parallel.py |
| `--pe-length` / `-N` | 1024 | f32 elements per PE |
| `--arch` | `wse3` | Target architecture |
| `--simulator` | off | Run in appliance simulator mode |

## Output Example

```
=== Direct-Link H2D Bandwidth Test (on-device timing) ===
Architecture : WSE3
PE length    : 1024 f32  (4.0 KB)

Building and compiling layout ...
Compilation done in 8.2 s

Sending data and receiving timestamps ...

--- Results (on-device timing) ---
time_start          : 123456
time_end            : 234567
Elapsed cycles      : 111111
Elapsed time        : 130.7 us
Data transferred    : 4096 bytes  (4.0 KB)
H2D Bandwidth       : 31.33 MB/s  (0.0313 GB/s)
```

## See Also

- `bandwidth-test/` — original memcpy-based benchmark (with sync module)
- `sdklayout-05-gemv/` — tutorial showing the demux/mux pattern
- `DESIGN.md` — detailed design notes
