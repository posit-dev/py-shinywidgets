"""
Accessors for `render_lonboard`, backed by the map's traits (`view_state`,
`selected_bounds`), its click handler registry, and each layer's
`selected_index` trait.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    from lonboard import Map as LonboardMap  # pyright: ignore[reportMissingImports]


def attach_view_state(widget: LonboardMap, emit: Emit) -> Callable[[], None]:
    def on_change(change: Any) -> None:
        emit(change["new"])

    widget.observe(on_change, "view_state")
    emit(widget.view_state)  # computed from the layers at construction
    return lambda: widget.unobserve(on_change, "view_state")


def attach_selected_bounds(widget: LonboardMap, emit: Emit) -> Callable[[], None]:
    def on_change(change: Any) -> None:
        emit(change["new"])

    widget.observe(on_change, "selected_bounds")
    emit(widget.selected_bounds)  # None until the first bbox selection
    return lambda: widget.unobserve(on_change, "selected_bounds")


def attach_clicked(widget: LonboardMap, emit: Emit) -> Callable[[], None]:
    # Registering flips _has_click_handlers, which is what makes the browser
    # send click messages at all. This is why the spec must attach lazily
    # (on first read), never eagerly: users who never read clicked() must
    # see no change.
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
SELECTED_INDEX = AccessorSpec(
    name="selected_index", kind="event", attach=attach_selected_index
)
SELECTED_BOUNDS = AccessorSpec(
    name="selected_bounds", kind="state", attach=attach_selected_bounds
)
CLICKED = AccessorSpec(name="clicked", kind="event", attach=attach_clicked)

LONBOARD_ACCESSORS = (VIEW_STATE, SELECTED_INDEX, SELECTED_BOUNDS, CLICKED)
