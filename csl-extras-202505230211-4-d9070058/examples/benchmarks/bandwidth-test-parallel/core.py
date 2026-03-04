"""
Loopback core helper for bandwidth-test-parallel.

Creates a width×height code region that:
  - Receives pe_length f32 wavelets per PE from the LEFT (from demux)
  - Stores them in a local buffer
  - Sends them back to the RIGHT (to mux)
"""
from cerebras.sdk.runtime.sdkruntimepybind import (
    Edge,
    Route,
    RoutingPosition,
)


def get_loopback_core(layout, name, pe_length, width, height):
    """
    Create a width×height loopback core region.

    Each PE buffers pe_length f32 wavelets received on in_color (from the
    WEST / demux) and echoes them on out_color (to the EAST / mux).

    Returns: (core_in_port, core_out_port, core_region)
    """
    core = layout.create_code_region('./src/bw_loopback_kernel.csl', name, width, height)
    core.set_param_all('pe_length', pe_length)

    in_color  = core.color('in_color')
    out_color = core.color('out_color')
    core.set_param_all(in_color)
    core.set_param_all(out_color)

    # in_color: data arrives from WEST (from demux RIGHT edge) → goes to RAMP (local PE).
    core.paint_all(in_color,
                   [RoutingPosition().set_input([Route.WEST]).set_output([Route.RAMP])])

    # out_color: data from RAMP (local PE) → exits EAST (to mux LEFT edge).
    core.paint_all(out_color,
                   [RoutingPosition().set_input([Route.RAMP]).set_output([Route.EAST])])

    total    = pe_length * width * height
    in_port  = core.create_input_port( in_color,  Edge.LEFT,  [RoutingPosition().set_output([Route.RAMP])], total)
    out_port = core.create_output_port(out_color, Edge.RIGHT, [RoutingPosition().set_input([Route.RAMP])],  total)
    return (in_port, out_port, core)
