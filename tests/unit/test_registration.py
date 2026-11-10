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
