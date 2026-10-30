"""
Accessors for `render_ipyleaflet` and `render_leafmap` (whose ipyleaflet
backend is an `ipyleaflet.Map`). Coordinates are `[lat, lng]`, as ipyleaflet
reports them; lonboard is `(lng, lat)`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, List, Optional

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    import ipyleaflet


def check_ipyleaflet(widget: Any, accessor: str) -> "ipyleaflet.Map":
    # render_leafmap shares these accessors, but only its ipyleaflet backend
    # is an ipyleaflet.Map
    import ipyleaflet

    if not isinstance(widget, ipyleaflet.Map):
        raise TypeError(
            f"`.{accessor}()` requires an ipyleaflet map, but the rendered "
            f"widget is a {type(widget).__name__} (leafmap's {type(widget).__module__} "
            "backend). Read its state with `reactive_read()` instead (see the "
            "renderer for that backend, e.g. `render_maplibre`)."
        )
    return widget


def attach_trait(
    trait: str, accessor: str
) -> Callable[[Any, Emit], Callable[[], None]]:
    """Observe a synced trait, seeding its current value (state accessors)."""

    def attach(widget: Any, emit: Emit) -> Callable[[], None]:
        m = check_ipyleaflet(widget, accessor)

        def on_change(change: Any) -> None:
            emit(change["new"])

        m.observe(on_change, trait)
        emit(getattr(m, trait))
        return lambda: m.unobserve(on_change, trait)

    return attach


def attach_clicked(widget: Any, emit: Emit) -> Callable[[], None]:
    m = check_ipyleaflet(widget, "clicked")

    def on_interaction(**kwargs: Any) -> None:
        # Also arrives for mousemove, dblclick, etc.; a double-click is two
        # clicks plus a dblclick
        if kwargs.get("type") == "click":
            emit(kwargs)

    m.on_interaction(on_interaction)
    return lambda: m.on_interaction(on_interaction, remove=True)


# Emitted by attach_drawn_features when the map has no DrawControl. Attach
# runs during render (Accessors.on_render), so it must never raise -- the
# drawn_features() method raises for this raw value at read time instead.
NO_DRAW_CONTROL = object()

NO_DRAW_CONTROL_MESSAGE = (
    "`drawn_features()` needs an ipyleaflet.DrawControl on the "
    "map (leafmap adds one by default). Add one, e.g. "
    "`m.add(DrawControl())`."
)


def attach_drawn_features(widget: Any, emit: Emit) -> Callable[[], None]:
    m = check_ipyleaflet(widget, "drawn_features")
    detach_control: List[Optional[Callable[[], None]]] = [None]

    def attach_control() -> None:
        control = draw_control_of(m)
        if control is None:
            emit(NO_DRAW_CONTROL)
            return

        def on_change(change: Any) -> None:
            emit(change["new"])

        control.observe(on_change, "data")
        emit(control.data)
        detach_control[0] = lambda: control.unobserve(on_change, "data")

    def on_controls(change: Any) -> None:
        # The DrawControl can be added or replaced after the first read
        if detach_control[0] is not None:
            detach_control[0]()
            detach_control[0] = None
        attach_control()

    attach_control()
    m.observe(on_controls, "controls")

    def detach() -> None:
        m.unobserve(on_controls, "controls")
        if detach_control[0] is not None:
            detach_control[0]()

    return detach


def draw_control_of(m: "ipyleaflet.Map") -> Optional["ipyleaflet.DrawControl"]:
    import ipyleaflet

    for control in m.controls:
        if isinstance(control, ipyleaflet.DrawControl):
            return control
    return None


BOUNDS = AccessorSpec(
    name="bounds",
    kind="state",
    attach=attach_trait("bounds", "bounds"),
    # () until the browser first reports the viewport
    not_ready=lambda raw: raw == (),
)
ZOOM = AccessorSpec(name="zoom", kind="state", attach=attach_trait("zoom", "zoom"))
CENTER = AccessorSpec(
    name="center", kind="state", attach=attach_trait("center", "center")
)
CLICKED = AccessorSpec(name="clicked", kind="event", attach=attach_clicked)
DRAWN_FEATURES = AccessorSpec(
    name="drawn_features", kind="state", attach=attach_drawn_features
)

IPYLEAFLET_ACCESSORS = (BOUNDS, ZOOM, CENTER, CLICKED, DRAWN_FEATURES)
