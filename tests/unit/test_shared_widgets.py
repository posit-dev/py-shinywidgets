from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import Callable, Coroutine, Iterator
from pathlib import Path
from types import ModuleType
from typing import Any, TypeVar

import pytest
import shinywidgets._shinywidgets as sw
from ipywidgets import HTML, Button, DOMWidget, Widget
from packaging.version import Version
from shiny import Session, reactive
from shiny.reactive._core import Context
from shiny.session import session_context
from shinywidgets._comm import OrphanedShinyComm
from shinywidgets._render_widget_base import WidgetRenderContext, is_closed_widget

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
def shared_state() -> Iterator[None]:
    before = dict(sw.SHARED_WIDGETS)
    try:
        yield
    finally:
        for model_id, w in list(sw.SHARED_WIDGETS.items()):
            if before.get(model_id) is not w:
                w.close()
        sw.SHARED_WIDGETS.clear()
        sw.SHARED_WIDGETS.update(before)


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
