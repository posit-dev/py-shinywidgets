import base64
import hashlib
import os
import sys
import types
import warnings
from importlib.metadata import FileHash, PackageNotFoundError
from pathlib import PurePosixPath
from types import ModuleType, SimpleNamespace

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


@pytest.fixture(autouse=True)
def clear_distribution_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    # distribution_nbextension_paths() caches per distribution; each test fakes
    # distributions, so it needs a fresh cache
    monkeypatch.setattr(deps, "_distribution_nbextension_dirs", {})


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


def recorded_hash(content: bytes) -> FileHash:
    digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest())
    return FileHash("sha256=" + digest.rstrip(b"=").decode("ascii"))


def make_distribution_nbextension(
    tmp_path,
    module_name: str,
    pkg: str = "fakepkg",
    files: tuple[str, ...] = ("index.js", "asset.svg"),
    overwritten: dict[str, bytes] | None = None,
) -> SimpleNamespace:
    """
    A fake installed distribution that put a (complete) nbextension for
    `module_name` into a Jupyter data dir, as a wheel records it in RECORD.

    `overwritten` replaces the content of files on disk without changing what
    the distribution recorded, which is what another interpreter's install of
    the same widget into a shared data dir looks like.
    """

    class FakeDistribution:
        def __init__(self, data_dir, recorded: dict[str, bytes]) -> None:
            self.data_dir = data_dir
            self.files = [
                SimpleNamespace(
                    parts=PurePosixPath(
                        "..",
                        "..",
                        "..",
                        "share",
                        "jupyter",
                        "nbextensions",
                        module_name,
                        f,
                    ).parts,
                    hash=recorded_hash(recorded[f]),
                )
                for f in files
            ]

        def locate_file(self, path) -> str:
            # `path` is relative to the distribution's install location (e.g.
            # site-packages); resolve it against the data dir's own root
            parts = PurePosixPath(str(path)).parts
            tail = parts[parts.index("nbextensions") :]
            return str(self.data_dir.joinpath(*tail))

    recorded = {f: f"// {pkg} {f}".encode() for f in files}
    on_disk = {**recorded, **(overwritten or {})}

    data_dir = tmp_path / pkg / "share" / "jupyter"
    nb_dir = data_dir / "nbextensions" / module_name
    nb_dir.mkdir(parents=True)
    for f, content in on_disk.items():
        (nb_dir / f).write_bytes(content)

    return SimpleNamespace(dist=FakeDistribution(data_dir, recorded), dir=nb_dir)


def install_distributions(monkeypatch: pytest.MonkeyPatch, **dists) -> None:
    """Make `deps.distribution()` return the given fake distributions by name."""

    def fake_distribution(name: str):
        if name not in dists:
            raise PackageNotFoundError(name)
        return dists[name]

    monkeypatch.setattr(deps, "distribution", fake_distribution)


