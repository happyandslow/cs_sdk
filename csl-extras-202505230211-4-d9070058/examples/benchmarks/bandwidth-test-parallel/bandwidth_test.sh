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
#   --cmaddr   IP:port of the CS system (default: omit for simulator)
#   --arch     wse2 or wse3 (default: wse3)
#
# Each test compiles and runs a loopback program measuring H2D+D2H bandwidth.
# ============================================================================

set -e

CMADDR=""
ARCH="wse3"

# Parse optional args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --cmaddr) CMADDR="--cmaddr $2"; shift 2;;
    --arch)   ARCH="$2";            shift 2;;
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

# ---- Test 1: Smoke test (tiny, with verification) ----
echo "[TEST 1/5] Smoke test: H=2, pe_length=4  (with --verify)"
${RUNNER} run_single.py --height 2 --pe-length 4 ${ARCH_FLAG} ${CMADDR} --verify
echo ""

# ---- Test 2: Small ----
echo "[TEST 2/5] Small:  H=4,  pe_length=256"
${RUNNER} run_single.py --height 4 --pe-length 256 ${ARCH_FLAG} ${CMADDR}
echo ""

# ---- Test 3: Medium ----
echo "[TEST 3/5] Medium: H=8,  pe_length=1024"
${RUNNER} run_single.py --height 8 --pe-length 1024 ${ARCH_FLAG} ${CMADDR}
echo ""

# ---- Test 4: Large ----
echo "[TEST 4/5] Large:  H=16, pe_length=2048"
${RUNNER} run_single.py --height 16 --pe-length 2048 ${ARCH_FLAG} ${CMADDR}
echo ""

# ---- Test 5: Maximum single-column ----
echo "[TEST 5/5] Max:    H=32, pe_length=4096"
${RUNNER} run_single.py --height 32 --pe-length 4096 ${ARCH_FLAG} ${CMADDR}
echo ""

echo "============================================================"
echo " All tests completed successfully."
echo "============================================================"
