#!/usr/bin/env cs_python

import argparse
import json
import numpy as np

from cerebras.sdk.runtime.sdkruntimepybind import SdkRuntime, MemcpyDataType, MemcpyOrder # pylint: disable=no-name-in-module

# Read arguments
parser = argparse.ArgumentParser()
parser.add_argument('--name', help="the test compile output dir")
parser.add_argument('--cmaddr', help="IP:port for CS system")
args = parser.parse_args()

# Get matrix dimensions from compile metadata
with open(f"{args.name}/out.json", encoding='utf-8') as json_file:
  compile_data = json.load(json_file)

# Matrix dimensions
N = int(compile_data['params']['N'])
M = int(compile_data['params']['M'])

# Number of PEs in program
width = int(compile_data['params']['width'])

# Construct A, x, b
A = np.arange(M*N, dtype=np.float32)
x = np.full(shape=N, fill_value=1.0, dtype=np.float32)
b = np.full(shape=M, fill_value=2.0, dtype=np.float32)

# Calculate expected y
y_expected = A.reshape(M,N)@x + b

# Construct a runner using SdkRuntime
runner = SdkRuntime(args.name, cmaddr=args.cmaddr)

# Get symbols for A, x, b, y on device
A_symbol = runner.get_id('A')
x_symbol = runner.get_id('x')
b_symbol = runner.get_id('b')
y1_symbol = runner.get_id('y1')
y2_symbol = runner.get_id('y2')

# Load and run the program
runner.load()
runner.run()

for step in range(2):
  # Copy A, x, b to device
  runner.memcpy_h2d(A_symbol, np.tile(A, width), 0, 0, width, 1, M*N, streaming=False,
    order=MemcpyOrder.ROW_MAJOR, data_type=MemcpyDataType.MEMCPY_32BIT, nonblock=False)
  runner.memcpy_h2d(x_symbol, np.tile(x, width), 0, 0, width, 1, N, streaming=False,
    order=MemcpyOrder.ROW_MAJOR, data_type=MemcpyDataType.MEMCPY_32BIT, nonblock=False)
  runner.memcpy_h2d(b_symbol, np.tile(b, width), 0, 0, width, 1, M, streaming=False,
    order=MemcpyOrder.ROW_MAJOR, data_type=MemcpyDataType.MEMCPY_32BIT, nonblock=False)
  
  runner.memcpy_h2d(A_symbol, np.tile(A, width), width, 0, width, 1, M*N, streaming=False,
    order=MemcpyOrder.ROW_MAJOR, data_type=MemcpyDataType.MEMCPY_32BIT, nonblock=False)
  runner.memcpy_h2d(x_symbol, np.tile(x, width), width, 0, width, 1, N, streaming=False,
    order=MemcpyOrder.ROW_MAJOR, data_type=MemcpyDataType.MEMCPY_32BIT, nonblock=False)
  runner.memcpy_h2d(b_symbol, np.tile(b, width), width, 0, width, 1, M, streaming=False,
    order=MemcpyOrder.ROW_MAJOR, data_type=MemcpyDataType.MEMCPY_32BIT, nonblock=False)

  # Launch the init_and_compute function on device
  runner.launch('compute', nonblock=False)

  # Copy y back from device
  y1_result = np.zeros([M*width], dtype=np.float32)
  runner.memcpy_d2h(y1_result, y1_symbol, 0, 0, width, 1, M, streaming=False,
    order=MemcpyOrder.ROW_MAJOR, data_type=MemcpyDataType.MEMCPY_32BIT, nonblock=False)
  
  y2_result = np.zeros([M*width], dtype=np.float32)
  runner.memcpy_d2h(y2_result, y2_symbol, width, 0, width, 1, M, streaming=False,
    order=MemcpyOrder.ROW_MAJOR, data_type=MemcpyDataType.MEMCPY_32BIT, nonblock=False)
  # Ensure that the result matches our expectation
  np.testing.assert_allclose(y1_result, np.tile(y_expected, width), atol=0.01, rtol=0)
  np.testing.assert_allclose(y2_result, np.tile(y_expected, width), atol=0.01, rtol=0)
  print("SUCCESS!")

# Stop the program
runner.stop()


