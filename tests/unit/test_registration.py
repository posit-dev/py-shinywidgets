from __future__ import annotations

from typing import Any, Callable

import pytest
import shinywidgets._accessors as acc
from shiny.types import SilentException
from shinywidgets._render_widget_base import render_widget_base

REASON = (
    "click events are opt-in because subscribing flips the map into "
    "click-handling mode. Add listen_to=['clicked'] to the "
    "@render_lonboard decorator."
)


def noop_attach(widget: object, emit: acc.Emit) -> Callable[[], None]:
    return lambda: None


def registered_spec() -> acc.AccessorSpec:
    return acc.AccessorSpec(
        name="clicked",
        kind="event",
        attach=noop_attach,
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


def test_unregistered_eager_accessor_never_attaches() -> None:
    spec = acc.AccessorSpec(
        name="clicked",
        kind="state",  # state resolves eager=True
        attach=noop_attach,
        requires_registration=REASON,
    )
    a = acc.Accessors([spec])
    a.on_render(object())
    assert a._slots["clicked"].detach is None

    registered = acc.Accessors([spec], listen_to=["clicked"])
    registered.on_render(object())
    assert registered._slots["clicked"].detach is not None


class render_fake(render_widget_base[Any, Any]):
    _accessor_specs = (
        acc.AccessorSpec(
            name="clicked",
            kind="event",
            attach=noop_attach,
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


def test_listen_to_bare_string_rejected() -> None:
    with pytest.raises(TypeError, match=r"listen_to=\['clicked'\]"):
        render_fake(listen_to="clicked")  # type: ignore[arg-type]  # the guard targets exactly this mistake


def test_listen_to_valid_name_accepted() -> None:
    r = render_fake(listen_to=["clicked"])
    assert "clicked" in r._accessors._listening


def test_lonboard_clicked_requires_registration() -> None:
    from shinywidgets._lonboard import CLICKED

    assert CLICKED.requires_registration is not None
    assert "listen_to=['clicked']" in CLICKED.requires_registration


def test_mols2grid_clicks_kwarg_registers() -> None:
    pytest.importorskip("mols2grid")
    from shinywidgets._render_widget import render_mols2grid

    spec = next(s for s in render_mols2grid._accessor_specs if s.name == "clicked")
    assert spec.requires_registration is not None
    assert "clicks=True" in spec.requires_registration

    r = render_mols2grid(clicks=True)
    assert "clicked" in r._accessors._listening

    r2 = render_mols2grid()
    with pytest.raises(acc.AccessorRegistrationError, match="clicks=True"):
        r2._accessors.read("clicked")


def test_mols2grid_clicked_is_retained() -> None:
    pytest.importorskip("mols2grid")
    from shinywidgets._render_widget import render_mols2grid

    spec = next(s for s in render_mols2grid._accessor_specs if s.name == "clicked")
    assert spec.kind == "state"
