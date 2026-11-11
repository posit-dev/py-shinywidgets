from __future__ import annotations

import json
import sys
from typing import List

import pytest
import shinywidgets._render_widget as rw
import shinywidgets._rerun as sr
from shiny import Session
from shiny.session import session_context

pytest.importorskip("numpy")
rr = pytest.importorskip("rerun")
pytest.importorskip("rerun_notebook")

# rerun requires Python 3.11+; pytest.importorskip() skips execution on 3.10,
# but pyright would still resolve these imports statically, so guard them (the
# fallback alias is never used since the module is skipped on 3.10)
if sys.version_info >= (3, 11):
    from rerun.notebook import SelectionChangeEvent
else:
    from typing import Any

    SelectionChangeEvent = Any


def inner_viewer(session: Session):
    with session_context(session):
        rec = rr.RecordingStream(application_id="test_rerun_accessors")
        rec.log("points", rr.Points3D([[0, 0, 0], [1, 1, 1]]))
        from rerun.notebook import Viewer

        return Viewer(recording=rec)._viewer


SELECTION_JSON = json.dumps(
    {
        "type": "selection_change",
        "application_id": "test",
        "recording_id": "rec",
        "segment_id": None,
        "items": [{"type": "entity", "entity_path": "points"}],
    }
)

# The viewer sends this once when it loads, whether or not the user has
# selected anything; a later empty event is a real deselection
EMPTY_SELECTION_JSON = json.dumps(
    {
        "type": "selection_change",
        "application_id": "test",
        "recording_id": "rec",
        "segment_id": None,
        "items": [],
    }
)


def test_selected_ignores_the_load_time_empty_seed(widget_session: Session) -> None:
    # The first empty selection per attach is the viewer's load-time seed and
    # must not be emitted (it would clobber a selection kept across a
    # re-render); a *subsequent* empty event is a real deselection
    widget = inner_viewer(widget_session)
    emitted: List[object] = []
    sr.SELECTED.attach(widget, emitted.append)
    cb = widget._raw_event_callbacks[-1]
    cb(EMPTY_SELECTION_JSON)
    assert emitted == []
    cb(SELECTION_JSON)
    assert len(emitted) == 1
    cb(EMPTY_SELECTION_JSON)
    assert len(emitted) == 2
    evt = emitted[-1]
    assert isinstance(evt, SelectionChangeEvent)
    assert evt.items == []


def test_selected_ignores_a_delayed_load_time_empty_seed(
    widget_session: Session,
) -> None:
    # In the browser, a fast early selection can reach Python before the
    # viewer's asynchronous load-time empty report. The first empty report is
    # still that seed; the next empty report is a real deselection.
    widget = inner_viewer(widget_session)
    emitted: List[object] = []
    sr.SELECTED.attach(widget, emitted.append)
    cb = widget._raw_event_callbacks[-1]
    cb(SELECTION_JSON)
    cb(EMPTY_SELECTION_JSON)
    assert len(emitted) == 1
    cb(EMPTY_SELECTION_JSON)
    assert len(emitted) == 2
    evt = emitted[-1]
    assert isinstance(evt, SelectionChangeEvent)
    assert evt.items == []


def test_selected_emits_parsed_event(widget_session: Session) -> None:
    # Pins the shape of rerun's private _on_raw_event/_viewer_event_from_json_str
    # APIs (Review Focus 5): an upstream change must fail loudly here
    widget = inner_viewer(widget_session)
    emitted: List[object] = []
    sr.SELECTED.attach(widget, emitted.append)
    cb = widget._raw_event_callbacks[-1]
    cb(
        json.dumps(
            {
                "type": "time_update",
                "application_id": "t",
                "recording_id": "r",
                "segment_id": None,
                "time": 1.0,
            }
        )
    )
    assert emitted == []  # non-selection events are filtered before parsing
    cb(SELECTION_JSON)
    assert len(emitted) == 1
    evt = emitted[0]
    assert isinstance(evt, SelectionChangeEvent)
    assert evt.items[0].entity_path == "points"


def test_selected_spec_is_state() -> None:
    # A selection is user-interaction state, so it is kept across re-renders
    assert sr.SELECTED.kind == "state"


def test_selected_detach_is_a_safe_noop(widget_session: Session) -> None:
    # rerun's _on_raw_event has no remove API (upstream TODO), so the detach
    # must tolerate being called and rely on the helper's generation guard to
    # drop stale callbacks (the guard itself is covered by the helper's tests)
    widget = inner_viewer(widget_session)
    before = len(widget._raw_event_callbacks)
    detach = sr.SELECTED.attach(widget, lambda raw: None)
    assert len(widget._raw_event_callbacks) == before + 1
    detach()
    detach()  # must not raise
    assert len(widget._raw_event_callbacks) == before + 1


def test_renderer_selected_round_trips_and_is_retained(
    widget_session: Session,
) -> None:
    widget = inner_viewer(widget_session)
    r = rw.render_rerun()
    r._widget = widget  # stands in for _render()
    r._accessors.on_render(widget)
    assert r.selected() is None
    widget._raw_event_callbacks[-1](SELECTION_JSON)
    evt = r.selected()
    assert isinstance(evt, SelectionChangeEvent)
    # Retained semantics: a re-render keeps the last selection
    r._accessors.on_render(widget)
    assert isinstance(r.selected(), SelectionChangeEvent)
    # ...the new viewer's load-time empty seed doesn't clobber it...
    widget._raw_event_callbacks[-1](EMPTY_SELECTION_JSON)
    assert isinstance(r.selected(), SelectionChangeEvent)
    # ...and the re-attach still reports selections
    widget._raw_event_callbacks[-1](SELECTION_JSON)
    assert isinstance(r.selected(), SelectionChangeEvent)


def test_selected_ignores_events_named_like_the_type_tag(
    widget_session: Session,
) -> None:
    # The cheap prefilter is a substring match, so an application_id of
    # "selection_change" passes it; only the parsed event's type may decide
    widget = inner_viewer(widget_session)
    emitted: List[object] = []
    sr.SELECTED.attach(widget, emitted.append)
    cb = widget._raw_event_callbacks[-1]
    cb(
        json.dumps(
            {
                "type": "time_update",
                "application_id": "selection_change",
                "recording_id": "r",
                "segment_id": None,
                "time": 1.0,
            }
        )
    )
    assert emitted == []


def test_selected_is_retained() -> None:
    from shinywidgets._rerun import SELECTED

    assert SELECTED.kind == "state"
