"""
shinywidgets' half of anywidget's shared `_esm`/`_css` assets (anywidget PR
#1037, opt-in via ANYWIDGET_SHARED_ASSETS=1 or
anywidget.hosts.configure(shared_assets=True)): the current Shiny session is
named as anywidget's asset scope, and each session's asset models stay
session-owned (not render-owned) so a re-render can't close an asset that
anywidget's per-session cache still hands out.

The repo pins anywidget 0.11.0 (no hosts module, no _AssetModel), so the
PR-specific tests skip there; a stub AnyAssetModel exercises the ownership
rules on either version.
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

import pytest
from ipywidgets import HTML, Widget
from shiny import Session, reactive
from shiny.reactive._core import Context
from shiny.session import session_context
from shinywidgets._comm import ShinyComm
from shinywidgets._render_widget_base import WidgetRenderContext
from shinywidgets._shinywidgets import RENDER_OWNED_WIDGETS, is_anywidget_asset
from traitlets import Unicode

T = TypeVar("T")


def run(coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.get_event_loop().run_until_complete(coro)


def flush() -> None:
    run(reactive.flush())


def is_open(widget: Widget) -> bool:
    return isinstance(widget.comm, ShinyComm)


class FakeAssetModel(Widget):
    """Stands in for anywidget's `_AssetModel` when the pinned anywidget predates it."""

    _model_name = Unicode("AnyAssetModel").tag(sync=True)


def test_is_anywidget_asset(widget_session: Session) -> None:
    with session_context(widget_session):
        assert is_anywidget_asset(FakeAssetModel())
        assert not is_anywidget_asset(HTML(value="not an asset"))


def test_asset_model_is_session_owned_not_render_owned(widget_session: Session) -> None:
    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            asset = FakeAssetModel()
        flush()
        assert is_open(asset)
        assert all(asset not in owned for owned in RENDER_OWNED_WIDGETS.values())
        context.invalidate()
        flush()
        # A re-render must not close the asset: anywidget only replaces cached
        # assets whose comm is None, and a closed widget keeps an
        # OrphanedShinyComm, so the cache would keep handing out a dead asset.
        assert is_open(asset)


def test_shared_assets_not_vetoed_by_construction_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assets = pytest.importorskip("anywidget._assets")
    pytest.importorskip("anywidget.hosts")
    monkeypatch.setenv("ANYWIDGET_SHARED_ASSETS", "1")
    # shinywidgets hooks Widget.on_widget_constructed, which vetoes shared
    # assets unless the host configures a scope (see _shinywidgets.py).
    assert assets._shared_assets_enabled()


def test_asset_scope_is_the_current_shiny_session(widget_session: Session) -> None:
    hosts = pytest.importorskip("anywidget.hosts")
    assert hosts._scope() is None
    with session_context(widget_session):
        assert hosts._scope() is widget_session


def test_anywidget_scope_outside_session_is_none() -> None:
    from shinywidgets._shinywidgets import anywidget_asset_scope

    assert anywidget_asset_scope() is None


def test_anywidget_scope_is_the_root_session(widget_session: Session) -> None:
    from shinywidgets._shinywidgets import anywidget_asset_scope

    with session_context(widget_session):
        assert anywidget_asset_scope() is widget_session.root_scope()


def test_anywidget_scope_normalizes_module_sessions(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A module-scoped session shares its browser with the root session, so the
    # asset cache must key on the root (else the same _esm ships once per
    # module that constructs the class).
    import shinywidgets._shinywidgets as sw
    from shinywidgets._shinywidgets import anywidget_asset_scope

    class ModuleSession:
        def __init__(self, root: object) -> None:
            self._root = root

        def root_scope(self) -> object:
            return self._root

    root = widget_session.root_scope()
    monkeypatch.setattr(
        sw, "get_current_session", lambda: ModuleSession(root)
    )
    assert anywidget_asset_scope() is root


def test_anywidget_scope_is_process_wide_during_shared_construction(
    widget_session: Session, shared_state: None
) -> None:
    # A shared widget's asset scoped to the constructing session couldn't be
    # resolved by other sessions (a browser never receives a reference to an
    # asset opened for another scope) and would close when that session ends.
    from shinywidgets import shared_lifetime
    from shinywidgets._shinywidgets import anywidget_asset_scope

    with session_context(widget_session):
        with shared_lifetime():
            assert anywidget_asset_scope() is None


def test_shared_asset_survives_render_invalidation(
    widget_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("anywidget.hosts")
    import anywidget

    monkeypatch.setenv("ANYWIDGET_SHARED_ASSETS", "1")

    class Counter(anywidget.AnyWidget):
        _esm = "export default { render() {} }"

    with session_context(widget_session):
        context = Context()
        with context(), WidgetRenderContext():
            w = Counter()
        flush()
        asset = getattr(w, "_esm")
        assert is_anywidget_asset(asset)
        assert is_open(asset)
        # The widget's state references the asset rather than inlining the source.
        assert w.get_state("_esm")["_esm"] == f"anywidget-asset:{asset.model_id}"
        context.invalidate()
        flush()
        assert is_open(asset)
        # The next render is handed the same live asset, not the closed one.
        context2 = Context()
        with context2(), WidgetRenderContext():
            w2 = Counter()
        flush()
        assert getattr(w2, "_esm") is asset
        assert is_open(w2)
