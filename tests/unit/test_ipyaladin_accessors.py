from __future__ import annotations

from typing import TYPE_CHECKING

import shinywidgets._ipyaladin as sa
import shinywidgets._render_widget as rw
from shiny import Session
from shiny.session import session_context

if TYPE_CHECKING:
    from ipyaladin import Aladin

CLICKED = {"ra": 83.6, "dec": 22.0, "data": {"id": 1}}


def make_renderer(aladin: Aladin) -> rw.render_ipyaladin[Aladin]:
    r: rw.render_ipyaladin[Aladin] = rw.render_ipyaladin()
    r._widget = aladin  # stands in for _render()
    r._accessors.on_render(aladin)
    return r


def test_clicked_object_is_a_state_accessor() -> None:
    # Attached at render like every accessor (see Accessors.on_render)
    assert sa.CLICKED_OBJECT.kind == "state"


def test_clicked_object_reads_none_until_a_click(widget_session: Session) -> None:
    from ipyaladin import Aladin

    with session_context(widget_session):
        aladin = Aladin()
    # The synced trait defaults to {} (no click yet) ...
    assert aladin.clicked_object == {}
    r = make_renderer(aladin)
    # ... which the accessor reports as None
    assert r.clicked_object() is None
    # What the browser syncs back on a catalog-source click
    aladin.clicked_object = CLICKED
    assert r.clicked_object() == CLICKED


def test_clicked_object_seeds_a_click_from_before_render(
    widget_session: Session,
) -> None:
    from ipyaladin import Aladin

    with session_context(widget_session):
        aladin = Aladin()
    # A click that synced before the render (e.g. on a re-rendered widget the
    # user kept interacting with) is picked up by the seed at attach
    aladin.clicked_object = CLICKED
    r = make_renderer(aladin)
    assert r.clicked_object() == CLICKED


def test_clicked_object_reflects_a_click_before_the_first_read(
    widget_session: Session,
) -> None:
    # The accessor attaches at render, so a click that lands
    # before anything reads it -- e.g. a reader gated behind an input -- is
    # reflected in that first read instead of being lost
    from ipyaladin import Aladin

    with session_context(widget_session):
        aladin = Aladin()
    r = make_renderer(aladin)
    aladin.clicked_object = CLICKED
    assert r.clicked_object() == CLICKED


def test_clicked_object_reclicking_the_same_source_does_not_republish(
    widget_session: Session,
) -> None:
    # "Clicking the same source twice doesn't fire twice": traitlets itself
    # doesn't notify on an equal dict, and input priority would dedupe the
    # emit anyway, so the published value keeps its identity
    from ipyaladin import Aladin
    from shiny import reactive

    def published_box() -> object:
        with reactive.isolate():
            return r._accessors.values["clicked_object"].get()

    with session_context(widget_session):
        aladin = Aladin()
    r = make_renderer(aladin)
    aladin.clicked_object = CLICKED
    box = published_box()
    aladin.clicked_object = dict(CLICKED)
    assert published_box() is box
    assert r.clicked_object() == CLICKED


def test_clicked_object_is_per_widget_instance(widget_session: Session) -> None:
    # The retention lives on the widget's own synced trait (the frontend
    # model.set is per model), so a click on one viewer doesn't leak into
    # another -- unlike set_listener, which ipyaladin 0.8.x shares across
    # instances
    from ipyaladin import Aladin

    with session_context(widget_session):
        aladin1 = Aladin()
        aladin2 = Aladin()
    r1 = make_renderer(aladin1)
    r2 = make_renderer(aladin2)
    aladin1.clicked_object = CLICKED
    assert r1.clicked_object() == CLICKED
    assert r2.clicked_object() is None


def test_clicked_object_starts_over_on_rerender(widget_session: Session) -> None:
    # A re-render builds a new viewer, whose synced trait has no click yet;
    # its seed at attach brings the accessor back to None
    from ipyaladin import Aladin

    with session_context(widget_session):
        aladin = Aladin()
    r = make_renderer(aladin)
    aladin.clicked_object = CLICKED
    assert r.clicked_object() == CLICKED
    with session_context(widget_session):
        new_aladin = Aladin()
    r._widget = new_aladin
    r._accessors.on_render(new_aladin)
    assert r.clicked_object() is None


def test_clicked_object_detach_removes_the_trait_observer(
    widget_session: Session,
) -> None:
    from ipyaladin import Aladin

    with session_context(widget_session):
        aladin = Aladin()
    emitted = []
    detach = sa.CLICKED_OBJECT.attach(aladin, emitted.append)
    # The attach seeds the current (empty) value
    assert emitted == [{}]
    detach()
    aladin.clicked_object = CLICKED
    assert emitted == [{}]


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
