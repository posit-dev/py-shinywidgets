import asyncio
import json
import sys
from pathlib import Path
from types import ModuleType

import pandas as pd
import panel as pn
import pytest
from bokeh.core.has_props import Local
from bokeh.embed.bundle import extension_dirs
from bokeh.models import Div
from htmltools import HTMLDependency, TagChild, TagList
from shiny import Session, reactive
from shiny.session import session_context
from shiny.session._utils import RenderedDeps
from shinywidgets._as_widget import as_widget_panel
from shinywidgets._dependencies import (
    bokeh_extension_dependencies,
    extension_urls_to_dependencies,
)


def _bokeh_model(root):
    # Avoid calling the BokehModel constructor: shinywidgets registers a
    # widget-construction callback that requires an active Shiny session.
    # bokeh_extension_dependencies() only duck-types on _model anyway.
    from jupyter_bokeh import BokehModel

    w = BokehModel.__new__(BokehModel)
    w._model = root
    return w


def _dep_files(dep: HTMLDependency) -> list:
    """Collect all script srcs and stylesheet hrefs from an HTMLDependency."""
    srcs = [s.get("src", "") for s in dep.script]
    hrefs = [s.get("href", "") for s in dep.stylesheet]
    return srcs + hrefs


def test_no_extension_for_plain_bokeh():
    from bokeh.plotting import figure

    w = _bokeh_model(figure())
    assert bokeh_extension_dependencies(w) == []


def test_no_extension_for_non_bokeh_widget():
    from ipywidgets.widgets.widget import Widget

    w = Widget.__new__(Widget)
    assert bokeh_extension_dependencies(w) == []


def test_panel_tabulator_extension_files():
    w = _bokeh_model(pn.widgets.Tabulator(pd.DataFrame({"x": [1]})).get_root())
    deps = bokeh_extension_dependencies(w)
    files = [f for dep in deps for f in _dep_files(dep)]
    assert any(f.endswith("panel.min.js") for f in files), files
    assert any("tabulator" in f and f.endswith(".js") for f in files), files
    assert any("tabulator" in f and f.endswith(".css") for f in files), files
    # Base bokeh JS is provided by bokeh_dependency(); must not be duplicated
    assert not any("bokeh.min.js" in f for f in files), files
    assert not any("cdn.bokeh.org" in f for f in files), files


def test_panel_module_dependencies_preserve_exports() -> None:
    pane = pn.pane.Perspective(pd.DataFrame({"x": [1, 2]}))
    root = pane.get_root()
    try:
        deps = bokeh_extension_dependencies(_bokeh_model(root))
        modules = [
            script
            for dep in deps
            for script in dep.script
            if script.get("type") == "module"
        ]

        assert len(modules) == 4
        exports = {
            name
            for dep in deps
            for name in dep.as_dict().get("shinywidgets_module_exports", {})
        }
        assert exports == {"perspective", "perspective_viewer"}
    finally:
        pn.state._views.pop(root.id, None)
        pane._cleanup(root)


def test_extension_dep_urls_are_not_pre_encoded():
    # Deps delivered via session._process_ui() (websocket messages) get
    # encodeURI()'d by Shiny's client; if as_dict() also pre-encodes
    # (as HTMLDependency does), URLs end up double-encoded (e.g.,
    # 'tabulator-tables@6.4.0' -> '%40' -> '%2540') and 404.
    w = _bokeh_model(pn.widgets.Tabulator(pd.DataFrame({"x": [1]})).get_root())
    deps = bokeh_extension_dependencies(w)
    for dep in deps:
        d = dep.as_dict(lib_prefix="lib")
        # The dep dict travels over the websocket as JSON
        json.dumps(d)
        for s in d["script"] + d["stylesheet"]:
            url = s.get("src", s.get("href", ""))
            assert "%" not in url, url


def test_unresolvable_extension_warns():
    class FakeExtModel(Div, Local):
        __view_module__ = "fakeextpkg12345.models"

    w = _bokeh_model(FakeExtModel(text="hi"))
    with pytest.warns(UserWarning, match="fakeextpkg12345"):
        deps = bokeh_extension_dependencies(w)
    files = [f for dep in deps for f in _dep_files(dep)]
    assert not any("fakeextpkg12345" in f for f in files)


def test_extension_deps_included_in_comm_open(
    monkeypatch: pytest.MonkeyPatch, widget_session: Session
) -> None:
    dependencies: list[HTMLDependency] = []
    process_ui = widget_session._process_ui

    def capture_dependencies(value: TagChild) -> RenderedDeps:
        if isinstance(value, TagList):
            dependencies.extend(value.get_dependencies())
        return process_ui(value)

    monkeypatch.setattr(widget_session, "_process_ui", capture_dependencies)
    with session_context(widget_session):
        as_widget_panel(pn.widgets.Tabulator(pd.DataFrame({"x": [1]})))
        asyncio.run(reactive.flush())

    assert any(dep.name.startswith("bokeh-ext-panel-") for dep in dependencies)


def test_later_remote_extension_assets_survive_dependency_deduplication() -> None:
    first = extension_urls_to_dependencies(["https://example.invalid/first.js"], [])
    later = extension_urls_to_dependencies(["https://example.invalid/later.js"], [])

    deps = TagList(*first, *later).get_dependencies()

    assert [script["src"] for dep in deps for script in dep.script] == [
        "https://example.invalid/first.js",
        "https://example.invalid/later.js",
    ]


@pytest.mark.parametrize(
    ("artifact_path", "script_name"),
    [
        ("dist/review_test_ext.min.js", "review_test_ext.min.js"),
        ("dist/nested/custom.min.js", "custom.min.js"),
    ],
)
def test_prebuilt_extension_uses_its_local_bundle_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    artifact_path: str,
    script_name: str,
) -> None:
    package = ModuleType("review_test_ext")
    package.__file__ = str(tmp_path / "__init__.py")
    monkeypatch.setattr(package, "__version__", "1.0.0", raising=False)
    monkeypatch.setitem(sys.modules, package.__name__, package)
    monkeypatch.setitem(extension_dirs, package.__name__, tmp_path / "dist")
    (tmp_path / "bokeh.ext.json").write_text("{}")
    (tmp_path / "package.json").write_text(
        json.dumps(
            {"name": "review-test-ext", "version": "1.0.0", "main": artifact_path}
        )
    )
    artifact = tmp_path / artifact_path
    artifact.parent.mkdir(parents=True)
    artifact.write_text("// Prebuilt extension bundle")

    class BundledExtension(Div, Local):
        __view_module__ = "review_test_ext.models"

    deps = bokeh_extension_dependencies(_bokeh_model(BundledExtension()))
    bundles = [dep for dep in deps if dep.script == [{"src": script_name}]]

    assert len(bundles) == 1
    assert bundles[0].source_path_map()["source"] == str(artifact.parent)
