from __future__ import annotations

from typing import Callable

import pytest
from shiny.types import SilentException

import shinywidgets._accessors as acc

REASON = (
    "click events are opt-in because subscribing flips the map into "
    "click-handling mode. Add listen_to=['clicked'] to the "
    "@render_lonboard decorator."
)


def noop_attach(widget: object, emit: acc.Emit) -> Callable[[], None]:
    return lambda: None


def registered_spec() -> acc.AccessorSpec:
    return acc.AccessorSpec(
        name="clicked", kind="event", attach=noop_attach,
        requires_registration=REASON,
    )


def test_unregistered_read_raises_with_fix() -> None:
    a = acc.Accessors([registered_spec()])
    with pytest.raises(acc.AccessorRegistrationError, match=r"listen_to=\['clicked'\]"):
        a.read("clicked")


def test_registered_read_does_not_raise() -> None:
    a = acc.Accessors([registered_spec()], listen_to=["clicked"])
    # No widget has rendered, so the read cancels (req(False)) instead of
    # raising the registration error.
    with pytest.raises(SilentException):
        a.read("clicked")


def test_plain_accessor_needs_no_registration() -> None:
    a = acc.Accessors(
        [acc.AccessorSpec(name="clicked", kind="event", attach=noop_attach)]
    )
    with pytest.raises(SilentException):
        a.read("clicked")


from typing import Any

from shinywidgets._render_widget_base import render_widget_base


class render_fake(render_widget_base[Any, Any]):
    _accessor_specs = (
        acc.AccessorSpec(
            name="clicked", kind="event", attach=noop_attach,
            requires_registration=REASON,
        ),
        acc.AccessorSpec(name="selected", kind="state", attach=noop_attach),
    )


def test_listen_to_unknown_name_rejected() -> None:
    with pytest.raises(ValueError, match="no accessor named 'zoomed'"):
        render_fake(listen_to=["zoomed"])


def test_listen_to_unneeded_name_rejected() -> None:
    with pytest.raises(ValueError, match="'selected' doesn't need listen_to"):
        render_fake(listen_to=["selected"])


def test_listen_to_valid_name_accepted() -> None:
    r = render_fake(listen_to=["clicked"])
    assert "clicked" in r._accessors._listening
