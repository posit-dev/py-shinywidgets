"""
Support for ipyreact's process-global dependency widgets.

`ipyreact.define_module()` and `ipyreact.define_import_map()` construct
`Module` and `ImportMap` widgets whose frontend *models* register ES modules
with the browser's import shim; every ipyreact widget then waits on those
modules by name. ipyreact treats them as process-wide (it keeps them in
`ipyreact.module._module_widgets` and `ipyreact.importmap._import_map_widget`),
and they're usually constructed at import time (e.g. reactable-py calls
`define_module()` at module level), so they can't belong to one session:
shinywidgets mirrors them into every session, like shared_lifetime() widgets.
"""

from __future__ import annotations

import sys
from typing import List

from ipywidgets import Widget

from ._comm import SharedShinyComm, is_sessionless
from ._dependencies import widget_pkg
from ._utils import restrict_client_traits
from ._widget_registry import WIDGET_INSTANCE_MAP


def is_ipyreact_widget(w: Widget) -> bool:
    """Is `w` any ipyreact widget (i.e., a consumer of the registry widgets)?"""
    return any(widget_pkg(cls) == "ipyreact" for cls in type(w).__mro__)


def is_ipyreact_registry_widget(w: Widget) -> bool:
    """Is `w` one of ipyreact's process-global dependency widgets?"""
    return any(
        widget_pkg(cls) == "ipyreact" and cls.__name__ in ("Module", "ImportMap")
        for cls in type(w).__mro__
    )


def constructing_ipyreact_registry_widget() -> bool:
    """
    Is ipyreact's define_module()/define_import_map() constructing this widget?

    Catches the sub-widgets a Module/ImportMap materializes while it's being
    constructed (e.g. its Layout, when Widget.open() serializes state): they
    must be process-global for the same reason the Module/ImportMap itself is.
    """
    if "ipyreact.module" not in sys.modules and "ipyreact.importmap" not in sys.modules:
        return False
    frame = sys._getframe(1)
    try:
        while frame is not None:
            if frame.f_globals.get("__name__") in (
                "ipyreact.module",
                "ipyreact.importmap",
            ):
                return True
            frame = frame.f_back
        return False
    finally:
        del frame


def ipyreact_registry_widgets() -> List[Widget]:
    """
    ipyreact's process-global dependency widgets, if ipyreact is imported.

    Picks up widgets our construction hook missed (ipyreact imported before
    shinywidgets, or during a stub session, where define_module() returns the
    already-registered widget instead of constructing a new one): the ones in
    ipyreact's own registries, plus any sessionless Module/ImportMap.
    """
    widgets: List[Widget] = []
    module_mod = sys.modules.get("ipyreact.module")
    widgets.extend(getattr(module_mod, "_module_widgets", {}).values())
    importmap_mod = sys.modules.get("ipyreact.importmap")
    import_map_widget = getattr(importmap_mod, "_import_map_widget", None)
    if import_map_widget is not None:
        widgets.append(import_map_widget)
    # Snapshot, since opening the widgets (by the caller) can construct
    # widgets. Already-shared registries (SharedShinyComm) must be discovered
    # too: one opened in a session still needs opening in every other session
    # that renders a consumer (ipyreact < 0.7 has no _module_widgets registry
    # to find it through, and it may predate that registry regardless).
    widgets.extend(
        w
        for w in list(WIDGET_INSTANCE_MAP.values())
        if is_ipyreact_registry_widget(w)
        and (is_sessionless(w) or isinstance(w.comm, SharedShinyComm))
        and w not in widgets
    )
    return widgets


# The one synced trait an ipyreact registry widget's frontend may write: its
# Module model reports load progress through `status`. Everything else
# (Module.code/url, ImportMap.import_map) the browser executes as JavaScript,
# so only Python may author it.
_IPYREACT_REGISTRY_CLIENT_TRAITS = frozenset({"status"})


def guard_ipyreact_registry_state(w: Widget) -> None:
    """
    Drop client-authored state updates to an ipyreact registry, except `status`.

    `code`/`url`/`import_map` are synced traits, so any session's browser
    could rewrite them through an ordinary `update` comm message -- and the
    registry is process-global, so every later session would load that
    JavaScript. Python is the only legitimate author of everything but
    `status` (which ipyreact's frontend sets to report load progress).
    """
    restrict_client_traits(
        w, _IPYREACT_REGISTRY_CLIENT_TRAITS, "_shinywidgets_ipyreact_guarded"
    )
