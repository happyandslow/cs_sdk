#!/usr/bin/env cs_python

"""
Analyze sim_stats_*.json files and print detailed statistics.

For each numeric metric found in the JSON files, this script computes:
- count
- mean
- standard deviation
- min
- 25th / 50th / 75th percentiles
- max

Usage (from this directory):
  cs_python analyze_sim_stats.py
or
  python analyze_sim_stats.py
"""

import glob
import json
import math
import os
from typing import Dict, List, Any


def load_stats(pattern: str = "sim_stats_*.json") -> List[Dict[str, Any]]:
    files = sorted(glob.glob(pattern))
    if not files:
        raise SystemExit(f"No files match pattern '{pattern}'")

    runs = []
    for fname in files:
        with open(fname, "r") as f:
            runs.append(json.load(f))
    return runs


def is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def percentile(values: List[float], p: float) -> float:
    """
    Compute percentile p (0-100) using linear interpolation
    between closest ranks.
    """
    if not values:
        return float("nan")
    if len(values) == 1:
        return values[0]
    v = sorted(values)
    k = (p / 100.0) * (len(v) - 1)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return v[int(k)]
    d0 = v[f] * (c - k)
    d1 = v[c] * (k - f)
    return d0 + d1


def summarize(runs: List[Dict[str, Any]]) -> None:
    # Collect all numeric keys
    numeric_keys = set()
    for r in runs:
        for k, v in r.items():
            if is_number(v):
                numeric_keys.add(k)

    numeric_keys = sorted(numeric_keys)

    # Build per-key list of values
    data: Dict[str, List[float]] = {k: [] for k in numeric_keys}
    for r in runs:
        for k in numeric_keys:
            v = r.get(k, None)
            if is_number(v):
                data[k].append(float(v))

    # Header
    header_cols = [
        "metric",
        "count",
        "mean",
        "stddev",
        "min",
        "p25",
        "p50",
        "p75",
        "max",
    ]
    col_widths = {
        "metric": 26,
        "count": 5,
        "mean": 13,
        "stddev": 13,
        "min": 13,
        "p25": 13,
        "p50": 13,
        "p75": 13,
        "max": 13,
    }

    def fmt_row(cols: Dict[str, str]) -> str:
        parts = []
        for name in header_cols:
            width = col_widths[name]
            if name == "metric":
                parts.append(f"{cols[name]:<{width}}")
            else:
                parts.append(f"{cols[name]:>{width}}")
        return "  ".join(parts)

    print(f"Found {len(runs)} runs.")
    print()
    print(fmt_row({k: k for k in header_cols}))
    print("-" * (sum(col_widths.values()) + 2 * (len(header_cols) - 1)))

    for key in numeric_keys:
        vals = data[key]
        if not vals:
            continue
        n = len(vals)
        mean = sum(vals) / n
        if n > 1:
            var = sum((x - mean) ** 2 for x in vals) / (n - 1)
            std = math.sqrt(var)
        else:
            std = float("nan")

        row = {
            "metric": key,
            "count": str(n),
            "mean": f"{mean:.6g}",
            "stddev": f"{std:.6g}",
            "min": f"{min(vals):.6g}",
            "p25": f"{percentile(vals, 25):.6g}",
            "p50": f"{percentile(vals, 50):.6g}",
            "p75": f"{percentile(vals, 75):.6g}",
            "max": f"{max(vals):.6g}",
        }
        print(fmt_row(row))


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)
    runs = load_stats()
    summarize(runs)


if __name__ == "__main__":
    main()


# Found 10 runs.

# metric                      count           mean         stddev            min            p25            p50            p75            max
# ------------------------------------------------------------------------------------------------------------------------------------------
# cycle_count                    10        46973.9        9032.91          37021        40133.8          44255        52892.5          63999
# cycles_per_second              10        14203.7        4245.05           9039        11317.4        13517.3        16463.7        21244.4
# fabric_x                       10             15              0             15             15             15             15             15
# fabric_y                       10              3              0              3              3              3              3              3
# hwtile_count                   10             17              0             17             17             17             17             17
# idle_ce_cycles                 10        24212.3        8979.98          14918          17760        20836.5          30180          41510
# idle_wavelet_cycles            10        24267.3        8979.98          14973          17815        20891.5          30235          41565
# init_time                      10      0.0283541     0.00164099      0.0264111      0.0271699      0.0278826      0.0297654        0.03069
# iotile_count                   10              4              0              4              4              4              4              4
# nodes                          10              1              0              1              1              1              1              1
# nultile_count                  10             60              0             60             60             60             60             60
# sim_time                       10        3.41647       0.470655        2.86544        3.03209        3.42082        3.66098        4.17313
# simulated_tile_count           10             21              0             21             21             21             21             21
# sunset_count                   10              0              0              0              0              0              0              0
# threads                        10              5              0              5              5              5              5              5
# tile_count                     10             81              0             81             81             81             81             81
# tile_cycles_per_second         10         298279          89146         189819         237666         283864         345737         446133
# tile_cycles_per_second_per_thread     10        59655.7        17829.2        37963.8        47533.2        56772.7        69147.3        89226.6
# total_time                     10        3.44482       0.471059        2.89604        3.06081        3.44816        3.68816        4.20311