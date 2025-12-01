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
# cycle_count                    10        46761.4        10208.6          36295        38642.8        43995.5        51811.2          66195
# cycles_per_second              10        16047.6        5693.57        10284.4        11218.1        14480.1          19286        25246.4
# fabric_x                       10             11              0             11             11             11             11             11
# fabric_y                       10              4              0              4              4              4              4              4
# hwtile_count                   10             22              0             22             22             22             22             22
# idle_ce_cycles                 10        24216.7        9535.46          14248        16674.2        22243.5        28409.8          42639
# idle_wavelet_cycles            10        24252.7        9535.46          14284        16710.2        22279.5        28445.8          42675
# init_time                      10      0.0322554      0.0023908       0.029521      0.0306993      0.0311811      0.0329807      0.0366311
# iotile_count                   10              4              0              4              4              4              4              4
# nodes                          10              1              0              1              1              1              1              1
# nultile_count                  10             48              0             48             48             48             48             48
# sim_time                       10        3.04425        0.46249        2.39171         2.6894         2.9982        3.31186        3.78715
# simulated_tile_count           10             26              0             26             26             26             26             26
# sunset_count                   10              0              0              0              0              0              0              0
# threads                        10              5              0              5              5              5              5              5
# tile_count                     10             74              0             74             74             74             74             74
# tile_cycles_per_second         10         417236         148033         267394         291670         376482         501435         656406
# tile_cycles_per_second_per_thread     10        83447.3        29606.6        53478.7        58333.9        75296.3         100287         131281
# total_time                     10         3.0765       0.462769        2.42123        2.72191        3.03185        3.34757        3.81781