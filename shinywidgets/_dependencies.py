import importlib
import json
import os
import re
import tempfile
import warnings
from types import ModuleType
from typing import Dict, List, Optional

import packaging.version
from htmltools import HTMLDependency, tags
from htmltools._core import (
    HTMLDependencySource,  # pyright: ignore[reportPrivateImportUsage]
)
from ipywidgets.widgets.domwidget import DOMWidget
from ipywidgets.widgets.widget import Widget
from jupyter_core.paths import jupyter_path
from shiny import Session

from . import __version__


# TODO: scripts/static_download.R should produce/update these
def output_binding_dependency() -> HTMLDependency:
    # Jupyter Notebook/Lab both come "preloaded" with several @jupyter-widgets packages
    # (i.e., base, controls, output), all of which are bundled into this extension.js file
    # provided by the widgetsnbextension package, which is a dependency of ipywidgets.
    # https://github.com/nteract/nes/tree/master/portable-widgets
    # https://github.com/jupyter-widgets/ipywidgets/blob/88cec8/packages/html-manager/src/htmlmanager.ts#L115-L120
    #
    # Unfortunately, I don't think there is a good way for us to "pre-bundle" these dependencies
    # since they could change depending on the version of ipywidgets (and ipywidgets itself
    # doesn't include these dependencies in such a way that require("@jupyter-widget/base") would
    # work robustly when used in other 3rd party widgets). Moreover, I don't think we can simply
    # have @jupyter-widget/base point to https://unpkg.com/@jupyter-widgets/base@__version__/lib/index.js
    # (or a local version of this) since it appears the lib entry points aren't usable in the browser.
    #
    # All this is to say that I think we are stuck with this mega 3.5MB file that contains all of the
    # stuff we need to render widgets outside of the notebook.
    return HTMLDependency(
        name="ipywidget-output-binding",
        version=__version__,
        source={"package": "shinywidgets", "subdir": "static"},
        script=[
            # require-config.js must load before libembed-amd.js so require.js
            # resolves the @jupyter-widgets/* AMD module URLs to this directory
            # (the widgets bundles derive their CSS font URLs from it).
            {"src": "require-config.js"},
            {"src": "libembed-amd.js"},
            # Bundle our output.js in the same dependency as libembded since Quarto
            # has a bug where it doesn't renders dependencies in the order they are defined
            # (i.e., this way we can ensure the output.js script always comes after the libembed-amd.js script tag)
            {"src": "output.js"},
        ],
        stylesheet={"href": "shinywidgets.css"},
    )


def custom_elements_dependency() -> HTMLDependency:
    # Perspective's anywidget ES module calls customElements.define() at module
    # scope, and anywidget evaluates that module once per model, so a second model
    # in the page (e.g., after a re-render) throws "the name ... has already been
    # used" and never initializes. Perspective guards its own registrations
    # against this, but these three elements (registered at module scope by its
    # bundled regular-layout dependency) are unguarded. Ignoring just their
    # redefinition leaves the elements registered by the first evaluation in
    # place, while duplicate registration of any other element still throws, as
    # the platform intends.
    return HTMLDependency(
        name="shinywidgets-custom-elements",
        version=__version__,
        head=tags.script(
            """
(function () {
  const PERSPECTIVE_ELEMENTS = new Set([
    "regular-layout",
    "regular-layout-frame",
    "regular-layout-tab",
  ]);
  const define = customElements.define;
  customElements.define = function (name, constructor, options) {
    if (PERSPECTIVE_ELEMENTS.has(name) && customElements.get(name)) return;
    define.call(customElements, name, constructor, options);
  };
})();
"""
        ),
    )


