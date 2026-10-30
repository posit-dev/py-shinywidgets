"""
Accessors for `render_altair`.

Altair selections are state the chart declares, so one accessor observes all
of them (altair's own `JupyterChart.selections`), and `selected_rows()` filters
a frame by a selection's Vega "store", porting Vega's `selectionTest`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, Literal, Optional, Union
from zoneinfo import ZoneInfo

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    import narwhals as nw
    from altair import JupyterChart
    from altair.utils.selection import (
        IndexSelection,
        IntervalSelection,
        PointSelection,
    )
    from narwhals.typing import IntoDataFrameT

    Selection = Union[IntervalSelection, PointSelection, IndexSelection]


def attach_selections(widget: JupyterChart, emit: Emit) -> Callable[[], None]:
    def on_change(change: object) -> None:
        # altair's own observer, registered first, has already rebuilt
        # `.selections` from the raw Vega signals by now.
        emit(dict(widget.selections.trait_values()))

    widget.observe(on_change, "_vl_selections")
    emit(dict(widget.selections.trait_values()))
    return lambda: widget.unobserve(on_change, "_vl_selections")


SELECTED = AccessorSpec(
    name="selected",
    kind="state",
    attach=attach_selections,
    rate_policy="debounce",
)

ALTAIR_ACCESSORS = (SELECTED,)


def pick_selection(selections: Dict[str, Selection], name: Optional[str]) -> Selection:
    if not selections:
        raise ValueError(
            "The chart has no selections. Add one with e.g. "
            '`alt.selection_point(name="pick")` and `.add_params()`.'
        )
    names = ", ".join(selections)
    if name is None:
        if len(selections) > 1:
            raise ValueError(
                f"The chart has several selections ({names}); pass the name of one."
            )
        return next(iter(selections.values()))
    if name not in selections:
        raise ValueError(
            f"The chart has no selection named {name!r}; its selections are: {names}."
        )
    return selections[name]


def chart_frame(widget: JupyterChart) -> Any:
    data = getattr(widget.chart, "data", None)
    if is_frame(data):
        return data
    found = type(data).__name__
    if isinstance(data, str):
        found = f"a URL ({data!r})"
    raise TypeError(
        f"`selected_rows()` can only find rows in a chart built from a data frame, "
        f"but this chart's data is {found}. Pass the frame to filter as "
        "`selected_rows(df=...)`."
    )


def is_frame(x: object) -> bool:
    try:
        import narwhals as nw
    except ImportError:  # the altair extra installs narwhals; this is defensive
        return False
    return nw.dependencies.is_into_dataframe(x)


def filter_selection(
    selection: Selection, df: IntoDataFrameT, local_tz: Optional[str]
) -> IntoDataFrameT:
    """
    The rows of `df` in `selection`. An empty selection selects no rows (unlike
    Vega's default `empty="all"`).
    """
    import narwhals as nw
    from altair.utils.selection import IndexSelection

    frame = nw.from_native(df, eager_only=True)
    if isinstance(selection, IndexSelection):
        row = "__shinywidgets_row__"
        return (
            frame.with_row_index(row)
            .filter(nw.col(row).is_in(list(selection.value)))
            .drop(row)
            .to_native()
        )

    test: Optional[nw.Expr] = None
    for entry in selection.store:
        match = nw.lit(True)
        for field, value in zip(entry["fields"], entry["values"]):
            match = match & field_test(frame, field, value, local_tz)
        test = match if test is None else test | match
    if test is None:
        return frame.head(0).to_native()
    return frame.filter(test).to_native()


def field_test(
    frame: nw.DataFrame[Any], field: Dict[str, Any], value: Any, local_tz: Optional[str]
) -> nw.Expr:
    import narwhals as nw

    name = field["field"]
    if name not in frame.columns:
        raise ValueError(
            f"The selection is on field {name!r}, which isn't a column of the data "
            f"frame (columns: {', '.join(frame.columns)}). Pass the frame the "
            "chart was built from as `selected_rows(df=...)`."
        )
    col = nw.col(name)
    dtype = frame.schema[name]
    kind = field["type"]
    if dtype == nw.Date or dtype == nw.Datetime:
        if dtype == nw.Date:
            col = col.cast(nw.Datetime("us"))
        # Convert the selection's UTC bounds to the column's time, rather than
        # the column to UTC: localizing naive times can fail at DST changes.
        value = to_column_time(value, getattr(dtype, "time_zone", None), local_tz)
    elif kind.startswith("R") and any(isinstance(v, str) for v in value):
        raise ValueError(
            f"The selection on {name!r} is a range of dates, but that column holds "
            f"{dtype}, not dates. Parse it as dates, e.g. with `pd.to_datetime()` "
            "or `read_csv(..., parse_dates=[...])`."
        )

    if kind == "E":
        return col.is_in(value) if isinstance(value, list) else col == nw.lit(value)
    if kind in CLOSED:
        lo, hi = sorted(value)
        return col.is_between(nw.lit(lo), nw.lit(hi), closed=CLOSED[kind])
    if kind == "E-LT":
        return col < nw.lit(value)
    if kind == "E-LTE":
        return col <= nw.lit(value)
    if kind == "E-GT":
        return col > nw.lit(value)
    if kind == "E-GTE":
        return col >= nw.lit(value)
    if kind == "E-VALID":
        return ~col.is_null()
    raise ValueError(f"Unsupported Vega selection field type {kind!r}.")


# Vega's range types, by which ends are included
CLOSED: Dict[str, Literal["both", "left", "right", "none"]] = {
    "R": "both",
    "R-RE": "left",
    "R-LE": "right",
    "R-E": "none",
}


def to_column_time(value: Any, zone: Optional[str], local_tz: Optional[str]) -> Any:
    """
    A Vega date (an ISO string or epoch milliseconds, always UTC) as a
    datetime comparable to a column in time zone `zone`, or, for a tz-naive
    column, as naive time in the browser's zone (`local_tz`), which is how
    Vega reads naive dates.
    """
    if isinstance(value, list):
        return [to_column_time(v, zone, local_tz) for v in value]
    if isinstance(value, str):
        # Python < 3.11 can't parse a trailing Z
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
    elif isinstance(value, (int, float)):
        moment = datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    else:
        return value
    if zone is not None:
        return moment.astimezone(ZoneInfo(zone))
    return moment.astimezone(ZoneInfo(local_tz or "UTC")).replace(tzinfo=None)
