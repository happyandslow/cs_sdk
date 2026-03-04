#!/usr/bin/env bash
# run_appliance.sh — compile and run bandwidth-test-parallel on the CS appliance.
#
# Prerequisites (appliance host machine):
#   - Regular Python 3 with cerebras.sdk.client installed (no cs_python needed)
#   - Access to a running CS appliance (the SdkCompiler and SdkLauncher
#     connect to it automatically via environment variables or config)
#
# Usage:
#   bash run_appliance.sh                                     # defaults: W=1 H=1024 N=4096 C=1 wse3
#   bash run_appliance.sh 64 1024 4096 16 wse3                # W H N channels arch
#   bash run_appliance.sh 64 1024 4096 16 wse3 --verify       # with loopback verification
#   bash run_appliance.sh 64 1024 4096 16 wse3 "--sync --verify"  # sync + verify
#
# The script runs two steps:
#   1. compile_single.py  — SdkCompiler: compiles src/layout.csl on the appliance
#   2. run_launcher.py    — SdkLauncher: stages run_hw.py, executes on appliance

set -euo pipefail

# ---------------------------------------------------------------------------- #
# Parameters
# ---------------------------------------------------------------------------- #
W="${1:-1}"           # width (number of PE columns)
H="${2:-1024}"        # height (number of PE rows)
N="${3:-4096}"        # pe_length (f32 elements per PE)
CHANNELS="${4:-1}"    # number of I/O channels (1-16)
ARCH="${5:-wse3}"     # target architecture
EXTRA="${6:-}"        # optional extra flag, e.g. --verify

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo " bandwidth-test-parallel  (appliance, memcpy path)"
echo " arch=${ARCH}  width=${W}  height=${H}  pe_length=${N}  channels=${CHANNELS}"
echo "============================================================"
echo ""

# ---------------------------------------------------------------------------- #
# Step 1: Compile on the appliance using SdkCompiler (no cs_python needed)
# ---------------------------------------------------------------------------- #
echo "[COMPILE] python compile_single.py --width ${W} --height ${H} --pe-length ${N} --channels ${CHANNELS} --arch ${ARCH}"
python compile_single.py \
    --width "${W}" \
    --height "${H}" \
    --pe-length "${N}" \
    --channels "${CHANNELS}" \
    --arch "${ARCH}"

echo ""
echo "[COMPILE] Done. Artifact hash saved to artifact_path.json"
echo ""

# ---------------------------------------------------------------------------- #
# Step 2: Launch on the appliance using SdkLauncher
# ---------------------------------------------------------------------------- #
echo "[RUN] python run_launcher.py --width ${W} --height ${H} --pe-length ${N} --arch ${ARCH} ${EXTRA}"
python run_launcher.py \
    --width "${W}" \
    --height "${H}" \
    --pe-length "${N}" \
    --arch "${ARCH}" \
    ${EXTRA}

echo ""
echo "============================================================"
echo " Appliance run complete."
echo "============================================================"