# TODO: this function might have to be recursive since it's technically
# possible for a Widget to have traits that are themselves Widgets
# (which could have their own npm module), but in practice, I haven't seen any cases
# where a 3rd party widget can contain a 3rd party widget.
def require_dependency(
    w: Widget, session: Session, warn_if_missing: bool = True
) -> List[HTMLDependency]:
    """
    Obtain HTMLDependencies for a 3rd party ipywidget that point
    require('widget-npm-package') requests in the browser to the correct local
    paths. The first entry serves the widget's own module; any additional
    entries serve AMD externals of the widget's bundle that are themselves
    installed nbextensions (see amd_require_config()).
    """

    # The relevant npm package should be specified as an attribute on the widget
    # instance. If the widget is installed as a jupyter extension, in most cases, that
    # name will registered at the extension name/directory
    module_attr = "_view_module" if isinstance(w, DOMWidget) else "_model_module"
    module_name: str = getattr(w, module_attr, widget_pkg(w))

    # ipywidgets (i.e., @jupyter-widgets) come pre-bundled in libembed-amd.js
    # # (i.e., _core() dependencies)
    if module_name.startswith("@jupyter-widgets/"):
        return []

    # It's technically possible for the npm package name to be different from the actual
    # extension path (defined by `_jupyter_nbextension_paths` in __init__.py), but we
    # also don't have a fool-proof way to discovering the relevant __init__.py file,
    # which is why we only use look for it if the npm package isn't installed
    module_dir = jupyter_extension_path(module_name)
    if module_dir is None:
        module_dir = jupyter_extension_path(jupyter_extension_destination(w))
        if module_dir is None:
            if warn_if_missing:
                warnings.warn(
                    f"Couldn't find local path to widget extension for {type(w)}."
                    + " Since a CDN fallback is provided, the widget will still render if an internet connection is available."
                    + " To avoid depending on a CDN, make sure the widget is installed as a jupyter extension.",
                    stacklevel=2,
                )
            return []

    if module_name == "anywidget":
        module_dir = relax_anywidget_init_timeout(module_dir)

    version = parse_version_safely(getattr(w, "_model_module_version", "1.0"))

    deps: List[HTMLDependency] = []
    # The widget's own module, plus any AMD externals (of the modules visited
    # along the way) that are themselves installed nbextensions
    seen: set[str] = set()
    worklist = [(module_name, module_dir, version)]
    while worklist:
        name, dir_, ver = worklist.pop(0)
        if name in seen:
            continue
        seen.add(name)
        source = HTMLDependencySource(subdir=dir_)
        dep = HTMLDependency(name, ver, source=source)
        # Get the location where the dependency files will be mounted by the shiny app
        # and use that to inform the requirejs import path
        href = dep.source_path_map(lib_prefix=session.app.lib_prefix)["href"]
        config, nbextensions = amd_require_config(name, dir_, href)
        # Basically our equivalent of the extension.js file provided by the cookiecutter
        # https://github.com/jupyter-widgets/widget-cookiecutter/blob/master/%7B%7Bcookiecutter.github_project_name%7D%7D/js/lib/extension.js
        deps.append(
            HTMLDependency(
                name,
                ver,
                source=source,
                all_files=True,
                head=tags.script(f"window.require.config({json.dumps(config)})"),
            )
        )
        for ext in nbextensions:
            ext_dir = jupyter_extension_path(ext)
            if ext_dir is not None:
                worklist.append((ext, ext_dir, dir_version(ext_dir)))

    return deps


# Module names that a widget bundle may declare in the define([...]) header of
# its AMD bundle, but that shinywidgets' browser environment already provides:
# the @jupyter-widgets packages come prebundled in libembed-amd.js, and the
# rest are require.js or classic-notebook builtins
AMD_PREBUNDLED = {
    "module",
    "require",
    "exports",
    "jquery",
    "jupyter-js-widgets",
}


def amd_externals(module_dir: str) -> List[str]:
    """
    The externals declared by an nbextension's AMD bundle (in the define([...])
    header of its index.js) that shinywidgets' browser environment doesn't
    already provide.

    Widget packages built with a webpack `externals` config (e.g., ipyvolume
    and pythreejs externalize `three`; jupyter-vuetify externalizes
    `jupyter-vue`) rely on the classic notebook's global require.config
    registry (built up at page load from every enabled nbextension's
    extension.js) to resolve those names. shinywidgets loads widget modules on
    demand instead, so without an explicit paths/map entry, require.js
    resolves such names relative to the app root (404).
    """
    try:
        with open(
            os.path.join(module_dir, "index.js"), encoding="utf-8", errors="replace"
        ) as f:
            head = f.read(8192)
    except OSError:
        return []
    m = re.search(r"define\(\s*\[([^\]]*)\]", head)
    if not m:
        # Not an AMD bundle (e.g., an anywidget ESM index.js), or not one we
        # can parse; either way there's nothing to resolve
        return []
    deps = re.findall(r"""["']([^"']+)["']""", m.group(1))
    return [
        dep
        for dep in deps
        if dep not in AMD_PREBUNDLED
        and not dep.startswith(("@jupyter-widgets/", "base/js/", "./", "../"))
    ]


