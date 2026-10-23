import asyncio
import json
import sys
import warnings
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import List, cast

import bokeh
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
from shinywidgets._bokeh import (
    _bokeh_dependency,
    bokeh_dependency,
    bokeh_extension_assets,
    extension_urls_to_dependencies,
)


def _fake_session() -> Session:
    # Extension asset resolution only needs the app's lib_prefix
    return cast(Session, SimpleNamespace(app=SimpleNamespace(lib_prefix="lib")))


def _bokeh_model(root):
    # Avoid calling the BokehModel constructor: shinywidgets registers a
    # widget-construction callback that requires an active Shiny session.
    # bokeh_extension_assets() only duck-types on _model anyway.
    from jupyter_bokeh import BokehModel

    w = BokehModel.__new__(BokehModel)
    w._model = root
    return w


def _dep_heads(deps: List[HTMLDependency]) -> List[str]:
    """Collect all head-content HTML strings from a list of dependencies."""
    return [d["head"] for d in (dep.as_dict() for dep in deps) if d.get("head")]


def test_bokeh_dependency_serves_installed_core_scripts() -> None:
    with pytest.warns(DeprecationWarning, match="no longer needed"):
        dep = bokeh_dependency()
    source = dep.source_path_map()["source"]

    assert source is not None
    assert dep.script
    assert str(dep.version) == bokeh.__version__
    for script in dep.script:
        assert (Path(source) / script["src"]).is_file()


def test_private_bokeh_dependency_does_not_warn() -> None:
    # Internal callers (widget init, render_* decorator UIs) use the private
    # variant so users aren't warned by shinywidgets' own machinery
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        dep = _bokeh_dependency()
    assert dep.name == "bokeh"


def test_no_extension_for_plain_bokeh():
    from bokeh.plotting import figure

    w = _bokeh_model(figure())
    assert bokeh_extension_assets(w, _fake_session()).deps == []


def test_no_extension_for_non_bokeh_widget():
    from ipywidgets.widgets.widget import Widget

    w = Widget.__new__(Widget)
    assert bokeh_extension_assets(w, _fake_session()).deps == []


def test_panel_tabulator_extension_files():
    w = _bokeh_model(pn.widgets.Tabulator(pd.DataFrame({"x": [1]})).get_root())
    assets = bokeh_extension_assets(w, _fake_session())
    heads = _dep_heads(assets.deps)
    assert any("panel.min.js" in h for h in heads), heads
    assert any("tabulator" in h and ".js" in h for h in heads), heads
    assert any("tabulator" in h and ".css" in h for h in heads), heads
    # Base bokeh JS is provided by bokeh_dependency(); must not be duplicated
    assert not any("bokeh.min.js" in h for h in heads), heads
    assert not any("cdn.bokeh.org" in h for h in heads), heads


def test_panel_module_dependencies_preserve_exports() -> None:
    pane = pn.pane.Perspective(pd.DataFrame({"x": [1, 2]}))
    root = pane.get_root()
    try:
        assets = bokeh_extension_assets(_bokeh_model(root), _fake_session())

        assert set(assets.module_exports) == {"perspective", "perspective_viewer"}
        n_modules = len(assets.module_urls) + len(set(assets.module_exports.values()))
        assert n_modules == 4
    finally:
        pn.state._views.pop(root.id, None)
        pane._cleanup(root)


def test_extension_asset_urls_are_not_pre_encoded():
    # Assets delivered via session._process_ui() (websocket messages) get
    # encodeURI()'d by Shiny's client; if the server also pre-encodes (as
    # HTMLDependency.as_dict() does), URLs end up double-encoded (e.g.,
    # 'tabulator-tables@6.4.0' -> '%40' -> '%2540') and 404.
    w = _bokeh_model(pn.widgets.Tabulator(pd.DataFrame({"x": [1]})).get_root())
    assets = bokeh_extension_assets(w, _fake_session())
    urls = _dep_heads(assets.deps) + assets.module_urls
    urls += list(assets.module_exports.values())
    for url in urls:
        assert "%" not in url, url


def test_unresolvable_extension_warns():
    class FakeExtModel(Div, Local):
        __view_module__ = "fakeextpkg12345.models"

    w = _bokeh_model(FakeExtModel(text="hi"))
    with pytest.warns(UserWarning, match="fakeextpkg12345"):
        assets = bokeh_extension_assets(w, _fake_session())
    assert not any("fakeextpkg12345" in head for head in _dep_heads(assets.deps))


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

    assert any(dep.name == "bokeh-ext-panel" for dep in dependencies)


def test_later_remote_extension_assets_survive_dependency_deduplication() -> None:
    session = _fake_session()
    first = extension_urls_to_dependencies(
        ["https://example.invalid/first.js"], [], session
    )
    later = extension_urls_to_dependencies(
        ["https://example.invalid/later.js"], [], session
    )

    deps = TagList(*first, *later).get_dependencies()

    assert _dep_heads(deps) == [
        '<script src="https://example.invalid/first.js"></script>',
        '<script src="https://example.invalid/later.js"></script>',
    ]


@pytest.mark.parametrize(
    ("artifact_path", "asset_path"),
    [
        ("dist/review_test_ext.min.js", "review_test_ext.min.js"),
        ("dist/nested/custom.min.js", "custom.min.js"),
    ],
)
def test_prebuilt_extension_uses_its_local_bundle_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    artifact_path: str,
    asset_path: str,
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

    assets = bokeh_extension_assets(_bokeh_model(BundledExtension()), _fake_session())

    # The directory behind the package's static/extensions URLs gets mounted
    # for local serving...
    mounts = [dep for dep in assets.deps if dep.name == "bokeh-ext-review_test_ext"]
    assert len(mounts) == 1
    paths = mounts[0].source_path_map()
    assert paths["source"] == str(artifact.parent)

    # ...and the bundle loads via a <script> tag pointing at that mount
    script = f'<script src="{paths["href"]}/{asset_path}"></script>'
    assert script in _dep_heads(assets.deps)