def test_distribution_nbextension_path_finds_data_files(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The wheel's data files are where the distribution that's actually
    # installed put its extension -- wherever that is (here: outside the
    # environment's own data dir, e.g. a `pip install --user` layout)
    class DummyWidget:
        __module__ = "fakepkg.sub"

    fake = make_distribution_nbextension(tmp_path, "some-widget-module")
    install_distributions(monkeypatch, fakepkg=fake.dist)

    path = deps.distribution_nbextension_path(DummyWidget(), "some-widget-module")  # type: ignore[arg-type]
    assert path == str(fake.dir)


def test_distribution_nbextension_path_resolves_base_class_package(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An app-defined subclass of an installed widget (e.g. an
    # `ipydatagrid.DataGrid` subclass in the app's own package) must resolve
    # through the base class's distribution, not the app's package
    fake = make_distribution_nbextension(
        tmp_path, "some-widget-module", pkg="base_widget_pkg"
    )
    install_distributions(monkeypatch, base_widget_pkg=fake.dist)

    class BaseWidget:
        __module__ = "base_widget_pkg.grid"

    class AppWidget(BaseWidget):
        __module__ = "app_pkg.maps"

    path = deps.distribution_nbextension_path(AppWidget(), "some-widget-module")  # type: ignore[arg-type]
    assert path == str(fake.dir)


def test_distribution_nbextension_path_ignores_unrecorded_extension(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A distribution that doesn't ship an nbextension for this module (e.g.
    # ipyleaflet 0.20, which removed its bundled nbextension)
    class DummyWidget:
        __module__ = "fakepkg.sub"

    dist = SimpleNamespace(
        files=[
            SimpleNamespace(parts=PurePosixPath("fakepkg/__init__.py").parts, hash=None)
        ],
        locate_file=lambda path: path,
    )
    install_distributions(monkeypatch, fakepkg=dist)

    assert (
        deps.distribution_nbextension_path(DummyWidget(), "some-widget-module")  # type: ignore[arg-type]
        is None
    )


def test_distribution_nbextension_path_skips_overwritten_data_files(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # `pip install --user` puts data files in a dir that's shared across Python
    # versions, so another interpreter's install of the same widget can
    # overwrite what this one recorded. The hash mismatch means this copy isn't
    # the frontend this package expects, so it isn't used.
    class DummyWidget:
        __module__ = "fakepkg.sub"

    fake = make_distribution_nbextension(
        tmp_path,
        "some-widget-module",
        overwritten={"index.js": b"// another interpreter's install"},
    )
    install_distributions(monkeypatch, fakepkg=fake.dist)

    assert (
        deps.distribution_nbextension_path(DummyWidget(), "some-widget-module")  # type: ignore[arg-type]
        is None
    )


def test_distribution_nbextension_path_checks_only_index_js(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # require.js loads `index.js`, so an intact alternate bundle must not vouch
    # for an `index.js` that another install overwrote
    class DummyWidget:
        __module__ = "fakepkg.sub"

    fake = make_distribution_nbextension(
        tmp_path,
        "some-widget-module",
        files=("index.js", "index.min.js"),
        overwritten={"index.js": b"// another interpreter's install"},
    )
    install_distributions(monkeypatch, fakepkg=fake.dist)

    assert (
        deps.distribution_nbextension_path(DummyWidget(), "some-widget-module")  # type: ignore[arg-type]
        is None
    )


def test_distribution_nbextension_path_handles_scoped_extension(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Scoped extension names (e.g. "@scope/some-widget") keep their full path
    # below the nbextensions dir
    class DummyWidget:
        __module__ = "fakepkg.sub"

    fake = make_distribution_nbextension(tmp_path, "@scope/some-widget")
    install_distributions(monkeypatch, fakepkg=fake.dist)

    path = deps.distribution_nbextension_path(DummyWidget(), "@scope/some-widget")  # type: ignore[arg-type]
    assert path == str(fake.dir)
    assert path is not None and path.endswith(
        os.path.join("nbextensions", "@scope", "some-widget")
    )


def test_require_dependency_falls_back_to_bundled_when_data_files_overwritten(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # ... and when that happens, the nbextension bundled with the imported
    # package is used instead of the overwritten copy
    class DummyWidget:
        __module__ = "fakepkg.sub"

    w = DummyWidget()
    w._model_module = "some-widget-module"
    w._model_module_version = "^1.2.3"

    mod = make_nbextension_pkg(tmp_path)
    fake = make_distribution_nbextension(
        tmp_path,
        "some-widget-module",
        overwritten={"index.js": b"// another interpreter's install"},
    )

    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))
    install_distributions(monkeypatch, fakepkg=fake.dist)
    monkeypatch.setitem(sys.modules, "fakepkg", mod)

    dep = require_dependency(w, session)
    assert dep is not None
    assert dep.source == {"subdir": str(tmp_path / "fakepkg" / "nbextension")}


def test_recorded_file_matches() -> None:
    # Unknown/absent hashes can't be checked, so the file is accepted
    assert deps.recorded_file_matches("/nonexistent", None) is True
    assert deps.recorded_file_matches("/nonexistent", FileHash("md5=abc")) is True
    # A recorded file that's missing on disk doesn't match
    assert deps.recorded_file_matches("/nonexistent", FileHash("sha256=abc")) is False


def test_require_dependency_prefers_data_files_over_bundled(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The data files the wheel installed are complete (they include the assets
    # the bundle loads at runtime), unlike some bundled nbextensions (e.g.,
    # ipydatagrid's bundled copy lacks its SVG/PNG assets)
    class DummyWidget:
        __module__ = "fakepkg.sub"

    w = DummyWidget()
    w._model_module = "some-widget-module"
    w._model_module_version = "^1.2.3"

    mod = make_nbextension_pkg(tmp_path)
    fake = make_distribution_nbextension(tmp_path, "some-widget-module")

    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))
    install_distributions(monkeypatch, fakepkg=fake.dist)
    monkeypatch.setitem(sys.modules, "fakepkg", mod)

    dep = require_dependency(w, session)
    assert dep is not None
    assert dep.source == {"subdir": str(fake.dir)}


def test_require_dependency_data_files_win_over_stale_data_dirs(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The distribution's own data files win over a stale copy in another
    # Jupyter data dir (the #332 failure mode), even with no bundled copy
    # available (e.g., an editable install)
    class DummyWidget:
        __module__ = "fakepkg.sub"

    w = DummyWidget()
    w._model_module = "some-widget-module"
    w._model_module_version = "^1.2.3"

    fake = make_distribution_nbextension(tmp_path, "some-widget-module")

    stale_root = tmp_path / "stale"
    stale_dir = stale_root / "nbextensions" / "some-widget-module"
    stale_dir.mkdir(parents=True)
    (stale_dir / "index.js").write_text("// stale", encoding="utf-8")

    session = types.SimpleNamespace(app=types.SimpleNamespace(lib_prefix="/lib"))
    install_distributions(monkeypatch, fakepkg=fake.dist)
    monkeypatch.setattr(deps, "jupyter_path", lambda: [str(stale_root)])

    dep = require_dependency(w, session)
    assert dep is not None
    assert dep.source == {"subdir": str(fake.dir)}


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
