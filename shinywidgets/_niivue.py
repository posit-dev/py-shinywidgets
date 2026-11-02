"""
Accessors for `render_niivue`, backed by ipyniivue's `on_location_change`.

`on_msg` would not work here: ipyniivue overrides `_handle_custom_msg`,
bypassing the `on_msg` dispatcher, so only the library's own event registry
(`on_location_change`) sees crosshair reports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    from ipyniivue import NiiVue


def attach_location(widget: NiiVue, emit: Emit) -> Callable[[], None]:
    widget.on_location_change(emit)
    return lambda: widget.on_location_change(emit, remove=True)


# Crosshair drags report continuously (~22 updates per drag), so debounce
LOCATION = AccessorSpec(
    name="location",
    kind="event",
    attach=attach_location,
    rate_policy="debounce",
)
