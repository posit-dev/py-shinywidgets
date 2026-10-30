"""
Accessors for `render_plotly`, backed by shinywidgets' plotly event bridge.

plotly.py's widget forwards only some plotly.js events (no `plotly_selecting`
or `plotly_doubleclick`) and drops `customdata`, so the bridge in
`js/src/plotly.ts` listens to plotly.js directly. An accessor's attach asks the
browser to forward the events it needs (`{"shinywidgets": "bind"}`); the
browser then sends each one as a custom message (`{"shinywidgets": "event"}`)
with a payload shaped like R plotly's `event_data()`.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Sequence, cast

from ._accessors import AccessorSpec, Emit
from ._comm import when_comm_open

if TYPE_CHECKING:
    import pandas as pd
    from narwhals.typing import IntoDataFrameT

Point = Dict[str, Any]

# Events that clear an accessor (as in R plotly's eventClearMap).
DESELECT = "plotly_deselect"
DOUBLECLICK = "plotly_doubleclick"

# Returned by a shape function for messages that shouldn't reach the accessor.
SKIP = object()

# The relayout keys `relayout()` reports. Others (autosize on every render,
# dragmode on modebar clicks, selections on every box select) aren't viewport
# changes.
AXIS_RANGE_KEY = re.compile(r"^[xy]axis\d*\.(range|autorange)")


def points_frame(points: List[Point]) -> "pd.DataFrame":
    try:
        import pandas as pd
    except ImportError as e:  # plotly itself doesn't need pandas
        raise ImportError(
            "Reading plotly points as a DataFrame requires pandas "
            "(`pip install 'shinywidgets[plotly]'`)."
        ) from e

    columns = ["trace_index", "point_index", "x", "y"]
    for optional in ("z", "customdata"):
        if any(optional in p for p in points):
            columns.append(optional)
    return pd.DataFrame(points, columns=columns)


def select_rows(
    points: Optional[List[Point]], df: IntoDataFrameT, key: Optional[str]
) -> IntoDataFrameT:
    # Optional: plotly 6 depends on narwhals, and the plotly extra adds it for
    # plotly 5.
    import narwhals as nw

    if key is None:
        if not nw.dependencies.is_pandas_dataframe(df):
            raise ValueError(
                "`selected_rows(df)` needs `key=` for frames without row labels: "
                "name a column of `df` whose values the figure carries as "
                'customdata, e.g. `custom_data=["id"]` and `key="id"`.'
            )
        # `custom_data=[df.index]` carries index labels, which differ from
        # positions in a filtered, sorted, or re-indexed frame
        values = [customdata_value(p) for p in points or []]
        return cast("IntoDataFrameT", df[df.index.isin(values)])

    values = [customdata_value(p) for p in points or []]
    frame = nw.from_native(df, eager_only=True)
    return frame.filter(nw.col(key).is_in(values)).to_native()


def customdata_value(point: Point) -> object:
    if "customdata" not in point:
        raise ValueError(
            "`selected_rows()` matches each point's customdata to a row, but the "
            "selected points carry none. Add it to the figure, e.g. "
            "`px.scatter(df, ..., custom_data=[df.index])`."
        )
    value = point["customdata"]
    # px's custom_data=[...] gives each point a list; the first entry is the key.
    if isinstance(value, list):
        return value[0] if value else None
    return value


def bridge_attach(
    fires: str, shape: Callable[[Dict[str, Any]], object], clears: Sequence[str]
) -> Callable[[Any, Emit], Callable[[], None]]:
    def attach(widget: Any, emit: Emit) -> Callable[[], None]:
        # ipywidgets swallows exceptions raised here, so this must not raise.
        def on_msg(_widget: object, content: object, _buffers: object) -> None:
            if not isinstance(content, dict) or content.get("shinywidgets") != "event":
                return
            name = content.get("event")
            if name == fires:
                value = shape(content)
                if value is not SKIP:
                    emit(value)
            elif name in clears:
                emit(None)

        widget.on_msg(on_msg)
        events = [fires, *clears]
        when_comm_open(
            widget, lambda: widget.send({"shinywidgets": "bind", "events": events})
        )
        return lambda: widget.on_msg(on_msg, remove=True)

    return attach


def points_of(content: Dict[str, Any]) -> object:
    # plotly.js fires plotly_selected with no data when a select gesture
    # selected nothing at all (e.g. a click in select mode): no selection.
    return content.get("points")


def region_of(content: Dict[str, Any]) -> object:
    for key in ("range", "lassoPoints"):
        if key in content:
            return {key: content[key]}
    return None


def relayout_of(content: Dict[str, Any]) -> object:
    relayout = content.get("relayout")
    if not isinstance(relayout, dict):
        return SKIP
    axes = {k: v for k, v in relayout.items() if AXIS_RANGE_KEY.match(k)}
    return axes or SKIP


CLICKED = AccessorSpec(
    name="clicked",
    kind="event",
    attach=bridge_attach("plotly_click", points_of, (DOUBLECLICK, DESELECT)),
    payload=points_frame,
)
SELECTED = AccessorSpec(
    name="selected",
    kind="event",
    attach=bridge_attach("plotly_selected", points_of, (DESELECT,)),
    payload=points_frame,
)
SELECTING = AccessorSpec(
    name="selecting",
    kind="event",
    attach=bridge_attach("plotly_selecting", points_of, (DESELECT,)),
    payload=points_frame,
    rate_policy="debounce",
)
BRUSHED = AccessorSpec(
    name="brushed",
    kind="event",
    attach=bridge_attach("plotly_selected", region_of, (DESELECT,)),
)
BRUSHING = AccessorSpec(
    name="brushing",
    kind="event",
    attach=bridge_attach("plotly_selecting", region_of, (DESELECT,)),
    rate_policy="debounce",
)
RELAYOUT = AccessorSpec(
    name="relayout",
    kind="event",
    attach=bridge_attach("plotly_relayout", relayout_of, ()),
)

PLOTLY_ACCESSORS = (CLICKED, SELECTED, SELECTING, BRUSHED, BRUSHING, RELAYOUT)
