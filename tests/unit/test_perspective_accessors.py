from __future__ import annotations

from typing import List

import pytest
import shinywidgets._perspective as sp
from shiny import Session
from shiny.session import session_context
from shinywidgets import render_perspective

pytest.importorskip("perspective")
pd = pytest.importorskip("pandas")
pytest.importorskip("pyarrow")

from perspective.widget import PerspectiveWidget  # noqa: E402

DF = pd.DataFrame({"x": [1, 2, 3], "y": ["a", "b", "c"]})


def widget(session: Session) -> PerspectiveWidget:
    with session_context(session):
        return PerspectiveWidget(DF)


def test_filter_seeds_empty_and_follows_the_trait(widget_session: Session) -> None:
    w = widget(widget_session)
    emitted: List[object] = []
    detach = sp.FILTER.attach(w, emitted.append)
    assert emitted == [[]]
    w.filter = [["x", ">", 1]]
    assert emitted[-1] == [["x", ">", 1]]
    detach()
    w.filter = []
    assert len(emitted) == 2


def test_view_config_holds_the_structural_keys(widget_session: Session) -> None:
    w = widget(widget_session)
    emitted: List[object] = []
    detach = sp.VIEW_CONFIG.attach(w, emitted.append)
    assert len(emitted) == 1
    cfg = emitted[0]
    assert set(cfg) == set(sp.CONFIG_KEYS)
    assert cfg["plugin"] == "Datagrid"
    detach()

    # The documented way to reproduce the rows: Table.view() rejects the
    # viewer-only `plugin` key, so it's excluded before forwarding
    with pytest.raises(Exception, match="plugin"):
        w.table.view(**cfg)
    w.table.view(**{k: v for k, v in cfg.items() if k != "plugin"})

    # A cosmetic change emits nothing; a structural one emits once
    emitted2: List[object] = []
    sp.VIEW_CONFIG.attach(w, emitted2.append)
    n = len(emitted2)
    w.settings = False
    assert len(emitted2) == n
    w.sort = [["x", "desc"]]
    assert len(emitted2) == n + 1
    assert emitted2[-1]["sort"] == [["x", "desc"]]


def test_renderer_reads(widget_session: Session) -> None:
    w = widget(widget_session)
    r = render_perspective()
    r._widget = w  # stands in for _render()
    r._accessors.on_render(w)
    assert r.filter() == []
    assert r.view_config()["filter"] == []
    w.filter = [["x", ">", 1]]
    assert r.filter() == [["x", ">", 1]]
    assert r.view_config()["filter"] == [["x", ">", 1]]
