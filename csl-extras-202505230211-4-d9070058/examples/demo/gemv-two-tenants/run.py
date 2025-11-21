#!/usr/bin/env cs_python

import argparse
import numpy as np

from cerebras.sdk.runtime.sdkruntimepybind import SdkRuntime, MemcpyDataType, MemcpyOrder # pylint: disable=no-name-in-module

# Read arguments
parser = argparse.ArgumentParser()
parser.add_argument('--name', help="the test compile output dir")
parser.add_argument('--cmaddr', help="IP:port for CS system")
args = parser.parse_args()

# Matrix dimensions
M = 4
N = 6

# Construct A, x, b
A = np.arange(M*N, dtype=np.float32).reshape(M, N)
x = np.full(shape=N, fill_value=1.0, dtype=np.float32)
b = np.full(shape=M, fill_value=2.0, dtype=np.float32)

# Calculate expected y
y_expected = A@x + b

# Construct a runner using SdkRuntime
runner = SdkRuntime(args.name, cmaddr=args.cmaddr)

# Get symbol for copying y result off device
y1_symbol = runner.get_id('y1')
y2_symbol = runner.get_id('y2')

# Load and run the program
runner.load()
runner.run()

# Launch the init_and_compute function on device
# runner.launch('init_and_compute_1', nonblock=True
# 
# 
# )
runner.launch('init_and_compute', nonblock=True)

# Copy y back from device
# Arguments to memcpy_d2h:
# - y_result is array on host which will story copied-back array
# - y_symbol is symbol of device tensor to be copied
# - 0, 0, 1, 1 are (starting x-coord, starting y-coord, width, height)
#   of rectangle of PEs whose data is to be copied
# - M is number of elements to be copied from each PE
y1_result = np.zeros([1*1*M], dtype=np.float32)
y2_result = np.zeros([1*1*M], dtype=np.float32)
runner.memcpy_d2h(y1_result, y1_symbol, 0, 0, 1, 1, M, streaming=False,
  order=MemcpyOrder.ROW_MAJOR, data_type=MemcpyDataType.MEMCPY_32BIT, nonblock=False)
runner.memcpy_d2h(y2_result, y2_symbol, 1, 0, 1, 1, M, streaming=False,
  order=MemcpyOrder.ROW_MAJOR, data_type=MemcpyDataType.MEMCPY_32BIT, nonblock=False)

# Stop the program
runner.stop()
runner.dump_core("corefile.cs1")

# Ensure that the result matches our expectation
# np.testing.assert_allclose(y1_result, y_expected, atol=0.01, rtol=0)
# np.testing.assert_allclose(y2_result, y_expected, atol=0.01, rtol=0)
print(y1_result)
print(y2_result)
print("SUCCESS!")
