from __future__ import annotations

import asyncio
import json
import os
import sys
import warnings
from collections.abc import Callable, Coroutine, Iterator
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar

import pytest
import shinywidgets
import shinywidgets._shinywidgets as sw
from ipywidgets import HTML, Button, DOMWidget, IntSlider, VBox, Widget
from packaging.version import Version
from shiny import App, Session, reactive, ui
from shiny._connection import MockConnection
from shiny.reactive._core import Context
from shiny.session import session_context
from shiny.session._session import AppSession
from shinywidgets import session_lifetime, shared_lifetime
from shinywidgets._comm import OrphanedShinyComm, SharedShinyComm, ShinyComm
from shinywidgets._render_widget_base import (
    WidgetRenderContext,
    is_closed_widget,
    render_widget_base,
)
from shinywidgets._widget_registry import WIDGET_INSTANCE_MAP

from tests.unit.conftest import widget_test_server

T = TypeVar("T")


def run(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.get_event_loop().run_until_complete(coro)


def flush() -> None:
    run(reactive.flush())


class IpyvueThing(DOMWidget):
    pass


IpyvueThing.__module__ = "ipyvue.fake"


class OtherThing(DOMWidget):
    pass


OtherThing.__module__ = "otherpkg.fake"


@pytest.fixture
def preimported() -> Iterator[Callable[[type[Widget]], Widget]]:
    """Construct a widget the way one built before `import shinywidgets` would be."""
    built: list[Widget] = []

    def make(cls: type[Widget]) -> Widget:
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(Widget, "_widget_construction_callback", None)
            w = cls()
        built.append(w)
        return w

    yield make
    for w in list(sw.walk_widget_tree(built)):
        w.close()


def test_orphaned_comm_has_no_kernel() -> None:
    assert OrphanedShinyComm("x").kernel is None


def test_ipyvue_does_not_cache_templates_under_shinywidgets(
    widget_session: Session, tmp_path: Path
) -> None:
    path = tmp_path / "template.vue"
    path.write_text("<template><div>hi</div></template>")

    ipyvue = pytest.importorskip("ipyvue")
    if Version(ipyvue.__version__) < Version("3"):
        pytest.skip("ipyvue < 3 caches templates regardless of comm kind")

    template_module = sys.modules["ipyvue.Template"]
    with session_context(widget_session):
        first = template_module.get_template(str(path))
        second = template_module.get_template(str(path))
    try:
        assert first is not second
        assert os.path.normpath(path) not in template_module.template_registry
    finally:
        first.close()
        second.close()


def test_import_time_singleton_requires_listed_package(
    preimported: Callable[[type[Widget]], Widget],
) -> None:
    assert sw.is_process_global(preimported(IpyvueThing))
    assert not sw.is_process_global(preimported(OtherThing))


def test_init_tolerates_widgets_built_while_ipyvue_imports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("ipyvue.ForceLoad", "ipyvuetify.Themes"):
        with monkeypatch.context() as mp:
            mp.setitem(sys.modules, name, ModuleType(name))
            w = HTML()
        for x in list(sw.walk_widget_tree([w])):
            x.close()


@pytest.mark.parametrize("module", ["ipyvue.ForceLoad", "ipyvuetify.Themes"])
def test_widgets_built_while_ipyvue_imports_in_a_render_are_shared(
    widget_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    shared_state: None,
    module: str,
) -> None:
    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            with monkeypatch.context() as mp:
                mp.setitem(sys.modules, module, ModuleType(module))
                w = HTML()
        flush()
        context.invalidate()
        flush()
    for x in (w, w.layout):
        assert sw.SHARED_WIDGETS.get(x.model_id) is x
        assert not is_closed_widget(x)


def test_template_registry_widget_survives_render_invalidation(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    template_module = ModuleType("ipyvue.Template")
    registry: dict[str, Widget] = {}
    setattr(template_module, "template_registry", registry)
    monkeypatch.setitem(sys.modules, "ipyvue.Template", template_module)

    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            t = HTML()
        registry["x.vue"] = t
        flush()
        context.invalidate()
        flush()
    assert not is_closed_widget(t)


def test_shared_construction_in_session_survives_render_and_session_end(
    widget_session: Session, shared_state: None
) -> None:
    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            with sw.shared_construction():
                s = Button()
        flush()
        context.invalidate()
        flush()
    run(widget_session.close())
    assert not is_closed_widget(s)
    assert not is_closed_widget(s.layout)
    assert sw.SHARED_WIDGETS[s.model_id] is s
    assert sw.SHARED_WIDGETS[s.layout.model_id] is s.layout


def test_shared_construction_without_session_records_widget(
    shared_state: None,
) -> None:
    with sw.shared_construction():
        s = HTML()
    assert sw.SHARED_WIDGETS[s.model_id] is s


def test_widget_outside_session_still_raises() -> None:
    with pytest.raises(RuntimeError, match="active Shiny session"):
        HTML()


@pytest.fixture
def other_session() -> Iterator[Session]:
    session = App(ui.page_fluid(), widget_test_server)._create_session(MockConnection())
    try:
        yield session
    finally:
        run(session.close())


def shared_html(session: Session) -> HTML:
    with session_context(session), sw.shared_construction():
        w = HTML()
    flush()
    return w


def test_open_shared_in_keeps_live_comm_and_adds_session(
    widget_session: Session, other_session: Session, shared_state: None
) -> None:
    a, b = widget_session, other_session
    w = shared_html(a)
    ca = w.comm
    sw.open_shared_in(w, b)
    assert isinstance(w.comm, SharedShinyComm)
    assert w.comm.comms[a.id] is ca
    assert w.comm.has_session(b.id)
    assert w.model_id in sw.COMM_MANAGERS[b.id].comms
    assert WIDGET_INSTANCE_MAP[w.model_id] is w
    assert not is_closed_widget(w)

    cb = w.comm.comms[b.id]
    sw.open_shared_in(w, b)
    assert w.comm.comms[b.id] is cb


def test_open_shared_in_initializes_a_session_with_no_widgets(
    widget_session: Session, other_session: Session, shared_state: None
) -> None:
    w = shared_html(widget_session)
    assert other_session not in sw.SESSIONS
    sw.open_shared_in(w, other_session)
    assert other_session in sw.SESSIONS


def test_open_shared_in_uses_root_scope(
    widget_session: Session, other_session: Session, shared_state: None
) -> None:
    w = shared_html(widget_session)
    sw.open_shared_in(w, other_session.make_scope("mod"))
    assert isinstance(w.comm, SharedShinyComm)
    assert w.comm.has_session(other_session.id)


def test_open_shared_in_opens_unowned_references(
    widget_session: Session, other_session: Session, shared_state: None
) -> None:
    with session_context(widget_session), sw.shared_construction():
        child = HTML()
        box = VBox(children=(child,))
    flush()
    sw.open_shared_in(box, other_session)
    assert child.model_id in sw.COMM_MANAGERS[other_session.id].comms


def test_session_end_drops_shared_entry_and_keeps_widget(
    widget_session: Session, other_session: Session, shared_state: None
) -> None:
    a, b = widget_session, other_session
    w = shared_html(a)
    sw.open_shared_in(w, b)
    run(b.close())
    assert isinstance(w.comm, SharedShinyComm)
    assert not w.comm.has_session(b.id)
    assert w.comm.has_session(a.id)
    assert not is_closed_widget(w)


def test_browser_comm_close_keeps_shared_widget_open(
    widget_session: Session, other_session: Session, shared_state: None
) -> None:
    a, b = widget_session, other_session
    w = shared_html(a)
    sw.open_shared_in(w, b)
    close = {
        "header": {"msg_type": "comm_close"},
        "content": {"comm_id": w.model_id, "data": {}},
        "buffers": [],
    }
    with session_context(b):
        sw.handle_client_comm_msg(b, close)
    assert not is_closed_widget(w)
    assert WIDGET_INSTANCE_MAP[w.model_id] is w
    assert isinstance(w.comm, SharedShinyComm)
    assert w.comm.has_session(a.id)


def test_wrapping_drops_an_ended_sessions_comm(
    widget_session: Session, other_session: Session, shared_state: None
) -> None:
    a, b = widget_session, other_session
    w = shared_html(a)
    run(a.close())
    sw.open_shared_in(w, b)
    assert isinstance(w.comm, SharedShinyComm)
    assert not w.comm.has_session(a.id)


def test_lazily_created_defaults_of_shared_widget_are_shared(
    widget_session: Session, shared_state: None
) -> None:
    with sw.shared_construction():
        b = Button()
    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            sw.open_shared_in(b, widget_session)
        flush()
        context.invalidate()
        flush()
    for d in (b.layout, b.style):
        assert sw.SHARED_WIDGETS.get(d.model_id) is d
        assert not is_closed_widget(d)


def test_defaults_first_serialized_by_open_shared_in_are_shared(
    widget_session: Session, shared_state: None
) -> None:
    # Unlike a widget built outside a session, one built inside a session
    # doesn't serialize (so doesn't create its Layout) until its comm opens
    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            with sw.shared_construction():
                b = Button()
            assert not b.trait_has_value("layout")
            sw.open_shared_in(b, widget_session)
        flush()
        context.invalidate()
        flush()
    for d in (b.layout, b.style):
        assert sw.SHARED_WIDGETS.get(d.model_id) is d
        assert not is_closed_widget(d)


def test_pending_open_defers_to_shared_comm(
    widget_session: Session, other_session: Session, shared_state: None
) -> None:
    a, b = widget_session, other_session
    with session_context(a):
        with Context()(), WidgetRenderContext():
            with sw.shared_construction():
                w = HTML()
            sw.open_shared_in(w, b)
        flush()
    assert isinstance(w.comm, SharedShinyComm)
    assert w.comm.has_session(a.id)
    assert w.comm.has_session(b.id)


def test_open_shared_in_opens_sessionless_references(
    widget_session: Session,
    shared_state: None,
    preimported: Callable[[type[Widget]], Widget],
) -> None:
    # The Layout ipyvue's ForceLoad materializes at import time is an ipywidgets
    # widget, so it isn't process-global by package, but the browser still needs it
    w = preimported(IpyvueThing)
    assert isinstance(w, DOMWidget)
    layout = w.layout
    assert layout is not None
    assert not sw.is_process_global(layout)
    sw.open_shared_in(w, widget_session)
    assert layout.model_id in sw.COMM_MANAGERS[widget_session.id].comms


def test_open_shared_in_leaves_per_session_references_alone(
    widget_session: Session, other_session: Session, shared_state: None
) -> None:
    with session_context(widget_session):
        child = HTML()
        with sw.shared_construction():
            box = VBox(children=(child,))
    flush()
    with pytest.warns(UserWarning, match="shared VBox references HTML"):
        sw.open_shared_in(box, other_session)
    assert child.model_id not in sw.SHARED_WIDGETS
    assert not isinstance(child.comm, SharedShinyComm)
    assert child.model_id not in sw.COMM_MANAGERS[other_session.id].comms


def test_open_shared_in_leaves_closed_references_closed(
    widget_session: Session, other_session: Session, shared_state: None
) -> None:
    # A user-closed reference (comm None) can't get this far: ipywidgets can't
    # serialize the referencing widget, since the reference has no model id
    with session_context(widget_session):
        child = HTML()
        with sw.shared_construction():
            box = VBox(children=(child,))
    flush()
    sw.close_widget(child)
    with pytest.warns(UserWarning, match="was closed"):
        sw.open_shared_in(box, other_session)
    assert is_closed_widget(child)
    assert child.model_id not in sw.SHARED_WIDGETS
    assert child.model_id not in sw.COMM_MANAGERS[other_session.id].comms


def test_open_shared_in_warns_once_on_a_session_owned_reference(
    widget_session: Session, other_session: Session, shared_state: None
) -> None:
    with session_context(widget_session):
        child = HTML()
    with sw.shared_construction():
        box = VBox(children=(child,))
    flush()
    with pytest.warns(UserWarning, match="shared VBox references HTML") as record:
        sw.open_shared_in(box, widget_session)
    message = str(record[0].message)
    assert "shared_lifetime" in message
    assert "Timeout waiting for widget model" in message
    # The child stays session-owned...
    assert child.model_id not in sw.SHARED_WIDGETS
    assert not isinstance(child.comm, SharedShinyComm)
    # ...and opening in another session doesn't repeat the warning
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        sw.open_shared_in(box, other_session)


def test_open_shared_in_snapshots_plotly_figure(
    widget_session: Session, shared_state: None
) -> None:
    go = pytest.importorskip("plotly.graph_objects")
    with sw.shared_construction():
        fig = go.FigureWidget()
        fig.add_scatter(y=[1, 2])
    assert fig._widget_data == []
    sw.open_shared_in(fig, widget_session)
    assert len(fig._widget_data) == 1


def test_open_shared_in_gives_canvas_its_own_manager(
    widget_session: Session, shared_state: None
) -> None:
    pytest.importorskip("ipycanvas")
    import ipycanvas.canvas

    module_manager = ipycanvas.canvas._CANVAS_MANAGER
    with sw.shared_construction():
        canvas = ipycanvas.Canvas()
    assert canvas._canvas_manager is module_manager
    sw.open_shared_in(canvas, widget_session)
    manager = canvas._canvas_manager
    assert manager is not module_manager
    assert not isinstance(module_manager.comm, SharedShinyComm)
    assert isinstance(manager.comm, SharedShinyComm)
    assert manager.comm.has_session(widget_session.id)
    # Its cached commands were flushed once its comm opened
    assert not manager._caching


def test_open_shared_in_resets_ipycanvas_canvas_tracking(
    widget_session: Session, other_session: Session, shared_state: None
) -> None:
    pytest.importorskip("ipycanvas")
    import ipycanvas.canvas

    with sw.shared_construction():
        canvas = ipycanvas.Canvas()
    sw.open_shared_in(canvas, widget_session)
    manager = canvas._canvas_manager
    # Drawing after the first session opened goes straight through (caching is
    # off), so the manager only re-announces the canvas when it changes
    canvas.fill_rect(0, 0, 10, 10)
    assert manager._current_canvas is canvas
    # A session joining since then never saw the switchCanvas command; the next
    # draw must re-announce the canvas or that browser errors on every command
    sw.open_shared_in(canvas, other_session)
    assert manager._current_canvas is None


def test_import_time_widget_constructed_in_shared_lifetime_is_not_shared(
    monkeypatch: pytest.MonkeyPatch, shared_state: None
) -> None:
    pytest.importorskip("ipycanvas")
    import ipycanvas.canvas

    # Simulate ipycanvas itself being imported inside shared_lifetime(): the
    # module-level _CANVAS_MANAGER it constructs must not become shared -- a
    # fan-out comm on it would broadcast every session's draw commands (the
    # scenario is_swapped_out_default() exists to prevent)
    monkeypatch.setattr(sw, "importing_ipycanvas", lambda: True)
    with shared_lifetime():
        manager = ipycanvas.canvas._CanvasManager()
    assert manager.model_id not in sw.SHARED_WIDGETS
    assert not isinstance(manager.comm, SharedShinyComm)


def comm_open_contents(
    session: Session, monkeypatch: pytest.MonkeyPatch, open_: Callable[[], Widget]
) -> dict[str, Any]:
    """The comm-open message content `open_()` sends `session` for its widget."""
    messages: list[str] = []

    async def send_custom_message(type: str, message: object) -> None:
        if type == "shinywidgets_comm_open":
            assert isinstance(message, str)
            messages.append(message)

    monkeypatch.setattr(session, "send_custom_message", send_custom_message)
    assert isinstance(session, AppSession)
    w = open_()
    flush()
    run(session._flush_callbacks.invoke())
    return next(
        msg["content"]
        for msg in map(json.loads, messages)
        if msg["content"]["comm_id"] == w.model_id
    )


def open_shared(w: Widget, session: Session) -> Widget:
    sw.open_shared_in(w, session)
    return w


def test_open_shared_in_protects_page_jquery_for_itables(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch, shared_state: None
) -> None:
    pd = pytest.importorskip("pandas")
    itables_widget = pytest.importorskip("itables.widget")
    with shared_lifetime():
        table = itables_widget.ITable(pd.DataFrame({"a": [1]}))
    content = comm_open_contents(
        widget_session, monkeypatch, lambda: open_shared(table, widget_session)
    )
    assert content["protect_jquery"] is True


def test_open_shared_in_sends_bokeh_and_extension_assets(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch, shared_state: None
) -> None:
    pd = pytest.importorskip("pandas")
    pn = pytest.importorskip("panel")
    jupyter_bokeh = pytest.importorskip("jupyter_bokeh")
    # Its extension ships ES modules, which ride the `modules` open key
    pane = pn.pane.Perspective(pd.DataFrame({"x": [1, 2]}))
    root = pane.get_root()
    try:
        with shared_lifetime():
            model = jupyter_bokeh.BokehModel(root)
        content = comm_open_contents(
            widget_session, monkeypatch, lambda: open_shared(model, widget_session)
        )
    finally:
        pn.state._views.pop(root.id, None)
        pane._cleanup(root)
    dep_names = {d["name"] for d in content["html_deps"]}
    assert {"bokeh", "bokeh-ext-panel"} <= dep_names
    assert content["modules"]["exports"]


def render_in(session: Session, fn: Callable[[], object]) -> None:
    renderer = render_widget_base()
    renderer(fn)
    with session_context(session):
        with Context()():
            run(renderer.render())


@pytest.fixture
def template_registry(monkeypatch: pytest.MonkeyPatch) -> dict[str, Widget]:
    """A fake ipyvue template registry (see in_template_registry())."""
    template_module = ModuleType("ipyvue.Template")
    registry: dict[str, Widget] = {}
    setattr(template_module, "template_registry", registry)
    monkeypatch.setitem(sys.modules, "ipyvue.Template", template_module)
    return registry


@pytest.fixture
def registered(
    widget_session: Session, template_registry: dict[str, Widget], shared_state: None
) -> HTML:
    """A widget A's (since invalidated) render built and put in the registry."""
    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            t = HTML()
        template_registry["x.vue"] = t
        flush()
        context.invalidate()
        flush()
    return t


def test_session_start_opens_listed_import_time_singletons(
    widget_session: Session,
    preimported: Callable[[type[Widget]], Widget],
    shared_state: None,
) -> None:
    g = preimported(IpyvueThing)
    o = preimported(OtherThing)
    o_comm = o.comm
    with session_context(widget_session):
        HTML()
    flush()
    assert isinstance(g.comm, SharedShinyComm)
    assert g.comm.has_session(widget_session.id)
    assert o.comm is o_comm


def test_rendering_an_unlisted_sessionless_widget_raises(
    widget_session: Session, preimported: Callable[[type[Widget]], Widget]
) -> None:
    o = preimported(OtherThing)
    with pytest.raises(RuntimeError):
        render_in(widget_session, lambda: o)


def test_template_registry_widget_reaches_a_second_session_on_render(
    registered: HTML, other_session: Session
) -> None:
    # The registry widget's render-owned Layout/Style survived its render, but
    # they belong to its original session, so opening it elsewhere warns
    with pytest.warns(UserWarning, match="belongs to one Shiny session"):
        render_in(other_session, lambda: VBox(children=(registered,)))
    assert isinstance(registered.comm, SharedShinyComm)
    assert registered.comm.has_session(other_session.id)


def test_comm_open_opens_references_of_an_undisplayed_widget(
    registered: HTML, other_session: Session
) -> None:
    with session_context(other_session), session_lifetime():
        VBox(children=(registered,))
    # registered's Layout/Style belong to its original session (see
    # test_template_registry_widget_reaches_a_second_session_on_render)
    with pytest.warns(UserWarning, match="belongs to one Shiny session"):
        flush()
    assert isinstance(registered.comm, SharedShinyComm)
    assert registered.comm.has_session(other_session.id)


def test_process_global_root_is_accepted(
    registered: HTML, other_session: Session
) -> None:
    # registered's Layout/Style belong to its original session (see
    # test_template_registry_widget_reaches_a_second_session_on_render)
    with pytest.warns(UserWarning, match="belongs to one Shiny session"):
        render_in(other_session, lambda: registered)
    assert isinstance(registered.comm, SharedShinyComm)
    assert registered.comm.has_session(other_session.id)


def test_ipycanvas_and_lonboard_defaults_are_not_shared(
    widget_session: Session,
) -> None:
    ipycanvas = pytest.importorskip("ipycanvas")
    render_in(widget_session, lambda: ipycanvas.Canvas())
    flush()
    assert not isinstance(
        sys.modules["ipycanvas.canvas"]._CANVAS_MANAGER.comm, SharedShinyComm
    )

    lonboard = pytest.importorskip("lonboard")
    defaults = lonboard.Map.class_traits()["controls"].default()

    def read_controls() -> Widget:
        # Reading the trait materializes the defaults before the comm opens
        m = lonboard.Map(layers=[])
        assert list(m.controls) == defaults
        return m

    render_in(widget_session, lambda: lonboard.Map(layers=[]))
    render_in(widget_session, read_controls)
    flush()
    assert not any(isinstance(c.comm, SharedShinyComm) for c in defaults)


def test_in_session_ipyvue_module_widget_is_not_process_global(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        w = IpyvueThing()
    assert isinstance(w.comm, OrphanedShinyComm)
    assert not sw.is_process_global(w)
    flush()
    assert isinstance(w.comm, ShinyComm)
    assert not sw.is_process_global(w)


def test_module_level_shared_widget_renders_in_two_sessions(
    widget_session: Session, other_session: Session, shared_state: None
) -> None:
    with shared_lifetime():
        s = IntSlider()
    a, b = widget_session, other_session

    renderer = render_widget_base()
    renderer(lambda: s)
    with session_context(a):
        context = Context()
        with context():
            run(renderer.render())
    flush()
    render_in(b, lambda: s)
    flush()
    assert isinstance(s.comm, SharedShinyComm)
    assert s.comm.has_session(a.id)
    assert s.comm.has_session(b.id)

    context.invalidate()
    flush()
    assert not is_closed_widget(s)


def test_shared_lifetime_inside_render_reaches_other_session(
    widget_session: Session, other_session: Session, shared_state: None
) -> None:
    def build() -> object:
        with shared_lifetime():
            return HTML()

    holder: list[HTML] = []

    def in_a() -> HTML:
        s = build()
        assert isinstance(s, HTML)
        holder.append(s)
        return s

    render_in(widget_session, in_a)
    flush()
    s = holder[0]

    render_in(other_session, lambda: VBox(children=(s,)))
    flush()
    assert isinstance(s.comm, SharedShinyComm)
    assert s.comm.has_session(other_session.id)


def test_interaction_in_one_session_reaches_the_other(
    widget_session: Session, other_session: Session, shared_state: None
) -> None:
    with shared_lifetime():
        s = IntSlider()
    render_in(widget_session, lambda: s)
    render_in(other_session, lambda: s)
    flush()
    assert isinstance(s.comm, SharedShinyComm)

    sent: list[object] = []
    comm_b = s.comm.comms[other_session.id]
    setattr(comm_b, "send", lambda *args, **kwargs: sent.append((args, kwargs)))
    s.comm.comms[widget_session.id].handle_msg(
        {
            "header": {"msg_id": "m1"},
            "buffers": [],
            "content": {
                "data": {
                    "method": "update",
                    "state": {"value": 5},
                    "buffer_paths": [],
                }
            },
        }
    )
    assert s.value == 5
    assert sent


def test_ipy_model_references_finds_nested_ids() -> None:
    data = {
        "method": "update",
        "state": {"children": ["IPY_MODEL_a", {"x": ("IPY_MODEL_b",)}]},
        "buffer_paths": [],
    }
    assert set(sw.ipy_model_references(data)) == {"a", "b"}
    assert list(sw.ipy_model_references(None)) == []
    assert list(sw.ipy_model_references({"state": {"value": 5}})) == []


def shared_box_open_in(*sessions: Session) -> VBox:
    with shared_lifetime():
        box = VBox()
    for session in sessions:
        sw.open_shared_in(box, session)
    return box


def test_shared_send_opens_a_lazily_shared_reference_everywhere(
    widget_session: Session, other_session: Session, shared_state: None
) -> None:
    box = shared_box_open_in(widget_session, other_session)
    # A shared child built lazily (see shared_lifetime()), after box was
    # already open in both sessions: nothing would otherwise open it in
    # other_session, and the children update would dangle there
    with session_context(widget_session), sw.shared_construction():
        child = HTML()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        box.children = (child,)
    assert isinstance(child.comm, SharedShinyComm)
    assert child.comm.has_session(widget_session.id)
    assert child.comm.has_session(other_session.id)
    box.children = ()
    flush()


def test_shared_send_warns_once_on_a_session_owned_reference(
    widget_session: Session, other_session: Session, shared_state: None
) -> None:
    box = shared_box_open_in(widget_session, other_session)
    with session_context(widget_session):
        child = HTML()
    flush()

    # Capture the fan-out, so the test proves the update still reaches both
    # sessions (the guard warns; it doesn't block the send)
    assert isinstance(box.comm, SharedShinyComm)
    sent: list[object] = []
    for comm in box.comm.comms.values():
        setattr(comm, "send", lambda *args, **kwargs: sent.append((args, kwargs)))

    with pytest.warns(
        UserWarning, match="update to the shared VBox references HTML"
    ) as record:
        box.children = (child,)
    message = str(record[0].message)
    assert "shared_lifetime" in message
    assert len(sent) == 2

    # Warn once per referenced widget, not per update
    box.children = ()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        box.children = (child,)
    box.children = ()


def test_shared_send_allows_a_reference_open_in_every_session(
    widget_session: Session, other_session: Session, shared_state: None
) -> None:
    box = shared_box_open_in(widget_session, other_session)
    with shared_lifetime():
        child = HTML()
    for session in (widget_session, other_session):
        sw.open_shared_in(child, session)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        box.children = (child,)
    box.children = ()


def test_shared_send_allows_a_reference_pending_open_in_its_own_session(
    widget_session: Session, other_session: Session, shared_state: None
) -> None:
    box = shared_box_open_in(widget_session, other_session)
    # The child's comm opens at the next flush, so widget_session's browser
    # does get its model; only other_session can never display it
    with session_context(widget_session):
        child = HTML()
    assert child.model_id not in sw.COMM_MANAGERS[widget_session.id].comms
    with pytest.warns(UserWarning, match="references HTML"):
        box.children = (child,)
    box.children = ()


# A VBox built by a rejected render still has its deferred open pending, and that
# open hits the closed child at the next flush.
@pytest.mark.filterwarnings("ignore:Error in Effect")
def test_ownership_errors_point_to_both_lifetimes(
    widget_session: Session,
    other_session: Session,
    preimported: Callable[[type[Widget]], Widget],
) -> None:
    with pytest.raises(RuntimeError, match="shared_lifetime") as e:
        HTML()
    assert "active Shiny session" in str(e.value)

    with session_context(widget_session), session_lifetime():
        closed_root = HTML()
        closed_child = HTML()
    with session_context(other_session), session_lifetime():
        foreign_root = HTML()
        foreign_child = HTML()
    flush()
    closed_root.close()
    closed_child.close()
    outside = preimported(OtherThing)

    cases: list[tuple[Callable[[], Widget], str]] = [
        (lambda: closed_root, "can't be displayed again"),
        (lambda: VBox(children=(closed_child,)), "can't be displayed again"),
        (lambda: foreign_root, "another Shiny session"),
        (lambda: VBox(children=(foreign_child,)), "another Shiny session"),
        (lambda: outside, "outside a Shiny session"),
    ]
    for build, phrase in cases:
        with pytest.raises(RuntimeError, match="shared_lifetime") as e:
            render_in(widget_session, build)
        assert phrase in str(e.value)


def test_shared_lifetime_is_exported() -> None:
    from shinywidgets import shared_lifetime as exported

    assert exported is sw.shared_lifetime
    assert "shared_lifetime" in shinywidgets.__all__


def test_session_lifetime_is_exported() -> None:
    from shinywidgets import session_lifetime as exported

    assert exported is sw.session_lifetime
    assert "session_lifetime" in shinywidgets.__all__
