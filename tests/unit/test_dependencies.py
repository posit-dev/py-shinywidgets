import json
import os
import sys
import types
import warnings
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import shinywidgets._dependencies as deps
from htmltools import HTMLDependency
from ipywidgets.widgets.domwidget import DOMWidget
from shiny import Session
from shiny.session import session_context
from shinywidgets._dependencies import (
    amd_externals,
    jupyter_extension_destination,
    jupyter_extension_path,
    output_binding_dependency,
    parse_version,
    parse_version_safely,
    require_dependencies,
    widget_pkg,
)
from traitlets import Unicode


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


@pytest.fixture
def ipyreact_guard() -> Iterator[Any]:
    # Importing ipyreact constructs its process-global ImportMap widget, which
    # our hook registers in SHARED_WIDGETS; don't let it leak into other test
    # modules (they would try to open it in every session they create). Evict
    # ipyreact from sys.modules afterwards so test_ipyreact.py re-imports it
    # fresh and finds the ImportMap widget it expects to be shared.
    import shinywidgets._shinywidgets as sw

    before = dict(sw.SHARED_WIDGETS)
    mod = pytest.importorskip("ipyreact")
    try:
        yield mod
    finally:
        for model_id, w in list(sw.SHARED_WIDGETS.items()):
            if before.get(model_id) is not w:
                w.close()
                sw.SHARED_WIDGETS.pop(model_id, None)
        for name in (
            n for n in list(sys.modules) if n == "ipyreact" or n.startswith("ipyreact.")
        ):
            del sys.modules[name]


def test_ipyreact_subclass_in_app_module_resolves_dependencies(
    ipyreact_guard: Any, widget_session: Session
) -> None:
    # Subclassing a third-party widget in app code (e.g.
    # `class ConfettiButton(ipyreact.ValueWidget)` in app.py) makes the class's
    # __module__ the app module; its JavaScript must still resolve to the base
    # package. ipyreact is the case that actually breaks without this: its
    # _model_module ("@widgetti/jupyter-react") doesn't match its nbextension
    # dest ("jupyter-react"), so this fallback path is the only way its JS
    # dependencies are found (previously require_dependencies() returned []
    # and the browser failed with `ReferenceError: React is not defined`).
    ipyreact = ipyreact_guard

    class ConfettiButton(ipyreact.ValueWidget):
        _esm = "export default { render: () => null }"

    ConfettiButton.__module__ = "app"

    with session_context(widget_session):
        w = ConfettiButton()
    assert jupyter_extension_destination(w) == "jupyter-react"
    resolved = require_dependencies(w, widget_session)
    assert len(resolved) > 0
    assert resolved[0].name == "@widgetti/jupyter-react"


def test_ipyreact_subclass_in_another_package_resolves_dependencies(
    ipyreact_guard: Any, widget_session: Session
) -> None:
    # A component library built on ipyreact subclasses its widgets in its own
    # installed package, which ships no JavaScript of its own: the JavaScript
    # still belongs to ipyreact, the package whose class declares the npm
    # module name.
    ipyreact = ipyreact_guard

    class LibraryButton(ipyreact.ValueWidget):
        _esm = "export default { render: () => null }"

    # htmltools stands in for any installed package without an nbextension
    LibraryButton.__module__ = "htmltools.components"

    with session_context(widget_session):
        w = LibraryButton()
    assert jupyter_extension_destination(w) == "jupyter-react"
    resolved = require_dependencies(w, widget_session)
    assert len(resolved) > 0
    assert resolved[0].name == "@widgetti/jupyter-react"


def test_subclass_declaring_its_own_npm_module_is_not_served_the_base_bundle(
    ipyreact_guard: Any, widget_session: Session
) -> None:
    # A subclass that points at its own JavaScript (here, a module that only
    # exists on a CDN) must not have its base package's bundle served under
    # that module's name; with no local copy, it's left to the CDN fallback.
    ipyreact = ipyreact_guard

    class ForkedButton(ipyreact.ValueWidget):
        _esm = "export default { render: () => null }"
        _model_module = Unicode("my-cdn-only-fork").tag(sync=True)
        _view_module = Unicode("my-cdn-only-fork").tag(sync=True)

    ForkedButton.__module__ = "app"

    with session_context(widget_session):
        w = ForkedButton()
    with pytest.warns(UserWarning, match="CDN fallback"):
        assert require_dependencies(w, widget_session) == []


