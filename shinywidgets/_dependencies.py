import importlib
import json
import os
import posixpath
import re
import tempfile
import warnings
from copy import deepcopy
from hashlib import sha256
from types import ModuleType
from typing import Any, Dict, List, Optional, Set, Tuple

import packaging.version
from htmltools import HTMLDependency, tags
from htmltools._core import (
    HTMLDependencySource,  # pyright: ignore[reportPrivateImportUsage]
    ScriptItem,
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
            return None

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


def bokeh_dependency() -> HTMLDependency:
    from bokeh import __version__ as bokeh_version
    from bokeh.resources import Resources

    resources = Resources(mode="absolute")
    suffix = ".min" if resources.minified else ""
    scripts: List[ScriptItem] = [
        {"src": f"js/{component}{suffix}.js"}
        for component in resources.components_for("js")
    ]
    return HTMLDependency(
        name="bokeh",
        version=bokeh_version,
        source={"subdir": str(resources.base_dir)},
        script=scripts,
        head=tags.script("\n".join(resources.js_raw)),
        all_files=True,
    )


def bokeh_extension_dependencies(w: Widget) -> List[HTMLDependency]:
    """
    Obtain HTMLDependencies for bokeh extension models
    referenced by a jupyter_bokeh.BokehModel.

    Returns [] for non-BokehModel widgets and for BokehModels that only
    reference core bokeh models.
    """
    if getattr(w, "_model_module", None) != "@bokeh/jupyter_bokeh":
        return []

    model = getattr(w, "_model", None)
    if model is None:
        return []

    ext_pkgs = {type(m).__view_module__.split(".")[0] for m in model.references()} - {
        "bokeh"
    }
    if not ext_pkgs:
        return []

    js_urls, css_urls = bokeh_extension_urls(model, ext_pkgs)
    return extension_urls_to_dependencies(js_urls, css_urls)


def jupyter_extension_path(module_name: str) -> Optional[str]:
    paths: List[str] = jupyter_path()
    module_dir = None
    for x in paths:
        dir = os.path.join(x, "nbextensions", module_name)
        if not os.path.exists(dir):
            continue
        for f in os.listdir(dir):
            if f.startswith("index") and f.endswith(".js"):
                module_dir = dir
                break

    return module_dir


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
    return w.__module__.split(".")[0]


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


def bokeh_extension_urls(model: Any, ext_pkgs: Set[str]) -> Tuple[List[str], List[str]]:
    """
    Compute scripts and styles for the bokeh document, excluding
    base bokeh assets (already provided by bokeh_dependency()).
    """
    from bokeh.resources import Resources

    resources = Resources(mode="server", root_url="")

    from bokeh.embed.bundle import bundle_for_objs_and_resources

    try:
        # N.B. this only scans models referenced by the document, so it's
        # robust against unrelated broken extension classes
        bundle = bundle_for_objs_and_resources([model], resources)
    except Exception:
        # bundle_for_objs_and_resources() imports each extension package
        # (bokeh.embed.bundle._bundle_extensions does __import__(name)); an
        # unresolvable package shouldn't take down the whole render.
        for pkg in sorted(ext_pkgs):
            if not importable(pkg):
                warn_missing_extension(pkg)
        return [], []

    js_urls = filter_bokeh_core([str(u) for u in bundle.js_files])
    css_urls = filter_bokeh_core([str(u) for u in bundle.css_files])

    # Warn about extension packages that produced no assets
    covered = {
        pkg
        for pkg in ext_pkgs
        if any(f"extensions/{pkg}/" in u for u in js_urls + css_urls)
    }
    for pkg in sorted(ext_pkgs - covered):
        warn_missing_extension(pkg)

    return js_urls, css_urls


def importable(pkg: str) -> bool:
    try:
        importlib.import_module(pkg)
        return True
    except Exception:
        return False


def warn_missing_extension(pkg: str) -> None:
    warnings.warn(
        f"The bokeh document contains models from the extension package "
        f"'{pkg}', but shinywidgets couldn't locate its JS/CSS assets (does "
        f"it ship a bokeh.ext.json/dist bundle?). The widget may fail to "
        f"render in the browser.",
        stacklevel=3,
    )


def filter_bokeh_core(urls: List[str]) -> List[str]:
    """Drop base bokeh assets (provided by bokeh_dependency()) from a url list."""
    res = []
    for u in urls:
        if "cdn.bokeh.org" in u:
            continue
        # e.g., static/js/bokeh.min.js, bokeh-gl.min.js, bokeh-widgets.min.js, ...
        if "static/js/bokeh" in u:
            continue
        res.append(u)
    return res


class MessageDependency(HTMLDependency):
    """
    An HTMLDependency whose script/stylesheet URLs are NOT pre-encoded in
    as_dict().

    Dependencies delivered via session._process_ui() (i.e., over the websocket)
    get encodeURI()'d by Shiny's client before loading; the pre-encoding that
    HTMLDependency.as_dict() performs (urllib.parse.quote) then results in
    double-encoded URLs (e.g., '@' -> '%40' -> '%2540') that 404. Skipping the
    pre-encoding lets the client's encodeURI() be the only encoder (and raw
    URLs also work fine in server-rendered pages).
    """

    def as_dict(
        self, *, lib_prefix: Optional[str] = "lib", include_version: bool = True
    ) -> Dict[str, Any]:
        source_href = self.source_path_map(
            lib_prefix=lib_prefix, include_version=include_version
        )["href"]

        stylesheets = deepcopy(self.stylesheet)
        for s in stylesheets:
            s.update(
                {
                    "href": posixpath.join(source_href, s["href"]),
                    "rel": "stylesheet",
                }
            )

        scripts = deepcopy(self.script)
        for s in scripts:
            s.update({"src": posixpath.join(source_href, s["src"])})

        head: Optional[str] = None
        if self.head is not None:
            head = self.head.get_html_string()

        result: Dict[str, Any] = {
            "name": self.name,
            "version": str(self.version),
            "script": scripts,
            "stylesheet": stylesheets,
            "meta": self.meta,
            "head": head,
        }
        return result


def extension_urls_to_dependencies(
    js_urls: List[str],
    css_urls: List[str],
) -> List[HTMLDependency]:
    """
    Convert bokeh-server-style URLs (static/extensions/<pkg>/<path>) into
    locally-served HTMLDependencies; pass through remote (http/https) URLs.
    """
    deps: List[HTMLDependency] = []
    for urls, is_script in ((js_urls, True), (css_urls, False)):
        for url in urls:
            dep = extension_url_to_dependency(url, is_script=is_script)
            if dep is not None:
                deps.append(dep)
    return deps


def extension_url_to_dependency(
    url: str, *, is_script: bool
) -> Optional[HTMLDependency]:
    source: Optional[HTMLDependencySource] = None
    pkg = "remote"
    version = "0.0"
    asset = url
    if not url.startswith(("http://", "https://")):
        from bokeh.embed.bundle import extension_dirs

        path = url.split("?", 1)[0]
        match = re.match(r"^/?static/extensions/([^/]+)/(.+)$", path)
        if match is None:
            warnings.warn(
                f"Don't know how to serve bokeh extension asset '{url}'. "
                "The widget may fail to render in the browser.",
                stacklevel=3,
            )
            return None
        pkg, asset = match.group(1), match.group(2)
        try:
            module = importlib.import_module(pkg)
            if module.__file__ is None:
                warn_missing_extension(pkg)
                return None
            # Bokeh records the directory behind its static/extensions URLs,
            # including bundles located by package.json outside the default dist.
            artifact_dir = extension_dirs.get(pkg)
            dist = (
                str(artifact_dir)
                if artifact_dir is not None
                else os.path.join(os.path.dirname(module.__file__), "dist")
            )
        except ImportError:
            warn_missing_extension(pkg)
            return None
        if not os.path.isfile(os.path.join(dist, asset)):
            warn_missing_extension(pkg)
            return None
        source = HTMLDependencySource(subdir=dist)
        version = pkg_version(pkg)

    kind = "js" if is_script else "css"
    script: ScriptItem = {"src": asset}
    # Shiny deduplicates by name, so each asset needs an identity independent
    # of the other assets requested by earlier widget renders.
    identity = sha256(asset.encode()).hexdigest()[:16]
    dependency = MessageDependency(
        f"bokeh-ext-{pkg}-{kind}-{identity}",
        version,
        source=source,
        script=[script] if is_script else None,
        stylesheet=None if is_script else [{"href": asset}],
        all_files=source is not None,
    )
    return dependency


def pkg_version(pkg: str) -> str:
    try:
        version = getattr(importlib.import_module(pkg), "__version__", "0.0")
        return str(version)
    except Exception:
        return "0.0"
