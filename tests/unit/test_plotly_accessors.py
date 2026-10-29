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
    assert w.sent[0]["events"] == ["plotly_selecting", "plotly_deselect"]
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


def test_specs_have_expected_names() -> None:
    names: List[str] = [s.name for s in sp.PLOTLY_ACCESSORS]
    assert names == [
        "clicked",
        "selected",
        "selecting",
        "brushed",
        "brushing",
        "relayout",
    ]


def rendered() -> tuple[Any, FakeFigureWidget]:
    from shinywidgets import render_plotly

    r = render_plotly()
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
    r, w = rendered()
    df = pd.DataFrame({"a": [10, 20, 30]})
    assert len(r.selected_rows(df)) == 0  # attaches; nothing selected yet
    w.message(event("plotly_selected", points=CLICK_POINTS))
    assert r.selected_rows(df)["a"].tolist() == [10, 30]


def test_render_plotly_brushed_and_relayout() -> None:
    r, w = rendered()
    assert r.brushed() is None and r.relayout() is None
    w.message(event("plotly_selected", points=[], range={"x": [0, 1]}))
    w.message(event("plotly_relayout", relayout={"xaxis.autorange": True}))
    assert r.brushed() == {"range": {"x": [0, 1]}}
    assert r.relayout() == {"xaxis.autorange": True}


def test_selected_rows_by_position_accepts_float_customdata_polars() -> None:
    df = pl.DataFrame({"a": [10, 20, 30]})
    pts = [{"trace_index": 0, "point_index": 0, "x": 0, "y": 0, "customdata": [2.0]}]
    assert sp.select_rows(pts, df, key=None)["a"].to_list() == [30]


def test_selected_rows_matches_pandas_index_labels() -> None:
    df = pd.DataFrame({"a": range(10)}).iloc[5:]  # labels 5..9
    pts = [{"trace_index": 0, "point_index": 0, "x": 0, "y": 0, "customdata": [5]}]
    assert sp.select_rows(pts, df, key=None)["a"].tolist() == [5]
    labelled = pd.DataFrame({"a": [1, 2]}, index=["p", "q"])
    pts = [{"trace_index": 0, "point_index": 0, "x": 0, "y": 0, "customdata": ["q"]}]
    assert sp.select_rows(pts, labelled, key=None)["a"].tolist() == [2]


def test_selected_rows_positions_must_be_integers_polars() -> None:
    df = pl.DataFrame({"a": [1, 2]})
    pts = [{"trace_index": 0, "point_index": 0, "x": 0, "y": 0, "customdata": ["q"]}]
    with pytest.raises(ValueError, match="key="):
        sp.select_rows(pts, df, key=None)
