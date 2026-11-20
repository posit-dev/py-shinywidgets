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

CDN_DEFAULT = "https://cdn.jsdelivr.net/npm/"

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
    # CDN fallback base URL for widget JS when no local nbextension is found.
    # output_widget() bakes it into the UI's data attributes, so it's read
    # when the UI is built, not per render.
    "cdn": lambda: os.environ.get("SHINYWIDGETS_CDN", CDN_DEFAULT),
    # Only "true" counts, matching the env vars' historical parsing
    "cdn_only": lambda: (
        os.environ.get("SHINYWIDGETS_CDN_ONLY", "false").lower() == "true"
    ),
    "extension_warning": lambda: (
        os.environ.get("SHINYWIDGETS_EXTENSION_WARNING", "false").lower() == "true"
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
    - ``cdn`` (str, default ``"https://cdn.jsdelivr.net/npm/"``, env var
      ``SHINYWIDGETS_CDN``): the base URL of the CDN that widget JavaScript
      falls back to when no local copy of a widget's extension is found.
      ``output_widget()`` bakes the value into the UI's data attributes, so
      ``config(cdn=...)`` must run before the UI is built (e.g., the top of
      app.py); the env var remains the deployment-time alternative.
    - ``cdn_only`` (bool, default ``False``, env var ``SHINYWIDGETS_CDN_ONLY``):
      always load widget JavaScript from the CDN, never from a local copy.
      Read per render, so it only needs to be set before the first render.
    - ``extension_warning`` (bool, default ``False``, env var
      ``SHINYWIDGETS_EXTENSION_WARNING``): warn when no local path to a
      widget's extension is found (the widget still renders via the CDN
      fallback). Read per render, so it only needs to be set before the
      first render.
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


def cdn_url() -> str:
    """The current value of the ``cdn`` setting (see `config()`)."""
    return str(_get("cdn"))


def cdn_only() -> bool:
    """The current value of the ``cdn_only`` setting (see `config()`)."""
    return bool(_get("cdn_only"))


def extension_warning() -> bool:
    """The current value of the ``extension_warning`` setting (see `config()`)."""
    return bool(_get("extension_warning"))


def _get(name: str) -> Any:
    if name in _SETTINGS:
        return _SETTINGS[name]
    return _DEFAULTS[name]()
