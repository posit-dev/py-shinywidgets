from __future__ import annotations

from typing import Any, Callable, Dict, List

import pandas as pd
import polars as pl
import pytest
import shinywidgets._plotly as sp

CLICK_POINTS = [
    {"trace_index": 0, "point_index": 2, "x": 3, "y": 30, "customdata": [2]},
    {"trace_index": 1, "point_index": 0, "x": 1, "y": 10, "customdata": [0]},
]


class FakeFigureWidget:
    """Records on_msg handlers and sent messages, like an ipywidgets Widget."""

    def __init__(self) -> None:
        self.handlers: List[Callable[[Any, Any, Any], None]] = []
        self.sent: List[Dict[str, Any]] = []

    def on_msg(self, fn: Callable[[Any, Any, Any], None], remove: bool = False) -> None:
        if remove:
            self.handlers.remove(fn)
        else:
            self.handlers.append(fn)

    def send(self, content: Dict[str, Any]) -> None:
        self.sent.append(content)

    def message(self, content: Dict[str, Any]) -> None:
        for fn in list(self.handlers):
            fn(self, content, [])


def event(name: str, **data: Any) -> Dict[str, Any]:
    return {"shinywidgets": "event", "event": name, **data}


def attach(spec: Any) -> tuple[FakeFigureWidget, List[object], Callable[[], None]]:
    w = FakeFigureWidget()
    emitted: List[object] = []
    detach = spec.attach(w, emitted.append)
    return w, emitted, detach


def test_points_frame_columns() -> None:
    df = sp.points_frame(CLICK_POINTS)
    assert list(df.columns) == ["trace_index", "point_index", "x", "y", "customdata"]
    assert df["point_index"].tolist() == [2, 0]


def test_points_frame_empty_has_core_columns() -> None:
    df = sp.points_frame([])
    assert len(df) == 0
    assert list(df.columns) == ["trace_index", "point_index", "x", "y"]


def test_points_frame_keeps_z_when_present() -> None:
    df = sp.points_frame([{"trace_index": 0, "point_index": 0, "x": 1, "y": 2, "z": 3}])
    assert list(df.columns) == ["trace_index", "point_index", "x", "y", "z"]


def test_clicked_binds_its_events_and_emits_points() -> None:
    w, emitted, _ = attach(sp.CLICKED)
    assert w.sent == [
        {
            "shinywidgets": "bind",
            "events": ["plotly_click", "plotly_doubleclick", "plotly_deselect"],
        }
    ]
    w.message(event("plotly_click", points=CLICK_POINTS))
    assert emitted == [CLICK_POINTS]


def test_clicked_cleared_by_doubleclick_and_deselect() -> None:
    w, emitted, _ = attach(sp.CLICKED)
    w.message(event("plotly_doubleclick"))
    w.message(event("plotly_deselect"))
    assert emitted == [None, None]


def test_bridge_ignores_foreign_messages_and_other_events() -> None:
    w, emitted, _ = attach(sp.CLICKED)
    w.message({"method": "something", "event": "plotly_click"})
    w.message(event("plotly_selected", points=[]))
    assert emitted == []


def test_detach_removes_handler() -> None:
    w, emitted, detach = attach(sp.CLICKED)
    detach()
    w.message(event("plotly_click", points=CLICK_POINTS))
    assert emitted == [] and w.handlers == []


def test_selected_empty_selection_is_empty_not_none() -> None:
    w, emitted, _ = attach(sp.SELECTED)
    w.message(event("plotly_selected", points=[]))
    w.message(
        event("plotly_selected")
    )  # plotly.js sends no data when nothing was selected
    assert emitted == [[], None]


def test_brushed_emits_native_region() -> None:
    w, emitted, _ = attach(sp.BRUSHED)
    w.message(event("plotly_selected", points=[], range={"x": [1, 2], "y": [3, 4]}))
    w.message(event("plotly_selected", points=[], lassoPoints={"x": [1], "y": [2]}))
    w.message(event("plotly_deselect"))
    assert emitted == [
        {"range": {"x": [1, 2], "y": [3, 4]}},
        {"lassoPoints": {"x": [1], "y": [2]}},
        None,
    ]


def test_streaming_variants_listen_to_selecting_and_debounce() -> None:
    assert sp.SELECTING.rate_policy == "debounce"
    assert sp.BRUSHING.rate_policy == "debounce"
    assert sp.SELECTED.rate_policy is None
    w, emitted, _ = attach(sp.BRUSHING)
    assert w.sent[0]["events"] == [
        {"name": "plotly_selecting", "payload": "region"},
        "plotly_deselect",
    ]
    w.message(event("plotly_selecting", points=[], range={"x": [0, 1]}))
    assert emitted == [{"range": {"x": [0, 1]}}]


