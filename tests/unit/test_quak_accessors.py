from __future__ import annotations

from typing import List
from unittest.mock import patch

import pandas as pd
import pytest
import shinywidgets._quak as sq
from shiny import Session
from shiny.session import session_context
from shiny.types import SilentException
from shinywidgets import render_quak

pytest.importorskip("quak")
from quak import Widget as QuakWidget  # noqa: E402

DF = pd.DataFrame({"x": [1, 2, 3], "y": ["a", "b", "c"]})


def widget(session: Session) -> QuakWidget:
    with session_context(session):
        return QuakWidget(DF)


def renderer(w: QuakWidget, **kwargs) -> "render_quak[object]":
    r = render_quak(**kwargs)
    r._widget = w  # stands in for _render()
    r._accessors.on_render(w)
    return r


def test_sql_seeds_current_query_and_follows_the_trait(
    widget_session: Session,
) -> None:
    w = widget(widget_session)
    emitted: List[object] = []
    detach = sq.SQL.attach(w, emitted.append)
    assert emitted == ['SELECT * FROM "df"']  # seeded at attach
    w.sql = 'SELECT * FROM "df" WHERE "x" > 1'
    assert emitted[-1] == 'SELECT * FROM "df" WHERE "x" > 1'
    detach()
    w.sql = "SELECT 1"
    assert len(emitted) == 2


def test_sql_declares_the_stream_debounce_default() -> None:
    assert sq.SQL.rate_policy == "debounce"
    assert sq.SQL.rate_delay == 0.25


def test_empty_query_cancels_like_a_not_yet_rendered_output(
    widget_session: Session,
) -> None:
    r = renderer(widget(widget_session), rate_delay=0)
    assert r.sql() == 'SELECT * FROM "df"'
    w = r.widget
    assert isinstance(w, QuakWidget)
    w.sql = ""  # what the browser briefly syncs while it initializes
    with pytest.raises(SilentException):
        r.sql()
    w.sql = 'SELECT * FROM "df" ORDER BY "x"'
    assert r.sql() == 'SELECT * FROM "df" ORDER BY "x"'


def test_data_runs_the_current_query(widget_session: Session) -> None:
    r = renderer(widget(widget_session), rate_delay=0)
    assert len(r.data().df()) == 3
    w = r.widget
    assert isinstance(w, QuakWidget)
    w.sql = 'SELECT * FROM "df" WHERE "x" > 1'
    assert len(r.data().df()) == 2


def test_data_runs_the_published_query_not_widget_data(
    widget_session: Session,
) -> None:
    r = renderer(widget(widget_session), rate_delay=0)
    # data() runs the published (debounced) query on the widget's DuckDB
    # connection, not the widget's own live-state data(), so data() and
    # sql() always describe the same state
    with patch.object(QuakWidget, "data", side_effect=AssertionError):
        assert len(r.data().df()) == 3
