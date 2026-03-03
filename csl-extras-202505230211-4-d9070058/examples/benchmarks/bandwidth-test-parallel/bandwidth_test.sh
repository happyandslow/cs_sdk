#!/usr/bin/env bash
# ============================================================================
# bandwidth-test-parallel: Direct-Link Loopback Bandwidth Test Script
# ============================================================================
# Runs a series of single-host loopback bandwidth tests using the SdkLayout
# direct-link API (no memcpy framework).
#
# Usage:
#   bash bandwidth_test.sh [--cmaddr IP:PORT] [--arch wse2|wse3]
#
# Options:
#   --cmaddr   IP:port of the CS appliance (omit for simulator mode)
#   --arch     wse2 or wse3 (default: wse3)
#
# Modes:
#   Simulator (no --cmaddr):
#     Each test compiles and runs in one step via run_single.py.
#
#   Appliance (--cmaddr provided):
#     Each test is a two-step workflow:
#       1. Compile locally (no hardware connection needed):
#            cs_python run_single.py --compile-only --height H --pe-length N --arch A
#       2. Launch on appliance via SdkLauncher:
#            python run_launcher.py --height H --pe-length N --arch A
#     The SdkLauncher transfers the compiled artifact to the appliance, stages the
#     Python helper files, and runs run_single.py --run-only --cmaddr <IP:PORT>.
# ============================================================================

set -e

CMADDR=""
ARCH="wse3"

# Parse optional args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --cmaddr) CMADDR="$2"; shift 2;;
    --arch)   ARCH="$2";   shift 2;;
    *)        echo "Unknown arg: $1"; exit 1;;
  esac
done

ARCH_FLAG="--arch ${ARCH}"
RUNNER="cs_python"

echo "============================================================"
echo " bandwidth-test-parallel  (direct-link loopback)"
echo " arch=${ARCH}  cmaddr=${CMADDR:-simulator}"
echo "============================================================"
echo ""

# Helper: run one test.
#   For simulator: compile + run in a single step.
#   For appliance: compile locally, then launch via SdkLauncher.
run_test() {
  local HEIGHT=$1
  local PELENGTH=$2
  local EXTRA=$3          # optional extra flags, e.g. --verify
  local NAME="out_H${HEIGHT}_N${PELENGTH}"

  if [[ -z "${CMADDR}" ]]; then
    # ---- Simulator mode: compile + run together ----
    ${RUNNER} run_single.py \
      --height "${HEIGHT}" --pe-length "${PELENGTH}" \
      ${ARCH_FLAG} --name "${NAME}" ${EXTRA}
  else
    # ---- Appliance mode: compile locally, then launch ----
    echo "  [compile] height=${HEIGHT} pe-length=${PELENGTH} ..."
    ${RUNNER} run_single.py \
      --compile-only \
      --height "${HEIGHT}" --pe-length "${PELENGTH}" \
      ${ARCH_FLAG} --name "${NAME}"

    echo "  [launch]  submitting to appliance ${CMADDR} ..."
    python run_launcher.py \
      --height "${HEIGHT}" --pe-length "${PELENGTH}" \
      ${ARCH_FLAG} ${EXTRA}
  fi
}

# ---- Test 1: Smoke test (tiny, with verification) ----
echo "[TEST 1/5] Smoke test: H=2, pe_length=4  (with --verify)"
run_test 2 4 "--verify"
echo ""

# ---- Test 2: Small ----
echo "[TEST 2/5] Small:  H=4,  pe_length=256"
run_test 4 256
echo ""

# ---- Test 3: Medium ----
echo "[TEST 3/5] Medium: H=8,  pe_length=1024"
run_test 8 1024
echo ""

# ---- Test 4: Large ----
echo "[TEST 4/5] Large:  H=16, pe_length=2048"
run_test 16 2048
echo ""

# ---- Test 5: Maximum single-column ----
echo "[TEST 5/5] Max:    H=32, pe_length=4096"
run_test 32 4096
echo ""

echo "============================================================"
echo " All tests completed successfully."
echo "============================================================"