def test_relayout_filters_to_axis_ranges_and_skips_the_rest() -> None:
    w, emitted, _ = attach(sp.RELAYOUT)
    w.message(event("plotly_relayout", relayout={"autosize": True}))
    w.message(event("plotly_relayout", relayout={"dragmode": "select"}))
    w.message(
        event(
            "plotly_relayout",
            relayout={
                "xaxis.range[0]": 1,
                "xaxis.range[1]": 2,
                "yaxis2.autorange": True,
                "selections": [],
            },
        )
    )
    assert emitted == [
        {"xaxis.range[0]": 1, "xaxis.range[1]": 2, "yaxis2.autorange": True}
    ]


def test_selected_rows_by_position_pandas() -> None:
    df = pd.DataFrame({"a": [10, 20, 30]})
    out = sp.select_rows(CLICK_POINTS, df, key=None)
    assert out["a"].tolist() == [10, 30]  # original order, not selection order


def test_selected_rows_by_key_polars() -> None:
    df = pl.DataFrame({"id": [0, 1, 2], "a": [10, 20, 30]})
    pts = [{"trace_index": 0, "point_index": 9, "x": 0, "y": 0, "customdata": 1}]
    out = sp.select_rows(pts, df, key="id")
    assert isinstance(out, pl.DataFrame)
    assert out["a"].to_list() == [20]


def test_selected_rows_none_is_empty_frame() -> None:
    df = pd.DataFrame({"a": [1, 2]})
    out = sp.select_rows(None, df, key=None)
    assert (
        isinstance(out, pd.DataFrame) and len(out) == 0 and list(out.columns) == ["a"]
    )


def test_selected_rows_requires_customdata() -> None:
    pts = [{"trace_index": 0, "point_index": 0, "x": 0, "y": 0}]
    with pytest.raises(ValueError, match="custom_data"):
        sp.select_rows(pts, pd.DataFrame({"a": [1]}), key=None)


def test_hover_binds_hover_and_unhover_and_emits_points() -> None:
    w, emitted, _ = attach(sp.HOVER)
    assert w.sent == [
        {"shinywidgets": "bind", "events": ["plotly_hover", "plotly_unhover"]}
    ]
    w.message(event("plotly_hover", points=CLICK_POINTS))
    assert emitted == [CLICK_POINTS]


def test_hover_cleared_by_unhover_and_debounced() -> None:
    assert sp.HOVER.rate_policy == "debounce"
    w, emitted, _ = attach(sp.HOVER)
    w.message(event("plotly_unhover"))
    assert emitted == [None]


def test_double_clicked_is_a_republishing_pulse() -> None:
    assert sp.DOUBLE_CLICKED.priority == "event"
    w, emitted, _ = attach(sp.DOUBLE_CLICKED)
    assert w.sent == [{"shinywidgets": "bind", "events": ["plotly_doubleclick"]}]
    w.message(event("plotly_doubleclick"))
    w.message(event("plotly_doubleclick"))
    assert emitted == [True, True]


LEGEND_TRACES = [
    {"trace_index": 2, "name": "c", "legendgroup": "g1"},
    {"trace_index": 0, "name": "a", "legendgroup": "g1"},
]

VISIBLE_TRACES = [
    {"trace_index": 0, "name": "a", "visible": True},
    {"trace_index": 1, "name": "b", "visible": False},
]


def test_legend_clicked_emits_minimal_traces_and_republishes() -> None:
    assert sp.LEGEND_CLICKED.priority == "event"
    w, emitted, _ = attach(sp.LEGEND_CLICKED)
    assert w.sent == [{"shinywidgets": "bind", "events": ["plotly_legendclick"]}]
    msg = event("plotly_legendclick", legend={"traces": LEGEND_TRACES})
    w.message(msg)
    w.message(msg)
    assert emitted == [LEGEND_TRACES, LEGEND_TRACES]


def test_legend_clicked_skips_messages_without_legend_data() -> None:
    w, emitted, _ = attach(sp.LEGEND_CLICKED)
    w.message(event("plotly_legendclick"))
    assert emitted == []


def test_visible_traces_binds_restyle_update_and_redraw() -> None:
    w, emitted, _ = attach(sp.VISIBLE_TRACES)
    assert w.sent == [
        {
            "shinywidgets": "bind",
            "events": ["plotly_restyle", "plotly_update", "plotly_redraw"],
        }
    ]
    w.message(event("plotly_restyle", traces=VISIBLE_TRACES))
    assert emitted == [VISIBLE_TRACES]
    # Plotly.update (plotly.py's batch_update) emits plotly_update instead
    w.message(event("plotly_update", traces=VISIBLE_TRACES))
    assert emitted == [VISIBLE_TRACES, VISIBLE_TRACES]
    # add/delete/moveTraces redraw, emitting plotly_redraw
    w.message(event("plotly_redraw", traces=VISIBLE_TRACES))
    assert emitted == [VISIBLE_TRACES] * 3
    # A restyle message without trace visibility (shouldn't happen) is skipped
    w.message(event("plotly_restyle"))
    assert emitted == [VISIBLE_TRACES] * 3


