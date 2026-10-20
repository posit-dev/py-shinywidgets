"""Access to ipywidgets' widget instance registry."""

from __future__ import annotations

__all__ = ("WIDGET_INSTANCE_MAP",)

# Registry of all "active" widgets: ipywidgets adds each widget to this dictionary
# when it's created and removes it when the widget is explicitly closed. We rely on
# this being the *actual* registry: session cleanup closes the widgets it finds here,
# and the render-context invalidation handler removes the reference that assigning an
# OrphanedShinyComm re-adds. A substitute map would silently leak widgets, so fail
# loudly at import time if ipywidgets ever stops providing it. Import it directly
# (available since ipywidgets 8.0.3; we require >=8.1) since the deprecated public
# alias, `Widget.widgets`, warns on every access.
try:
    from ipywidgets.widgets.widget import _instances as WIDGET_INSTANCE_MAP
except ImportError as e:
    raise ImportError(
        "shinywidgets relies on ipywidgets' widget instance registry "
        "(ipywidgets.widgets.widget._instances), but it could not be found. "
        "This likely means that ipywidgets is either older than 8.1 (in which "
        "case, please upgrade ipywidgets) or newer than this version of "
        "shinywidgets supports (in which case, please upgrade shinywidgets, "
        "or report an issue at "
        "https://github.com/posit-dev/py-shinywidgets/issues)."
    ) from e
