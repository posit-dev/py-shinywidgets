from __future__ import annotations

import pandas as pd
import pytest
import shinywidgets._embedding_atlas as se
from shiny import Session
from shiny.session import session_context

# embedding-atlas requires Python 3.11+, so it's absent from 3.10 environments
pytest.importorskip("embedding_atlas")


def atlas_widget(session: Session) -> object:
    from embedding_atlas.widget import EmbeddingAtlasWidget

    with session_context(session):
        return EmbeddingAtlasWidget(
            pd.DataFrame(
                {
                    "x": [0.0, 1.0, 2.0, 3.0],
                    "y": [0.0, 1.0, 0.0, 1.0],
                    "text": ["a", "b", "c", "d"],
                    "group": ["g1", "g1", "g2", "g2"],
                }
            ),
            x="x",
            y="y",
            text="text",
        )


def test_predicate_attach_seeds_and_emits(widget_session: Session) -> None:
    w = atlas_widget(widget_session)
    emitted: list[object] = []
    detach = se.PREDICATE.attach(w, emitted.append)
    assert emitted == [None]  # None = no filter
    w._predicate = "((\"group\" = 'g1'))"
    assert emitted[-1] == "((\"group\" = 'g1'))"
    detach()
    w._predicate = None
    assert emitted[-1] == "((\"group\" = 'g1'))"


def test_predicate_and_selection_accessors(widget_session: Session) -> None:
    from shinywidgets import render_embedding_atlas

    w = atlas_widget(widget_session)
    r = render_embedding_atlas(rate_delay=0)
    r._widget = w  # stands in for _render()
    r._accessors.on_render(w)
    assert r.predicate() is None
    # No filter means all rows (library semantics), with __row_index__
    assert len(r.selection()) == 4
    assert "__row_index__" in r.selection().columns
    w._predicate = "((\"group\" = 'g2'))"
    assert r.predicate() == "((\"group\" = 'g2'))"
    assert r.selection()["text"].tolist() == ["c", "d"]
    # A re-render starts the new widget at no-filter
    r._accessors.on_render(atlas_widget(widget_session))
    assert r.predicate() is None
