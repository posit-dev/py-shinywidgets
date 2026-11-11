from __future__ import annotations

from typing import Any, Callable

import pytest
import shinywidgets._accessors as acc
from shiny.types import SilentException
from shinywidgets._render_widget_base import render_widget_base


def noop_attach(widget: object, emit: acc.Emit) -> Callable[[], None]:
    return lambda: None


class render_fake(render_widget_base[Any, Any]):
    _accessor_specs = (
        acc.AccessorSpec(name="clicked", kind="state", attach=noop_attach),
        acc.AccessorSpec(name="selected", kind="state", attach=noop_attach),
    )


def test_read_dispatches_to_accessor() -> None:
    r = render_fake()
    # Nothing rendered yet: the accessor read cancels (req(False)), which
    # proves dispatch reached the accessor machinery.
    with pytest.raises(SilentException):
        r.read("clicked")


def test_read_unknown_name_hints() -> None:
    r = render_fake()
    with pytest.raises(AttributeError, match="Did you mean 'clicked'"):
        r.read("clikced")


def test_read_in_own_render_function_raises() -> None:
    from shinywidgets._render_widget_base import rendering_renderer

    r = render_fake()
    r.output_id = "fake"  # set when a renderer is bound to an output
    token = rendering_renderer.set(r)
    try:
        with pytest.raises(RuntimeError, match="own render function"):
            r.read("clicked")
    finally:
        rendering_renderer.reset(token)


def test_read_pre_render_unknown_name_explains() -> None:
    r = render_fake()
    with pytest.raises(AttributeError, match="hasn't rendered yet"):
        r.read("value")
    # ...but a typo'd accessor name still gets the hint
    with pytest.raises(AttributeError, match="Did you mean 'clicked'"):
        r.read("clikced")


def test_read_falls_through_to_trait(widget_session: object) -> None:
    import ipywidgets as wi
    from shiny.session import session_context

    with session_context(widget_session):  # type: ignore[arg-type]
        slider = wi.IntSlider(value=7)
    r = render_fake()
    r._widget = slider
    assert r.read("value") == 7


def test_read_overloads_typecheck() -> None:
    # Runtime smoke: the overloaded read() still dispatches correctly.
    pytest.importorskip("plotly")
    from shinywidgets._render_widget import render_plotly

    r = render_plotly()
    with pytest.raises(AttributeError, match="no accessor named 'nope'"):
        r.read("nope")


def test_accessor_name_wins_over_trait(widget_session: object) -> None:
    import ipywidgets as wi
    import traitlets
    from shiny.session import session_context

    class Clicky(wi.Widget):
        _view_name = traitlets.Unicode("ClickyView").tag(sync=True)
        _model_name = traitlets.Unicode("ClickyModel").tag(sync=True)
        _view_module = traitlets.Unicode("clicky").tag(sync=True)
        _model_module = traitlets.Unicode("clicky").tag(sync=True)
        clicked = traitlets.Int(0).tag(sync=True)

    with session_context(widget_session):  # type: ignore[arg-type]
        w = Clicky(clicked=5)
    r = render_fake()
    r._widget = w
    # "clicked" is both an accessor and a trait: the accessor wins, so the
    # read reaches the accessor machinery (which cancels pre-render) rather
    # than returning the trait's 5
    with pytest.raises(SilentException):
        r.read("clicked")
