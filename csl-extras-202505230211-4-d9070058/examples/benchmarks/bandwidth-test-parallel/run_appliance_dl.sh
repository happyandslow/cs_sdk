#!/usr/bin/env bash
# run_appliance_dl.sh — compile and run bandwidth-test-parallel on the CS appliance
#                       using the SdkLayout DIRECT-LINK path (no memcpy framework).
#
# Two-step workflow:
#   1. cs_python run_single.py --compile-only  (local; needs cs_python)
#   2. python run_launcher.py                  (appliance; Path A auto-detected)
#
# Usage:
#   bash run_appliance_dl.sh                              # defaults: W=1 H=4 N=1024 wse3
#   bash run_appliance_dl.sh 1 1024 4096 wse3             # W H N arch
#   bash run_appliance_dl.sh 1 1024 4096 wse3 --verify    # with loopback verification
#
# The SdkLauncher stages run_single.py (+ helpers) to the appliance worker,
# which runs:  cs_python run_single.py --run-only --name . --cmaddr <IP:PORT>

set -euo pipefail

# ---------------------------------------------------------------------------- #
# Parameters
# ---------------------------------------------------------------------------- #
W="${1:-1}"           # width (number of PE columns)
H="${2:-4}"           # height (number of PE rows)
N="${3:-1024}"        # pe_length (f32 elements per PE)
ARCH="${4:-wse3}"     # target architecture
EXTRA="${5:-}"        # optional extra flag, e.g. --verify

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo " bandwidth-test-parallel  (appliance, direct-link path)"
echo " arch=${ARCH}  width=${W}  height=${H}  pe_length=${N}"
echo "============================================================"
echo ""

# ---------------------------------------------------------------------------- #
# Step 1: Compile locally using cs_python + SdkLayout (direct-link)
# ---------------------------------------------------------------------------- #
echo "[COMPILE] cs_python run_single.py --compile-only --width ${W} --height ${H} --pe-length ${N} --arch ${ARCH}"
cs_python run_single.py \
    --compile-only \
    --width "${W}" \
    --height "${H}" \
    --pe-length "${N}" \
    --arch "${ARCH}"

echo ""
echo "[COMPILE] Done. Artifact directory saved to artifact_path.json"
echo ""

# ---------------------------------------------------------------------------- #
# Step 2: Launch on the appliance using SdkLauncher (Path A: SdkLayout artifact)
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
