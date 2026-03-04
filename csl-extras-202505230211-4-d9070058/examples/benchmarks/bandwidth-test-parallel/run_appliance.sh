#!/usr/bin/env bash
# run_appliance.sh — compile and run bandwidth-test-parallel on the CS appliance.
#
# Prerequisites (appliance host machine):
#   - Regular Python 3 with cerebras.sdk.client installed (no cs_python needed)
#   - Access to a running CS appliance (the SdkCompiler and SdkLauncher
#     connect to it automatically via environment variables or config)
#
# Usage:
#   bash run_appliance.sh                       # default: H=4, N=1024, wse3
#   bash run_appliance.sh 4 1024 wse3           # explicit: H N arch
#   bash run_appliance.sh 4 1024 wse3 --verify  # with loopback verification
#
# The script runs two steps:
#   1. compile_single.py  — SdkCompiler: compiles src/layout.csl on the appliance
#   2. run_launcher.py    — SdkLauncher: stages run_hw.py, executes on appliance

set -euo pipefail

# ---------------------------------------------------------------------------- #
# Parameters
# ---------------------------------------------------------------------------- #
H="${1:-4}"          # height (number of PEs)
N="${2:-1024}"       # pe_length (f32 elements per PE)
ARCH="${3:-wse3}"    # target architecture
EXTRA="${4:-}"       # optional extra flag, e.g. --verify

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo " bandwidth-test-parallel  (appliance, memcpy path)"
echo " arch=${ARCH}  height=${H}  pe_length=${N}"
echo "============================================================"
echo ""

# ---------------------------------------------------------------------------- #
# Step 1: Compile on the appliance using SdkCompiler (no cs_python needed)
# ---------------------------------------------------------------------------- #
echo "[COMPILE] python compile_single.py --height ${H} --pe-length ${N} --arch ${ARCH}"
python compile_single.py \
    --height "${H}" \
    --pe-length "${N}" \
    --arch "${ARCH}"

echo ""
echo "[COMPILE] Done. Artifact hash saved to artifact_path.json"
echo ""

# ---------------------------------------------------------------------------- #
# Step 2: Launch on the appliance using SdkLauncher
# ---------------------------------------------------------------------------- #
echo "[RUN] python run_launcher.py --height ${H} --pe-length ${N} --arch ${ARCH} ${EXTRA}"
python run_launcher.py \
    --height "${H}" \
    --pe-length "${N}" \
    --arch "${ARCH}" \
    ${EXTRA}

echo ""
echo "============================================================"
echo " Appliance run complete."
echo "============================================================"
