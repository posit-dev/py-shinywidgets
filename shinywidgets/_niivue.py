"""
Accessors for `render_niivue`, backed by ipyniivue's `on_location_change`.

`on_msg` would not work here: ipyniivue overrides `_handle_custom_msg`,
bypassing the `on_msg` dispatcher, so only the library's own event registry
(`on_location_change`) sees crosshair reports.

The crosshair position is state, not just an event: ipyniivue's frontend
polls the viewer's scene (30 ms) while the canvas is focused and syncs the
diffs back, landing in `widget.scene.crosshair_pos` (NiiVue.set_state()
swallows the trait notification, so the value updates silently). `location()`
can therefore attach at render and seed itself from that synced position, so
a crosshair move made before the first read isn't lost; ongoing updates keep
flowing through `on_location_change`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, cast

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    from ipyniivue import NiiVue
    from ipyniivue.traits import Scene


def attach_location(widget: NiiVue, emit: Emit) -> Callable[[], None]:
    widget.on_location_change(emit)
    # Seed from the last synced crosshair position (see the module docstring).
    # Only the fractional position is retained Python-side, so the seed can't
    # carry the stream's other fields (mm/vox/values/...); "seeded" marks it.
    # NiiVue.__init__ always sets scene (ipyniivue's set_state assumes it
    # too), but its Instance trait types it as Optional
    frac = cast("Scene", widget.scene).crosshair_pos
    if frac is not None:
        emit({"frac": list(frac), "seeded": True})
    return lambda: widget.on_location_change(emit, remove=True)


# Crosshair drags report continuously (~22 updates per drag), so debounce
LOCATION = AccessorSpec(
    name="location",
    kind="state",
    attach=attach_location,
    rate_policy="debounce",
)
