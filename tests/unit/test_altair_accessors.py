from __future__ import annotations

from typing import Any, Dict, List

import altair as alt
import pandas as pd
import polars as pl
import pytest
import shinywidgets._altair as sa
from altair.utils.selection import IndexSelection, IntervalSelection, PointSelection
from shiny import Session
from shiny.session import session_context

DATES = pd.DataFrame(
    {"date": pd.date_range("2024-01-01", periods=30, freq="D"), "y": range(30)}
)
# Captured from a real brush drag (spikes-A/altair2)
DATE_BRUSH = [
    {
        "unit": "",
        "fields": [{"field": "date", "channel": "x", "type": "R"}],
        "values": [["2024-01-08T19:18:28.812Z", "2024-01-12T13:55:37.976Z"]],
    }
]


def interval(store: List[Dict[str, Any]]) -> IntervalSelection:
    return IntervalSelection(name="s", value={}, store=store)  # type: ignore[arg-type]


def point(store: List[Dict[str, Any]]) -> PointSelection:
    return PointSelection(name="s", value=[], store=store)  # type: ignore[arg-type]


def entry(*fields: tuple[str, str, Any]) -> Dict[str, Any]:
    return {
        "fields": [{"field": f, "type": t} for f, t, _ in fields],
        "values": [v for _, _, v in fields],
    }


def test_temporal_range_compares_in_utc() -> None:
    out = sa.filter_selection(interval(DATE_BRUSH), DATES, local_tz="UTC")
    assert out["y"].tolist() == [8, 9, 10, 11]


def test_temporal_range_reads_naive_dates_in_local_tz() -> None:
    out = sa.filter_selection(interval(DATE_BRUSH), DATES, local_tz="Asia/Tokyo")
    assert out["y"].tolist() == [9, 10, 11]


def test_binned_point_selection_is_half_open_and_ored() -> None:
    # Captured: clicking two adjacent histogram bars
    store = [entry(("v", "R-RE", [1, 2])), entry(("v", "R-RE", [2, 3]))]
    df = pd.DataFrame({"v": [0.5, 1, 1.5, 2, 2.5, 3]})
    assert sa.filter_selection(point(store), df, None)["v"].tolist() == [1, 1.5, 2, 2.5]


def test_enum_scalar_and_membership() -> None:
    df = pd.DataFrame({"g": list("abcd")})
    assert sa.filter_selection(point([entry(("g", "E", "b"))]), df, None)[
        "g"
    ].tolist() == ["b"]
    assert sa.filter_selection(point([entry(("g", "E", ["a", "c"]))]), df, None)[
        "g"
    ].tolist() == ["a", "c"]


def test_range_bounds_are_sorted_and_fields_anded() -> None:
    df = pd.DataFrame({"x": [1, 3, 5, 7], "y": [1, 1, 2, 2]})
    store = [entry(("x", "R", [6, 2]), ("y", "R", [2, 1.5]))]
    assert sa.filter_selection(interval(store), df, None)["x"].tolist() == [5]


def test_exclusive_and_predicate_types() -> None:
    df = pd.DataFrame({"x": [1, 2, 3]})

    def xs(t: str, v: Any) -> List[int]:
        return sa.filter_selection(point([entry(("x", t, v))]), df, None)["x"].tolist()

    assert xs("R-E", [1, 3]) == [2]
    assert xs("R-LE", [1, 3]) == [2, 3]
    assert xs("E-LT", 2) == [1]
    assert xs("E-LTE", 2) == [1, 2]
    assert xs("E-GT", 2) == [3]
    assert xs("E-GTE", 2) == [2, 3]


def test_empty_selection_is_empty_frame() -> None:
    out = sa.filter_selection(interval([]), DATES, None)
    assert len(out) == 0 and list(out.columns) == ["date", "y"]


def test_index_selection_uses_positions() -> None:
    sel = IndexSelection(name="s", value=[2, 0], store=[{"values": [3]}])  # type: ignore[arg-type]
    assert sa.filter_selection(sel, DATES, None)["y"].tolist() == [0, 2]


def test_polars_frames_work() -> None:
    df = pl.DataFrame({"g": list("abcd")})
    out = sa.filter_selection(point([entry(("g", "E", "b"))]), df, None)
    assert isinstance(out, pl.DataFrame) and out["g"].to_list() == ["b"]


def test_unknown_field_raises() -> None:
    with pytest.raises(ValueError, match="nope"):
        sa.filter_selection(point([entry(("nope", "E", 1))]), DATES, None)


def chart(*params: Any, data: Any = DATES) -> alt.JupyterChart:
    c = alt.Chart(data).mark_point().encode(x="date:T", y="y:Q")
    return alt.JupyterChart(c.add_params(*params) if params else c)


