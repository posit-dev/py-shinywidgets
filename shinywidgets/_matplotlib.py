"""
Accessors for `render_matplotlib` and `render_plotnine`, attached to the
ipympl `Canvas` both renderers coerce to.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List, Tuple

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    from ipympl.backend_nbagg import Canvas
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import MouseEvent
    from matplotlib.figure import Figure

# ((x0, x1), (y0, y1)) per axes, in `figure.axes` order
AxesLimits = Tuple[Tuple[Tuple[float, float], Tuple[float, float]], ...]


def attach_clicked(canvas: Canvas, emit: Emit) -> Callable[[], None]:
    def on_press(event: MouseEvent) -> None:
        # A press that starts a toolbar pan/zoom drag, or lands outside any
        # axes, isn't a click on the data. (A rendered canvas always has a
        # toolbar; the None check only covers bare canvases in tests.)
        toolbar = canvas.toolbar
        if event.inaxes is None or (toolbar is not None and toolbar.mode):
            return
        emit(event)

    cid = canvas.mpl_connect("button_press_event", on_press)
    # Handlers live on the canvas, so a cached Figure rendered twice would
    # stack them (emitting twice per click) without a real disconnect here
    return lambda: canvas.mpl_disconnect(cid)


def attach_picked(canvas: Canvas, emit: Emit) -> Callable[[], None]:
    cid = canvas.mpl_connect("pick_event", emit)
    return lambda: canvas.mpl_disconnect(cid)


def attach_limits(canvas: Canvas, emit: Emit) -> Callable[[], None]:
    figure = canvas.figure

    def on_limits_changed(ax: Axes) -> None:
        emit(axes_limits(figure))

    # Read the seed before connecting: on a not-yet-drawn figure, get_xlim()
    # autoscales the (stale) view limits, which fires these very signals, and
    # the handlers must not see the intermediate states as emissions
    seed = axes_limits(figure)
    # cids are unique per axes' CallbackRegistry, so keep the (axes, cid) pair
    connections: List[Tuple[Axes, int]] = []
    for ax in figure.axes:
        for signal in ("xlim_changed", "ylim_changed"):
            cid = ax.callbacks.connect(signal, on_limits_changed)
            connections.append((ax, cid))
    # Seed with the current limits, so readers see the rendered state
    emit(seed)

    def detach() -> None:
        for ax, cid in connections:
            ax.callbacks.disconnect(cid)

    return detach


def axes_limits(figure: Figure) -> AxesLimits:
    limits: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
    for ax in figure.axes:
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        limits.append(((x0, x1), (y0, y1)))
    return tuple(limits)


CLICKED = AccessorSpec(name="clicked", kind="event", attach=attach_clicked)
PICKED = AccessorSpec(name="picked", kind="event", attach=attach_picked)
LIMITS = AccessorSpec(
    name="limits", kind="state", attach=attach_limits, rate_policy="debounce"
)

MATPLOTLIB_ACCESSORS = (CLICKED, PICKED, LIMITS)
