import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import List, cast

import bokeh
import pytest
from bokeh.core.has_props import Local
from bokeh.embed.bundle import extension_dirs
from bokeh.models import Div
from htmltools import HTMLDependency, TagList
from shiny import Session
from shinywidgets._bokeh import (
    bokeh_dependency,
    bokeh_extension_dependencies,
    extension_urls_to_dependencies,
)


def _fake_session() -> Session:
    # Extension asset resolution only needs the app's lib_prefix
    return cast(Session, SimpleNamespace(app=SimpleNamespace(lib_prefix="lib")))


def _bokeh_model(root):
    # Avoid calling the BokehModel constructor: shinywidgets registers a
    # widget-construction callback that requires an active Shiny session.
    # bokeh_extension_dependencies() only duck-types on _model anyway.
    from jupyter_bokeh import BokehModel

    w = BokehModel.__new__(BokehModel)
    w._model = root
    return w


def _dep_heads(deps: List[HTMLDependency]) -> List[str]:
    """Collect all head-content HTML strings from a list of dependencies."""
    return [d["head"] for d in (dep.as_dict() for dep in deps) if d.get("head")]


def test_bokeh_dependency_serves_installed_core_scripts() -> None:
    dep = bokeh_dependency()
    source = dep.source_path_map()["source"]

    assert source is not None
    assert dep.script
    assert str(dep.version) == bokeh.__version__
    for script in dep.script:
        assert (Path(source) / script["src"]).is_file()


def test_no_extension_for_plain_bokeh():
    from bokeh.plotting import figure

    w = _bokeh_model(figure())
    assert bokeh_extension_dependencies(w, _fake_session()) == []


def test_no_extension_for_non_bokeh_widget():
    from ipywidgets.widgets.widget import Widget

    w = Widget.__new__(Widget)
    assert bokeh_extension_dependencies(w, _fake_session()) == []


def test_unresolvable_extension_warns():
    class FakeExtModel(Div, Local):
        __view_module__ = "fakeextpkg12345.models"

    w = _bokeh_model(FakeExtModel(text="hi"))
    with pytest.warns(UserWarning, match="fakeextpkg12345"):
        deps = bokeh_extension_dependencies(w, _fake_session())
    assert not any("fakeextpkg12345" in head for head in _dep_heads(deps))


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

    deps = bokeh_extension_dependencies(
        _bokeh_model(BundledExtension()), _fake_session()
    )

    # The directory behind the package's static/extensions URLs gets mounted
    # for local serving...
    mounts = [dep for dep in deps if dep.name == "bokeh-ext-review_test_ext"]
    assert len(mounts) == 1
    paths = mounts[0].source_path_map()
    assert paths["source"] == str(artifact.parent)

    # ...and the bundle loads via a <script> tag pointing at that mount
    script = f'<script src="{paths["href"]}/{asset_path}"></script>'
    assert script in _dep_heads(deps)
