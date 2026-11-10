"""
Accessors for `render_bokeh`, attached to the bokeh models the user returned
(`BokehModel._model`), since `BokehModel` itself has no useful traits.

A selection is state, not just an event: jupyter_bokeh mirrors every
browser-side model change onto the Python-side document, so
`source.selected.indices` holds the current selection at any moment.
`attach_selected` therefore seeds it at attach (no comm wait needed, unlike
`event_attach`, whose `on_event` registration patches the browser document),
which lets `selected()` be a state accessor that attaches at render -- a
selection made before the first read isn't lost.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, List, Optional, cast

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
    # A selection is retained on the Python-side document (see the module
    # docstring), so seed the accessor with the current one: a selection made
    # before this attach -- e.g. before the first read -- is not lost. An
    # empty selection seeds as [] (there is no "nothing selected yet" value).
    emit(list(source.selected.indices))
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


def attach_zoomed(widget: BokehModel, emit: Emit) -> Callable[[], None]:
    detach = event_attach("rangesupdate")(widget, emit)

    # Ranges are retained, browser-synced document properties, so a zoom made
    # before this attach is recoverable. Seed one event per Plot in document
    # order: the reader sees the last, as with live events in sequence.
    # FactorRange start/end are numeric synthetic coords, matching live
    # payloads; DatetimeRange values are ms-since-epoch floats in both.
    from bokeh.events import RangesUpdate
    from bokeh.models import Plot
    from bokeh.models.ranges import DataRange1d, FactorRange, Range1d

    numeric = (Range1d, DataRange1d, FactorRange)
    for model in widget._model.select({"type": Plot}):
        if not isinstance(model, Plot):
            continue
        x, y = model.x_range, model.y_range
        if isinstance(x, numeric) and isinstance(y, numeric):
            # bokeh's stubs type range start/end as the `Value` descriptor;
            # at runtime they're floats (or None before the first compute)
            emit(
                RangesUpdate(
                    model,
                    x0=cast("Optional[float]", x.start),
                    x1=cast("Optional[float]", x.end),
                    y0=cast("Optional[float]", y.start),
                    y1=cast("Optional[float]", y.end),
                )
            )
    return detach


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


def attach_source_data(widget: BokehModel, emit: Emit) -> Callable[[], None]:
    source = single_source(widget._model)
    version = [0]

    def on_change(attr: str, old: object, new: object) -> None:
        version[0] += 1
        emit(version[0])

    source.on_change("data", on_change)
    return lambda: source.remove_on_change("data", on_change)


def selected_frame(widget: BokehModel, indices: Optional[List[int]]) -> Any:
    df = single_source(widget._model).to_df()
    # After `source.data` shrinks in place, the browser prunes the selection,
    # but the pruned indices arrive later (debounced)
    return df.iloc[[i for i in indices or [] if i < len(df)]]


SELECTED = AccessorSpec(
    name="selected",
    kind="state",
    attach=attach_selected,
    rate_policy="debounce",
)
# Changes whenever `source.data` does. selected_rows() reads it, since data
# replaced in place (at the same length) keeps the selected indices.
SOURCE_DATA = AccessorSpec(name="source_data", kind="event", attach=attach_source_data)
TAPPED = AccessorSpec(name="tapped", kind="state", attach=event_attach("tap"))
ZOOMED = AccessorSpec(name="zoomed", kind="state", attach=attach_zoomed)

BOKEH_ACCESSORS = (SELECTED, SOURCE_DATA, TAPPED, ZOOMED)
