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

if TYPE_CHECKING:
    from bokeh.events import Event
    from bokeh.models import ColumnDataSource, Selection
    from jupyter_bokeh import BokehModel


# The Selection properties that report what a hit test found. `indices`
# covers point glyphs and (as line keys) MultiLine taps; `line_indices` is
# all a Line tap writes; `multiline_indices` never carries a line `indices`
# doesn't, but a bokehjs path that wrote it alone would be missed otherwise.
SELECTION_ATTRS = ("indices", "line_indices", "multiline_indices")


def attach_selected(widget: BokehModel, emit: Emit) -> Callable[[], None]:
    source = single_source(widget._model)

    # jupyter_bokeh runs property callbacks twice per browser change; the
    # accessor's input priority drops the repeat.
    def on_change(attr: str, old: object, new: object) -> None:
        emit(selected_indices(source.selected))

    for attr in SELECTION_ATTRS:
        source.selected.on_change(attr, on_change)
    # A selection is retained on the Python-side document (see the module
    # docstring), so seed the accessor with the current one: a selection made
    # before this attach -- e.g. before the first read -- is not lost. An
    # empty selection seeds as [] (there is no "nothing selected yet" value).
    emit(selected_indices(source.selected))

    def detach() -> None:
        for attr in SELECTION_ATTRS:
            source.selected.remove_on_change(attr, on_change)

    return detach


def selected_indices(selection: Selection) -> List[int]:
    # A Line tap reports the hit segment in line_indices; a Line's source has
    # one row per point, so the segment's position is the row of its first
    # point. A MultiLine tap reports its lines in both indices and
    # multiline_indices' keys, so dedup (order-preserving) to count each
    # once. Caveat: bokehjs remaps indices to full-source positions under a
    # CDSView filter but not line_indices, which stay view-space.
    return list(
        dict.fromkeys(
            [
                *selection.indices,
                *selection.line_indices,
                *selection.multiline_indices.keys(),
            ]
        )
    )


def event_attach(event: str) -> Callable[[BokehModel, Emit], Callable[[], None]]:
    def attach(widget: BokehModel, emit: Emit) -> Callable[[], None]:
        from bokeh.models import Plot

        active = [True]

        def on_event(e: Event) -> None:
            if active[0]:
                emit(e)

        # A list, since detach walks it again and a layout's select() returns
        # a one-shot generator (a figure's returns a list)
        plots = list(widget._model.select({"type": Plot}))
        for plot in plots:
            plot.on_event(event, on_event)
            # on_event only subscribes the plot to browser events when it
            # joins a document, which already happened at render.
            if plot.document is not None:
                plot.document.callbacks.subscribe(event, plot)

        def detach() -> None:
            active[0] = False
            for plot in plots:
                # bokeh has no public way to remove an on_event callback, so
                # drop it from bokeh's private registry; if that ever goes
                # away, the flag above still mutes the callback. Replace the
                # list rather than mutate it: a detach during dispatch would
                # otherwise make bokeh's loop over it skip the next callback.
                callbacks = getattr(plot, "_event_callbacks", None)
                if callbacks is not None:
                    callbacks[event] = [
                        cb for cb in callbacks[event] if cb is not on_event
                    ]

        return detach

    return attach


def attach_zoomed(widget: BokehModel, emit: Emit) -> Callable[[], None]:
    detach = event_attach("rangesupdate")(widget, emit)

    # Ranges are retained, browser-synced document properties, so a zoom made
    # before this attach is recoverable. Seed one event per Plot in document
    # order: the reader sees the last, as with live events in sequence. Only
    # seed ranges with real values at attach: a DataRange1d defaults to NaN
    # (its span is computed browser-side), and a FactorRange's synthetic
    # coords are likewise only known after the browser computes them.
    from bokeh.events import RangesUpdate
    from bokeh.models import Plot
    from bokeh.models.ranges import DataRange1d, Range1d

    numeric = (Range1d, DataRange1d)
    for model in widget._model.select({"type": Plot}):
        if not isinstance(model, Plot):
            continue
        x, y = model.x_range, model.y_range
        if not (isinstance(x, numeric) and isinstance(y, numeric)):
            continue
        # bokeh's stubs type range start/end as the `Value` descriptor; at
        # runtime they're floats (or None/NaN before the first compute, or
        # datetimes on a datetime axis -- converted to the ms floats the
        # browser's live RangesUpdate events report)
        values = (
            cast("Optional[float]", browser_ms(x.start)),
            cast("Optional[float]", browser_ms(x.end)),
            cast("Optional[float]", browser_ms(y.start)),
            cast("Optional[float]", browser_ms(y.end)),
        )
        if all(v is not None and v == v for v in values):
            emit(
                RangesUpdate(
                    model, x0=values[0], x1=values[1], y0=values[2], y1=values[3]
                )
            )
    return detach


def browser_ms(value: object) -> object:
    # The browser reports RangesUpdate coordinates as floats (ms since
    # epoch); a datetime axis holds datetimes/timedeltas Python-side, which
    # bokeh's converter turns into the same floats (it raises on numbers)
    from bokeh.util.serialization import convert_datetime_type

    try:
        return convert_datetime_type(value)
    except ValueError:
        return value


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
