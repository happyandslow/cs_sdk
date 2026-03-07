#!/usr/bin/env python3
"""
Appliance launcher for the I/O port location discovery script.

Usage:
    python run_appliance_discover.py
    python run_appliance_discover.py --arch wse3
    python run_appliance_discover.py --simulator
"""

import argparse
import os
import shutil

from cerebras.sdk.client import SdkLauncher


def main():
    parser = argparse.ArgumentParser(
        description='Discover valid I/O port locations on appliance'
    )
    parser.add_argument(
        '--arch', choices=['wse2', 'wse3'], default='wse3',
        help='Target WSE architecture (default: wse3)'
    )
    parser.add_argument(
        '--simulator', action='store_true',
        help='Run in appliance simulator mode'
    )
    parser.add_argument(
        '--max-y', type=int, default=1200,
        help='Max Y to scan (default: 1200)'
    )
    parser.add_argument(
        '--step', type=int, default=1,
        help='Y step size (default: 1). Use larger for faster scan.'
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    staging_dir = 'discover_staging'
    if os.path.exists(staging_dir):
        shutil.rmtree(staging_dir)
    os.makedirs(staging_dir)
    shutil.copy2('discover_io_locs.py', staging_dir)

    run_cmd = (
        "cs_python discover_io_locs.py "
        "--cmaddr %%CMADDR%% "
        "--arch %s "
        "--max-y %d "
        "--step %d"
    ) % (args.arch, args.max_y, args.step)

    print("=== I/O Port Location Discovery ===")
    print("Architecture : %s" % args.arch.upper())
    print("Simulator    : %s" % args.simulator)
    print("Max Y        : %d" % args.max_y)
    print("Step         : %d" % args.step)
    print("Run command  : %s" % run_cmd)
    print()

    with SdkLauncher(staging_dir, simulator=args.simulator,
                     disable_version_check=True) as launcher:
        response = launcher.run(run_cmd)

    print("Appliance response:")
    print(response)


if __name__ == '__main__':
    main()
