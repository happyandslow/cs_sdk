#!/usr/bin/env bash
# ============================================================================
# bandwidth-test-parallel: Direct-Link Loopback Bandwidth Test Suite
# ============================================================================
# Runs a series of single-host loopback bandwidth tests using the SdkLayout
# direct-link API (no memcpy framework).
#
# Usage:
#   bash bandwidth_test.sh [--arch wse2|wse3]
#
# Options:
#   --arch     wse2 or wse3 (default: wse3)
# ============================================================================

set -e

ARCH="wse3"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --arch)   ARCH="$2";   shift 2;;
    *)        echo "Unknown arg: $1"; exit 1;;
  esac
done

echo "============================================================"
echo " bandwidth-test-parallel  (direct-link loopback)"
echo " arch=${ARCH}"
echo "============================================================"
echo ""

run_test() {
  local HEIGHT=$1
  local PELENGTH=$2
  local EXTRA=$3

  cs_python run.py \
    --height "${HEIGHT}" --pe-length "${PELENGTH}" \
    --arch "${ARCH}" ${EXTRA}
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