def test_anywidget_subclass_in_app_module_dependencies_unchanged(
    widget_session: Session,
) -> None:
    # Regression: anywidget subclasses resolved fine before (their _model_module
    # matches their nbextension dest, so the first lookup path hits) and must
    # keep resolving.
    anywidget = pytest.importorskip("anywidget")

    class MyWidget(anywidget.AnyWidget):
        _esm = "export default { render: () => null }"

    MyWidget.__module__ = "app"

    with session_context(widget_session):
        w = MyWidget()
    assert jupyter_extension_destination(w) == "anywidget"
    resolved = require_dependencies(w, widget_session)
    assert len(resolved) > 0
    assert resolved[0].name == "anywidget"


def test_ipyleaflet_subclass_in_app_module_dependencies_unchanged(
    widget_session: Session,
) -> None:
    # Regression: ipyleaflet subclasses resolved fine before (its _model_module,
    # "jupyter-leaflet", matches its nbextension dest, so resolution succeeds on
    # the first lookup path) and must keep resolving.
    ipyleaflet = pytest.importorskip("ipyleaflet")

    class MyMap(ipyleaflet.Map):
        pass

    MyMap.__module__ = "app"

    with session_context(widget_session):
        w = MyMap()
    resolved = require_dependencies(w, widget_session)
    assert len(resolved) > 0
    assert resolved[0].name == "jupyter-leaflet"


@pytest.mark.parametrize(
    ("init_src", "dest"),
    [
        (
            "def _jupyter_nbextension_paths():\n"
            "    return [{'dest': 'srcpkg-nbext'}]\n",
            "srcpkg-nbext",
        ),
        ("", "srcpkg"),
    ],
    ids=["registered", "unregistered"],
)
def test_source_tree_widget_pkg_resolves_to_its_own_nbextension(
    init_src: str,
    dest: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    widget_session: Session,
) -> None:
    # A widget package that's importable without distribution metadata (e.g.,
    # vendored on sys.path, or some editable installs) still owns its
    # JavaScript: under its _jupyter_nbextension_paths() destination when it
    # registers one, and under the package's own name otherwise. (The widget's
    # _model_module, "srcpkg-npm", matches neither, so resolution depends on
    # the destination lookup.)
    pkg = tmp_path / "srcpkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(init_src, encoding="utf-8")
    (pkg / "widget.py").write_text(
        "from ipywidgets.widgets.domwidget import DOMWidget\n"
        "from traitlets import Unicode\n"
        "class SourceTreeWidget(DOMWidget):\n"
        "    _model_module = Unicode('srcpkg-npm').tag(sync=True)\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    try:
        import srcpkg.widget

        with session_context(widget_session):
            w = srcpkg.widget.SourceTreeWidget()
        assert jupyter_extension_destination(w) == dest
    finally:
        for name in (
            n for n in list(sys.modules) if n == "srcpkg" or n.startswith("srcpkg.")
        ):
            del sys.modules[name]


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


def test_jupyter_extension_path_prefers_first_matching_data_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module_name = "priority-test-widget"
    first_dir = tmp_path / "first" / "nbextensions" / module_name
    later_dir = tmp_path / "later" / "nbextensions" / module_name
    for directory in (first_dir, later_dir):
        directory.mkdir(parents=True)
        (directory / "index.js").write_text("// widget", encoding="utf-8")

    monkeypatch.setenv(
        "JUPYTER_PATH",
        os.pathsep.join(str(tmp_path / root) for root in ("first", "later")),
    )

    assert jupyter_extension_path(module_name) == str(first_dir)


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


def test_require_dependencies_core_widgets_return_empty_list() -> None:
    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))
    # Avoid calling ipywidgets constructors (shinywidgets registers a construction callback
    # that requires an active Shiny session).
    w = DOMWidget.__new__(DOMWidget)
    w._view_module = "@jupyter-widgets/controls"  # type: ignore[attr-defined]
    assert require_dependencies(w, session) == []


