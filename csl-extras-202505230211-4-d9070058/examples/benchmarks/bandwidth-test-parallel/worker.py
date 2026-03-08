"""Worker subprocess for distributed bandwidth test.

Each worker owns one pipeline (H2D + D2H stream pair) and runs inside its
own multiprocessing.Process.  The master process is responsible for
load() + run() on the full program; workers only attach to the already-
running fabric via their own SdkRuntime instance with a filtered port map.
"""

import os
import numpy as np

from cerebras.sdk.runtime.sdkruntimepybind import (
    SdkCompileArtifacts,
    SdkRuntime,
    SdkTarget,
    SimfabConfig,
    get_platform,
)


def worker_main(
    rank,
    artifact_dir,
    port_map_path,
    h2d_name,
    d2h_name,
    buf_size,
    num_batches,
    cmaddr,
    arch,
    load_done_event,
    result_queue,
):
    """Entry point executed by each worker subprocess.

    Parameters
    ----------
    rank : int
        Worker index (0 .. N-1).
    artifact_dir : str
        Path to the compiled output directory.
    port_map_path : str
        Path to this worker's filtered port_map JSON.
    h2d_name : str
        Stream name for host-to-device input.
    d2h_name : str
        Stream name for device-to-host output.
    buf_size : int
        Number of f32 elements per batch.
    num_batches : int
        Number of batches to send.
    cmaddr : str or None
        IP:port for the CS system, or None for simulation.
    arch : str
        Target architecture, e.g. "wse2" or "wse3".
    load_done_event : multiprocessing.Event
        Signalled by the master after load() + run() complete.
    result_queue : multiprocessing.Queue
        Worker puts its result dict here when finished.
    """
    try:
        # Block until master has loaded and started the program.
        load_done_event.wait()

        # Debug: print artifact directory info
        abs_artifact_dir = os.path.abspath(artifact_dir)
        print(f"[Worker {rank}] CWD: {os.getcwd()}", flush=True)
        print(f"[Worker {rank}] artifact_dir arg: '{artifact_dir}'", flush=True)
        print(f"[Worker {rank}] artifact_dir abs: '{abs_artifact_dir}'", flush=True)
        print(f"[Worker {rank}] exists: {os.path.exists(abs_artifact_dir)}", flush=True)
        if os.path.exists(abs_artifact_dir):
            for root, dirs, files in os.walk(abs_artifact_dir):
                level = root.replace(abs_artifact_dir, '').count(os.sep)
                indent = '  ' * level
                print(f"[Worker {rank}]   {indent}{os.path.basename(root)}/", flush=True)
                for f in files:
                    fpath = os.path.join(root, f)
                    fsize = os.path.getsize(fpath)
                    print(f"[Worker {rank}]   {indent}  {f}  ({fsize} bytes)", flush=True)

        # Resolve target enum from arch string.
        if arch == "wse3":
            target = SdkTarget.WSE3
        else:
            target = SdkTarget.WSE2

        # Create platform handle.
        platform = get_platform(cmaddr, SimfabConfig(), target)

        # Build compile artifacts with this worker's port mapping.
        print(f"[Worker {rank}] Creating SdkCompileArtifacts('{artifact_dir}') ...", flush=True)
        artifacts = SdkCompileArtifacts(artifact_dir)
        print(f"[Worker {rank}] SdkCompileArtifacts created: {artifacts}", flush=True)

        # Check what methods/attrs are available on artifacts
        artifact_attrs = [a for a in dir(artifacts) if not a.startswith('_')]
        print(f"[Worker {rank}] Artifact attrs: {artifact_attrs}", flush=True)

        #artifacts.add_port_mapping(port_map_path)

        # Create runtime (do NOT load — master already did that).
        print(f"[Worker {rank}] Creating SdkRuntime ...", flush=True)
        runtime = SdkRuntime(artifacts, platform, memcpy_required=False)
        runtime.run()

        # Prepare send data: contiguous block unique to this rank.
        total_elems = buf_size * num_batches
        data = np.arange(
            rank * total_elems, (rank + 1) * total_elems, dtype=np.float32
        )

        # Receive buffer: 4 x f32 packed timestamps from the device.
        time_buf = np.zeros(4, dtype=np.float32)

        # Issue non-blocking send and receive.
        send_task = runtime.send(h2d_name, data, nonblock=True)
        recv_task = runtime.receive(d2h_name, time_buf, 4, nonblock=True)

        # Wait for both to complete so time_buf is populated.
        runtime.task_wait(send_task)
        runtime.task_wait(recv_task)

        # Do NOT call runtime.stop() — the master handles lifecycle.

        result_queue.put(
            {"rank": rank, "time_buf": time_buf.tolist(), "error": None}
        )

    except Exception as e:
        result_queue.put({"rank": rank, "time_buf": None, "error": str(e)})