def amd_require_config(
    module_name: str, module_dir: str, href: str
) -> "tuple[dict[str, object], List[str]]":
    """
    The require.js config for one nbextension module: a paths entry for the
    module itself, plus scoped aliases for any externals the bundle ships
    inside its own nbextension directory. Also returns the names of externals
    that are themselves installed nbextensions (they need their own dependency
    to mount and configure them).
    """
    paths: Dict[str, str] = {module_name: os.path.join(href, "index")}
    map_: Dict[str, Dict[str, str]] = {}
    shim: Dict[str, Dict[str, str]] = {}
    nbextensions: List[str] = []
    for ext in amd_externals(module_dir):
        ext_file = os.path.join(module_dir, f"{ext}.js")
        if os.path.isfile(ext_file):
            # The bundle ships its own copy of the external: serve it under an
            # alias scoped to this module (via require.js map) -- another
            # module may ship an incompatible build under the same name
            # (ipyvolume and pythreejs, for example, bundle different
            # three.js builds, and an ipyvolume figure needs both)
            alias = f"{module_name}/{ext}"
            paths[alias] = os.path.join(href, ext)
            map_[module_name] = {**map_.get(module_name, {}), ext: alias}
            global_name = AMD_UMD_GLOBAL_OVERRIDES.get(module_name, {}).get(
                ext
            ) or umd_global(ext_file)
            if global_name is not None:
                # UMD bundles take the global-export branch (shiny's require.js
                # wrapper keeps define.amd = false), so expose the global as
                # the module value
                shim[alias] = {"exports": global_name}
        elif jupyter_extension_path(ext) is not None:
            nbextensions.append(ext)
        # Otherwise leave the external unresolved. The widget-level CDN retry
        # does not configure paths for its bare externals.
    config: dict[str, object] = {"paths": paths}
    if map_:
        config["map"] = map_
    if shim:
        config["shim"] = shim
    return config, nbextensions


# Override for UMD bundles whose exported global can't be sniffed from the
# bundle wrapper by umd_global() (module name -> external -> global name).
# Empty so far: every UMD bundle we've encountered writes its global in one of
# the standard shapes (e.g., pythreejs's three.js does `global.THREE = {}`)
AMD_UMD_GLOBAL_OVERRIDES: Dict[str, Dict[str, str]] = {}


def umd_global(js_file: str) -> Optional[str]:
    """
    The global variable a UMD-style bundle exports, or None for a plain AMD
    bundle (which provides its module value by calling define()).
    """
    try:
        with open(js_file, encoding="utf-8", errors="replace") as f:
            head = f.read(1024)
    except OSError:
        return None
    # Skip past leading comments/whitespace
    stripped = re.sub(r"\A(?:\s|/\*.*?\*/|//[^\n]*)*", "", head, flags=re.S)
    if stripped.startswith("define("):
        return None
    # The UMD global-export branch: rollup writes `global.Name = {}`, webpack
    # writes `root["Name"] = ...`
    m = re.search(r"\.([A-Za-z_$][\w$]*)\s*=\s*\{\s*\}", head) or re.search(
        r"""\[["']([A-Za-z_$][\w$]*)["']\]\s*=""", head
    )
    if m is None:
        warnings.warn(
            f"{js_file} doesn't look like an AMD bundle, but the global it "
            "exports couldn't be determined; it will be served without a "
            "require.js shim, which may prevent the widget from rendering.",
            stacklevel=2,
        )
        return None
    return m.group(1)


def dir_version(module_dir: str) -> str:
    """
    A pseudo-version for an nbextension we have no widget instance to take a
    module version from (e.g., an AMD external of a widget's bundle): use the
    newest file mtime so a reinstall/upgrade still busts the lib cache.
    """
    try:
        mtime = max(
            os.path.getmtime(os.path.join(module_dir, f))
            for f in os.listdir(module_dir)
        )
        return f"0.0.{int(mtime)}"
    except (OSError, ValueError):
        return "0.0"


# anywidget's front-end rejects a model's `ready` promise if initialization
# (i.e., loading the widget's `_esm`) takes longer than a hard-coded 2s
# (`AbortSignal.timeout(2e3)` -> "[anywidget] Failed to initialize model.").
# `_handle_comm_msg` awaits that promise, so once it rejects, every subsequent
# Python -> browser state update is dropped (and surfaces as a console error).
# That's unsuitable outside Jupyter for widgets with multi-MB inline ESM
# bundles (keplergl's `_esm` is ~13MB), which can't compile within 2s on
# slower hardware. Serve a patched copy with a more generous budget instead.
# Interim workaround for https://github.com/manzt/anywidget/issues/1030 --
# remove this (and serve anywidget's files unmodified) once upstream makes
# the init budget configurable or stops gating comm messages on it.
ANYWIDGET_INIT_TIMEOUT_MS = 60000


