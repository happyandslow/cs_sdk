#!/bin/bash

py_path=$(realpath $1)
package_name=$2
SINGULARITYENV_PYTHONPATH="$(realpath $py_path)"
cs_python -c "
import subprocess
import sys
package='$2'
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--target=$py_path', package])
"
echo -e "Please do\nexport SINGULARITYENV_PYTHONPATH=\"$SINGULARITYENV_PYTHONPATH\"\nbefore using cs_python"


# mkdir MY_LOCAL_PY_PATH
# bash sdk_install_python_package.sh ./MY_LOCAL_PY_PATH MY_PIP_PACKAGE_NAME

# export SINGULARITYENV_PYTHONPATH=$(realpath $MY_LOCAL_PY_PATH)