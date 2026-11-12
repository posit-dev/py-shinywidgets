"""
Accessors for `render_maplibre`, backed by the MapWidget's synced traits.

The browser side of maplibre (srcjs/ipywidget.js) syncs `view_state` on the
map's `load`, `zoomend`, and `moveend` events -- once per *completed*
gesture, not per animation frame -- sets `clicked` on each map click, and
replaces `draw_feature_collection_all` on every MapboxDraw
create/update/delete. All three report discretely, so none declares a
default rate limit (#400's convention: debounce only what streams
continuously through a gesture).

A fresh MapWidget's Dict traits all read `{}`. For `view_state` and
`clicked` an empty dict means "nothing to report yet", so the attach-time
seed skips it: seeding it on a re-render would clobber a kept value with
the new widget's "nothing yet". For `draw_feature_collection_all`, `{}` is
a truthful "no features" (drawn shapes live on the map, and the browser
only reports on draw events), so it seeds unconditionally and a re-render
re-seeds to empty.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, List

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    from maplibre.ipywidget import MapWidget  # pyright: ignore[reportMissingImports]


def attach_trait(
    trait: str, *, skip_empty_seed: bool
) -> Callable[["MapWidget", Emit], Callable[[], None]]:
    """Observe a synced Dict trait, seeding its current value.

    With `skip_empty_seed`, a `{}` current value isn't seeded: it's the
    trait's fresh-widget default, not a report (see the module docstring).
    """

    def attach(widget: "MapWidget", emit: Emit) -> Callable[[], None]:
        def on_change(change: Any) -> None:
            emit(change["new"])

        widget.observe(on_change, trait)
        current = getattr(widget, trait)
        if current or not skip_empty_seed:
            emit(current)
        return lambda: widget.unobserve(on_change, trait)

    return attach


def features(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    # The trait holds a FeatureCollection ({} before the first draw event);
    # the accessor returns its features, as ipyleaflet's drawn_features does
    return raw.get("features", [])


VIEW_STATE = AccessorSpec(
    name="view_state",
    kind="state",
    attach=attach_trait("view_state", skip_empty_seed=True),
    # The browser's first report comes with the map's load event
    not_ready=lambda raw: not raw,
)
CLICKED = AccessorSpec(
    name="clicked",
    kind="state",
    attach=attach_trait("clicked", skip_empty_seed=True),
)
DRAWN_FEATURES = AccessorSpec(
    name="drawn_features",
    kind="state",
    attach=attach_trait("draw_feature_collection_all", skip_empty_seed=False),
    payload=features,
)

MAPLIBRE_ACCESSORS = (VIEW_STATE, CLICKED, DRAWN_FEATURES)
