"""
Accessors for `render_bokeh`, attached to the bokeh models the user returned
(`BokehModel._model`), since `BokehModel` itself has no useful traits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, List, Optional

from ._accessors import AccessorSpec, Emit
from ._comm import when_comm_open

if TYPE_CHECKING:
    from bokeh.events import Event
    from bokeh.models import ColumnDataSource
    from jupyter_bokeh import BokehModel


def attach_selected(widget: BokehModel, emit: Emit) -> Callable[[], None]:
    source = single_source(widget._model)

    # jupyter_bokeh runs property callbacks twice per browser change; the
    # accessor's input priority drops the repeat.
    def on_change(attr: str, old: object, new: List[int]) -> None:
        emit(list(new))

    source.selected.on_change("indices", on_change)
    return lambda: source.selected.remove_on_change("indices", on_change)


def event_attach(event: str) -> Callable[[BokehModel, Emit], Callable[[], None]]:
    def attach(widget: BokehModel, emit: Emit) -> Callable[[], None]:
        from bokeh.models import Plot

        # bokeh has no public way to remove an on_event callback
        active = [True]

        def on_event(e: Event) -> None:
            if active[0]:
                emit(e)

        # Registering patches the browser's document (the plot's
        # subscribed_events), so it must wait for the widget's comm.
        def register() -> None:
            for plot in widget._model.select({"type": Plot}):
                plot.on_event(event, on_event)
                # on_event only subscribes the plot to browser events when it
                # joins a document, which already happened at render.
                if plot.document is not None:
                    plot.document.callbacks.subscribe(event, plot)

        when_comm_open(widget, register)

        def detach() -> None:
            active[0] = False

        return detach

    return attach


def single_source(model: Any) -> ColumnDataSource:
    from bokeh.models import ColumnDataSource, GlyphRenderer

    sources: List[ColumnDataSource] = []
    for renderer in model.select({"type": GlyphRenderer}):
        source = renderer.data_source
        if isinstance(source, ColumnDataSource) and source not in sources:
            sources.append(source)
    if len(sources) != 1:
        raise TypeError(
            "`selected()` and `selected_rows()` need a plot with exactly one "
            f"ColumnDataSource, but this one has {len(sources)}. Observe a "
            'source\'s selection with `source.selected.on_change("indices", ...)` '
            "instead."
        )
    return sources[0]


def selected_frame(widget: BokehModel, indices: Optional[List[int]]) -> Any:
    df = single_source(widget._model).to_df()
    return df.iloc[indices or []]


SELECTED = AccessorSpec(
    name="selected",
    kind="event",
    attach=attach_selected,
    rate_policy="debounce",
)
TAPPED = AccessorSpec(name="tapped", kind="event", attach=event_attach("tap"))
ZOOMED = AccessorSpec(name="zoomed", kind="event", attach=event_attach("rangesupdate"))

BOKEH_ACCESSORS = (SELECTED, TAPPED, ZOOMED)
