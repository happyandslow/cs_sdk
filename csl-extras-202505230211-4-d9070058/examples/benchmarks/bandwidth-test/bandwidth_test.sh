#!/bin/bash

# python master_bandwidth_test.py \
#     --k-values 4096 \
#     --m-values 448 \
#     --n-values 448 \
#     --channels-values 16 4 1 \
#     --buffer-sizes 152 100 50\
#     --directions h2d d2h \
#     --loop-count 5


# python master_bandwidth_test.py \
#     --k-values 4096 \
#     --m-values 448 \
#     --n-values 448 \
#     --channels-values 16 4 1 \
#     --buffer-sizes 152 100 50 \
#     --directions h2d \
#     --loop-count 5


python master_bandwidth_test.py \
    --k-values 2048 \
    --m-values 512 \
    --n-values 512 \
    --channels-values 16 4 1 \
    --buffer-sizes 90 60 30 \
    --directions h2d d2h \
    --loop-count 5