def relax_anywidget_init_timeout(module_dir: str) -> str:
    """
    Return a directory holding a copy of anywidget's front-end (nbextension)
    with the hard-coded 2s model-initialization budget raised. Falls back to
    `module_dir` itself if the timeout can't be located (e.g., a future
    anywidget release restructures this code).
    """
    index = os.path.join(module_dir, "index.js")
    try:
        mtime = os.path.getmtime(index)
    except OSError:
        return module_dir

    key = (module_dir, mtime)
    if key in _anywidget_patched_dirs:
        return _anywidget_patched_dirs[key]

    patched_dir = module_dir
    with open(index, encoding="utf-8") as f:
        js = f.read()

    i = js.find("Failed to initialize model")
    if i >= 0:
        # The timeout that guards model initialization sits just before the
        # rejection; match its numeric argument (2e3 or 2000)
        m = re.search(
            r"AbortSignal\.timeout\(\s*(?:2e3|2000)\s*\)", js[max(0, i - 500) : i]
        )
        if m is not None:
            patched_dir = tempfile.mkdtemp(prefix="shinywidgets-anywidget-")
            for f_ in os.listdir(module_dir):
                src = os.path.join(module_dir, f_)
                if not os.path.isfile(src):
                    continue
                with open(src, "rb") as fin:
                    contents = fin.read()
                if f_ == "index.js":
                    contents = (
                        js[: max(0, i - 500) + m.start()]
                        + f"AbortSignal.timeout({ANYWIDGET_INIT_TIMEOUT_MS})"
                        + js[max(0, i - 500) + m.end() :]
                    ).encode("utf-8")
                with open(os.path.join(patched_dir, f_), "wb") as fout:
                    fout.write(contents)

    _anywidget_patched_dirs[key] = patched_dir
    return patched_dir


_anywidget_patched_dirs: dict[tuple[str, float], str] = {}


def jupyter_extension_path(module_name: str) -> Optional[str]:
    paths: List[str] = jupyter_path()
    for x in paths:
        dir = os.path.join(x, "nbextensions", module_name)
        if not os.path.exists(dir):
            continue
        for f in os.listdir(dir):
            if f.startswith("index") and f.endswith(".js"):
                return dir

    return None


# Approximates what `jupyter nbextension install` does to discover and copy source files
# for the extension.
# https://github.com/jupyter-server/jupyter_server/blob/e70e7be/notebook/nbextensions.py#L211-L212
# https://github.com/jupyter-widgets/widget-cookiecutter/blob/master/%7B%7Bcookiecutter.github_project_name%7D%7D/%7B%7Bcookiecutter.python_package_name%7D%7D/__init__.py
#
# N.B. for now, we're only supporting the notebook extension (not the lab extension)
# model since it's simpler to understand and maps onto the HTMLDependency() model a bit
# better (i.e., it doesn't require node and/or widget registry implementation details).
# Also, this method isn't foolproof in the sense that it's possible for the widget
# instance's __module__ to not point to the right package. An example is
# plotly's FigureWidget() pointing to the plotly package, but the actual
# dependencies actually live in a separate jupyterlab_plotly package.
def jupyter_extension_destination(w: Widget) -> str:
    with tempfile.TemporaryDirectory():
        mod: ModuleType = importlib.import_module(".", package=widget_pkg(w))

    if mod.__file__ is None:
        raise RuntimeError(f"Module {mod.__name__} has no __file__ attribute")

    if hasattr(mod, "_jupyter_nbextension_paths"):
        return mod._jupyter_nbextension_paths()[0]["dest"]
    else:
        return widget_pkg(w)


def widget_pkg(w: object) -> str:
    # Instances of builtins (e.g., "x", {}) have no __module__ attribute
    module: str = getattr(w, "__module__", None) or type(w).__module__
    return module.split(".")[0]


def parse_version(v: str) -> str:
    # version could be in node-semver format
    # which is not compatible with packaging.version.parse
    # so we strip out the leading non-numeric characters
    # e.g., ^1.2.3 -> 1.2.3
    ver = re.sub("^\\D+", "", v)
    return str(packaging.version.parse(ver))


# parsing can fail if the version is something like "*",
# but it doesn't seem vital that we obtain the _actual_ version
# since this only gets the version of the HTMLManager and module
# dependencies, which should be unique within a given session
def parse_version_safely(v: str) -> str:
    try:
        return parse_version(v)
    except Exception:
        return "0.0"
