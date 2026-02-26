#!/usr/bin/env bash

set -e

python run.appliance.py -m=720 -n=720 -k=512 --latestlink latest --channels=16 --width-west-buf=1 --width-east-buf=1 --arch=wse3 --compile-only

# cslc ./src/bw_sync_layout.csl --arch wse3 --fabric-dims=762,1172 --fabric-offsets=5,2 \
# --params=width:720,height:720,pe_length:512 --params=C0_ID:0 \
# --params=C1_ID:1 --params=C2_ID:2 --params=C3_ID:3 --params=C4_ID:4 -o=out \
# --memcpy --channels=16 --width-west-buf=1 --width-east-buf=1

# cs_python run.py -m=762 -n=1172 -k=512 --latestlink latest --channels=16 --width-west-buf=1 --width-east-buf=1 --h2d --arch=wse3 --run-only --loop_count=1


# cs_python ./run.py -m=5 -n=5 -k=5 --latestlink out --channels=1 \
# --width-west-buf=0 --width-east-buf=0 --run-only --loop_count=1
