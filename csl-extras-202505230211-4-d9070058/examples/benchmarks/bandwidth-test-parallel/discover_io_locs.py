#!/usr/bin/env cs_python
"""
Discover valid I/O port locations on the connected WSE hardware.

Tries compiling a minimal SdkLayout program with io_loc at various
(0, y) positions on the WEST edge to find which ones are accepted.

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
    Edge,
    Route,
    RoutingPosition,
    get_platform,
)
from cerebras.geometry.geometry import IntVector


def test_io_loc(platform, csl_path, y, out_dir):
    """Try to compile with io_loc at (0, y). Returns True if valid."""
    try:
        layout = SdkLayout(platform)
        region = layout.create_code_region(csl_path, 'r', 1, 1)
        region.place(5, y)  # Place core near the io_loc row

        c = Color('c')
        region.set_param_all(c)
        rp = RoutingPosition().set_output([Route.RAMP])
        port = region.create_input_port(c, Edge.LEFT, [rp], 10)

        layout.create_input_stream(port, io_loc=IntVector(0, y))
        layout.compile(out_prefix=os.path.join(out_dir, f'test_{y}'))
        return True
    except RuntimeError as e:
        if 'is not valid' in str(e):
            return False
        # Other errors might indicate valid location but different issue
        print(f"  y={y}: other error: {e}")
        return None
    except Exception as e:
        print(f"  y={y}: unexpected error: {type(e).__name__}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='Discover valid I/O port locations')
    parser.add_argument('--cmaddr', help='IP:port for CS system')
    parser.add_argument('--arch', choices=['wse2', 'wse3'], default='wse3')
    parser.add_argument('--max-y', type=int, default=1200,
                        help='Max Y to scan (default: 1200)')
    parser.add_argument('--step', type=int, default=1,
                        help='Y step size for scanning (default: 1)')
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

    print(f"Scanning WEST edge (x=0) for valid I/O port locations...")
    print(f"Architecture: {args.arch.upper()}")
    print(f"Y range: 0 to {args.max_y}, step={args.step}")
    print()

    valid_locs = []
    for y in range(0, args.max_y, args.step):
        result = test_io_loc(platform, csl_path, y, out_dir)
        if result is True:
            valid_locs.append(y)
            print(f"  y={y}: VALID")
        elif result is False:
            pass  # silently skip invalid
        # result=None means other error, already printed

    print()
    print(f"=== Results ===")
    print(f"Valid I/O port Y locations at x=0 (WEST): {valid_locs}")
    print(f"Total valid: {len(valid_locs)}")

    if len(valid_locs) > 1:
        diffs = [valid_locs[i+1] - valid_locs[i] for i in range(len(valid_locs)-1)]
        print(f"Spacings between valid locations: {diffs}")
        print(f"Min spacing: {min(diffs)}, Max spacing: {max(diffs)}")

    # Also try x=1 (one column in from WEST edge)
    print()
    print("Trying a few locations at x=1...")
    for y in valid_locs[:5]:
        result = test_io_loc(platform, csl_path, y, out_dir)
        status = "VALID" if result else "INVALID" if result is False else "ERROR"
        print(f"  (1, {y}): {status}")

    # Save results
    results = {
        'arch': args.arch,
        'valid_west_y': valid_locs,
        'count': len(valid_locs),
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
