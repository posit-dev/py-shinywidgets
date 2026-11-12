"""
Accessors for `render_lonboard`, backed by the map's traits (`view_state`,
`selected_bounds`), its click handler registry, and each layer's
`selected_index` trait.

A pick is state, not just an event: lonboard retains it on the layer's
`selected_index` trait (the frontend sets it on click and pushes it with
`save_changes()`), so `attach_selected_index` seeds the accessor from the
layers' retained picks. That lets `selected()` be a state accessor
that attaches at render, so a pick made before its first read isn't lost.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable

from ._accessors import AccessorSpec, Emit, has_current_context

if TYPE_CHECKING:
    import geopandas
    from lonboard import Map as LonboardMap  # pyright: ignore[reportMissingImports]


def attach_view_state(widget: LonboardMap, emit: Emit) -> Callable[[], None]:
    def on_change(change: Any) -> None:
        emit(change["new"])

    widget.observe(on_change, "view_state")
    emit(widget.view_state)  # computed from the layers at construction
    return lambda: widget.unobserve(on_change, "view_state")


def pick_frame(
    widget: LonboardMap, positions: Iterable[int]
) -> "geopandas.GeoDataFrame":
    """
    The rows at `positions` of the frame a pick indexes into, for
    `selected_rows()`'s `df` default: those rows of the data table of the
    map's one pickable layer, sliced in Arrow and converted with
    `geopandas.GeoDataFrame.from_arrow` (slicing first keeps a pick on a
    large layer from converting rows nobody asked for; the result gets a
    fresh RangeIndex). A layer counts as pickable when it has the
    `selected_index` trait (which every lonboard layer has, data-backed or
    not) and `pickable=True` -- a non-pickable layer can't supply a pick, so
    it doesn't make the pick's origin ambiguous; a map whose pick could
    come from several pickable layers raises, since the pick has no layer
    identity. In a reactive context, reading also takes a dependency on the
    map's layers and the layer's table, so an in-place table replacement on
    a long-lived map re-reads the picked row.
    """
    layers = [
        layer
        for layer in widget.layers
        if layer.has_trait("selected_index") and getattr(layer, "pickable", True)
    ]
    if has_current_context():
        # Local import: ._shinywidgets imports ._render_widget, which
        # imports this module
        from ._shinywidgets import reactive_read

        reactive_read(widget, "layers")
    if len(layers) != 1:
        raise ValueError(
            f"`selected_rows()` can't default `df`: the map has {len(layers)} "
            "pickable layers and a pick doesn't say which layer it's from. "
            "Pass `df=` (the frame of the layer you mean), or read each "
            'layer\'s pick yourself with `reactive_read(layer, "selected_index")`.'
        )
    if has_current_context() and layers[0].has_trait("table"):
        from ._shinywidgets import reactive_read

        reactive_read(layers[0], "table")
    table = getattr(layers[0], "table", None)
    if table is None:
        raise TypeError(
            "`selected_rows()` can't default `df`: the map's pickable layer "
            "has no data table (e.g. a BitmapLayer). Pass `df=` explicitly."
        )
    try:
        import geopandas as gpd
        import pyarrow as pa
    except ImportError:
        raise ImportError(
            "`selected_rows()` without `df` reconstructs the layer's data "
            "frame with geopandas, which isn't installed "
            "(pip install geopandas). Or pass `df=` explicitly."
        ) from None
    idx = [int(p) for p in positions]
    pt = pa.table(table)
    if not idx and pt.num_rows:
        # from_arrow() can't convert an empty interleaved-geometry array (a
        # numpy reshape bug in geopandas), so build the empty frame by
        # converting one row and dropping it
        return gpd.GeoDataFrame.from_arrow(pt.slice(0, 1)).iloc[0:0]
    return gpd.GeoDataFrame.from_arrow(pt.take(pa.array(idx, type=pa.int64())))


def attach_selected_bounds(widget: LonboardMap, emit: Emit) -> Callable[[], None]:
    def on_change(change: Any) -> None:
        emit(change["new"])

    widget.observe(on_change, "selected_bounds")
    emit(widget.selected_bounds)  # None until the first bbox selection
    return lambda: widget.unobserve(on_change, "selected_bounds")


def attach_clicked(widget: LonboardMap, emit: Emit) -> Callable[[], None]:
    # Registering flips _has_click_handlers, which is what makes the browser
    # send click messages at all. That's the only effect: the map's picking,
    # selection, and cursor are driven by an onClick deck.gl always gets, so
    # subscribing changes nothing the user can see, and the per-click payload
    # is just a (lng, lat) pair -- no reason to gate it behind an opt-in.
    widget.on_click(emit)  # the callback receives the (lng, lat) tuple
    return lambda: widget.on_click(emit, remove=True)


def attach_selected_index(widget: LonboardMap, emit: Emit) -> Callable[[], None]:
    detaches: Dict[str, Callable[[], None]] = {}

    def attach_layer(layer: Any) -> None:
        if layer.model_id in detaches or not layer.has_trait("selected_index"):
            return

        def on_change(change: Any) -> None:
            if change["new"] is not None:
                emit(change["new"])

        layer.observe(on_change, "selected_index")
        detaches[layer.model_id] = lambda: layer.unobserve(on_change, "selected_index")

    def on_layers(change: Any) -> None:
        # Map.add_layer() replaces the layers tuple
        old = {layer.model_id for layer in change["old"]}
        new = {layer.model_id for layer in change["new"]}
        for model_id in old - new:
            detaches.pop(model_id, lambda: None)()
        for layer in change["new"]:
            attach_layer(layer)

    for layer in widget.layers:
        attach_layer(layer)
    widget.observe(on_layers, "layers")

    # Seed from the pick each layer retains on its `selected_index` trait.
    # With picks on several layers there is no timestamp to order them, so
    # the seed is a pick only when exactly one layer holds one; otherwise
    # it's None (a fresh map has no pick, and an ambiguous one can't be
    # attributed).
    picks = [
        layer.selected_index
        for layer in widget.layers
        if layer.has_trait("selected_index") and layer.selected_index is not None
    ]
    emit(picks[0] if len(picks) == 1 else None)

    def detach() -> None:
        widget.unobserve(on_layers, "layers")
        for d in detaches.values():
            d()
        detaches.clear()

    return detach


# The browser syncs `view_state` on every deck.gl `onViewStateChange` (each
# animation frame of a pan or zoom), so the accessor debounces by default
VIEW_STATE = AccessorSpec(
    name="view_state",
    kind="state",
    attach=attach_view_state,
    rate_policy="debounce",
)
SELECTED = AccessorSpec(name="selected", kind="state", attach=attach_selected_index)
SELECTED_BOUNDS = AccessorSpec(
    name="selected_bounds", kind="state", attach=attach_selected_bounds
)
CLICKED = AccessorSpec(name="clicked", kind="state", attach=attach_clicked)

LONBOARD_ACCESSORS = (VIEW_STATE, SELECTED, SELECTED_BOUNDS, CLICKED)
