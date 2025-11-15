#!/bin/bash

SDK_INSTALL_PATH=/Users/lexu/cs_sdk
PATH_CMD='export PATH='$SDK_INSTALL_PATH':$PATH'
eval $PATH_CMD
echo $PATH_CMD >> ~/.bashrc



cd $SDK_INSTALL_PATH
tar -xzvf csl-extras-202505230211-4-d9070058.tar.gz
# Optional: SINGULARITYENV_CSL_SUPPRESS_SIMFAB_TRACE=1
sdk_debug_shell smoke csl-extras-202505230211-4-d9070058


### Testing for GUI
build_id="202505230211-4-d9070058"
cd $SDK_INSTALL_PATH/csl-extras-${build_id}/examples/benchmarks/gemm-collectives_2d
./commands_wse2.sh 
## sdk_debug_shell visualize
## check GUI: http://localhost:8000/sdk-gui/