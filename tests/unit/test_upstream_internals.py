# Upstream-internals canary: fail fast when ipyvue/ipyvuetify restructure.
#
# shinywidgets/_shinywidgets.py works around ipyvue and ipyvuetify
# constructing process-global widgets at import time (outside any Shiny
# session). To tell "package mid-import" from "import finished", and to find
# ipyvue's process-wide template cache, its heuristics read module internals
# that upstream never promised to keep:
#
#   * importing_ipyvue()      checks sys.modules["ipyvue.ForceLoad"] lacks the
#                             attribute `force_load_instance` (bound only when
#                             ForceLoad.py finishes executing)
#   * importing_ipyvuetify()  checks sys.modules["ipyvuetify.Themes"] lacks the
#                             attribute `theme` (bound only when Themes.py
#                             finishes executing)
#   * in_template_registry()  reads sys.modules["ipyvue.Template"]'s
#                             `template_registry` dict
#
# If an upstream release renames or moves any of these, the heuristics
# silently stop firing and the bug they prevent returns (30-second browser
# hangs, previously caught only by a slow Playwright test with no scheduled
# CI run). This module imports the REAL packages -- not the fakes in
# tests/unit/_fakes.py -- so an upstream change fails immediately and loudly
# in the fast unit suite, naming the heuristic that relies on the changed
# internal. Keep each assertion grounded in what the heuristic actually
# reads, and update the heuristic and this canary together.

from __future__ import annotations

import subprocess
import sys

import pytest
import shinywidgets._shinywidgets as sw
from ipywidgets import Widget

pytest.importorskip("ipyvue")
pytest.importorskip("ipyvuetify")


def test_importing_ipyvue_heuristic_internals() -> None:
    """importing_ipyvue() reads sys.modules['ipyvue.ForceLoad'] and decides
    "mid-import" from the absence of `force_load_instance`."""
    force_load = sys.modules.get("ipyvue.ForceLoad")
    assert force_load is not None, (
        "ipyvue no longer imports a module named 'ipyvue.ForceLoad'; "
        "importing_ipyvue() in shinywidgets/_shinywidgets.py can no longer "
        "detect ipyvue's import-time ForceLoad widget"
    )
    instance = getattr(force_load, "force_load_instance", None)
    assert isinstance(instance, Widget), (
        "ipyvue.ForceLoad no longer binds a `force_load_instance` widget once "
        "the module finishes executing; importing_ipyvue() in "
        "shinywidgets/_shinywidgets.py now reports ipyvue as mid-import "
        "forever (or never), breaking its import-time-widget workaround"
    )
    assert not sw.importing_ipyvue(), (
        "importing_ipyvue() must be False once ipyvue has fully imported; "
        "it keys off ipyvue.ForceLoad lacking `force_load_instance`"
    )


def test_importing_ipyvuetify_heuristic_internals() -> None:
    """importing_ipyvuetify() reads sys.modules['ipyvuetify.Themes'] and
    decides "mid-import" from the absence of `theme`."""
    themes = sys.modules.get("ipyvuetify.Themes")
    assert themes is not None, (
        "ipyvuetify no longer imports a module named 'ipyvuetify.Themes'; "
        "importing_ipyvuetify() in shinywidgets/_shinywidgets.py can no "
        "longer detect ipyvuetify's import-time theme widget"
    )
    theme = getattr(themes, "theme", None)
    assert isinstance(theme, Widget), (
        "ipyvuetify.Themes no longer binds a `theme` widget once the module "
        "finishes executing; importing_ipyvuetify() in "
        "shinywidgets/_shinywidgets.py now reports ipyvuetify as mid-import "
        "forever (or never), breaking its import-time-widget workaround"
    )
    assert not sw.importing_ipyvuetify(), (
        "importing_ipyvuetify() must be False once ipyvuetify has fully "
        "imported; it keys off ipyvuetify.Themes lacking `theme`"
    )


def test_in_template_registry_heuristic_internals() -> None:
    """in_template_registry() treats sys.modules['ipyvue.Template']'
    `template_registry` as a dict of cached template widgets."""
    template_mod = sys.modules.get("ipyvue.Template")
    assert template_mod is not None, (
        "ipyvue no longer imports a module named 'ipyvue.Template'; "
        "in_template_registry() in shinywidgets/_shinywidgets.py can no "
        "longer find ipyvue's process-wide template cache"
    )
    registry = getattr(template_mod, "template_registry", None)
    assert isinstance(registry, dict), (
        "ipyvue.Template.template_registry is no longer a dict; "
        "in_template_registry() in shinywidgets/_shinywidgets.py silently "
        "stops recognizing cached templates, and widgets shared across "
        "sessions via the registry lose their process-global protection"
    )


def test_import_time_singletons_are_process_global() -> None:
    """The widgets ipyvue/ipyvuetify construct at import time must be the
    ones is_process_global()/EAGERLY_SHARED_PACKAGES treat as shared by
    every session."""
    force_load_instance = sys.modules["ipyvue.ForceLoad"].force_load_instance
    theme = sys.modules["ipyvuetify.Themes"].theme

    for singleton, pkg in ((force_load_instance, "ipyvue"), (theme, "ipyvuetify")):
        assert sw.is_process_global(singleton), (
            f"{pkg}'s import-time widget is no longer process-global; "
            "sessions would be allowed to close a widget every session shares"
        )
        assert sw.widget_pkg(type(singleton)) == pkg
        assert pkg in sw.EAGERLY_SHARED_PACKAGES, (
            f"{pkg} was dropped from EAGERLY_SHARED_PACKAGES, but its "
            "import-time widget must still be opened in every session"
        )


def test_import_time_singletons_are_sessionless_on_import() -> None:
    """Freshly imported, both singletons are sessionless and classified by
    is_import_time_singleton() (so they never got one of our comms).

    Runs in a subprocess because other tests open these widgets in sessions,
    after which they hold a SharedShinyComm and are no longer sessionless."""
    script = """
import sys
import shinywidgets
import ipyvue  # noqa: F401
import ipyvuetify  # noqa: F401
import shinywidgets._shinywidgets as sw

singletons = {
    "ipyvue": sys.modules["ipyvue.ForceLoad"].force_load_instance,
    "ipyvuetify": sys.modules["ipyvuetify.Themes"].theme,
}
for pkg, w in singletons.items():
    assert sw.is_import_time_singleton(w), (
        f"{pkg}'s import-time widget is no longer classified by "
        "is_import_time_singleton(); the package must construct it outside "
        "any session and stay in IMPORT_TIME_WIDGET_PACKAGES"
    )
"""
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
