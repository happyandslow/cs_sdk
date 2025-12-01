#!/bin/bash

for i in {1..10}; do
    echo "Running iteration $i"
    ./commands_wse3.sh 
    sleep 1
    mv sim_stats.json sim_stats_$i.json
done