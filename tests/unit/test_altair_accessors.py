from __future__ import annotations

import warnings
from typing import Any, Dict, List

import altair as alt
import pandas as pd
import polars as pl
import pytest
import shinywidgets._altair as sa
from altair.utils.selection import IndexSelection, IntervalSelection, PointSelection
from shiny import Session
from shiny.session import session_context

from tests.unit.conftest import reads_across_rerender

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


def interval(store: List[Dict[str, Any]], name: str = "s") -> IntervalSelection:
    return IntervalSelection(name=name, value={}, store=store)  # type: ignore[arg-type]


def point(store: List[Dict[str, Any]], name: str = "s") -> PointSelection:
    return PointSelection(name=name, value=[], store=store)  # type: ignore[arg-type]


def entry(*fields: tuple[str, str, Any]) -> Dict[str, Any]:
    return {
        "fields": [{"field": f, "type": t} for f, t, _ in fields],
        "values": [v for _, _, v in fields],
    }


POINTS = pd.DataFrame({"x": [1, 2, 3], "y": [10, 20, 30]})
LINES = pd.DataFrame({"x": [1, 2, 3], "z": [100, 200, 300]})


def uentry(unit: str, *fields: tuple[str, str, Any]) -> Dict[str, Any]:
    """A store entry with a `unit`, as multi-view selections report them."""
    return {"unit": unit, **entry(*fields)}


def layered_chart() -> alt.JupyterChart:
    """Layers with distinct datasets, each with its own interval selection."""
    pts = (
        alt.Chart(POINTS, name="pts")
        .mark_point()
        .encode(x="x", y="y")
        .add_params(alt.selection_interval(name="b1"))
    )
    lns = (
        alt.Chart(LINES, name="lns")
        .mark_point()
        .encode(x="x", y="z")
        .add_params(alt.selection_interval(name="b2"))
    )
    return alt.JupyterChart(alt.layer(pts, lns))


def hconcat_chart() -> alt.JupyterChart:
    """Concatenated charts with distinct datasets sharing one selection."""
    brush = alt.selection_interval(name="brush")
    pts = (
        alt.Chart(POINTS, name="pts")
        .mark_point()
        .encode(x="x", y="y")
        .add_params(brush)
    )
    lns = (
        alt.Chart(LINES, name="lns").mark_point().encode(x="x", y="z").add_params(brush)
    )
    with warnings.catch_warnings():
        # altair warns when it deduplicates the identical params
        warnings.simplefilter("ignore")
        return alt.JupyterChart(alt.hconcat(pts, lns))


def test_filter_by_unit_partitions_entries() -> None:
    store = [
        uentry("pts", ("x", "R", [1, 2])),
        uentry("lns", ("z", "R", [150, 250])),
    ]
    out = sa.filter_selection_by_unit(
        interval(store), {"pts": POINTS, "lns": LINES}, None
    )
    assert out["pts"]["y"].tolist() == [10, 20]
    assert out["lns"]["z"].tolist() == [200]


def test_filter_by_unit_empty_store_gives_empty_frames() -> None:
    out = sa.filter_selection_by_unit(interval([]), {"pts": POINTS, "lns": LINES}, None)
    assert set(out) == {"pts", "lns"}
    assert len(out["pts"]) == 0 and len(out["lns"]) == 0


def test_filter_by_unit_index_selection_raises() -> None:
    # A bare alt.selection_point() stores positional `_vgsid_` ids, which Vega
    # assigns across the whole chart's dataflow -- they can't be resolved to
    # rows of one view's frame, so the per-view path refuses them
    sel = IndexSelection(
        name="pick",
        value=[0, 2],
        store=[{"unit": "pts", "_vgsid_": 1}, {"unit": "lns", "_vgsid_": 3}],
    )  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="encodings="):
        sa.filter_selection_by_unit(sel, {"pts": POINTS, "lns": LINES}, None)


