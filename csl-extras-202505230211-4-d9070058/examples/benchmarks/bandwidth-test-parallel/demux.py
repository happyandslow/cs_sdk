"""
Demux helper functions for bandwidth-test-parallel.

Adapted from sdklayout-05-gemv/demux.py.
CSL files are in ./src/ (relative to the working directory).
"""
from cerebras.sdk.runtime.sdkruntimepybind import (
    Edge,
    Route,
    RoutingPosition,
    get_edge_routing,
)


def get_demux_adaptor(layout, name, batch_size, num_batches):
    """
    Create a 1×1 demux-adaptor region.

    Forwards data from the host (Edge.LEFT input stream) to the demux
    (Edge.RIGHT output port), injecting a SWITCH_ADV control wavelet
    after every batch_size wavelets so the downstream demux distributes
    data across num_batches PEs.

    Returns: (h2d_port, adaptor_out_port, adaptor_region)
    """
    adaptor = layout.create_code_region('./src/demux_adaptor.csl', name, 1, 1)
    adaptor.set_param_all('batch_size', batch_size)
    adaptor.set_param_all('num_batches', num_batches)

    in_color  = adaptor.color('in_color')
    out_color = adaptor.color('out_color')
    adaptor.set_param_all(in_color)
    adaptor.set_param_all(out_color)

    input_routes  = RoutingPosition().set_output([Route.RAMP])
    output_routes = RoutingPosition().set_input([Route.RAMP])

    size = batch_size * num_batches
    in_port  = adaptor.create_input_port( in_color,  Edge.LEFT,  [input_routes],  size)
    out_port = adaptor.create_output_port(out_color, Edge.RIGHT, [output_routes], size)
    return (in_port, out_port, adaptor)


def get_b_demux(layout, name, batch_size, width, height):
    """
    Create a vertical (width×height) demux region.

    Data enters from the TOP and is distributed southward: the first
    batch_size wavelets go to PE[0], the next batch_size to PE[1], etc.
    Each PE emits its batch_size wavelets through its RIGHT edge.

    No sentinel / control signal is emitted after the last batch.

    Returns: (demux_in_port, demux_out_port, demux_region)
    """
    demux = layout.create_code_region('./src/demux.csl', name, width, height)
    demux.set_param_all('size', batch_size)
    demux.set_param_all('has_sentinel', 0)
    demux.set_param_all('entry_point', 0)

    in_color  = demux.color('in_color')
    out_color = demux.color('out_color')
    demux.set_param_all(in_color)
    demux.set_param_all(out_color)

    # Routing for in_color:
    #   pos1 (initial):  NORTH → RAMP  (deliver to this PE)
    #   pos2 (after ADV): NORTH → SOUTH (forward to next PE)
    # Edge override: bottom PE is always at pos1 (last batch, no forwarding needed).
    core_out_route = RoutingPosition().set_input([Route.NORTH]).set_output([Route.RAMP])
    forward_route  = RoutingPosition().set_input([Route.NORTH]).set_output([Route.SOUTH])
    edge_route     = get_edge_routing(Edge.BOTTOM, [core_out_route])
    demux.paint_all(in_color, [core_out_route, forward_route], [edge_route])

    input_routes  = RoutingPosition().set_output([Route.RAMP])
    output_routes = RoutingPosition().set_input([Route.RAMP])

    size = batch_size * width * height
    blah     = RoutingPosition().set_output([Route.SOUTH])
    in_port  = demux.create_input_port( in_color,  Edge.TOP,   [input_routes, blah], size)
    out_port = demux.create_output_port(out_color, Edge.RIGHT, [output_routes],       size)
    return (in_port, out_port, demux)
