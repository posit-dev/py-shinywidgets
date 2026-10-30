from __future__ import annotations

import pandas as pd
import shinywidgets._ipydatagrid as sd
from shiny import Session
from shiny.session import session_context
from shinywidgets._accessors import Accessors

from tests.unit.test_accessors import FakeSchedule


def grid(session: Session, **kwargs: object) -> object:
    from ipydatagrid import DataGrid

    with session_context(session):
        return DataGrid(
            pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]}),
            selection_mode="row",
            editable=True,
            **kwargs,
        )


def test_selections_stream_debounces_by_default(widget_session: Session) -> None:
    # Dragging a selection rectangle streams `selections` continuously, so
    # (like other selection streams) the accessor debounces by default and
    # the renderer's rate_policy/rate_delay kwargs apply to it.
    assert sd.SELECTIONS.rate_policy == "debounce"

    g = grid(widget_session)
    s = FakeSchedule()
    a = Accessors([sd.SELECTIONS], schedule=s)
    a.on_render(g)
    assert a.read("selections") == []  # the seed doesn't wait out the debounce
    g.selections = [{"r1": 0, "r2": 1, "c1": 0, "c2": 0}]
    g.selections = [{"r1": 0, "r2": 2, "c1": 0, "c2": 0}]
    assert a.read("selections") == []  # mid-drag values are held
    s.fire()
    assert a.read("selections") == [{"r1": 0, "r2": 2, "c1": 0, "c2": 0}]


def test_selections_rate_delay_zero_disables_the_debounce(
    widget_session: Session,
) -> None:
    g = grid(widget_session)
    a = Accessors([sd.SELECTIONS], rate_delay=0, schedule=FakeSchedule())
    a.on_render(g)
    a.read("selections")
    g.selections = [{"r1": 0, "r2": 1, "c1": 0, "c2": 0}]
    assert a.read("selections") == [{"r1": 0, "r2": 1, "c1": 0, "c2": 0}]


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


def test_visible_data_follows_the_visible_row_map(widget_session: Session) -> None:
    g = grid(widget_session)
    emitted: list[object] = []
    detach = sd.VISIBLE_ROWS.attach(g, emitted.append)
    assert emitted == [[]]  # [] until the first sort/filter/edit (all rows)
    g._visible_rows = [2, 1, 0]  # what a descending sort syncs
    assert emitted[-1] == [2, 1, 0]
    detach()


def test_visible_data_invalidates_on_a_cell_edit(widget_session: Session) -> None:
    # An edit can change the displayed values without changing the row map
    # (e.g. editing an unsorted text column), so _visible_rows alone can't be
    # the trigger; the cell-change notification must emit a fresh token each
    # time (an equal one would be suppressed by the helper's dedup)
    g = grid(widget_session)
    emitted: list[object] = []
    detach = sd.VISIBLE_ROWS.attach(g, emitted.append)
    assert len(emitted) == 1  # the seed
    g._cell_change_handlers({"row": 1, "column": "b", "column_index": 1, "value": "yy"})
    assert len(emitted) == 2
    assert emitted[-1] is not emitted[0] and not emitted[-1] == emitted[0]
    g._cell_change_handlers({"row": 1, "column": "b", "column_index": 1, "value": "zz"})
    assert len(emitted) == 3
    detach()
    g._cell_change_handlers({"row": 1, "column": "b", "column_index": 1, "value": "ww"})
    assert len(emitted) == 3


def test_visible_data_invalidates_on_a_transform(widget_session: Session) -> None:
    # A zero-match filter straight from the initial state leaves
    # _visible_rows at [] ([] -> [] doesn't fire), so the transforms trait
    # must also be a trigger
    g = grid(widget_session)
    emitted: list[object] = []
    detach = sd.VISIBLE_ROWS.attach(g, emitted.append)
    assert len(emitted) == 1  # the seed
    g._transforms = [{"type": "filter", "column": "a", "operator": ">", "value": 100}]
    assert len(emitted) == 2
    detach()
    g._transforms = []
    assert len(emitted) == 2


def test_visible_data_distinguishes_empty_filter_from_initial(
    widget_session: Session,
) -> None:
    from shinywidgets import render_ipydatagrid

    g = grid(widget_session)
    r = render_ipydatagrid()
    r._widget = g  # stands in for _render()
    r._accessors.on_render(g)
    # Initial state (_visible_rows is [], no transforms): the whole frame
    assert r.visible_data()["a"].tolist() == [1, 2, 3]
    # A filter matching zero rows: an empty frame with the right columns,
    # not the entire frame (get_visible_data() only applies a truthy
    # _visible_rows, so it can't tell these two states apart)
    g._transforms = [{"type": "filter", "column": "a", "operator": ">", "value": 100}]
    out = r.visible_data()
    assert len(out) == 0
    assert list(out.columns) == ["a", "b"]
    # Clearing the filter shows the whole frame again
    g._transforms = []
    assert r.visible_data()["a"].tolist() == [1, 2, 3]


def test_visible_data_invalidates_on_data_replacement(
    widget_session: Session,
) -> None:
    # Assigning new data fires neither on_cell_change nor (necessarily) a
    # _visible_rows change, so _data must also be a trigger
    g = grid(widget_session)
    emitted: list[object] = []
    detach = sd.VISIBLE_ROWS.attach(g, emitted.append)
    assert len(emitted) == 1  # the seed
    g.data = pd.DataFrame({"a": [7, 8, 9], "b": list("qrs")})  # same shape
    assert len(emitted) == 2
    detach()
    g.data = pd.DataFrame({"a": [10], "b": ["t"]})
    assert len(emitted) == 2


def test_visible_data_follows_data_replacement(widget_session: Session) -> None:
    from shinywidgets import render_ipydatagrid

    g = grid(widget_session)
    r = render_ipydatagrid()
    r._widget = g  # stands in for _render()
    r._accessors.on_render(g)
    assert r.visible_data()["a"].tolist() == [1, 2, 3]
    g.data = pd.DataFrame({"a": [7, 8, 9], "b": list("qrs")})
    assert r.visible_data()["a"].tolist() == [7, 8, 9]


def test_visible_data_accessor(widget_session: Session) -> None:
    from shinywidgets import render_ipydatagrid

    g = grid(widget_session)
    r = render_ipydatagrid()
    r._widget = g  # stands in for _render()
    r._accessors.on_render(g)
    assert r.visible_data()["a"].tolist() == [1, 2, 3]
    g._visible_rows = [2, 1, 0]
    assert r.visible_data()["a"].tolist() == [3, 2, 1]
