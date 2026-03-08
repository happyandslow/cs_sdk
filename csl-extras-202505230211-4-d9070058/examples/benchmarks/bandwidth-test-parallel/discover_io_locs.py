#!/usr/bin/env cs_python
"""
Discover valid I/O port locations on the connected WSE hardware.

Tries compiling a minimal SdkLayout program with
create_input_stream_from_loc and create_output_stream_from_loc
at various (x, y) positions to find which ones are accepted.

Usage (on appliance worker):
    cs_python discover_io_locs.py --cmaddr <IP:PORT>

Usage (via SdkLauncher):
    python run_appliance_discover.py
"""

import argparse
import json
import os
import tempfile
import shutil

from cerebras.sdk.runtime.sdkruntimepybind import (
    SdkLayout,
    SdkTarget,
    SimfabConfig,
    Color,
    Route,
    RoutingPosition,
    get_platform,
)
from cerebras.geometry.geometry import IntVector


def test_input_loc(platform, csl_path, x, y, out_dir):
    """Try create_input_stream_from_loc at (x, y). Returns True if valid."""
    try:
        layout = SdkLayout(platform)
        region = layout.create_code_region(csl_path, f'r_in_{x}_{y}', 1, 1)
        region.place(x, y)

        c = Color('c', 0)
        region.set_param_all(c)
        region.paint_all(c,
            [RoutingPosition().set_input([Route.WEST]).set_output([Route.RAMP])])

        layout.create_input_stream_from_loc(IntVector(x, y), c)
        layout.compile(out_prefix=os.path.join(out_dir, f'test_in_{x}_{y}'))
        return True
    except RuntimeError as e:
        if 'is not valid' in str(e):
            return False
        print(f"  input ({x},{y}): other error: {e}")
        return None
    except Exception as e:
        print(f"  input ({x},{y}): unexpected: {type(e).__name__}: {e}")
        return None


def test_output_loc(platform, csl_path, x, y, out_dir):
    """Try create_output_stream_from_loc at (x, y). Returns True if valid."""
    try:
        layout = SdkLayout(platform)
        region = layout.create_code_region(csl_path, f'r_out_{x}_{y}', 1, 1)
        region.place(x, y)

        c = Color('c', 1)
        region.set_param_all(c)
        region.paint_all(c,
            [RoutingPosition().set_input([Route.RAMP]).set_output([Route.EAST])])

        layout.create_output_stream_from_loc(IntVector(x, y), c)
        layout.compile(out_prefix=os.path.join(out_dir, f'test_out_{x}_{y}'))
        return True
    except RuntimeError as e:
        if 'is not valid' in str(e):
            return False
        print(f"  output ({x},{y}): other error: {e}")
        return None
    except Exception as e:
        print(f"  output ({x},{y}): unexpected: {type(e).__name__}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='Discover valid I/O port locations')
    parser.add_argument('--cmaddr', help='IP:port for CS system')
    parser.add_argument('--arch', choices=['wse2', 'wse3'], default='wse3')
    parser.add_argument('--max-y', type=int, default=1200,
                        help='Max Y to scan (default: 1200)')
    parser.add_argument('--step', type=int, default=1,
                        help='Y step size for scanning (default: 1)')
    parser.add_argument('--max-x', type=int, default=5,
                        help='Max X to scan (default: 5)')
    args = parser.parse_args()

    config = SimfabConfig()
    target = SdkTarget.WSE3 if args.arch == 'wse3' else SdkTarget.WSE2
    platform = get_platform(args.cmaddr, config, target)

    # Create minimal CSL source
    csl_dir = tempfile.mkdtemp()
    csl_path = os.path.join(csl_dir, 'minimal.csl')
    with open(csl_path, 'w') as f:
        f.write('comptime {}')

    out_dir = tempfile.mkdtemp()

    # ---- Phase 1: Scan INPUT locations at x=0 ----
    print(f"=== Scanning INPUT stream locations (x=0) ===")
    print(f"Architecture: {args.arch.upper()}")
    print(f"Y range: 0 to {args.max_y}, step={args.step}")
    print()

    valid_input_y = []
    for y in range(0, args.max_y, args.step):
        result = test_input_loc(platform, csl_path, 0, y, out_dir)
        if result is True:
            valid_input_y.append(y)
            print(f"  input (0,{y}): VALID")

    print(f"\nValid INPUT Y at x=0: {valid_input_y}")
    print(f"Count: {len(valid_input_y)}")
    if len(valid_input_y) > 1:
        diffs = [valid_input_y[i+1] - valid_input_y[i] for i in range(len(valid_input_y)-1)]
        print(f"Spacings: {diffs}")

    # ---- Phase 2: Scan OUTPUT locations at x=0 ----
    print(f"\n=== Scanning OUTPUT stream locations (x=0) ===")

    valid_output_x0 = []
    for y in range(0, args.max_y, args.step):
        result = test_output_loc(platform, csl_path, 0, y, out_dir)
        if result is True:
            valid_output_x0.append(y)
            print(f"  output (0,{y}): VALID")

    print(f"\nValid OUTPUT Y at x=0: {valid_output_x0}")
    print(f"Count: {len(valid_output_x0)}")
    if len(valid_output_x0) > 1:
        diffs = [valid_output_x0[i+1] - valid_output_x0[i] for i in range(len(valid_output_x0)-1)]
        print(f"Spacings: {diffs}")

    # ---- Phase 3: Try OUTPUT at other x values using known valid Y ----
    # Use input valid Y positions as candidates
    test_ys = valid_input_y if valid_input_y else [0, 144, 288, 432, 576, 720, 864, 1008]

    print(f"\n=== Scanning OUTPUT at x=1..{args.max_x} for known valid Y ===")
    valid_output_other = {}
    for x in range(1, args.max_x + 1):
        valid_for_x = []
        for y in test_ys:
            result = test_output_loc(platform, csl_path, x, y, out_dir)
            if result is True:
                valid_for_x.append(y)
                print(f"  output ({x},{y}): VALID")
            elif result is False:
                print(f"  output ({x},{y}): invalid")
        if valid_for_x:
            valid_output_other[x] = valid_for_x

    # ---- Phase 4: Try OUTPUT at y offsets from valid input Y ----
    print(f"\n=== Scanning OUTPUT at y offsets from valid input positions ===")
    if valid_input_y:
        base_y = valid_input_y[0]  # use first valid position
        for x in range(0, args.max_x + 1):
            for dy in range(-5, 6):
                y = base_y + dy
                if y < 0:
                    continue
                result = test_output_loc(platform, csl_path, x, y, out_dir)
                if result is True:
                    print(f"  output ({x},{y}): VALID  (base={base_y}, dy={dy})")

    # ---- Summary ----
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Valid INPUT  locations (x=0): y={valid_input_y}")
    print(f"Valid OUTPUT locations (x=0): y={valid_output_x0}")
    for x, ys in valid_output_other.items():
        print(f"Valid OUTPUT locations (x={x}): y={ys}")

    # Save results
    results = {
        'arch': args.arch,
        'valid_input_x0': valid_input_y,
        'valid_output_x0': valid_output_x0,
        'valid_output_other_x': valid_output_other,
    }
    results_path = 'io_locs_results.json'
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {results_path}")

    # Cleanup
    shutil.rmtree(csl_dir, ignore_errors=True)
    shutil.rmtree(out_dir, ignore_errors=True)


if __name__ == '__main__':
    main()
