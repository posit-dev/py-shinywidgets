import base64
import hashlib
import importlib
import json
import os
import re
import tempfile
import warnings
from importlib.metadata import FileHash, PackageNotFoundError, distribution
from types import ModuleType
from typing import List, Optional

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


# TODO: this function might have to be recursive since it's technically
# possible for a Widget to have traits that are themselves Widgets
# (which could have their own npm module), but in practice, I haven't seen any cases
# where a 3rd party widget can contain a 3rd party widget.
def require_dependency(
    w: Widget, session: Session, warn_if_missing: bool = True
) -> Optional[HTMLDependency]:
    """
    Obtain an HTMLDependency for a 3rd party ipywidget that points
    require('widget-npm-package') requests in the browser to the correct local path.
    """

    # The relevant npm package should be specified as an attribute on the widget
    # instance. If the widget is installed as a jupyter extension, in most cases, that
    # name will registered at the extension name/directory
    module_attr = "_view_module" if isinstance(w, DOMWidget) else "_model_module"
    module_name: str = getattr(w, module_attr, widget_pkg(w))

    # ipywidgets (i.e., @jupyter-widgets) come pre-bundled in libembed-amd.js
    # # (i.e., _core() dependencies)
    if module_name.startswith("@jupyter-widgets/"):
        return None

    # Prefer the extension that ships with the installed widget package over
    # copies found in Jupyter data dirs, which can be stale leftovers from older
    # installs (a stale ipywidgets-7-era jupyterlab-plotly bundle in
    # /usr/local/share/jupyter caused #332). In order:
    # 1. the data files the widget's own distribution installed (complete, and
    #    from the same install as the package that's imported)
    # 2. the nbextension bundled inside the package itself
    # 3. any Jupyter data dir (environment, then user, then system-wide)
    module_dir = distribution_nbextension_path(w, module_name)
    if module_dir is None:
        module_dir = package_nbextension_path(w, module_name)
    if module_dir is None:
        module_dir = jupyter_extension_path(module_name)
    if module_dir is None:
        # It's technically possible for the npm package name to be different from the actual
        # extension path (defined by `_jupyter_nbextension_paths` in __init__.py), but we
        # also don't have a fool-proof way to discovering the relevant __init__.py file,
        # which is why we only use look for it if the npm package isn't installed
        module_dir = jupyter_extension_path(jupyter_extension_destination(w))
        if module_dir is None:
            if warn_if_missing:
                warnings.warn(
                    f"Couldn't find local path to widget extension for {type(w)}."
                    + " Since a CDN fallback is provided, the widget will still render if an internet connection is available."
                    + " To avoid depending on a CDN, make sure the widget is installed as a jupyter extension.",
                    stacklevel=2,
                )
            return None

    if module_name == "anywidget":
        module_dir = relax_anywidget_init_timeout(module_dir)

    version = parse_version_safely(getattr(w, "_model_module_version", "1.0"))
    source = HTMLDependencySource(subdir=module_dir)

    dep = HTMLDependency(module_name, version, source=source)
    # Get the location where the dependency files will be mounted by the shiny app
    # and use that to inform the requirejs import path
    href = dep.source_path_map(lib_prefix=session.app.lib_prefix)["href"]
    config = {"paths": {module_name: os.path.join(href, "index")}}
    # Basically our equivalent of the extension.js file provided by the cookiecutter
    # https://github.com/jupyter-widgets/widget-cookiecutter/blob/master/%7B%7Bcookiecutter.github_project_name%7D%7D/js/lib/extension.js
    return HTMLDependency(
        module_name,
        version,
        source=source,
        all_files=True,
        head=tags.script(f"window.require.config({json.dumps(config)})"),
    )


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


def jupyter_extension_path(
    module_name: str, paths: Optional[List[str]] = None
) -> Optional[str]:
    for x in jupyter_path() if paths is None else paths:
        dir = os.path.join(x, "nbextensions", module_name)
        if dir_has_index_js(dir):
            return dir

    return None


def frontend_packages(w: Widget, module_name: str) -> List[str]:
    """
    Python packages that could provide the widget's frontend extension.

    That's the packages of the widget's own class and its base classes (an
    app-defined subclass typically lives in another package than the widget it
    extends), plus a package named after the extension itself (plotly widgets
    request the "jupyterlab-plotly" module, whose extension ships in the
    jupyterlab_plotly package).
    """
    return [
        *(widget_pkg(cls) for cls in type(w).__mro__),
        module_name.replace("-", "_"),
    ]


