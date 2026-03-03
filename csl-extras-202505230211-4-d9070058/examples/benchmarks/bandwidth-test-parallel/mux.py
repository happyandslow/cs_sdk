"""
Mux helper function for bandwidth-test-parallel.

Adapted from sdklayout-05-gemv/mux.py.
CSL files are in ./src/ (relative to the working directory).
"""
from cerebras.sdk.runtime.sdkruntimepybind import (
    Edge,
    Route,
    RoutingPosition,
)


def get_mux(layout, name, batch_size, width, height):
    """
    Create a vertical (width×height) mux region.

    Each PE receives batch_size wavelets from its LEFT (from the core
    region). Data is then serialized upward: PE[0] sends its batch first,
    then PE[1], etc. The single-PE output stream is at the TOP edge.

    After forwarding its batch, each PE sends SWITCH_ADV to itself so
    subsequent batches from lower PEs can be forwarded northward.

    Returns: (mux_in_port, d2h_port, mux_region)
    """
    mux = layout.create_code_region('./src/mux.csl', name, width, height)
    mux.set_param_all('size', batch_size)

    in_color  = mux.color('in_color')
    out_color = mux.color('out_color')
    mux.set_param_all(in_color)
    mux.set_param_all(out_color)

    # Routing for out_color:
    #   pos1 (initial):   RAMP  → NORTH  (forward own data to host)
    #   pos2 (after ADV): SOUTH → NORTH  (forward lower PEs' data upward)
    core_out_route    = RoutingPosition().set_input([Route.RAMP]).set_output([Route.NORTH])
    forward_route     = RoutingPosition().set_input([Route.SOUTH]).set_output([Route.NORTH])
    mux.paint_all(out_color, [core_out_route, forward_route])

    input_routes        = RoutingPosition().set_output([Route.RAMP])
    output_routes       = RoutingPosition().set_input([Route.RAMP])
    forward_port_routes = RoutingPosition().set_input([Route.SOUTH])

    size     = batch_size * height
    in_port  = mux.create_input_port( in_color,  Edge.LEFT, [input_routes],                         size)
    out_port = mux.create_output_port(out_color, Edge.TOP,  [output_routes, forward_port_routes],   size)
    return (in_port, out_port, mux)
