from __future__ import annotations

import pandas as pd
import shinywidgets._itables as si
from shiny import Session
from shiny.session import session_context


def itable(session: Session) -> object:
    from itables.widget import ITable

    with session_context(session):
        return ITable(
            pd.DataFrame({"n": list(range(5)), "s": list("abcde")}), select=True
        )


def test_selection_rows_attach_seeds_and_emits(widget_session: Session) -> None:
    w = itable(widget_session)
    emitted: list[object] = []
    detach = si.SELECTED_ROWS.attach(w, emitted.append)
    assert emitted == [[]]  # seeded; [] until something is selected
    w.selected_rows = [1, 3]
    assert emitted[-1] == [1, 3]
    detach()
    w.selected_rows = [0]
    assert emitted[-1] == [1, 3]


def test_selection_rows_accessor(widget_session: Session) -> None:
    from shinywidgets import render_itables

    w = itable(widget_session)
    r = render_itables()
    r._widget = w  # stands in for _render()
    r._accessors.on_render(w)
    assert r.selected_rows() == []
    w.selected_rows = [49]  # positions are .iloc positions of the table's df
    assert r.selected_rows() == [49]
