import json
import os
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
    jupyter_vue_dependency,
    output_binding_dependency,
    parse_version,
    parse_version_safely,
    relax_anywidget_init_timeout,
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


def test_widget_pkg_accepts_classes_and_builtin_instances() -> None:
    class Dummy:
        pass

    Dummy.__module__ = "somepkg.sub.mod"
    assert widget_pkg(Dummy) == "somepkg"
    assert widget_pkg(str) == "builtins"
    assert widget_pkg("x") == "builtins"
    assert widget_pkg({}) == "builtins"
    assert widget_pkg(1) == "builtins"
    assert widget_pkg(object()) == "builtins"


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
    # require-config.js must load first (see comment in output_binding_dependency)
    assert dep.script == [
        {"src": "require-config.js"},
        {"src": "libembed-amd.js"},
        {"src": "output.js"},
    ]
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


# (module, expected shim): pythreejs's three.js is a UMD bundle, which takes
# the global-export branch under shiny's define.amd = false, so its module
# value has to come from a shim; ipyvolume's is a plain AMD module
@pytest.mark.parametrize(
    "module_name,shim",
    [("ipyvolume", None), ("jupyter-threejs", "THREE")],
)
def test_require_dependency_maps_bundled_amd_dependencies(
    tmp_path, monkeypatch: pytest.MonkeyPatch, module_name: str, shim: str | None
) -> None:
    # ipyvolume's and pythreejs's AMD bundles declare an external `three`
    # dependency; each ships its own three.js build in its nbextension
    # directory, which must be mapped (scoped per module) or require.js
    # resolves `three` relative to the app root and 404s
    class DummyWidget:
        __module__ = f"{module_name}.widgets"

    w = DummyWidget()
    w._model_module = module_name
    w._model_module_version = "^1.2.3"

    module_dir = tmp_path / "nbextensions" / module_name
    module_dir.mkdir(parents=True)
    (module_dir / "index.js").write_text("// hi", encoding="utf-8")
    (module_dir / "three.js").write_text("// three", encoding="utf-8")

    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))
    monkeypatch.setattr(deps, "jupyter_extension_path", lambda name: str(module_dir))

    dep = require_dependency(w, session)
    assert dep is not None
    head = str(dep.head)
    config = json.loads(head.split("window.require.config(", 1)[1].split(")", 1)[0])
    alias = f"{module_name}/three"
    assert config["paths"][alias].endswith(f"{module_name}-1.2.3/three")
    assert config["map"] == {module_name: {"three": alias}}
    if shim is None:
        assert "shim" not in config
    else:
        assert config["shim"] == {alias: {"exports": shim}}


def test_require_dependency_without_bundled_amd_dependency(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No three.js next to index.js: no map config (the CDN fallback applies)
    class DummyWidget:
        __module__ = "ipyvolume.widgets"

    w = DummyWidget()
    w._model_module = "ipyvolume"
    w._model_module_version = "^1.2.3"

    module_dir = tmp_path / "nbextensions" / "ipyvolume"
    module_dir.mkdir(parents=True)
    (module_dir / "index.js").write_text("// hi", encoding="utf-8")

    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))
    monkeypatch.setattr(deps, "jupyter_extension_path", lambda name: str(module_dir))

    dep = require_dependency(w, session)
    assert dep is not None
    head = str(dep.head)
    config = json.loads(head.split("window.require.config(", 1)[1].split(")", 1)[0])
    assert "map" not in config


def test_jupyter_vue_dependency_maps_the_nbextension(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # jupyter-vuetify's AMD bundle externally requires('jupyter-vue'); without
    # this path config require.js requests jupyter-vue.js at the app root
    # (404) and falls back to a CDN
    module_dir = tmp_path / "nbextensions" / "jupyter-vue"
    module_dir.mkdir(parents=True)
    (module_dir / "index.js").write_text("// hi", encoding="utf-8")

    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))
    monkeypatch.setattr(deps, "jupyter_extension_path", lambda name: str(module_dir))

    dep = jupyter_vue_dependency(session)
    assert dep is not None
    head = str(dep.head)
    config = json.loads(head.split("window.require.config(", 1)[1].split(")", 1)[0])
    assert config["paths"]["jupyter-vue"].startswith("/lib/jupyter-vue-")
    assert config["paths"]["jupyter-vue"].endswith("/index")


def test_jupyter_vue_dependency_missing_nbextension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))
    monkeypatch.setattr(deps, "jupyter_extension_path", lambda name: None)

    assert jupyter_vue_dependency(session) is None


ANYWIDGET_INDEX_JS = """
    AbortSignal.timeout(2e3).addEventListener("abort", () => {
      resolvers.reject(new Error("[anywidget] Failed to initialize model."));
    });
"""


def test_relax_anywidget_init_timeout_patches_copy(tmp_path) -> None:
    module_dir = tmp_path / "anywidget"
    module_dir.mkdir()
    (module_dir / "index.js").write_text(ANYWIDGET_INDEX_JS, encoding="utf-8")
    (module_dir / "extension.js").write_text("// ext", encoding="utf-8")

    patched_dir = relax_anywidget_init_timeout(str(module_dir))
    assert patched_dir != str(module_dir)

    with open(os.path.join(patched_dir, "index.js"), encoding="utf-8") as f:
        js = f.read()
    assert "AbortSignal.timeout(60000)" in js
    assert "2e3" not in js
    # The original extension directory is left untouched
    with open(module_dir / "index.js", encoding="utf-8") as f:
        assert f.read() == ANYWIDGET_INDEX_JS
    # Sibling files come along for the ride
    assert os.path.exists(os.path.join(patched_dir, "extension.js"))

    # Repeat calls are cached
    assert relax_anywidget_init_timeout(str(module_dir)) == patched_dir


def test_relax_anywidget_init_timeout_falls_back_when_pattern_missing(
    tmp_path,
) -> None:
    module_dir = tmp_path / "anywidget"
    module_dir.mkdir()
    (module_dir / "index.js").write_text("// no timeout here", encoding="utf-8")

    assert relax_anywidget_init_timeout(str(module_dir)) == str(module_dir)
