import json
import sys
from pathlib import Path
from types import ModuleType

import pytest
from bokeh.core.has_props import Local
from bokeh.embed.bundle import extension_dirs
from bokeh.models import Div
from htmltools import HTMLDependency, TagList
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


def test_unresolvable_extension_warns():
    class FakeExtModel(Div, Local):
        __view_module__ = "fakeextpkg12345.models"

    w = _bokeh_model(FakeExtModel(text="hi"))
    with pytest.warns(UserWarning, match="fakeextpkg12345"):
        deps = bokeh_extension_dependencies(w)
    files = [f for dep in deps for f in _dep_files(dep)]
    assert not any("fakeextpkg12345" in f for f in files)


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
