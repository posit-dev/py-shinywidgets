import asyncio
import json
import sys
from collections.abc import Callable, Iterator

import holoviews as hv
import pandas as pd
import panel as pn
import pytest
from bokeh.models import ImportedStyleSheet
from ipywidgets import VBox, Widget
from jupyter_bokeh import BokehModel
from shiny import Session, reactive
from shiny.reactive._core import Context
from shiny.session import session_context
from shinywidgets import session_lifetime
from shinywidgets._as_widget import as_widget_holoviews, as_widget_panel
from shinywidgets._render_widget_base import WidgetRenderContext
from shinywidgets._shinywidgets import COMM_MANAGERS
from shinywidgets._widget_registry import WIDGET_INSTANCE_MAP


def test_panel_stylesheets_stay_local_after_theme_changes(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        pane = pn.widgets.Tabulator(pd.DataFrame({"x": [1, 2, 3]}), theme="simple")
        widget = as_widget_panel(pane)
        assert isinstance(widget, BokehModel)
        stylesheets = [
            model
            for model in widget._model.references()
            if isinstance(model, ImportedStyleSheet)
        ]

        assert stylesheets
        assert all(not stylesheet.url.startswith("http") for stylesheet in stylesheets)
        assert "cdn.holoviz.org" not in json.dumps(widget.render_bundle)

        pane.theme = "bootstrap5"
        stylesheets = [
            model
            for model in widget._model.references()
            if isinstance(model, ImportedStyleSheet)
        ]
        assert any(
            "tabulator_bootstrap5" in stylesheet.url for stylesheet in stylesheets
        )
        assert all(not stylesheet.url.startswith("http") for stylesheet in stylesheets)


@pytest.mark.parametrize("initialized", [False, True], ids=["pending", "open"])
def test_explicit_close_releases_panel_root_without_reopening(
    widget_session: Session, initialized: bool
) -> None:
    with session_context(widget_session):
        pane = pn.pane.Markdown("# Content")
        widget = as_widget_panel(pane)
        assert isinstance(widget, BokehModel)
        root_id = widget._model.id
        model_id = widget.model_id
        if initialized:
            asyncio.run(reactive.flush())

        widget.close()
        widget.close()
        asyncio.run(reactive.flush())

    assert root_id not in pn.state._views
    assert root_id not in pane._models
    assert WIDGET_INSTANCE_MAP.get(model_id) is not widget
    assert model_id not in COMM_MANAGERS[widget_session.id].comms


def test_render_retirement_releases_panel_root(widget_session: Session) -> None:
    with session_context(widget_session):
        pane = pn.pane.Markdown("# Content")
        context = Context()
        with context():
            with WidgetRenderContext():
                widget = as_widget_panel(pane)
        assert isinstance(widget, BokehModel)
        root_id = widget._model.id
        asyncio.run(reactive.flush())

        context.invalidate()

    assert root_id not in pn.state._views
    assert root_id not in pane._models


def test_live_owner_preserves_panel_root_after_render_retirement(
    widget_session: Session,
) -> None:
    with session_context(widget_session):
        pane = pn.pane.Markdown("# Content")
        context = Context()
        with context():
            with WidgetRenderContext():
                widget = as_widget_panel(pane)
        assert isinstance(widget, BokehModel)
        root_id = widget._model.id
        with session_lifetime():
            owner = VBox(children=(widget,))
        asyncio.run(reactive.flush())

        context.invalidate()

    assert root_id in pn.state._views
    assert root_id in pane._models
    assert owner.children == (widget,)


def test_session_end_releases_panel_root(widget_session: Session) -> None:
    with session_context(widget_session):
        pane = pn.pane.Markdown("# Content")
        widget = as_widget_panel(pane)
        assert isinstance(widget, BokehModel)
        root_id = widget._model.id
        asyncio.run(reactive.flush())

    asyncio.run(widget_session.close())

    assert root_id not in pn.state._views
    assert root_id not in pane._models


@pytest.mark.parametrize(
    ("coerce", "make_value"),
    [
        (as_widget_panel, lambda: pn.pane.Markdown("# Content")),
        (as_widget_holoviews, lambda: hv.Curve([1, 2, 3])),
    ],
    ids=["panel", "holoviews"],
)
def test_widget_closure_releases_its_panel_root(
    monkeypatch: pytest.MonkeyPatch,
    coerce: Callable[[object], Widget | None],
    make_value: Callable[[], object],
) -> None:
    monkeypatch.setattr(Widget, "_widget_construction_callback", None)
    widget = coerce(make_value())
    assert isinstance(widget, BokehModel)
    root = widget._model
    document = root.document
    viewable = pn.state._views[root.id][0]
    live_root = viewable.get_root()

    try:
        widget.close()

        assert root.id not in pn.state._views
        assert root.id not in viewable._models
        assert live_root.id in pn.state._views
        assert live_root.id in viewable._models
    finally:
        viewable._cleanup(root)
        pn.state._views.pop(root.id, None)
        viewable._cleanup(live_root)
        pn.state._views.pop(live_root.id, None)
        if document is not None:
            # BokehModel.close() is not idempotent, including in __del__().
            document.remove_root(root)


def test_missing_jupyter_bokeh_does_not_register_a_panel_root(
    monkeypatch: pytest.MonkeyPatch, panel_views: set[str]
) -> None:
    pane = pn.pane.Markdown("# Content")
    monkeypatch.setitem(sys.modules, "jupyter_bokeh", None)

    with pytest.raises(ImportError, match="Install the jupyter_bokeh package"):
        as_widget_panel(pane)

    assert set(pn.state._views) == panel_views
    assert not pane._models


def test_failed_widget_construction_releases_its_panel_root(
    monkeypatch: pytest.MonkeyPatch, panel_views: set[str]
) -> None:
    pane = pn.pane.Markdown("# Content")

    def fail_construction(widget: Widget) -> None:
        raise RuntimeError("Widget construction failed")

    monkeypatch.setattr(Widget, "_widget_construction_callback", fail_construction)

    with pytest.raises(RuntimeError, match="Widget construction failed"):
        as_widget_panel(pane)

    assert set(pn.state._views) == panel_views
    assert not pane._models


@pytest.fixture
def panel_views() -> Iterator[set[str]]:
    initial = set(pn.state._views)
    yield initial
    for ref in set(pn.state._views) - initial:
        view, root, document, _ = pn.state._views.pop(ref)
        view._cleanup(root)
        document.remove_root(root)
