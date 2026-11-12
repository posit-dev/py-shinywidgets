"""
Accessors for `render_altair`.

Altair selections are state the chart declares, so one accessor observes all
of them (altair's own `JupyterChart.selections`), and `selected_rows()` filters
a frame by a selection's Vega "store", porting Vega's `selectionTest`. A
selection whose store spans several views (a layered or concatenated chart)
is partitioned by the store entries' `unit`, and each view's own data frame is
filtered.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Literal, Optional, Union
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


def view_frames(chart: Any) -> Dict[str, Any]:
    """
    The data frame each named view is fed, keyed by view name -- the name a
    Vega selection store reports as a store entry's `unit`. A view's frame is
    the nearest data frame declared on its subchart or one of its ancestors
    (altair hoists data shared by a compound chart's subcharts onto the
    parent). Layers, concatenations, and facet specs are walked (recursing
    into nesting); repeat charts aren't (their subcharts share one dataset).
    A view with no data frame declared above it maps to None. A name used by
    two subcharts raises.
    """
    import altair as alt

    found: Dict[str, Any] = {}

    def visit(node: Any, data: Any) -> None:
        node_data = getattr(node, "data", None)
        if is_frame(node_data):
            data = node_data
        if isinstance(node, alt.Chart):
            name = node.name
            if name is alt.Undefined:
                return
            if name in found:
                raise ValueError(
                    f"The chart has two subcharts named {name!r}. Give each "
                    "one a unique `name=` so `selected_rows()` can tell their "
                    "data apart."
                )
            found[name] = data
            return
        for attr in ("layer", "hconcat", "vconcat", "concat"):
            children: Any = getattr(node, attr, alt.Undefined)
            if children is not alt.Undefined:
                for subchart in children:
                    visit(subchart, data)
        if isinstance(node, alt.FacetChart):
            visit(node.spec, data)

    visit(chart, None)
    return found


def selection_views(chart: Any, name: str) -> Optional[List[str]]:
    """
    The names of the views selection `name` participates in, per the chart's
    hoisted selection param (the chart's record of which subcharts the user
    can gesture on). `None` when the param or its views can't be found --
    callers then fall back to the store's `unit`s.
    """
    import altair as alt

    params: Any = getattr(chart, "params", alt.Undefined)
    if params is alt.Undefined:
        return None
    for param in params:
        if getattr(param, "name", None) != name:
            continue
        views: Any = getattr(param, "views", alt.Undefined)
        if views is alt.Undefined:
            return None
        return [str(view) for view in views]
    return None


def chart_datasets(chart: Any) -> List[Any]:
    """The distinct data frames declared anywhere on `chart` (by identity)."""
    import altair as alt

    frames: List[Any] = []

    def visit(node: Any) -> None:
        data = getattr(node, "data", None)
        if is_frame(data) and not any(data is frame for frame in frames):
            frames.append(data)
        for attr in ("layer", "hconcat", "vconcat", "concat"):
            children: Any = getattr(node, attr, alt.Undefined)
            if children is not alt.Undefined:
                for subchart in children:
                    visit(subchart)
        if isinstance(node, alt.FacetChart):
            visit(node.spec)

    visit(chart)
    return frames


def chart_frame(chart: Any) -> Any:
    data = getattr(chart, "data", None)
    if is_frame(data):
        return data
    found = type(data).__name__
    if isinstance(data, str):
        found = f"a URL ({data!r})"
    raise TypeError(
        f"`selected_rows()` can only find rows in a chart built from a data "
        f"frame, but this chart's data is {found}. Pass the frame to filter "
        "as `selected_rows(df=...)`."
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
    Vega's default `empty="all"`). Every entry is applied to `df`, so use
    `filter_selection_by_unit()` for a selection whose store spans several
    views with different data.
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
    return filter_store(selection.store, frame, local_tz).to_native()


def filter_store(
    store: List[Dict[str, Any]],
    frame: nw.DataFrame[Any],
    local_tz: Optional[str],
) -> nw.DataFrame[Any]:
    """The rows of `frame` selected by `store` (entries of a single view)."""
    import narwhals as nw

    test: Optional[nw.Expr] = None
    for entry in store:
        match = nw.lit(True)
        for field, value in zip(entry["fields"], entry["values"]):
            match = match & field_test(frame, field, value, local_tz)
        test = match if test is None else test | match
    if test is None:
        return frame.head(0)
    return frame.filter(test)


def filter_selection_by_unit(
    selection: "Selection",
    frames: Dict[str, "IntoDataFrameT"],
    local_tz: Optional[str],
) -> Dict[str, "IntoDataFrameT"]:
    """
    The rows of each view's frame in `selection`, for a selection whose store
    spans several views: `frames` is keyed by view name (the store entries'
    `unit`) and each frame is filtered by its own view's entries only. An
    entry naming a view with no frame raises. So does a bare point selection
    (an `IndexSelection`): its store holds positional `_vgsid_` ids, which
    Vega assigns across the whole chart's dataflow, so they can't be mapped
    back to rows of one view's frame.
    """
    import narwhals as nw
    from altair.utils.selection import IndexSelection

    if isinstance(selection, IndexSelection):
        raise index_selection_error(selection.name)

    stores: Dict[str, List[Dict[str, Any]]] = {view: [] for view in frames}
    for entry in selection.store:
        unit = entry.get("unit", "")
        if unit not in stores:
            raise ValueError(
                f"The selection has entries from a view named {unit!r}, which "
                f"isn't among the chart's views ({', '.join(frames)}). Pass "
                "the frames to filter as `selected_rows(df=...)` keyed by "
                "view name."
            )
        stores[unit].append(entry)

    out: Dict[str, IntoDataFrameT] = {}
    for view, df in frames.items():
        frame = nw.from_native(df, eager_only=True)
        out[view] = filter_store(stores[view], frame, local_tz).to_native()
    return out


def check_index_selection(selection: "Selection", chart: Any) -> None:
    """
    Raise for a bare point selection (an `IndexSelection` of positional row
    indices) on a chart with several datasets: Vega assigns the `_vgsid_` ids
    the indices derive from across the whole chart's dataflow, so they can't
    be mapped back to rows of one dataset's frame.
    """
    from altair.utils.selection import IndexSelection

    if isinstance(selection, IndexSelection) and len(chart_datasets(chart)) > 1:
        raise index_selection_error(selection.name)


def index_selection_error(name: str) -> ValueError:
    return ValueError(
        f"The selection {name!r} selects positional row indices (a bare "
        "`alt.selection_point()` without `fields=`/`encodings=`), which "
        "can't be mapped back to rows on a chart with several datasets. "
        "Declare the selection with `fields=` or `encodings=` (e.g. "
        "`alt.selection_point(encodings=['x'])`) so it selects values "
        "instead of positions."
    )


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
        zone = getattr(dtype, "time_zone", None)
        if dtype == nw.Date:
            col = col.cast(nw.Datetime("us"))
        if zone is not None:
            # Compare instants: across a DST change, wall times can run
            # backwards
            col = col.dt.convert_time_zone("UTC")
        # A naive column's times can't be converted to UTC (localizing fails
        # at DST changes), so its bounds are converted to its time instead
        value = to_column_time(value, zone is not None, local_tz)
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


def to_column_time(value: Any, aware: bool, local_tz: Optional[str]) -> Any:
    """
    A Vega date (an ISO string or epoch milliseconds, always UTC) as a
    datetime comparable to a column converted to UTC (`aware`), or, for a
    tz-naive column, as naive time in the browser's zone (`local_tz`), which is
    how Vega reads naive dates.
    """
    if isinstance(value, list):
        return [to_column_time(v, aware, local_tz) for v in value]
    if isinstance(value, str):
        # Python < 3.11 can't parse a trailing Z
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
    elif isinstance(value, (int, float)):
        moment = datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    else:
        return value
    if aware:
        return moment.astimezone(timezone.utc)
    return moment.astimezone(ZoneInfo(local_tz or "UTC")).replace(tzinfo=None)