# Distributions don't change on disk while the process runs, so remember where
# each one put its nbextensions (scanning a distribution's file list isn't free)
_distribution_nbextension_dirs: dict[str, dict[str, str]] = {}


def distribution_nbextension_paths(pkg: str) -> dict[str, str]:
    """
    Map of extension name -> nbextension dir, for the data files (e.g.
    `share/jupyter/nbextensions/...`) that the installed `pkg` distribution put
    on disk.

    This is where the wheel that's actually installed put its extension, which
    is version-matched by construction and, unlike the copy bundled inside the
    package, complete: some packages only bundle part of the bundle's assets
    (e.g., ipydatagrid's bundled copy has no SVG/PNG files, which its
    index.js loads at runtime).
    """
    if pkg in _distribution_nbextension_dirs:
        return _distribution_nbextension_dirs[pkg]

    found: dict[str, str] = {}
    try:
        dist = distribution(pkg)
    except PackageNotFoundError:
        _distribution_nbextension_dirs[pkg] = found
        return found

    for file in dist.files or []:
        parts = file.parts
        name = parts[-1]
        if "nbextensions" not in parts:
            continue
        if not (name.startswith("index") and name.endswith(".js")):
            # Only the entry point (what require.js loads) is checked
            continue
        # Keep everything up to and including "<data dir>/nbextensions/<module>"
        end = len(parts) - 1 - parts[::-1].index("nbextensions") + 2
        if len(parts) < end + 1:
            continue
        module = parts[end - 1]
        if module in found:
            continue
        dir = os.path.normpath(str(dist.locate_file(os.path.join(*parts[:end]))))
        if recorded_file_matches(os.path.join(dir, name), file.hash):
            found[module] = dir

    _distribution_nbextension_dirs[pkg] = found
    return found


def recorded_file_matches(file: str, expected: Optional[FileHash]) -> bool:
    """
    Whether `file` is the file the distribution recorded (per its hash), or
    whether that can't be determined.

    Some data dirs are shared between Python installations (e.g.,
    `~/.local/share/jupyter` for `pip install --user`), so an install under a
    different interpreter can overwrite the files another one recorded. In that
    case the copy on disk doesn't match the package that's imported, and the
    nbextension bundled with that package is the better choice.
    """
    if expected is None or expected.mode != "sha256":
        return True
    try:
        with open(file, "rb") as f:
            digest = base64.urlsafe_b64encode(hashlib.sha256(f.read()).digest())
    except OSError:
        return False
    return digest.rstrip(b"=").decode("ascii") == expected.value


def distribution_nbextension_path(w: Widget, module_name: str) -> Optional[str]:
    """
    Path to the nbextension for `module_name` that the widget's own distribution
    installed into a Jupyter data dir, if any.
    """
    for pkg in dict.fromkeys(frontend_packages(w, module_name)):
        dir = distribution_nbextension_paths(pkg).get(module_name)
        if dir is not None and dir_has_index_js(dir):
            return dir

    return None


def package_nbextension_path(w: Widget, module_name: str) -> Optional[str]:
    """
    Path to the nbextension bundled inside the widget's own installed Python
    package (as declared by its `_jupyter_nbextension_paths()`), if that
    package provides an extension for `module_name`.

    Unlike `distribution_nbextension_path()`, this doesn't depend on the package
    installing data files (e.g., editable installs), but the bundled copy can be
    incomplete.
    """
    for pkg in dict.fromkeys(frontend_packages(w, module_name)):
        try:
            mod: ModuleType = importlib.import_module(pkg)
        except Exception:
            continue
        module_file = getattr(mod, "__file__", None)
        if module_file is None:
            # builtins, namespace packages, C extensions, ...
            continue
        nbextension_paths = getattr(mod, "_jupyter_nbextension_paths", None)
        if nbextension_paths is None:
            continue
        try:
            entries = nbextension_paths()
        except Exception:
            continue
        for entry in entries:
            if entry.get("dest") != module_name or "src" not in entry:
                continue
            dir = os.path.join(os.path.dirname(module_file), entry["src"])
            if dir_has_index_js(dir):
                return dir

    return None


def dir_has_index_js(dir: str) -> bool:
    if not os.path.isdir(dir):
        return False
    for f in os.listdir(dir):
        if f.startswith("index") and f.endswith(".js"):
            return True
    return False


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
