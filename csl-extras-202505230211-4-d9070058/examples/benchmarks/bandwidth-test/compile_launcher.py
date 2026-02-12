import json
from cerebras.sdk.client import SdkCompiler

# Instantiate copmiler using a context manager
# Disable version check to ignore appliance client and server version differences.
with SdkCompiler(disable_version_check=True) as compiler:

    # Launch compile job
    # artifact_path = compiler.compile(
    #     ".",
    #     "layout.csl",
    #     "--fabric-dims=8,3 --fabric-offsets=4,1 --memcpy --channels=1 -o out",
    #     "."
    # )
    # artifact_path = compiler.compile(
    #     "./src",
    #     "bw_sync_layout.csl",
    #     "--arch wse3 --fabric-dims=762,1172 --fabric-offsets=5,2 --params=width:720,height:720,pe_length:512 --params=C0_ID:0 --params=C1_ID:1 --params=C2_ID:2 --params=C3_ID:3 --params=C4_ID:4 -o=latest --memcpy --channels=16 --width-west-buf=1 --width-east-buf=1",
    #     "."
    # )
    artifact_path = compiler.compile(
        "./src",
        "bw_sync_layout.csl",
        "--arch wse3 --fabric-dims=762,1172 --fabric-offsets=5,2 --params=width:5,height:5,pe_length:5 --params=C0_ID:0 --params=C1_ID:1 --params=C2_ID:2 --params=C3_ID:3 --params=C4_ID:4 -o=latest --memcpy --channels=1 --width-west-buf=0 --width-east-buf=0",
        "."
    )

    # Write the artifact_path to a JSON file
    with open("artifact_path.json", "w", encoding="utf8") as f:
        json.dump({"artifact_path": artifact_path,}, f)
        
        
        
# cslc ./src/bw_sync_layout.csl --arch wse3 --fabric-dims=762,1172 --fabric-offsets=5,2 \
# --params=width:720,height:720,pe_length:512 --params=C0_ID:0 \
# --params=C1_ID:1 --params=C2_ID:2 --params=C3_ID:3 --params=C4_ID:4 -o=out \
# --memcpy --channels=16 --width-west-buf=1 --width-east-buf=1