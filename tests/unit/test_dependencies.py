import types
import warnings
from types import ModuleType

import pytest
import shinywidgets._dependencies as deps
from htmltools import HTMLDependency
from ipywidgets.widgets.domwidget import DOMWidget
from shinywidgets._dependencies import (
    jupyter_extension_destination,
    jupyter_extension_path,
    output_binding_dependency,
    parse_version,
    parse_version_safely,
    require_dependency,
    widget_pkg,
)


def test_parse_version_strips_semver_prefixes() -> None:
    assert parse_version("^1.2.3") == "1.2.3"
    assert parse_version(">=2.0.0") == "2.0.0"


def test_parse_version_safely_star_falls_back() -> None:
    assert parse_version_safely("*") == "0.0"


def test_widget_pkg_uses_first_module_component() -> None:
    class Dummy:
        pass

    Dummy.__module__ = "somepkg.sub.mod"
    assert widget_pkg(Dummy()) == "somepkg"


def test_jupyter_extension_path_finds_index_js(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module_name = "some-widget-module"
    module_dir = tmp_path / "nbextensions" / module_name
    module_dir.mkdir(parents=True)
    (module_dir / "index.js").write_text("// hi", encoding="utf-8")

    monkeypatch.setattr(deps, "jupyter_path", lambda: [str(tmp_path)])
    assert jupyter_extension_path(module_name) == str(module_dir)


def test_jupyter_extension_path_returns_none_when_no_index_js(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module_name = "missing-index-module"
    module_dir = tmp_path / "nbextensions" / module_name
    module_dir.mkdir(parents=True)

    monkeypatch.setattr(deps, "jupyter_path", lambda: [str(tmp_path)])
    assert jupyter_extension_path(module_name) is None


def test_jupyter_extension_destination_prefers_nbextension_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyWidget:
        __module__ = "fakepkg.sub"

    w = DummyWidget()

    mod = ModuleType("fakepkg")
    mod.__file__ = "/fake/path/__init__.py"

    def _jupyter_nbextension_paths():
        return [{"dest": "some-dest"}]

    mod._jupyter_nbextension_paths = _jupyter_nbextension_paths  # type: ignore[attr-defined]

    monkeypatch.setattr(deps.importlib, "import_module", lambda *a, **k: mod)
    assert jupyter_extension_destination(w) == "some-dest"


def test_jupyter_extension_destination_falls_back_to_widget_pkg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyWidget:
        __module__ = "fakepkg.sub"

    w = DummyWidget()

    mod = ModuleType("fakepkg")
    mod.__file__ = "/fake/path/__init__.py"

    monkeypatch.setattr(deps.importlib, "import_module", lambda *a, **k: mod)
    assert jupyter_extension_destination(w) == "fakepkg"


def test_jupyter_extension_destination_requires_module_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyWidget:
        __module__ = "fakepkg.sub"

    w = DummyWidget()

    mod = ModuleType("fakepkg")
    mod.__file__ = None

    monkeypatch.setattr(deps.importlib, "import_module", lambda *a, **k: mod)
    with pytest.raises(RuntimeError, match="has no __file__ attribute"):
        jupyter_extension_destination(w)


def test_output_binding_dependency_structure() -> None:
    dep = output_binding_dependency()
    assert isinstance(dep, HTMLDependency)
    assert dep.name == "ipywidget-output-binding"
    assert dep.source == {"package": "shinywidgets", "subdir": "static"}
    assert dep.script == [{"src": "libembed-amd.js"}, {"src": "output.js"}]
    assert any(x.get("href") == "shinywidgets.css" for x in dep.stylesheet)


def test_require_dependency_core_widgets_return_none() -> None:
    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))
    # Avoid calling ipywidgets constructors (shinywidgets registers a construction callback
    # that requires an active Shiny session).
    w = DOMWidget.__new__(DOMWidget)
    w._view_module = "@jupyter-widgets/controls"  # type: ignore[attr-defined]
    assert require_dependency(w, session) is None


def test_require_dependency_missing_extension_warns_and_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyWidget:
        __module__ = "fakepkg.sub"

    w = DummyWidget()
    w._model_module = "some-widget-module"
    w._model_module_version = "^1.2.3"

    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))

    monkeypatch.setattr(deps, "jupyter_extension_path", lambda name: None)
    monkeypatch.setattr(deps, "jupyter_extension_destination", lambda w: "some-dest")

    with pytest.warns(
        UserWarning, match="Couldn't find local path to widget extension"
    ):
        assert require_dependency(w, session, warn_if_missing=True) is None

    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        assert require_dependency(w, session, warn_if_missing=False) is None
    assert not any(
        "Couldn't find local path to widget extension" in str(w.message) for w in rec
    )


def test_require_dependency_extension_found_returns_dependency(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class DummyWidget:
        __module__ = "fakepkg.sub"

    w = DummyWidget()
    w._model_module = "some-widget-module"
    w._model_module_version = "^1.2.3"

    module_dir = tmp_path / "nbextensions" / "some-widget-module"
    module_dir.mkdir(parents=True)
    (module_dir / "index.js").write_text("// hi", encoding="utf-8")

    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))

    monkeypatch.setattr(deps, "jupyter_extension_path", lambda name: str(module_dir))

    dep = require_dependency(w, session)
    assert dep is not None
    assert dep.name == "some-widget-module"
    assert str(dep.version) == "1.2.3"
    assert dep.all_files is True

    head = str(dep.head)
    assert "window.require.config(" in head
    assert "some-widget-module" in head
    assert "/lib/some-widget-module-1.2.3/index" in head
