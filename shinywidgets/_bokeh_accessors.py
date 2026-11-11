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

import weakref
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, cast

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    from bokeh.events import Event
    from bokeh.models import ColumnDataSource, Plot
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

        # bokeh's stubs type select() as list[Model] even when filtered
        plots = cast("List[Plot]", widget._model.select({"type": Plot}))
        fans = [_event_fan_for(plot, event) for plot in plots]
        for fan in fans:
            fan.append(emit)

        detached = False

        def detach() -> None:
            nonlocal detached
            # Idempotent, so a stale handle can't remove a later attachment
            # of the same emit
            if detached:
                return
            detached = True
            for fan in fans:
                # Identity, not equality: another attachment of an equal
                # emit must not be removed
                for i, r in enumerate(fan):
                    if r is emit:
                        del fan[i]
                        break

        return detach

    return attach


# bokeh's on_event() only appends callbacks and has no public removal API, so
# each (plot, event) pair gets one permanent callback that fans out to the
# currently attached emits; detach removes its emit from the list instead of
# leaving a muted closure on the plot. The registry only finds a plot's
# fan-out state again at the next attach, so it references it weakly: the
# state is owned by the plot itself (through the callbacks it holds), whose
# emits capture the renderer, which owns the widget and its plot -- a strong
# reference here would keep plots alive after everything else has dropped
# them.
_EVENT_FANS: weakref.WeakKeyDictionary[Plot, "weakref.ReferenceType[_Fans]"] = (
    weakref.WeakKeyDictionary()
)


class _Fans(Dict[str, List[Emit]]):
    # A plain dict can't be weakly referenced, and _EVENT_FANS references
    # this weakly (see above)
    pass


def _event_fan_for(plot: Plot, event: str) -> List[Emit]:
    fans_ref = _EVENT_FANS.get(plot)
    fans = fans_ref() if fans_ref is not None else None
    if fans is None:
        fans = _Fans()
        _EVENT_FANS[plot] = weakref.ref(fans)
    if event in fans:
        return fans[event]
    emits: List[Emit] = []

    def on_event(
        e: Event, emits: List[Emit] = emits, _owns_fans: object = fans
    ) -> None:
        # Iterate a snapshot but check liveness before each delivery: an
        # emit may detach (mutating `emits`) mid-dispatch, and a detached
        # emit must not be called. Identity (not equality) keeps a later
        # attachment of an equal emit live.
        for emit in list(emits):
            if any(r is emit for r in emits):
                emit(e)

    plot.on_event(event, on_event)
    # on_event only subscribes the plot to browser events when it joins a
    # document, which already happened at render.
    if plot.document is not None:
        plot.document.callbacks.subscribe(event, plot)
    fans[event] = emits
    return emits


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
