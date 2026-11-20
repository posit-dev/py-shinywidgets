"""
Runtime configuration for shinywidgets.

`config()` is the front door for app-wide settings. Every setting also has
an environment variable, read lazily, so a deployment can set it without
touching app code; an explicit `config()` call wins over the environment.
Values are read where they're used (e.g. per render), never snapshotted at
import time, so `config()` works in tests and mid-session.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict

# Setting name -> default, computed from the environment on each read
# (until config() sets the setting explicitly)
_DEFAULTS: Dict[str, Callable[[], Any]] = {
    # Whether every widget's own (native) events reach Python, restoring
    # what renderers mute by default (render_widget_base._muted_traits()).
    # Read per render, so a deployment can set the env var without touching
    # app code.
    "native_events": lambda: (
        os.environ.get("SHINYWIDGETS_NATIVE_EVENTS", "").lower() in ("1", "true")
    ),
}

# Settings config() has set explicitly
_SETTINGS: Dict[str, Any] = {}


def config(**kwargs: Any) -> Dict[str, Any]:
    """
    Get or set shinywidgets' app-wide settings.

    Called with no arguments, returns a dict of the current settings.
    Called with keyword arguments, sets those settings and returns the
    updated dict. Unknown setting names raise `TypeError`.

    Currently available settings:

    - ``native_events`` (bool, default ``False``, env var
      ``SHINYWIDGETS_NATIVE_EVENTS``): some widgets sync their own event
      streams to Python by default (e.g. plotly.py's per-point click/hover/
      selection reports), which renderers mute unless the app uses them.
      Set ``native_events=True`` to receive every widget's native events
      app-wide.
    """
    unknown = set(kwargs) - set(_DEFAULTS)
    if unknown:
        raise TypeError(
            f"Unknown shinywidgets config setting(s) {sorted(unknown)}; "
            f"available settings are {sorted(_DEFAULTS)}."
        )
    _SETTINGS.update(kwargs)
    return {name: _get(name) for name in _DEFAULTS}


def native_events_enabled() -> bool:
    """The current value of the ``native_events`` setting (see `config()`)."""
    return bool(_get("native_events"))


def _get(name: str) -> Any:
    if name in _SETTINGS:
        return _SETTINGS[name]
    return _DEFAULTS[name]()
