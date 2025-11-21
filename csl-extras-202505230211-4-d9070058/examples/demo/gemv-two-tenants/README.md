# GEMV Two Tenants Example

This example demonstrates a complete CSL (Cerebras Software Language) program that shows how to run GEMV (General Matrix-Vector multiplication) computations on multiple processing elements (PEs), simulating a multi-tenant scenario.

## Overview

This example implements two independent "tenants" (Tenant A and Tenant B), each executing the same GEMV computation on their respective PEs:
- **Tenant A**: Runs on PE (0, 0) using `pe_program_r1.csl`
- **Tenant B**: Runs on PE (1, 0) using `pe_program_r2.csl`

Both tenants compute `y = Ax + b`, where:
- `A` is a 4×6 matrix (stored in row-major format)
- `x` is a 6×1 vector
- `b` is a 4×1 vector
- `y` is the result vector (4×1)

## File Structure

```
gemv-two-tenants/
├── layout_r.csl          # Layout file defining PE arrangement and code assignment
├── pe_program_r1.csl     # PE program for Tenant A
├── pe_program_r2.csl     # PE program for Tenant B
├── run.py                # Host program handling data transfer and function calls
├── commands_wse2.sh      # WSE-2 compilation and run commands
├── commands_wse3.sh      # WSE-3 compilation and run commands
└── README.md             # This document
```

## Program Structure

### Layout File (`layout_r.csl`)

The layout file defines:
- **PE Grid**: A 2×1 rectangular layout (2 PEs, 1 row)
- **Code Assignment**:
  - PE (0, 0) executes `pe_program_r1.csl`
  - PE (1, 0) executes `pe_program_r2.csl`
- **Exported Symbols**:
  - `y1`: Result vector for Tenant A
  - `y2`: Result vector for Tenant B
  - `init_and_compute`: Host-callable computation function

### PE Programs (`pe_program_r1.csl` and `pe_program_r2.csl`)

Both PE programs have the same structure but export different symbol names:

1. **Initialization** (`initialize` function):
   - Matrix `A`: Filled with `[0, 1, 2, ..., M*N-1]`
   - Vector `x`: All elements set to `1.0`
   - Vector `b`: All elements set to `2.0`
   - Result vector `y`: Initialized to `0.0`

2. **Computation** (`gemv` function):
   - Computes `y = Ax + b`
   - Uses nested loops to implement matrix-vector multiplication

3. **Main Function** (`init_and_compute` function):
   - Calls `initialize()` to initialize data
   - Calls `gemv()` to perform computation
   - Calls `sys_mod.unblock_cmd_stream()` to unblock the command stream

### Host Program (`run.py`)

The host program performs the following steps:

1. **Prepare Data**:
   - Creates matrix `A`, vectors `x` and `b`
   - Computes expected result `y_expected = A@x + b`

2. **Initialize Runtime**:
   - Creates `SdkRuntime` instance
   - Loads and runs the program

3. **Execute Computation**:
   - Launches `init_and_compute` function (executes simultaneously on both PEs)

4. **Retrieve Results**:
   - Copies `y1` result from PE (0, 0)
   - Copies `y2` result from PE (1, 0)

5. **Verify and Output**:
   - Prints results from both tenants
   - Outputs success message

## Building and Running

### WSE-2 System

```bash
# Compile
csbuild layout_r.csl -o out --params width=2

# Run (simulator)
python run.py --name out

# Run (actual hardware)
python run.py --name out --cmaddr <IP:port>
```

### WSE-3 System

```bash
# Compile
csbuild layout_r.csl -o out --params width=2

# Run (simulator)
python run.py --name out

# Run (actual hardware)
python run.py --name out --cmaddr <IP:port>
```

Or use the provided scripts directly:

```bash
# WSE-2
bash commands_wse2.sh

# WSE-3
bash commands_wse3.sh
```

## Expected Output

The program outputs computation results from both tenants:

```
[8. 14. 20. 26.]  # y1 result (Tenant A)
[8. 14. 20. 26.]  # y2 result (Tenant B)
SUCCESS!
```

Both results should be identical since both PEs execute the same computation.

## Key Concepts

### Multi-Tenant Architecture

This example demonstrates how to run multiple independent computation tasks on a single device:
- Each tenant runs on an independent PE
- Tenants are isolated from each other
- Can execute different computations or the same computation simultaneously

### Memory Management

- Uses `memcpy` module for data transfer between host and device
- Each PE has independent global memory space
- Host access to device memory is achieved through symbol export mechanism

### Remote Procedure Call (RPC)

- Host calls device functions through `launch()` function
- Device functions call `unblock_cmd_stream()` after completion to allow subsequent memcpy operations

## Matrix Dimensions

- `M = 4`: Number of matrix rows, also the length of the result vector
- `N = 6`: Number of matrix columns, also the length of input vector `x`

## Notes

- Both PE programs are essentially the same, differing only in exported symbol names (`y1` vs `y2`)
- In real applications, different tenants may execute different computations
- This example is primarily for demonstrating basic concepts of multi-PE and multi-tenant architectures

