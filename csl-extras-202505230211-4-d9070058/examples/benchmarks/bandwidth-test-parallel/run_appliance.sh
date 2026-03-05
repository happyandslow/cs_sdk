#!/usr/bin/env bash
# run_appliance.sh — compile and run bandwidth-test-parallel on the CS appliance.
#
# Prerequisites (appliance host machine):
#   - Regular Python 3 with cerebras.sdk.client installed (no cs_python needed)
#   - Access to a running CS appliance (the SdkCompiler and SdkLauncher
#     connect to it automatically via environment variables or config)
#
# Usage:
#   bash run_appliance.sh                                                 # defaults
#   bash run_appliance.sh 720 720 512 16 4 4 wse3 5                      # max BW config
#   bash run_appliance.sh 720 720 512 16 4 4 wse3 5 "--d2h"              # D2H direction
#   bash run_appliance.sh 720 720 512 16 4 4 wse3 5 "--verify"           # with verification
#   bash run_appliance.sh 720 720 512 16 4 4 wse3 5 "--sync --verify"    # sync + verify
#
# Parameters for maximum bandwidth:
#   W=720        wide rectangle to leverage multiple channels
#   H=720        tall rectangle for more data
#   N=512        elements per PE
#   C=16         maximum I/O channels
#   WB=4         west buffer columns (hides H2D latency)
#   EB=4         east buffer columns (hides D2H latency)
#   L=5          loop count (amortizes TCP overhead)
#
# The script runs two steps:
#   1. compile_single.py  — SdkCompiler: compiles src/layout.csl with --fabric-dims=762,1172
#   2. run_launcher.py    — SdkLauncher: stages run_hw.py, executes on appliance

set -euo pipefail

# ---------------------------------------------------------------------------- #
# Parameters
# ---------------------------------------------------------------------------- #
W="${1:-1}"           # width (number of PE columns)
H="${2:-1024}"        # height (number of PE rows)
N="${3:-4096}"        # pe_length (f32 elements per PE)
CHANNELS="${4:-1}"    # number of I/O channels (1-16)
WB="${5:-0}"          # west buffer columns
EB="${6:-0}"          # east buffer columns
ARCH="${7:-wse3}"     # target architecture
LOOP="${8:-1}"        # loop count
EXTRA="${9:-}"        # optional extra flags, e.g. --verify, --d2h, --sync

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo " bandwidth-test-parallel  (appliance, memcpy path)"
echo " arch=${ARCH}  W=${W}  H=${H}  N=${N}  channels=${CHANNELS}"
echo " west_buf=${WB}  east_buf=${EB}  loop_count=${LOOP}"
echo "============================================================"
echo ""

# ---------------------------------------------------------------------------- #
# Step 1: Compile on the appliance using SdkCompiler (no cs_python needed)
# ---------------------------------------------------------------------------- #
echo "[COMPILE] python compile_single.py --width ${W} --height ${H} --pe-length ${N} --channels ${CHANNELS} --width-west-buf ${WB} --width-east-buf ${EB} --arch ${ARCH}"
python compile_single.py \
    --width "${W}" \
    --height "${H}" \
    --pe-length "${N}" \
    --channels "${CHANNELS}" \
    --width-west-buf "${WB}" \
    --width-east-buf "${EB}" \
    --arch "${ARCH}"

echo ""
echo "[COMPILE] Done. Artifact hash saved to artifact_path.json"
echo ""

# ---------------------------------------------------------------------------- #
# Step 2: Launch on the appliance using SdkLauncher
# ---------------------------------------------------------------------------- #
echo "[RUN] python run_launcher.py --width ${W} --height ${H} --pe-length ${N} --loop-count ${LOOP} --arch ${ARCH} ${EXTRA}"
python run_launcher.py \
    --width "${W}" \
    --height "${H}" \
    --pe-length "${N}" \
    --loop-count "${LOOP}" \
    --arch "${ARCH}" \
    ${EXTRA}

echo ""
echo "============================================================"
echo " Appliance run complete."
echo "============================================================"
