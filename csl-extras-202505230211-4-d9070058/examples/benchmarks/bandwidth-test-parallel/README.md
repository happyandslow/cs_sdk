# bandwidth-test-parallel

A host-device bandwidth benchmark using the **SdkLayout direct-link** API
(point-to-point wavelet streams) instead of the memcpy framework.

## Architecture

```
host --[h2d_stream]--> in_adaptor(1x1)
                              | SWITCH_ADV every pe_length wavelets
                              v
                       in_demux(1xH)      <- distributes data vertically
                              | pe_length wavelets per PE
                              v
                       core(1xH)          <- loopback kernel: recv -> buf -> send
                              |
                              v
                       out_mux(1xH)       <- serialises results northward
                              |
                       <--[d2h_stream]---- host
```

Each column has **H** PEs. PE `i` receives exactly `pe_length` f32 wavelets,
stores them in a local buffer, and echoes them back. The timing measures the
full round-trip (H2D + D2H) wall-clock time.

## Quick Start

### Simulator

```bash
cd examples/benchmarks/bandwidth-test-parallel

# Smoke test (H=2, 4 elements/PE, with loopback verification)
cs_python run.py --height 2 --pe-length 4 --verify

# Larger test
cs_python run.py --height 8 --pe-length 1024

# Run the full test suite
bash bandwidth_test.sh
```

### CS Appliance

```bash
# Launch on appliance via SdkLauncher (compiles + runs on the worker)
python run_appliance.py --height 8 --pe-length 1024 --arch wse3

# With verification
python run_appliance.py --height 8 --pe-length 1024 --verify
```

## Files

```
bandwidth-test-parallel/
├── DESIGN.md                  Design document and architecture notes
├── README.md                  This file
├── run.py                     Compile + run (simulator or appliance via --cmaddr)
├── run_appliance.py           Appliance launcher (SdkLauncher)
├── core.py                    Loopback core helper (get_loopback_core)
├── demux.py                   Demux helper (get_demux_adaptor, get_b_demux)
├── mux.py                     Mux helper (get_mux)
├── bandwidth_test.sh          Simulator test suite
└── src/
    ├── bw_loopback_kernel.csl Per-PE loopback: recv pe_length wavelets -> send
    ├── demux_adaptor.csl      1x1 adaptor: forward + inject SWITCH_ADV
    ├── demux.csl              Demux PE: receive batch and optionally forward
    └── mux.csl                Mux PE: forward batch northward, then switch
```

## Parameters

### `run.py`

| Flag | Default | Description |
|------|---------|-------------|
| `--height` / `-H` | 4 | Number of PEs in the column |
| `--pe-length` / `-N` | 1024 | f32 elements per PE (max ~4096) |
| `--arch` | `wse3` | Target architecture (`wse2` or `wse3`) |
| `--cmaddr` | *(simulator)* | `IP:port` for CS system |
| `--verify` | off | Check loopback correctness after run |

### `run_appliance.py`

| Flag | Default | Description |
|------|---------|-------------|
| `--height` / `-H` | 4 | Number of PEs |
| `--pe-length` / `-N` | 1024 | f32 elements per PE |
| `--arch` | `wse3` | Target architecture |
| `--verify` | off | Pass --verify to run.py on the worker |
| `--simulator` | off | Run in appliance simulator mode |

## See Also

- `sdklayout-05-gemv/` — tutorial showing the demux/mux pattern
- `bandwidth-test/` — original memcpy-based benchmark
- `DESIGN.md` — detailed design notes
