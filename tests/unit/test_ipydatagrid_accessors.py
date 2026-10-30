from __future__ import annotations

import pandas as pd
import shinywidgets._ipydatagrid as sd
from shiny import Session
from shiny.session import session_context


def grid(session: Session, **kwargs: object) -> object:
    from ipydatagrid import DataGrid

    with session_context(session):
        return DataGrid(
            pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]}),
            selection_mode="row",
            editable=True,
            **kwargs,
        )


def test_selections_attach_seeds_and_emits(widget_session: Session) -> None:
    g = grid(widget_session)
    emitted: list[object] = []
    detach = sd.SELECTIONS.attach(g, emitted.append)
    assert emitted == [[]]
    g.selections = [{"r1": 1, "r2": 2, "c1": 0, "c2": 1}]
    assert emitted[-1] == [{"r1": 1, "r2": 2, "c1": 0, "c2": 1}]
    detach()
    g.selections = []
    assert emitted[-1] == [{"r1": 1, "r2": 2, "c1": 0, "c2": 1}]


def test_cell_clicked_is_an_event_with_detach(widget_session: Session) -> None:
    g = grid(widget_session)
    emitted: list[object] = []
    detach = sd.CELL_CLICKED.attach(g, emitted.append)
    assert emitted == []  # no seed: None until the first click
    click = {
        "region": "body",
        "row": 1,
        "primary_key_row": 2,
        "column": "a",
        "column_index": 0,
        "cell_value": 2,
    }
    g._cell_click_handlers(click)  # what the browser's cell-click message does
    assert emitted == [click]
    detach()
    g._cell_click_handlers(click)
    assert emitted == [click]


def test_cell_edited_is_an_event_with_detach(widget_session: Session) -> None:
    g = grid(widget_session)
    emitted: list[object] = []
    detach = sd.CELL_EDITED.attach(g, emitted.append)
    assert emitted == []
    edit = {"row": 2, "column": "a", "column_index": 0, "value": 555}
    g._cell_change_handlers(edit)  # what the browser's cell-changed message does
    assert emitted == [edit]
    detach()
    g._cell_change_handlers(edit)
    assert emitted == [edit]


def test_ipydatagrid_accessors(widget_session: Session) -> None:
    from shinywidgets import render_ipydatagrid

    g = grid(widget_session)
    r = render_ipydatagrid()
    r._widget = g  # stands in for _render()
    r._accessors.on_render(g)
    assert r.selections() == []
    assert r.cell_clicked() is None
    assert r.cell_edited() is None
    g._cell_click_handlers(
        {
            "region": "body",
            "row": 0,
            "primary_key_row": 0,
            "column": "a",
            "column_index": 0,
            "cell_value": 1,
        }
    )
    assert r.cell_clicked()["cell_value"] == 1
    g._cell_change_handlers({"row": 0, "column": "a", "column_index": 0, "value": 9})
    assert r.cell_edited()["value"] == 9
    # Events reset on re-render; state re-seeds
    r._accessors.on_render(grid(widget_session))
    assert r.cell_clicked() is None and r.cell_edited() is None
    assert r.selections() == []
