from cerebras.sdk.client import SdkCompiler
from cerebras.sdk.client import SdkRuntime

with SdkCompiler(resource_cpu=48000, resource_mem=64<<30) as compiler:
    artifact_id = compiler.compile(
        app_path="src",
        csl_main="bw_sync_layout.csl",
        options="--arch wse3 --fabric-dims=762,1172 --fabric-offsets=4,1 --memcpy --channels=1",
        out_path=".",
    )
    print(f"artifact_id: {artifact_id}")
    with SdkRuntime(artifact_id, simulator=False) as runner:
        pass