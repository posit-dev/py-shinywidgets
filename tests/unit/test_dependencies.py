import os
import sys
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
    package_nbextension_path,
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

    monkeypatch.setattr(deps, "jupyter_extension_path", lambda name, paths=None: None)
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


def make_nbextension_pkg(
    tmp_path, name: str = "fakepkg", dest: str = "some-widget-module"
) -> ModuleType:
    """A fake installed package that bundles an nbextension for `dest`."""
    ext_dir = tmp_path / name / "nbextension"
    ext_dir.mkdir(parents=True)
    (ext_dir / "index.js").write_text("// bundled", encoding="utf-8")

    mod = ModuleType(name)
    mod.__file__ = str(tmp_path / name / "__init__.py")
    mod._jupyter_nbextension_paths = lambda: [  # type: ignore[attr-defined]
        {"section": "notebook", "src": "nbextension", "dest": dest}
    ]
    return mod


def test_package_nbextension_path_finds_bundled_extension(tmp_path) -> None:
    class DummyWidget:
        __module__ = "fakepkg.sub"

    mod = make_nbextension_pkg(tmp_path)
    sys.modules["fakepkg"] = mod
    try:
        path = package_nbextension_path(DummyWidget(), "some-widget-module")
        assert path == str(tmp_path / "fakepkg" / "nbextension")
    finally:
        del sys.modules["fakepkg"]


def test_package_nbextension_path_resolves_extension_named_package(tmp_path) -> None:
    # plotly widgets request the "jupyterlab-plotly" module, but the
    # nbextension ships inside the separate jupyterlab_plotly package (#332)
    class DummyWidget:
        __module__ = "plotly.basewidget"

    mod = make_nbextension_pkg(
        tmp_path, name="jupyterlab_plotly", dest="jupyterlab-plotly"
    )
    sys.modules["jupyterlab_plotly"] = mod
    try:
        path = package_nbextension_path(DummyWidget(), "jupyterlab-plotly")
        assert path == str(tmp_path / "jupyterlab_plotly" / "nbextension")
    finally:
        del sys.modules["jupyterlab_plotly"]


def test_require_dependency_prefers_bundled_over_data_dirs(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A stale copy in a user/system Jupyter data dir must not win over the
    # nbextension bundled with the installed package (#332)
    class DummyWidget:
        __module__ = "fakepkg.sub"

    w = DummyWidget()
    w._model_module = "some-widget-module"
    w._model_module_version = "^1.2.3"

    mod = make_nbextension_pkg(tmp_path)

    stale_root = tmp_path / "data"
    stale_dir = stale_root / "nbextensions" / "some-widget-module"
    stale_dir.mkdir(parents=True)
    (stale_dir / "index.js").write_text("// stale", encoding="utf-8")

    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))
    # The env data dir (ENV_JUPYTER_PATH) doesn't have this module, so the
    # stale copy would win without the bundled-extension preference
    monkeypatch.setattr(deps, "jupyter_path", lambda: [str(stale_root)])
    monkeypatch.setitem(sys.modules, "fakepkg", mod)

    dep = require_dependency(w, session)
    assert dep is not None
    # The dependency source is the bundled copy, not the stale data-dir copy
    assert dep.source == {"subdir": str(tmp_path / "fakepkg" / "nbextension")}


def test_require_dependency_prefers_env_data_dir_over_bundled(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The environment's data dir (where the wheel installs its data files,
    # including any asset files the bundle loads at runtime) wins over the
    # package-bundled copy (e.g., ipydatagrid's bundled copy lacks assets)
    class DummyWidget:
        __module__ = "fakepkg.sub"

    w = DummyWidget()
    w._model_module = "some-widget-module"
    w._model_module_version = "^1.2.3"

    mod = make_nbextension_pkg(tmp_path)

    env_dir = tmp_path / "env" / "nbextensions" / "some-widget-module"
    env_dir.mkdir(parents=True)
    (env_dir / "index.js").write_text("// env", encoding="utf-8")

    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))
    monkeypatch.setattr(deps, "ENV_JUPYTER_PATH", [str(tmp_path / "env")])
    # The widget's package is installed in this environment, so the data dir
    # copy is known to match the installed version
    monkeypatch.setattr(deps, "widget_package_in_env", lambda w: True)
    monkeypatch.setitem(sys.modules, "fakepkg", mod)

    dep = require_dependency(w, session)
    assert dep is not None
    assert dep.source == {"subdir": str(env_dir)}