def test_filter_by_unit_rejects_unknown_units() -> None:
    with pytest.raises(ValueError, match="'nope'"):
        sa.filter_selection_by_unit(
            interval([uentry("nope", ("x", "R", [1, 2]))]), {"pts": POINTS}, None
        )


def test_view_frames_walks_layers_and_concats(widget_session: Session) -> None:
    with session_context(widget_session):
        layered = layered_chart()
        concatenated = hconcat_chart()
    for combo in (layered.chart, concatenated.chart):
        frames = sa.view_frames(combo)
        assert set(frames) == {"pts", "lns"}
        assert frames["pts"] is POINTS and frames["lns"] is LINES
    with session_context(widget_session):
        plain = chart()
    assert sa.view_frames(plain.chart) == {}


def test_view_frames_inherits_an_intermediate_charts_data() -> None:
    # The layers share one data frame, which altair hoists onto the inner
    # LayerChart, so the leaves declare no data of their own
    inner = alt.layer(
        alt.Chart(POINTS, name="pts").mark_point().encode(x="x"),
        alt.Chart(POINTS, name="dup").mark_point().encode(x="x"),
    )
    combo = alt.hconcat(inner, alt.Chart(LINES, name="lns").mark_point().encode(x="x"))
    assert inner.data is POINTS and inner.layer[0].data is alt.Undefined
    # altair disambiguates a nested layer's name with its concat position
    frames = sa.view_frames(combo)
    assert frames["pts_0"] is POINTS and frames["dup_0"] is POINTS
    assert frames["lns"] is LINES


def test_selection_views_reads_the_hoisted_param(widget_session: Session) -> None:
    with session_context(widget_session):
        layered = layered_chart()
        concatenated = hconcat_chart()
        plain = chart(alt.selection_interval(name="brush"))
    assert sa.selection_views(layered.chart, "b1") == ["pts"]
    assert sa.selection_views(layered.chart, "b2") == ["lns"]
    assert sa.selection_views(concatenated.chart, "brush") == ["pts", "lns"]
    assert sa.selection_views(concatenated.chart, "nope") is None
    assert sa.selection_views(plain.chart, "brush") is None
    variable = (
        alt.Chart(POINTS)
        .mark_point()
        .encode(x="x")
        .add_params(alt.param(name="v", value=1))
    )
    assert sa.selection_views(variable, "v") is None


def test_view_frames_explicit_non_frame_data_overrides_the_parent() -> None:
    combo = alt.hconcat(
        alt.Chart(POINTS, name="pts").mark_point().encode(x="x"),
        alt.Chart("https://example.com/d.csv", name="url").mark_point().encode(x="x:Q"),
        data=LINES,
    )
    frames = sa.view_frames(combo)
    assert frames["pts"] is POINTS
    # The URL dataset isn't a frame; inheriting the parent frame would
    # silently filter the wrong rows, so df= is required instead
    assert frames["url"] is None


def test_chart_datasets_counts_frames_urls_and_inline_data() -> None:
    combo = alt.hconcat(
        alt.Chart(POINTS).mark_point().encode(x="x"),
        alt.Chart("https://example.com/a.csv").mark_point().encode(x="x"),
        alt.Chart(alt.Data(values=[{"x": 1}])).mark_point().encode(x="x"),
    )
    assert len(sa.chart_datasets(combo)) == 3
    same_url = alt.hconcat(
        alt.Chart("https://example.com/a.csv").mark_point().encode(x="x"),
        alt.Chart("https://example.com/a.csv").mark_point().encode(x="x"),
    )
    assert len(sa.chart_datasets(same_url)) == 1