def test_attach_emits_current_selections_then_changes(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        w = chart(alt.selection_interval(name="brush"))
    emitted: List[object] = []
    detach = sa.SELECTED.attach(w, emitted.append)
    assert emitted == [{"brush": IntervalSelection(name="brush", value={}, store=[])}]
    w._vl_selections = {"brush": {"value": {"y": [1, 2]}, "store": DATE_BRUSH}}
    assert emitted[-1] == {
        "brush": IntervalSelection(name="brush", value={"y": [1, 2]}, store=DATE_BRUSH)  # type: ignore[arg-type]
    }
    detach()
    w._vl_selections = {"brush": {"value": {}, "store": []}}
    assert len(emitted) == 2


def test_selected_spec_debounces_by_default() -> None:
    assert sa.SELECTED.rate_policy == "debounce" and sa.SELECTED.kind == "state"


def test_pick_selection_by_name() -> None:
    a = IntervalSelection(name="a", value={}, store=[])  # type: ignore[arg-type]
    b = PointSelection(name="b", value=[], store=[])  # type: ignore[arg-type]
    assert sa.pick_selection({"a": a}, None) is a
    assert sa.pick_selection({"a": a, "b": b}, "b") is b
    with pytest.raises(ValueError, match="a, b"):
        sa.pick_selection({"a": a, "b": b}, None)
    with pytest.raises(ValueError, match="no selections"):
        sa.pick_selection({}, None)
    with pytest.raises(ValueError, match="'c'"):
        sa.pick_selection({"a": a}, "c")


def test_chart_frame_from_chart_data_or_raises(widget_session: Session) -> None:
    with session_context(widget_session):
        assert sa.chart_frame(chart()) is DATES
        url_chart = chart(data="https://example.com/data.csv")
    with pytest.raises(TypeError, match="df="):
        sa.chart_frame(url_chart)


def test_render_altair_selected_and_selected_rows(widget_session: Session) -> None:
    from shinywidgets import render_altair

    r = render_altair()
    with session_context(widget_session):
        w = chart(alt.selection_interval(name="brush"))
    r._widget = w  # stands in for _render()
    r._accessors.on_render(w)
    assert r.selected() == IntervalSelection(name="brush", value={}, store=[])
    assert len(r.selected_rows()) == 0
    r._accessors.values["selected"].set(  # stands in for a debounced publish
        sa_box({"brush": interval(DATE_BRUSH)})
    )
    w.local_tz = "UTC"
    assert r.selected_rows()["y"].tolist() == [8, 9, 10, 11]
    other = pd.DataFrame({"date": DATES["date"], "z": range(30)})
    assert r.selected_rows(df=other)["z"].tolist() == [8, 9, 10, 11]


def sa_box(raw: object) -> Any:
    from shinywidgets._accessors import Box

    return Box(raw)


def test_naive_dates_across_a_dst_change_dont_raise() -> None:
    # 2024-11-03 01:00-02:00 happens twice in America/Chicago
    df = pd.DataFrame(
        {"t": pd.date_range("2024-11-02 22:00", periods=8, freq="h"), "y": range(8)}
    )
    brush = [
        entry(("t", "R", ["2024-11-03T05:00:00.000Z", "2024-11-03T09:00:00.000Z"]))
    ]
    out = sa.filter_selection(interval(brush), df, local_tz="America/Chicago")
    # 05:00Z = 00:00 CDT and 09:00Z = 03:00 CST, in naive local time
    assert out["y"].tolist() == [2, 3, 4, 5]


def test_tz_aware_columns_compare_in_their_own_zone() -> None:
    df = pd.DataFrame(
        {
            "t": pd.date_range("2024-01-01", periods=4, freq="h", tz="Asia/Tokyo"),
            "y": range(4),
        }
    )
    brush = [entry(("t", "R", ["2023-12-31T15:30:00Z", "2023-12-31T17:00:00Z"]))]
    assert sa.filter_selection(interval(brush), df, None)["y"].tolist() == [1, 2]


def test_fixed_offset_columns_compare_in_their_offset() -> None:
    # pandas names a parsed "+02:00" column's zone "UTC+02:00", which isn't a
    # ZoneInfo key
    df = pd.DataFrame(
        {
            "t": pd.to_datetime([f"2024-01-01T0{h}:00:00+02:00" for h in range(4)]),
            "y": range(4),
        }
    )
    brush = [entry(("t", "R", ["2023-12-31T22:30:00Z", "2024-01-01T00:00:00Z"]))]
    assert sa.filter_selection(interval(brush), df, None)["y"].tolist() == [1, 2]


def test_temporal_point_selection_with_epoch_ms() -> None:
    sel = point([entry(("date", "E", [1704153600000]))])  # 2024-01-02T00:00Z
    assert sa.filter_selection(sel, DATES, local_tz="UTC")["y"].tolist() == [1]


def test_date_strings_in_a_text_column_raise_a_clear_error() -> None:
    df = pd.DataFrame({"date": ["2024-01-01", "2024-01-02"], "y": [1, 2]})
    with pytest.raises(ValueError, match="parse"):
        sa.filter_selection(interval(DATE_BRUSH), df, "UTC")
