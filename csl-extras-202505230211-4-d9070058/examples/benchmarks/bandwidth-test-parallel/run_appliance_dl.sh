#!/usr/bin/env bash
# run_appliance_dl.sh — DEPRECATED, use run_appliance.sh instead.
#
# The SdkLayout (direct-link) path cannot be compiled via SdkCompiler/cslc
# because it requires multi-region layout and create_input/output_stream(),
# which are SdkLayout Python-API-only features.
#
# For appliance runs, use the memcpy path:
#   bash run_appliance.sh W H N CHANNELS ARCH [EXTRA]
#
# The SdkLayout path (run_single.py) remains available for simulator testing:
#   cs_python run_single.py --width 1 --height 4 --pe-length 1024 --arch wse3

echo "ERROR: run_appliance_dl.sh is deprecated."
echo "SdkLayout (direct-link) programs cannot be compiled via SdkCompiler/cslc."
echo ""
echo "Use the memcpy path instead:"
echo "  bash run_appliance.sh ${1:-1} ${2:-4} ${3:-1024} ${4:-1} ${5:-wse3} ${6:-}"
echo ""
echo "For simulator testing with direct-link:"
echo "  cs_python run_single.py --width 1 --height 4 --pe-length 1024 --arch wse3"
exit 1
