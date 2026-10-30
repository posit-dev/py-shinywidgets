from __future__ import annotations

import shinywidgets._ipyaladin as sa
import shinywidgets._render_widget as rw
from shiny import Session
from shiny.session import session_context


def test_clicked_object_reads_object_clicked_messages(widget_session: Session) -> None:
    from ipyaladin import Aladin

    with session_context(widget_session):
        aladin = Aladin()
    r = rw.render_ipyaladin()
    r._widget = aladin  # stands in for _render()
    r._accessors.on_render(aladin)
    assert r.clicked_object() is None
    # What the browser sends on a catalog-source click
    aladin._msg_callbacks(
        aladin,
        {
            "event_type": "object_clicked",
            "content": {"ra": 83.6, "dec": 22.0, "data": {"id": 1}},
        },
        [],
    )
    assert r.clicked_object() == {"ra": 83.6, "dec": 22.0, "data": {"id": 1}}
    # Other event types don't reach it
    aladin._msg_callbacks(aladin, {"event_type": "click", "content": {"ra": 0}}, [])
    assert r.clicked_object() is not None and r.clicked_object()["dec"] == 22.0


def test_clicked_object_detach_removes_the_message_handler(
    widget_session: Session,
) -> None:
    from ipyaladin import Aladin

    with session_context(widget_session):
        aladin = Aladin()
    before = len(aladin._msg_callbacks.callbacks)
    detach = sa.CLICKED_OBJECT.attach(aladin, lambda raw: None)
    assert len(aladin._msg_callbacks.callbacks) == before + 1
    detach()
    assert len(aladin._msg_callbacks.callbacks) == before


def test_state_accessors_seed_and_follow_traits(widget_session: Session) -> None:
    from astropy.coordinates import SkyCoord
    from ipyaladin import Aladin

    with session_context(widget_session):
        aladin = Aladin(target="10 20", fov=5)
    r = rw.render_ipyaladin()
    r._widget = aladin
    r._accessors.on_render(aladin)
    target = r.target()
    assert isinstance(target, SkyCoord) and target.ra.deg == 10
    assert r.fov().deg == 5
    assert r.selected_objects() == []
    aladin._target = "30 40"  # what a browser pan syncs back
    assert r.target().ra.deg == 30
    aladin._selected_objects = [[{"data": {"a": 1}}]]
    tables = r.selected_objects()
    assert len(tables) == 1 and tables[0]["a"][0] == 1
