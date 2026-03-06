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
echo "[TEST 1/6] Single PE, buf_size=64, 1 batch"
cs_python run.py --buf-size 64 --arch "${ARCH}"
echo ""

echo "[TEST 2/6] Single PE, buf_size=1024, 1 batch"
cs_python run.py --buf-size 1024 --arch "${ARCH}"
echo ""

echo "[TEST 3/6] Single PE, buf_size=1024, 10 batches (10 KB total)"
cs_python run.py --buf-size 1024 --num-batches 10 --arch "${ARCH}"
echo ""

# ---- Parallel pipeline tests ----
echo "[TEST 4/6] 2 pipelines, buf_size=1024, 1 batch"
cs_python run_parallel.py --num-pipelines 2 --buf-size 1024 --arch "${ARCH}"
echo ""

echo "[TEST 5/6] 4 pipelines, buf_size=1024, 1 batch"
cs_python run_parallel.py --num-pipelines 4 --buf-size 1024 --arch "${ARCH}"
echo ""

echo "[TEST 6/6] 2 pipelines, buf_size=512, 8 batches (16 KB total)"
cs_python run_parallel.py --num-pipelines 2 --buf-size 512 --num-batches 8 --arch "${ARCH}"
echo ""

echo "============================================================"
echo " All tests completed successfully."
echo "============================================================"