def test_require_dependencies_missing_extension_warns_and_returns_empty_list(
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
        assert require_dependencies(w, session, warn_if_missing=True) == []

    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        assert require_dependencies(w, session, warn_if_missing=False) == []
    assert not any(
        "Couldn't find local path to widget extension" in str(w.message) for w in rec
    )


def test_require_dependencies_extension_found_returns_dependencies(
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

    resolved = require_dependencies(w, session)
    assert len(resolved) == 1
    dep = resolved[0]
    assert dep.name == "some-widget-module"
    assert str(dep.version) == "1.2.3"
    assert dep.all_files is True

    head = str(dep.head)
    assert "window.require.config(" in head
    assert "some-widget-module" in head
    assert "/lib/some-widget-module-1.2.3/index" in head
    assert '"shim"' not in head


def test_require_dependencies_falls_back_when_view_module_is_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class NoViewModuleWidget(DOMWidget):
        _view_module = Unicode(None, allow_none=True).tag(sync=True)
        _model_module = Unicode("jupyter-vue").tag(sync=True)

    w = NoViewModuleWidget.__new__(NoViewModuleWidget)
    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))

    looked_up: list[str] = []

    def spy(module_name: str) -> None:
        looked_up.append(module_name)

    monkeypatch.setattr(deps, "jupyter_extension_path", spy)
    monkeypatch.setattr(deps, "jupyter_extension_destination", lambda w: "some-dest")

    assert require_dependencies(w, session, warn_if_missing=False) == []
    assert looked_up[0] == "jupyter-vue"


AMD_INDEX = 'define(["three","@jupyter-widgets/base"],function(t,e){return {}})'
# ipyvolume's three.js is a plain AMD bundle...
AMD_THREE_JS = "define(function(){return {}})"
# ...while pythreejs's is a UMD bundle, which takes the global-export branch
# under shiny's define.amd = false, so its module value has to come from a shim
UMD_THREE_JS = '(function(g,f){"object"===typeof exports?f(exports):"function"===typeof define&&define.amd?define(["exports"],f):f(g.THREE={})})(this,function(g){})'


# (module, three.js content, expected shim): the module's own copy of a
# bundled external must be mapped (scoped per module) or require.js resolves
# `three` relative to the app root and 404s
@pytest.mark.parametrize(
    "module_name,three_js,shim",
    [("ipyvolume", AMD_THREE_JS, None), ("jupyter-threejs", UMD_THREE_JS, "THREE")],
)
def test_require_dependencies_maps_bundled_amd_dependencies(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    three_js: str,
    shim: str | None,
) -> None:
    # ipyvolume's and pythreejs's AMD bundles declare an external `three`
    # dependency; each ships its own three.js build in its nbextension
    # directory
    class DummyWidget:
        __module__ = f"{module_name}.widgets"

    w = DummyWidget()
    w._model_module = module_name
    w._model_module_version = "^1.2.3"

    module_dir = tmp_path / "nbextensions" / module_name
    module_dir.mkdir(parents=True)
    (module_dir / "index.js").write_text(AMD_INDEX, encoding="utf-8")
    (module_dir / "three.js").write_text(three_js, encoding="utf-8")

    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))
    monkeypatch.setattr(deps, "jupyter_extension_path", lambda name: str(module_dir))

    resolved = require_dependencies(w, session)
    assert len(resolved) == 1
    head = str(resolved[0].head)
    config = json.loads(head.split("window.require.config(", 1)[1].split(")", 1)[0])
    alias = f"{module_name}/three"
    assert config["paths"][alias].endswith(f"{module_name}-1.2.3/three")
    assert config["map"] == {module_name: {"three": alias}}
    if shim is None:
        assert "shim" not in config
    else:
        assert config["shim"] == {alias: {"exports": shim}}


def test_require_dependencies_warns_for_unknown_sibling_format(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class DummyWidget:
        __module__ = "fakepkg.widgets"

    w = DummyWidget()
    w._model_module = "some-widget"
    w._model_module_version = "^1.2.3"

    module_dir = tmp_path / "nbextensions" / "some-widget"
    module_dir.mkdir(parents=True)
    (module_dir / "index.js").write_text(
        'define(["three"],function(t){})', encoding="utf-8"
    )
    (module_dir / "three.js").write_text(
        "!function(){ oddWrapperSyntax(); }()", encoding="utf-8"
    )

    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))
    monkeypatch.setattr(
        deps,
        "jupyter_extension_path",
        lambda name: str(module_dir) if name == "some-widget" else None,
    )

    with pytest.warns(UserWarning, match="doesn't look like an AMD bundle"):
        resolved = require_dependencies(w, session)
    head = str(resolved[0].head)
    config = json.loads(head.split("window.require.config(", 1)[1].split(")", 1)[0])
    assert config["map"] == {"some-widget": {"three": "some-widget/three"}}
    assert "shim" not in config


