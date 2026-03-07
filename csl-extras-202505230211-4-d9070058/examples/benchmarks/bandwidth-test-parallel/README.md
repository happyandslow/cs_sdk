# bandwidth-test-parallel

A host-to-device bandwidth benchmark using the **SdkLayout direct-link** API
with **on-device timing** (TSC timestamps on the PE itself).

## Architecture

Each pipeline is a single PE connected directly to the host via input/output streams
(no demux/mux overhead):

```
host --[h2d_stream]--> core PE (1x1) --[d2h_stream]--> host (4 f32 timing)
```

The PE:
1. Enables TSC at startup
2. DMA-receives `buf_size` f32 wavelets per batch, looping `num_batches` times
   (reusing the same small buffer — data is discarded)
3. Records `time_start` after the first batch completes (excludes host startup latency)
4. Records `time_end` after the last batch
5. Packs `{time_start, time_end}` into 4 f32 (3 data + 1 padding) and sends via d2h stream

Bandwidth is computed from on-device timestamps over `(num_batches - 1)` batches:
```
cycles = time_end - time_start
time_us = cycles / 850e3                              # 850 MHz clock
BW = (num_batches - 1) * buf_size * 4 / time_us      # MB/s
```

For parallel mode, N independent pipelines are stacked vertically, each with
its own stream pair. Aggregate bandwidth uses `min(start)` to `max(end)` across
all PEs.

## Quick Start

### Simulator

```bash
cd examples/benchmarks/bandwidth-test-parallel

# Single PE, 1024 f32 buffer, 1 batch
cs_python run.py --buf-size 1024

# Single PE, large transfer via batching (400 KB)
cs_python run.py --buf-size 1024 --num-batches 100

# 2 parallel pipelines
cs_python run_parallel.py --num-pipelines 2 --buf-size 1024 --num-batches 10

# Run the full test suite
bash bandwidth_test.sh
```

### CS Appliance (single runtime)

```bash
# Single pipeline
python run_appliance.py --buf-size 1024 --num-batches 100 --arch wse3

# 4 parallel pipelines
python run_appliance.py --num-pipelines 4 --buf-size 1024 --num-batches 10 --arch wse3

## max bandwidth
python run_appliance.py -P 16 -B 8192 -K 100000 --arch wse3

# Appliance simulator mode
python run_appliance.py --num-pipelines 2 --buf-size 256 --simulator
```

### CS Appliance (distributed — multiple SdkRuntime processes)

The distributed mode spawns N independent worker subprocesses, each with its own
`SdkRuntime` instance and a filtered port map. A master process handles the
program lifecycle (`load()`/`run()`/`stop()`) while workers handle data transfer.

This is the first step toward multi-host bandwidth testing, where each worker
could run on a different physical host connected to the same WSE device.

```bash
# 2 workers, each sending 1024 x 10 batches (40 KB per worker)
python run_appliance_distributed.py -P 2 -B 1024 -K 10

# 4 workers, larger transfer
python run_appliance_distributed.py -P 4 -B 1024 -K 100 --arch wse3

# Appliance simulator mode
python run_appliance_distributed.py -P 2 -B 256 -K 5 --simulator
```

**How it works:**
1. `run_appliance_distributed.py` stages files and launches `run_distributed.py` on the appliance via `SdkLauncher`
2. `run_distributed.py` compiles the layout, splits the port map into per-worker JSONs, creates a master `SdkRuntime` (lifecycle only), then spawns N worker subprocesses
3. Each worker (`worker.py`) creates its own `SdkRuntime` with `SdkCompileArtifacts.add_port_mapping()` to restrict it to its assigned streams, then calls `run()` + `send()/receive()`
4. Master collects results, stops the runtime, and reports per-pipeline + aggregate bandwidth

## Files

```
bandwidth-test-parallel/
├── README.md                          This file
├── run.py                             Single-pipeline: compile + run + report BW
├── run_parallel.py                    Multi-pipeline: N parallel streams (single runtime)
├── run_distributed.py                 Multi-pipeline: N worker subprocesses (distributed)
├── run_appliance.py                   Appliance launcher (single/parallel)
├── run_appliance_distributed.py       Appliance launcher (distributed)
├── worker.py                          Worker subprocess for distributed mode
├── core.py                            Core helpers (get_direct_core, get_loopback_core)
├── bandwidth_test.sh                  Simulator test suite
└── src/
    └── bw_direct_kernel.csl           Per-PE kernel: recv + timestamp + send timing
```

## Parameters

### `run.py`

| Flag | Default | Description |
|------|---------|-------------|
| `--buf-size` / `-B` | 1024 | Buffer size per batch in f32 elements |
| `--num-batches` / `-K` | 1 | Number of batches (total data = buf_size × num_batches × 4 bytes) |
| `--arch` | `wse3` | Target architecture (`wse2` or `wse3`) |
| `--cmaddr` | *(simulator)* | `IP:port` for CS system |

### `run_parallel.py`

| Flag | Default | Description |
|------|---------|-------------|
| `--num-pipelines` / `-P` | 2 | Number of parallel pipelines |
| `--buf-size` / `-B` | 1024 | Buffer size per batch in f32 elements |
| `--num-batches` / `-K` | 1 | Number of batches per PE |
| `--arch` | `wse3` | Target architecture |
| `--cmaddr` | *(simulator)* | `IP:port` for CS system |

### `run_distributed.py`

| Flag | Default | Description |
|------|---------|-------------|
| `--num-pipelines` / `-P` | 2 | Number of worker subprocesses |
| `--buf-size` / `-B` | 1024 | Buffer size per batch in f32 elements |
| `--num-batches` / `-K` | 1 | Number of batches per PE |
| `--arch` | `wse3` | Target architecture |
| `--cmaddr` | *(simulator)* | `IP:port` for CS system |

### `run_appliance.py`

| Flag | Default | Description |
|------|---------|-------------|
| `--num-pipelines` / `-P` | 1 | 1 = run.py, >1 = run_parallel.py |
| `--buf-size` / `-B` | 1024 | Buffer size per batch in f32 elements |
| `--num-batches` / `-K` | 1 | Number of batches per PE |
| `--arch` | `wse3` | Target architecture |
| `--simulator` | off | Run in appliance simulator mode |

### `run_appliance_distributed.py`

| Flag | Default | Description |
|------|---------|-------------|
| `--num-pipelines` / `-P` | 2 | Number of worker subprocesses |
| `--buf-size` / `-B` | 1024 | Buffer size per batch in f32 elements |
| `--num-batches` / `-K` | 1 | Number of batches per PE |
| `--arch` | `wse3` | Target architecture |
| `--simulator` | off | Run in appliance simulator mode |

## See Also

- `bandwidth-test/` — original memcpy-based benchmark (with sync module)
- `sdklayout-05-gemv/` — tutorial showing the demux/mux pattern
