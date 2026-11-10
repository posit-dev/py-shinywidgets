from __future__ import annotations

from typing import Any, Callable

import pytest
from shiny.types import SilentException

import shinywidgets._accessors as acc
from shinywidgets._render_widget_base import render_widget_base

REASON = "opt-in for the test. Add listen_to=['clicked'] to the decorator."


def noop_attach(widget: object, emit: acc.Emit) -> Callable[[], None]:
    return lambda: None


class render_fake(render_widget_base[Any, Any]):
    _accessor_specs = (
        acc.AccessorSpec(name="clicked", kind="state", attach=noop_attach),
        acc.AccessorSpec(
            name="selected",
            kind="state",
            attach=noop_attach,
            requires_registration=REASON,
        ),
    )


def test_read_dispatches_to_accessor() -> None:
    r = render_fake()
    # Nothing rendered yet: the accessor read cancels (req(False)), which
    # proves dispatch reached the accessor machinery.
    with pytest.raises(SilentException):
        r.read("clicked")


def test_read_surfaces_registration_error() -> None:
    r = render_fake()
    with pytest.raises(acc.AccessorRegistrationError, match="listen_to"):
        r.read("selected")


def test_read_unknown_name_hints() -> None:
    r = render_fake()
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