def test_require_dependencies_without_bundled_amd_dependency(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An external `three` with no three.js next to index.js and no `three`
    # nbextension: no map config, so the external remains unresolved
    class DummyWidget:
        __module__ = "ipyvolume.widgets"

    w = DummyWidget()
    w._model_module = "ipyvolume"
    w._model_module_version = "^1.2.3"

    module_dir = tmp_path / "nbextensions" / "ipyvolume"
    module_dir.mkdir(parents=True)
    (module_dir / "index.js").write_text(AMD_INDEX, encoding="utf-8")

    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))
    monkeypatch.setattr(
        deps,
        "jupyter_extension_path",
        lambda name: str(module_dir) if name == "ipyvolume" else None,
    )

    resolved = require_dependencies(w, session)
    assert len(resolved) == 1
    head = str(resolved[0].head)
    config = json.loads(head.split("window.require.config(", 1)[1].split(")", 1)[0])
    assert "map" not in config


def _nbextension(tmp_path: Path, name: str, index_js: str) -> str:
    module_dir = tmp_path / "nbextensions" / name
    module_dir.mkdir(parents=True)
    (module_dir / "index.js").write_text(index_js, encoding="utf-8")
    return str(module_dir)


def test_require_dependencies_resolves_external_nbextensions(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # jupyter-vuetify's AMD bundle externally requires('jupyter-vue'); when an
    # nbextension by that name is installed, it's mounted and path-configured
    # alongside the widget's own module (otherwise require.js requests
    # jupyter-vue.js at the app root and 404s)
    dirs = {
        "jupyter-vuetify": _nbextension(
            tmp_path,
            "jupyter-vuetify",
            'define(["jupyter-vue","@jupyter-widgets/base"],function(v,w){})',
        ),
        "jupyter-vue": _nbextension(
            tmp_path, "jupyter-vue", 'define(["@jupyter-widgets/base"],function(w){})'
        ),
    }

    class DummyWidget:
        __module__ = "ipyvuetify.widgets"

    w = DummyWidget()
    w._model_module = "jupyter-vuetify"
    w._model_module_version = "^1.2.3"

    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))
    monkeypatch.setattr(deps, "jupyter_extension_path", lambda name: dirs.get(name))

    resolved = require_dependencies(w, session)
    assert [d.name for d in resolved] == ["jupyter-vuetify", "jupyter-vue"]
    head = str(resolved[1].head)
    config = json.loads(head.split("window.require.config(", 1)[1].split(")", 1)[0])
    assert config["paths"]["jupyter-vue"].startswith("/lib/jupyter-vue-")
    assert config["paths"]["jupyter-vue"].endswith("/index")


def test_require_dependencies_resolves_transitive_external_nbextensions(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An external nbextension may itself declare externals
    dirs = {
        "some-widget": _nbextension(
            tmp_path, "some-widget", 'define(["ext-a"],function(a){})'
        ),
        "ext-a": _nbextension(tmp_path, "ext-a", 'define(["ext-b"],function(b){})'),
        "ext-b": _nbextension(tmp_path, "ext-b", "define([],function(){})"),
    }

    class DummyWidget:
        __module__ = "fakepkg.sub"

    w = DummyWidget()
    w._model_module = "some-widget"
    w._model_module_version = "^1.2.3"

    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))
    monkeypatch.setattr(deps, "jupyter_extension_path", lambda name: dirs.get(name))

    resolved = require_dependencies(w, session)
    assert [d.name for d in resolved] == ["some-widget", "ext-a", "ext-b"]


def test_require_dependencies_unresolvable_external_adds_no_config(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An external that is neither a sibling file nor an installed nbextension
    # produces no extra config or dependency
    dirs = {
        "some-widget": _nbextension(
            tmp_path, "some-widget", 'define(["not-installed"],function(x){})'
        ),
    }

    class DummyWidget:
        __module__ = "fakepkg.sub"

    w = DummyWidget()
    w._model_module = "some-widget"
    w._model_module_version = "^1.2.3"

    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))
    monkeypatch.setattr(deps, "jupyter_extension_path", lambda name: dirs.get(name))

    resolved = require_dependencies(w, session)
    assert [d.name for d in resolved] == ["some-widget"]
    head = str(resolved[0].head)
    config = json.loads(head.split("window.require.config(", 1)[1].split(")", 1)[0])
    assert "map" not in config
    assert "shim" not in config


def test_amd_externals_ignores_prebundled_and_relative_modules(tmp_path) -> None:
    module_dir = _nbextension(
        tmp_path,
        "some-widget",
        'define(["module","jquery","jupyter-js-widgets","@jupyter-widgets/base",'
        '"@jupyter-widgets/controls","base/js/dialog","./local","ext"],function(){});',
    )
    assert amd_externals(module_dir) == ["ext"]


def test_amd_externals_non_amd_bundle(tmp_path) -> None:
    module_dir = _nbextension(tmp_path, "some-widget", "export const x = 1;")
    assert amd_externals(module_dir) == []