def test_view_frames_rejects_duplicate_names() -> None:
    a = alt.Chart(POINTS, name="dup").mark_point().encode(x="x")
    b = alt.Chart(LINES, name="dup").mark_point().encode(x="x")
    with pytest.raises(ValueError, match="'dup'"):
        sa.view_frames(alt.hconcat(a, b))


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
        assert sa.chart_frame(chart().chart) is DATES
        url_chart = chart(data="https://example.com/data.csv")
    with pytest.raises(TypeError, match="df="):
        sa.chart_frame(url_chart.chart)


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
    with pytest.raises(TypeError, match="positional"):
        r.selected_rows("brush", other)


def test_selected_rows_uses_the_selection_views_own_data(
    widget_session: Session,
) -> None:
    from shinywidgets import render_altair

    r = render_altair()
    with session_context(widget_session):
        w = layered_chart()
    r._widget = w
    r._accessors.on_render(w)
    r._accessors.values["selected"].set(
        sa_box(
            {
                "b1": interval([uentry("pts", ("x", "R", [1, 2]))], name="b1"),
                "b2": interval([uentry("lns", ("z", "R", [150, 250]))], name="b2"),
            }
        )
    )
    w.local_tz = "UTC"
    assert r.selected_rows("b1")["y"].tolist() == [10, 20]
    assert r.selected_rows("b2")["z"].tolist() == [200]


def test_selected_rows_facet_chart_still_filters_the_whole_frame(
    widget_session: Session,
) -> None:
    from shinywidgets import render_altair

    df = pd.DataFrame({"x": range(6), "y": range(6), "g": list("aaabbb")})
    brush = alt.selection_interval(name="brush")
    faceted = (
        alt.Chart(df)
        .mark_point()
        .encode(x="x:Q", y="y:Q")
        .add_params(brush)
        .facet(column="g:N")
    )
    with session_context(widget_session):
        w = alt.JupyterChart(faceted)
    r = render_altair()
    r._widget = w
    r._accessors.on_render(w)
    # Facet store units carry a `__facet` suffix; the single-view path ignores
    # them and filters the chart's (hoisted) frame, as before this change
    r._accessors.values["selected"].set(
        sa_box(
            {
                "brush": interval(
                    [uentry("view_1_0__facet_g_a", ("x", "R", [1, 2]))], name="brush"
                )
            }
        )
    )
    w.local_tz = "UTC"
    assert r.selected_rows("brush")["y"].tolist() == [1, 2]


def test_selected_rows_returns_a_dict_for_multi_dataset_views(
    widget_session: Session,
) -> None:
    from shinywidgets import render_altair

    r = render_altair()
    with session_context(widget_session):
        w = hconcat_chart()
    r._widget = w
    r._accessors.on_render(w)
    w.local_tz = "UTC"

    # An empty selection is a dict of empty frames, keyed by view name
    empty = r.selected_rows("brush")
    assert isinstance(empty, dict) and set(empty) == {"pts", "lns"}
    assert all(len(frame) == 0 for frame in empty.values())

    r._accessors.values["selected"].set(
        sa_box(
            {
                "brush": interval(
                    [
                        uentry("pts", ("x", "R", [1, 2])),
                        uentry("lns", ("z", "R", [150, 250])),
                    ],
                    name="brush",
                )
            }
        )
    )
    out = r.selected_rows("brush")
    assert isinstance(out, dict)
    assert out["pts"]["y"].tolist() == [10, 20]
    assert out["lns"]["z"].tolist() == [200]


