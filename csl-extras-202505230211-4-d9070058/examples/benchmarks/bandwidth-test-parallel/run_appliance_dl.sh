#!/usr/bin/env bash
# run_appliance_dl.sh — run bandwidth-test-parallel on the CS appliance
#                       using the SdkLayout DIRECT-LINK path (no memcpy framework).
#
# Single-step workflow:
#   python run_launcher.py --direct-link ...
#   → packages src/ + Python scripts into a tarball, uploads to the appliance,
#     compiles AND runs on the appliance worker where get_system(%CMADDR%)
#     provides the full WSE-3 fabric dimensions (762×1172).
#
# Usage:
#   bash run_appliance_dl.sh                              # defaults: W=1 H=4 N=1024 wse3
#   bash run_appliance_dl.sh 1 1024 4096 wse3             # W H N arch
#   bash run_appliance_dl.sh 1 1024 4096 wse3 --verify    # with loopback verification

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
# Compile + run on the appliance worker (single step)
# ---------------------------------------------------------------------------- #
echo "[RUN] python run_launcher.py --direct-link --width ${W} --height ${H} --pe-length ${N} --arch ${ARCH} ${EXTRA}"
python run_launcher.py \
    --direct-link \
    --width "${W}" \
    --height "${H}" \
    --pe-length "${N}" \
    --arch "${ARCH}" \
    ${EXTRA}

echo ""
echo "============================================================"
echo " Appliance run complete."
echo "============================================================"