def test_specs_have_expected_names() -> None:
    names: List[str] = [s.name for s in sp.PLOTLY_ACCESSORS]
    assert names == [
        "clicked",
        "selected",
        "selecting",
        "brushed",
        "brushing",
        "relayout",
        "hover",
        "double_clicked",
        "legend_clicked",
        "visible_traces",
    ]


def rendered(*listen_to: str) -> tuple[Any, FakeFigureWidget]:
    from shinywidgets import render_plotly

    r = render_plotly(listen_to=list(listen_to))
    w = FakeFigureWidget()
    r._accessors.on_render(w)
    return r, w


def test_render_plotly_clicked_returns_points_frame() -> None:
    r, w = rendered()
    assert r.clicked() is None
    w.message(event("plotly_click", points=CLICK_POINTS))
    clicked = r.clicked()
    assert isinstance(clicked, pd.DataFrame)
    assert clicked["x"].tolist() == [3, 1]


def test_render_plotly_selected_rows() -> None:
    r, w = rendered("selected")
    df = pd.DataFrame({"a": [10, 20, 30]})
    assert len(r.selected_rows(df)) == 0  # attaches; nothing selected yet
    w.message(event("plotly_selected", points=CLICK_POINTS))
    assert r.selected_rows(df)["a"].tolist() == [10, 30]


def test_render_plotly_hover_returns_points_frame() -> None:
    # rate_delay=0: the debounce is pinned separately on the spec, and the
    # limiter would need a running event loop here
    from shinywidgets import render_plotly

    r = render_plotly(rate_delay=0, listen_to=["hover"])
    w = FakeFigureWidget()
    r._accessors.on_render(w)
    assert r.hover() is None
    w.message(event("plotly_hover", points=CLICK_POINTS))
    hovered = r.hover()
    assert isinstance(hovered, pd.DataFrame)
    assert hovered["y"].tolist() == [30, 10]
    w.message(event("plotly_unhover"))
    assert r.hover() is None


def test_render_plotly_double_clicked_pulses() -> None:
    r, w = rendered()
    assert r.double_clicked() is None
    w.message(event("plotly_doubleclick"))
    assert r.double_clicked() is True


def test_render_plotly_legend_clicked_returns_frame() -> None:
    r, w = rendered()
    assert r.legend_clicked() is None
    w.message(event("plotly_legendclick", legend={"traces": LEGEND_TRACES}))
    clicked = r.legend_clicked()
    assert isinstance(clicked, pd.DataFrame)
    assert list(clicked.columns) == ["trace_index", "name", "legendgroup"]
    assert clicked["trace_index"].tolist() == [2, 0]


def test_render_plotly_visible_traces_returns_frame() -> None:
    r, w = rendered()
    assert r.visible_traces() is None
    w.message(event("plotly_restyle", traces=VISIBLE_TRACES))
    visible = r.visible_traces()
    assert isinstance(visible, pd.DataFrame)
    assert visible["visible"].tolist() == [True, False]


def test_render_plotly_brushed_and_relayout() -> None:
    r, w = rendered()
    assert r.brushed() is None and r.relayout() is None
    w.message(event("plotly_selected", points=[], range={"x": [0, 1]}))
    w.message(event("plotly_relayout", relayout={"xaxis.autorange": True}))
    assert r.brushed() == {"range": {"x": [0, 1]}}
    assert r.relayout() == {"xaxis.autorange": True}


def test_all_accessors_are_retained_and_bind_at_render() -> None:
    # Every accessor is retained last-interaction state and binds at render:
    # the browser only reports an event with a listener, and an interaction
    # made before the first read is not lost.
    r, w = rendered("selected", "selecting", "hover")
    for spec in sp.PLOTLY_ACCESSORS:
        assert spec.kind == "state", spec.name
    assert w.sent == [
        {
            "shinywidgets": "bind",
            "events": ["plotly_click", "plotly_doubleclick", "plotly_deselect"],
        },
        {
            "shinywidgets": "bind",
            "events": [
                {"name": "plotly_selected", "payload": "points"},
                "plotly_deselect",
            ],
        },
        {
            "shinywidgets": "bind",
            "events": [
                {"name": "plotly_selecting", "payload": "points"},
                "plotly_deselect",
            ],
        },
        {
            "shinywidgets": "bind",
            "events": [
                {"name": "plotly_selected", "payload": "region"},
                "plotly_deselect",
            ],
        },
        {
            "shinywidgets": "bind",
            "events": [
                {"name": "plotly_selecting", "payload": "region"},
                "plotly_deselect",
            ],
        },
        {"shinywidgets": "bind", "events": ["plotly_relayout"]},
        {"shinywidgets": "bind", "events": ["plotly_hover", "plotly_unhover"]},
        {"shinywidgets": "bind", "events": ["plotly_doubleclick"]},
        {"shinywidgets": "bind", "events": ["plotly_legendclick"]},
        {
            "shinywidgets": "bind",
            "events": ["plotly_restyle", "plotly_update", "plotly_redraw"],
        },
    ]


