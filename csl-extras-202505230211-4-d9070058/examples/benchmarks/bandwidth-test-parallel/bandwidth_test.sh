#!/usr/bin/env bash
# ============================================================================
# bandwidth-test-parallel: Direct-Link H2D Bandwidth Test Suite
# ============================================================================
# Runs single-PE and parallel-PE bandwidth tests using the SdkLayout
# direct-link API with on-device timing (no memcpy, no demux/mux).
#
# Usage:
#   bash bandwidth_test.sh [--arch wse2|wse3]
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
echo " bandwidth-test-parallel  (direct-link, on-device timing)"
echo " arch=${ARCH}"
echo "============================================================"
echo ""

# ---- Single pipeline tests ----
echo "[TEST 1/5] Single PE, pe_length=64"
cs_python run.py --pe-length 64 --arch "${ARCH}"
echo ""

echo "[TEST 2/5] Single PE, pe_length=1024"
cs_python run.py --pe-length 1024 --arch "${ARCH}"
echo ""

echo "[TEST 3/5] Single PE, pe_length=4096"
cs_python run.py --pe-length 4096 --arch "${ARCH}"
echo ""

# ---- Parallel pipeline tests ----
echo "[TEST 4/5] 2 pipelines, pe_length=1024"
cs_python run_parallel.py --num-pipelines 2 --pe-length 1024 --arch "${ARCH}"
echo ""

echo "[TEST 5/5] 4 pipelines, pe_length=1024"
cs_python run_parallel.py --num-pipelines 4 --pe-length 1024 --arch "${ARCH}"
echo ""

echo "============================================================"
echo " All tests completed successfully."
echo "============================================================"
