import json
import os

from cerebras.sdk.client import SdkLauncher

# read the compile artifact_path from the json file
artifact_path = ""
with open("artifact_path.json", "r", encoding="utf8") as f:
    data = json.load(f)
    artifact_path = data["artifact_path"]


# artifact_path contains the path to the compiled artifact.
# It will be transferred and extracted in the appliance.
# The extracted directory will be the working directory.
# Set simulator=False if running on CS system within appliance.
# Disable version check to ignore appliance client and server version differences.
with SdkLauncher(artifact_path, simulator=False, disable_version_check=True) as launcher:

    # Transfer an additional file to the appliance,
    # then write contents to stdout on appliance
    launcher.stage("run.py")
    launcher.stage("bw_cmd_parser.py")
    response = launcher.run(
        "echo \"ABOUT TO RUN IN THE APPLIANCE\"",
        # "cat additional_artifact.txt",
    )
    print("Test response: ", response)

    # Run the original host code as-is on the appliance,
    # using the same cmd as when using the Singularity container
    #response = launcher.run("cs_python run.py --name out --cmaddr %CMADDR%")
    response = launcher.run("cs_python run.py -m=5 -n=5 -k=5 --latestlink latest --channels=1 --width-west-buf=0 --width-east-buf=0 --d2h --arch=wse3 --run-only --loop_count=1 ")
    print("Host code execution response: ", response)
    
    # # cs_python ./run.py -m=5 -n=5 -k=5 --latestlink out --channels=1 --width-west-buf=0 --width-east-buf=0 --run-only --loop_count=1

    # Fetch files from the appliance
    launcher.download_artifact("sim.log", "./output_dir/sim.log")