def test_selection_reported_before_first_read_survives() -> None:
    r, w = rendered("selected")
    # The bind's seed (or an event) arrives before anything reads the accessor
    w.message(event("plotly_selected", points=CLICK_POINTS))
    selected = r.selected()
    assert isinstance(selected, pd.DataFrame)
    assert selected["point_index"].tolist() == [2, 0]


def test_rerender_keeps_selection_until_the_new_plot_reports() -> None:
    r, w = rendered("selected")
    w.message(event("plotly_selected", points=CLICK_POINTS))
    assert r.selected() is not None
    # State accessors don't reset on re-render ...
    w2 = FakeFigureWidget()
    r._accessors.on_render(w2)
    assert r.selected() is not None
    # ... the new plot's seed (no selection: a no-data plotly_selected) clears it
    w2.message(event("plotly_selected"))
    assert r.selected() is None
    assert r.brushed() is None
    # And the old widget's handlers are gone
    w.message(event("plotly_selected", points=CLICK_POINTS))
    assert r.selected() is None


def test_selected_rows_requires_a_key_for_non_pandas_frames() -> None:
    # Their rows have no labels, and positions break once the frame is filtered
    df = pl.DataFrame({"a": [10, 20, 30]})
    pts = [{"trace_index": 0, "point_index": 0, "x": 0, "y": 0, "customdata": [2]}]
    with pytest.raises(ValueError, match="key="):
        sp.select_rows(pts, df, key=None)
    with pytest.raises(ValueError, match="key="):
        sp.select_rows(None, df, key=None)


def test_render_plotly_selected_rows_key_is_keyword_only() -> None:
    r, _ = rendered()
    with pytest.raises(TypeError, match="positional"):
        r.selected_rows(pd.DataFrame({"a": [1]}), "a")


def test_selected_rows_matches_pandas_index_labels() -> None:
    df = pd.DataFrame({"a": range(10)}).iloc[5:]  # labels 5..9
    pts = [{"trace_index": 0, "point_index": 0, "x": 0, "y": 0, "customdata": [5]}]
    assert sp.select_rows(pts, df, key=None)["a"].tolist() == [5]
    labelled = pd.DataFrame({"a": [1, 2]}, index=["p", "q"])
    pts = [{"trace_index": 0, "point_index": 0, "x": 0, "y": 0, "customdata": ["q"]}]
    assert sp.select_rows(pts, labelled, key=None)["a"].tolist() == [2]


def test_event_origin_accessors_are_retained() -> None:
    from shinywidgets._plotly import BRUSHING, CLICKED, RELAYOUT, SELECTING

    for spec in (CLICKED, SELECTING, BRUSHING, RELAYOUT):
        assert spec.kind == "state", spec.name


def test_selected_binds_points_payload_and_is_opt_in() -> None:
    assert sp.SELECTED.opt_in and sp.SELECTING.opt_in
    w = FakeFigureWidget()
    sp.SELECTED.attach(w, lambda v: None)
    assert w.sent == [
        {
            "shinywidgets": "bind",
            "events": [
                {"name": "plotly_selected", "payload": "points"},
                "plotly_deselect",
            ],
        }
    ]


def test_brushed_binds_region_payload_and_is_default_on() -> None:
    assert not sp.BRUSHED.opt_in and not sp.BRUSHING.opt_in
    w = FakeFigureWidget()
    sp.BRUSHED.attach(w, lambda v: None)
    assert w.sent == [
        {
            "shinywidgets": "bind",
            "events": [
                {"name": "plotly_selected", "payload": "region"},
                "plotly_deselect",
            ],
        }
    ]


def test_hover_is_opt_in() -> None:
    assert sp.HOVER.opt_in
    assert not sp.CLICKED.opt_in


def test_selection_frame_drops_coordinates_keeps_customdata() -> None:
    points = [
        {"trace_index": 0, "point_index": 3, "x": 1.5, "y": 2.5, "customdata": "row-3"}
    ]
    frame = sp.selection_frame(points)
    assert list(frame.columns) == ["trace_index", "point_index", "customdata"]
    full = sp.points_frame(points)
    assert list(full.columns) == ["trace_index", "point_index", "x", "y", "customdata"]