def test_require_dependency_ignores_env_dir_for_packages_installed_elsewhere(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # If the widget's package isn't installed in this environment (e.g.,
    # `pip install --user`, or a leftover from an older install), a copy in
    # this environment's data dir may be stale, so the version-matched,
    # package-bundled copy wins
    class DummyWidget:
        __module__ = "fakepkg.sub"

    w = DummyWidget()
    w._model_module = "some-widget-module"
    w._model_module_version = "^1.2.3"

    mod = make_nbextension_pkg(tmp_path)

    env_dir = tmp_path / "env" / "nbextensions" / "some-widget-module"
    env_dir.mkdir(parents=True)
    (env_dir / "index.js").write_text("// stale", encoding="utf-8")

    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))
    monkeypatch.setattr(deps, "ENV_JUPYTER_PATH", [str(tmp_path / "env")])
    monkeypatch.setattr(deps, "widget_package_in_env", lambda w: False)
    monkeypatch.setitem(sys.modules, "fakepkg", mod)

    dep = require_dependency(w, session)
    assert dep is not None
    assert dep.source == {"subdir": str(tmp_path / "fakepkg" / "nbextension")}


def test_widget_package_in_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyWidget:
        __module__ = "fakepkg.sub"

    mod = types.ModuleType("fakepkg")
    monkeypatch.setitem(sys.modules, "fakepkg", mod)

    # A package installed outside of this environment (e.g., user site)
    mod.__file__ = str(tmp_path / "fakepkg" / "__init__.py")  # type: ignore[attr-defined]
    monkeypatch.setattr(deps.sys, "prefix", "/usr/nonexistent-env")
    assert deps.widget_package_in_env(DummyWidget()) is False  # type: ignore[arg-type]

    # The same package, installed in this environment
    monkeypatch.setattr(deps.sys, "prefix", str(tmp_path))
    assert deps.widget_package_in_env(DummyWidget()) is True  # type: ignore[arg-type]

    # A directory that merely shares the prefix as a string prefix is not
    # inside the environment
    sibling = tmp_path / "env-sibling"
    sibling.mkdir()
    mod.__file__ = str(sibling / "fakepkg" / "__init__.py")  # type: ignore[attr-defined]
    monkeypatch.setattr(deps.sys, "prefix", str(tmp_path / "env"))
    assert deps.widget_package_in_env(DummyWidget()) is False  # type: ignore[arg-type]

    # Unknown packages keep the historical behavior
    class Unknown:
        __module__ = "not_an_importable_package_xyz.sub"

    assert deps.widget_package_in_env(Unknown()) is True  # type: ignore[arg-type]


def test_package_nbextension_path_resolves_base_class_package(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An app-defined subclass (e.g., a leafmap-style ipyleaflet.Map subclass)
    # lives in another package, but it renders with the base class's extension
    mod = make_nbextension_pkg(
        tmp_path, name="base_widget_pkg", dest="some-widget-module"
    )
    monkeypatch.setitem(sys.modules, "base_widget_pkg", mod)

    class BaseWidget:
        __module__ = "base_widget_pkg.leaflet"

    class AppWidget(BaseWidget):
        __module__ = "app_pkg.maps"

    w = AppWidget()
    w._model_module = "some-widget-module"  # type: ignore[attr-defined]

    assert package_nbextension_path(w, "some-widget-module") == str(  # type: ignore[arg-type]
        tmp_path / "base_widget_pkg" / "nbextension"
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

    monkeypatch.setattr(
        deps, "jupyter_extension_path", lambda name, paths=None: str(module_dir)
    )

    dep = require_dependency(w, session)
    assert dep is not None
    assert dep.name == "some-widget-module"
    assert str(dep.version) == "1.2.3"
    assert dep.all_files is True

    head = str(dep.head)
    assert "window.require.config(" in head
    assert "some-widget-module" in head
    assert "/lib/some-widget-module-1.2.3/index" in head


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
