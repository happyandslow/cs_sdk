#!/bin/bash
set -x 


for k in 512; #1024 ; #2048 4096 ;
do
    for m in 720; #360; #1024 1150 ;
    do
        for n in 720; # 360;
        do
            for channels in 16 4 1;
            do
                for buffer_size in 1 2 4 8;
                do
                    rm cs_*.tar.gz
                    rm -r latest
                    rm -r hash.json
                    rm wsjob*
                    
                    echo "Compile for k = $k and m = $m and n = $n and buffer_size = $buffer_size and channels = $channels and direction = $direction"
                    python run.appliance.py -m=$m -n=$n -k=$k --latestlink latest --channels=$channels --width-west-buf=$buffer_size --width-east-buf=$buffer_size --arch=wse3 --compile-only
                    for direction in  "--h2d" #"--d2h" #"--h2d"
                    do 
                        echo "Run for k = $k and m = $m and n = $n and buffer_size = $buffer_size and channels = $channels and direction = $direction"
                        if [ $direction == "--d2h" ]; then
                            python run.appliance.py -m=$m -n=$n -k=$k --latestlink latest --channels=$channels --width-west-buf=$buffer_size --width-east-buf=$buffer_size $direction --arch=wse3 --run-only --loop_count=5 > logs/m${m}-n${n}-k${k}-buffer_size${buffer_size}-channels${channels}-${direction}.txt 2>&1
                        else
                            python run.appliance.py -m=$m -n=$n -k=$k --latestlink latest --channels=$channels --width-west-buf=$buffer_size --width-east-buf=$buffer_size --arch=wse3 --run-only --loop_count=5 > logs/m${m}-n${n}-k${k}-buffer_size${buffer_size}-channels${channels}-${direction}.txt 2>&1
                        fi
                    done
                done
            done
        done
    done
done



# rm cs_*.tar.gz
# rm -r latest
# rm -r hash.json
# rm wsjob*
# python run.appliance.py -m=720 -n=720 -k=1024 --latestlink latest --channels=16 --width-west-buf=3 --width-east-buf=3  --arch=wse3 --compile-only
# python run.appliance.py -m=720 -n=720 -k=1024 --latestlink latest --channels=16 --width-west-buf=3 --width-east-buf=3 --arch=wse3 --run-only --loop_count=5

# python run.py -m=2 -n=2 -k=2 --latestlink latest --channels=1 --width-west-buf=0 --width-east-buf=0 --run-only --arch=wse3 --loop_count=1


# cslc ./src/bw_sync_layout.csl --arch wse3 --fabric-dims=12,7 --fabric-offsets=4,1 -o=. --memcpy --channels=1 



# cs_python ./run.py -m=5 -n=5 -k=5 --latestlink out --channels=1 \
# --width-west-buf=0 --width-east-buf=0 --run-only --loop_count=1


# step 4: toc() records time_end
# step 5: prepare (time_start, time_end)
# step 6: D2H (time_start, time_end)
# step 7: prepare reference clock
# step 8: D2H reference clock
# wvlts = 134217728, loop_count = 100
# cycles_send = 417059576101 cycles
# time_send = 490658324.8247059 us
# bandwidth = 109.41848631464761 MB/S 