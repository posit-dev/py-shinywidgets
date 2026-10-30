from __future__ import annotations

from typing import List

import pandas as pd
import pytest
import shinywidgets._mosaic_widget as sm
from shiny import Session
from shiny.session import session_context
from shinywidgets import render_mosaic_widget

pytest.importorskip("mosaic_widget")
from mosaic_widget import MosaicWidget  # noqa: E402

SPEC = {"plot": [{"mark": "dot", "data": {"from": "t"}, "x": "x", "y": "y"}]}
DF = pd.DataFrame({"x": [1, 2, 3], "y": ["a", "b", "c"]})


def widget(session: Session) -> MosaicWidget:
    with session_context(session):
        return MosaicWidget(SPEC, data={"t": DF})


def renderer(w: MosaicWidget, **kwargs) -> "render_mosaic_widget":
    r = render_mosaic_widget(**kwargs)
    r._widget = w  # stands in for _render()
    r._accessors.on_render(w)
    return r


def test_params_seeds_empty_and_follows_the_trait(widget_session: Session) -> None:
    w = widget(widget_session)
    emitted: List[object] = []
    detach = sm.PARAMS.attach(w, emitted.append)
    assert emitted == [{}]  # no selections yet
    w.params = {"brush": {"value": None, "predicate": '"x" > 1'}}
    assert emitted[-1] == {"brush": {"value": None, "predicate": '"x" > 1'}}
    detach()
    w.params = {}
    assert len(emitted) == 2


def test_params_declares_the_stream_debounce_default() -> None:
    assert sm.PARAMS.rate_policy == "debounce"
    assert sm.PARAMS.rate_delay == 0.25


def test_data_queries_with_the_current_predicates(widget_session: Session) -> None:
    w = widget(widget_session)
    r = renderer(w, rate_delay=0)
    assert len(r.data().df()) == 3
    w.params = {"brush": {"value": None, "predicate": '"x" > 1'}}
    assert len(r.data().df()) == 2
    w.params = {}
    assert len(r.data().df()) == 3
