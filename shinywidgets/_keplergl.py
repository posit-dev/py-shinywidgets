"""Accessors for `render_keplergl`, backed by the KeplerGl widget's traits."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    from keplergl import KeplerGl


def attach_config(widget: "KeplerGl", emit: Emit) -> Callable[[], None]:
    """Observe the `config` trait, seeding its current value.

    A fresh KeplerGl's config is {} -- a truthful "no config yet" (the
    browser replaces the whole trait on change), so it seeds
    unconditionally.
    """

    def on_change(change: Any) -> None:
        emit(change["new"])

    widget.observe(on_change, "config")
    emit(widget.config)
    return lambda: widget.unobserve(on_change, "config")


CONFIG = AccessorSpec(
    name="config",
    kind="state",
    attach=attach_config,
    # The whole map config on every kepler.gl store dispatch (per frame
    # while panning/zooming); debounced by default like other streaming
    # accessors
    rate_policy="debounce",
    opt_in=True,
    muted_trait="config",
)