def test_selected_rows_shared_data_concat_stays_a_single_frame(
    widget_session: Session,
) -> None:
    from shinywidgets import render_altair

    brush = alt.selection_interval(name="brush")
    pts = (
        alt.Chart(POINTS, name="pts")
        .mark_point()
        .encode(x="x", y="y")
        .add_params(brush)
    )
    dup = (
        alt.Chart(POINTS, name="dup")
        .mark_point()
        .encode(x="x", y="y")
        .add_params(brush)
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        combo = alt.hconcat(pts, dup)
    with session_context(widget_session):
        w = alt.JupyterChart(combo)
    r = render_altair()
    r._widget = w
    r._accessors.on_render(w)
    w.local_tz = "UTC"
    r._accessors.values["selected"].set(
        sa_box({"brush": interval([uentry("pts", ("x", "R", [1, 2]))], name="brush")})
    )
    out = r.selected_rows("brush")
    assert isinstance(out, pd.DataFrame)
    assert out["y"].tolist() == [10, 20]
    # A scalar df can stand in for the dataset every view shares
    out = r.selected_rows("brush", df=POINTS)
    assert isinstance(out, pd.DataFrame)
    assert out["y"].tolist() == [10, 20]


def test_selected_rows_df_dict_filters_each_frame(widget_session: Session) -> None:
    from shinywidgets import render_altair

    r = render_altair()
    with session_context(widget_session):
        w = hconcat_chart()
    r._widget = w
    r._accessors.on_render(w)
    w.local_tz = "UTC"
    r._accessors.values["selected"].set(
        sa_box(
            {
                "brush": IntervalSelection(
                    name="brush",
                    value={},
                    store=[
                        uentry("pts", ("x", "R", [1, 2])),
                        uentry("lns", ("z", "R", [150, 250])),
                    ],
                )  # type: ignore[arg-type]
            }
        )
    )
    out = r.selected_rows("brush", df={"pts": POINTS, "lns": LINES})
    assert isinstance(out, dict)
    assert out["pts"]["y"].tolist() == [10, 20]
    assert out["lns"]["z"].tolist() == [200]
    with pytest.raises(ValueError, match="don't match"):
        r.selected_rows("brush", df={"pts": POINTS})
    with pytest.raises(ValueError, match="dict"):
        r.selected_rows("brush", df=POINTS)


def test_selected_rows_unresolvable_view_points_at_df_dict(
    widget_session: Session,
) -> None:
    from shinywidgets import render_altair

    r = render_altair()
    with session_context(widget_session):
        w = hconcat_chart()
    # A view the chart walk can't find (e.g. a chart from alt.Chart.from_dict)
    w.chart.params[0].views = ["ghost", "lns"]
    r._widget = w
    r._accessors.on_render(w)
    w.local_tz = "UTC"
    with pytest.raises(ValueError, match="ghost"):
        r.selected_rows("brush")


def test_view_resolution_under_the_vegafusion_transformer(
    widget_session: Session,
) -> None:
    with alt.data_transformers.enable("vegafusion"):
        with session_context(widget_session):
            w = hconcat_chart()
    assert sa.selection_views(w.chart, "brush") == ["pts", "lns"]
    frames = sa.view_frames(w.chart)
    assert frames["pts"] is POINTS and frames["lns"] is LINES


def test_selected_rows_bare_point_selection_raises_on_a_multi_dataset_chart(
    widget_session: Session,
) -> None:
    from shinywidgets import render_altair

    pick = alt.selection_point(name="pick")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        combo = alt.hconcat(
            alt.Chart(POINTS, name="pts")
            .mark_point()
            .encode(x="x", y="y")
            .add_params(pick),
            alt.Chart(LINES, name="lns")
            .mark_point()
            .encode(x="x", y="z")
            .add_params(pick),
        )
    with session_context(widget_session):
        w = alt.JupyterChart(combo)
    r = render_altair()
    r._widget = w
    r._accessors.on_render(w)
    w.local_tz = "UTC"
    # Even with one participating view (or an explicit df), Vega's `_vgsid_`
    # ids are assigned across the whole chart's dataflow, so they aren't row
    # positions of any one view's frame
    r._accessors.values["selected"].set(
        sa_box(
            {
                "pick": IndexSelection(
                    name="pick",
                    value=[3],
                    store=[{"unit": "lns", "_vgsid_": 4}],
                )  # type: ignore[arg-type]
            }
        )
    )
    with pytest.raises(ValueError, match="encodings="):
        r.selected_rows("pick")
    with pytest.raises(ValueError, match="encodings="):
        r.selected_rows("pick", df=LINES)


def test_selected_rows_bare_point_selection_on_a_single_dataset_chart(
    widget_session: Session,
) -> None:
    from shinywidgets import render_altair

    r = render_altair()
    with session_context(widget_session):
        w = chart(alt.selection_point(name="pick"))
    r._widget = w
    r._accessors.on_render(w)
    w.local_tz = "UTC"
    r._accessors.values["selected"].set(
        sa_box(
            {
                "pick": IndexSelection(
                    name="pick",
                    value=[2, 0],
                    store=[{"unit": "", "_vgsid_": 1}],
                )  # type: ignore[arg-type]
            }
        )
    )
    assert r.selected_rows("pick")["y"].tolist() == [0, 2]


def test_selected_rows_single_view_with_unresolvable_data_raises(
    widget_session: Session,
) -> None:
    from shinywidgets import render_altair

    brush = alt.selection_interval(name="b")
    combo = alt.hconcat(
        alt.Chart(POINTS, name="pts").mark_point().encode(x="x"),
        alt.Chart("https://example.com/d.csv", name="url")
        .mark_point()
        .encode(x="x:Q")
        .add_params(brush),
        data=LINES,
    )
    with session_context(widget_session):
        w = alt.JupyterChart(combo)
    r = render_altair()
    r._widget = w
    r._accessors.on_render(w)
    w.local_tz = "UTC"
    r._accessors.values["selected"].set(
        sa_box({"b": interval([uentry("url", ("x", "R", [1, 2]))], name="b")})
    )
    # The view's data is a URL: the chart's root frame must not be
    # substituted for it, but an explicit df rescues the call
    with pytest.raises(ValueError, match="'url'"):
        r.selected_rows("b")
    assert r.selected_rows("b", df=POINTS)["y"].tolist() == [10, 20]


def test_selected_rows_bare_point_selection_raises_for_mixed_frame_and_url_data(
    widget_session: Session,
) -> None:
    from shinywidgets import render_altair

    pick = alt.selection_point(name="pick")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        combo = alt.hconcat(
            alt.Chart(POINTS, name="pts")
            .mark_point()
            .encode(x="x", y="y")
            .add_params(pick),
            alt.Chart("https://example.com/d.csv", name="url")
            .mark_point()
            .encode(x="x:Q", y="y:Q")
            .add_params(pick),
        )
    with session_context(widget_session):
        w = alt.JupyterChart(combo)
    r = render_altair()
    r._widget = w
    r._accessors.on_render(w)
    w.local_tz = "UTC"
    r._accessors.values["selected"].set(
        sa_box(
            {
                "pick": IndexSelection(
                    name="pick",
                    value=[0],
                    store=[{"unit": "pts", "_vgsid_": 1}],
                )  # type: ignore[arg-type]
            }
        )
    )
    with pytest.raises(ValueError, match="encodings="):
        r.selected_rows("pick")
    with pytest.raises(ValueError, match="encodings="):
        r.selected_rows("pick", df=POINTS)


def test_selected_rows_repeat_chart_filters_the_shared_frame(
    widget_session: Session,
) -> None:
    from shinywidgets import render_altair

    brush = alt.selection_interval(name="b")
    rep = (
        alt.Chart(POINTS, name="pts")
        .mark_point()
        .encode(x="x:Q", y="y:Q")
        .add_params(brush)
        .repeat(column=["x", "y"])
    )
    with session_context(widget_session):
        w = alt.JupyterChart(rep)
    views = sa.selection_views(w.chart, "b")
    assert views is not None and len(views) == 2
    r = render_altair()
    r._widget = w
    r._accessors.on_render(w)
    w.local_tz = "UTC"
    r._accessors.values["selected"].set(
        sa_box(
            {
                "b": IntervalSelection(
                    name="b",
                    value={},
                    store=[uentry(view, ("x", "R", [1, 2])) for view in views],
                )  # type: ignore[arg-type]
            }
        )
    )
    # A selection spans the repeat's generated views, which all share the
    # chart's one data frame: no per-view dict, and a scalar df= works
    assert r.selected_rows("b")["y"].tolist() == [10, 20]
    assert r.selected_rows("b", df=POINTS)["y"].tolist() == [10, 20]


def test_selected_rows_scalar_df_for_views_sharing_a_url(
    widget_session: Session,
) -> None:
    from shinywidgets import render_altair

    brush = alt.selection_interval(name="b")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        combo = alt.hconcat(
            alt.Chart("https://example.com/d.csv", name="a")
            .mark_point()
            .encode(x="x:Q")
            .add_params(brush),
            alt.Chart("https://example.com/d.csv", name="b")
            .mark_point()
            .encode(x="x:Q")
            .add_params(brush),
        )
    with session_context(widget_session):
        w = alt.JupyterChart(combo)
    assert sa.selection_views(w.chart, "b") == ["a", "b"]
    r = render_altair()
    r._widget = w
    r._accessors.on_render(w)
    w.local_tz = "UTC"
    r._accessors.values["selected"].set(
        sa_box(
            {
                "b": IntervalSelection(
                    name="b",
                    value={},
                    store=[
                        uentry("a", ("x", "R", [1, 2])),
                        uentry("b", ("x", "R", [1, 2])),
                    ],
                )  # type: ignore[arg-type]
            }
        )
    )
    # Both views are fed the same URL: a scalar df stands in for it, and
    # without one there is nothing to filter
    assert r.selected_rows("b", df=POINTS)["y"].tolist() == [10, 20]
    with pytest.raises(ValueError, match="'a'"):
        r.selected_rows("b")


def test_selected_rows_nested_repeat_with_its_own_data_is_not_mis_filtered(
    widget_session: Session,
) -> None:
    from shinywidgets import render_altair

    brush = alt.selection_interval(name="b")
    combo = alt.hconcat(
        alt.Chart(POINTS, name="pts").mark_point().encode(x="x", y="y"),
        alt.Chart(LINES)
        .mark_point()
        .encode(x="x:Q", y="z:Q")
        .add_params(brush)
        .repeat(column=["x", "y"]),
        data=POINTS,
    )
    with session_context(widget_session):
        w = alt.JupyterChart(combo)
    views = sa.selection_views(w.chart, "b")
    assert views is not None and len(views) == 2
    r = render_altair()
    r._widget = w
    r._accessors.on_render(w)
    w.local_tz = "UTC"
    r._accessors.values["selected"].set(
        sa_box(
            {
                "b": IntervalSelection(
                    name="b",
                    value={},
                    store=[uentry(view, ("x", "R", [1, 2])) for view in views],
                )  # type: ignore[arg-type]
            }
        )
    )
    # The repeat declares its own data (LINES) but the concat's root is
    # POINTS: resolving the generated views to the root frame would
    # silently filter the wrong rows, so the call must raise instead
    with pytest.raises(ValueError, match="df="):
        r.selected_rows("b")
    # A scalar df can't stand in for two distinct datasets either
    with pytest.raises(ValueError, match="dict"):
        r.selected_rows("b", df=LINES)


def test_selection_views_reads_imported_param_names() -> None:
    brush = alt.selection_interval(name="brush")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        combo = alt.hconcat(
            alt.Chart(POINTS, name="pts")
            .mark_point()
            .encode(x="x", y="y")
            .add_params(brush),
            alt.Chart(LINES, name="lns")
            .mark_point()
            .encode(x="x", y="z")
            .add_params(brush),
        )
    # from_dict wraps parameter names in schema objects (ParameterName);
    # the declared views must still be readable
    imported = alt.Chart.from_dict(combo.to_dict())
    assert sa.selection_views(imported, "brush") == ["pts", "lns"]


def test_selected_rows_unreadable_views_reject_scalar_df_on_multi_dataset(
    widget_session: Session,
) -> None:
    from shinywidgets import render_altair

    r = render_altair()
    with session_context(widget_session):
        w = hconcat_chart()
    # Simulate a chart whose selection participation can't be read (e.g.
    # alt.Chart.from_dict): selected_rows() falls back to the store's units
    w.chart.params[0].views = alt.Undefined
    r._widget = w
    r._accessors.on_render(w)
    w.local_tz = "UTC"
    r._accessors.values["selected"].set(
        sa_box(
            {
                "brush": IntervalSelection(
                    name="brush",
                    value={},
                    store=[uentry("lns", ("z", "R", [150, 250]))],
                )  # type: ignore[arg-type]
            }
        )
    )
    # Only "lns" reports entries, but the selection may participate in more
    # views: neither a scalar df nor the chart's own frames can be matched
    # to their views safely
    with pytest.raises(ValueError, match="dict"):
        r.selected_rows("brush", df=POINTS)
    with pytest.raises(ValueError, match="dict"):
        r.selected_rows("brush")
    out = r.selected_rows("brush", df={"lns": LINES})
    assert isinstance(out, dict)
    assert out["lns"]["z"].tolist() == [200]


def test_selected_rows_empty_views_means_unknown_participation(
    widget_session: Session,
) -> None:
    from shinywidgets import render_altair

    r = render_altair()
    with session_context(widget_session):
        w = hconcat_chart()
    # An empty views list means the selection may apply to any view (Vega
    # semantics): participation is unknown, not "no views"
    w.chart.params[0].views = []
    r._widget = w
    r._accessors.on_render(w)
    w.local_tz = "UTC"
    r._accessors.values["selected"].set(
        sa_box(
            {
                "brush": IntervalSelection(
                    name="brush",
                    value={},
                    store=[uentry("lns", ("z", "R", [150, 250]))],
                )  # type: ignore[arg-type]
            }
        )
    )
    # The store entry belongs to "lns": filtering the chart's root frame
    # would silently return the wrong rows
    with pytest.raises(ValueError, match="dict"):
        r.selected_rows("brush")


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


@pytest.mark.parametrize("lib", ["pandas", "polars"])
def test_tz_aware_brush_within_a_repeated_hour(lib: str) -> None:
    # 2024-11-03 01:00-02:00 happens twice in America/Chicago: 06:45Z is 01:45
    # CDT and 07:15Z is 01:15 CST, so the bounds' wall times run backwards
    t = pd.date_range("2024-11-03 06:00", periods=13, freq="10min", tz="UTC")
    df = pd.DataFrame({"t": t.tz_convert("America/Chicago"), "y": range(13)})
    frame = df if lib == "pandas" else pl.from_pandas(df)
    brush = [entry(("t", "R", ["2024-11-03T06:45:00Z", "2024-11-03T07:15:00Z"]))]
    out = sa.filter_selection(interval(brush), frame, None)
    assert list(out["y"]) == [5, 6, 7]  # 06:50Z, 07:00Z, 07:10Z


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


def test_selected_rows_follows_a_rerender_with_new_data(
    widget_session: Session,
) -> None:
    # A new chart starts with the same (empty) selection as the previous one,
    # so the accessor publishes nothing: readers have to follow the widget
    from shinywidgets import render_altair

    other = pd.DataFrame({"date": DATES["date"], "z": range(30)})
    with session_context(widget_session):
        first = chart(alt.selection_interval(name="brush"))
        second = chart(alt.selection_interval(name="brush"), data=other)
    r = render_altair()
    seen = reads_across_rerender(
        r, first, second, lambda: list(r.selected_rows().columns)
    )
    assert seen == [["date", "y"], ["date", "z"]]
