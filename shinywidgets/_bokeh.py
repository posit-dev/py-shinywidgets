import importlib
import os
import posixpath
import re
import warnings
from typing import Any, Dict, List, NamedTuple, Optional, Set, Tuple

from htmltools import HTMLDependency, head_content, tags
from htmltools._core import (
    HTMLDependencySource,  # pyright: ignore[reportPrivateImportUsage]
    ScriptItem,
)
from ipywidgets.widgets.widget import Widget
from shiny import Session


def bokeh_dependency() -> HTMLDependency:
    """
    Create an HTML dependency on bokeh's JavaScript/CSS resources.

    You don't normally need to add this to the UI yourself: the dependency is sent
    along with every bokeh-based widget (including those in outputs created
    dynamically, e.g., an :func:`~shinywidgets.output_widget` rendered inside a
    ``@render.ui``), and the `render_bokeh`, `render_panel`, and `render_holoviews`
    decorators also include it in their UI.

    Returns
    -------
    :
        An `htmltools.HTMLDependency` suitable for inclusion in the app's UI
        definition.
    """

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


class ExtensionAssets(NamedTuple):
    """Browser assets required by bokeh extension models."""

    # Dependencies that load classic scripts/styles (via head content)
    # and/or mount local asset directories.
    deps: List[HTMLDependency]
    # Side-effect-only ES modules (import()'d client-side before the model
    # is constructed).
    module_urls: List[str]
    # Global name -> ES module URL; the module's default export is assigned
    # to the global (also client-side, before model construction).
    module_exports: Dict[str, str]


def bokeh_extension_assets(w: Widget, session: Session) -> ExtensionAssets:
    """
    Obtain browser assets for bokeh extension models referenced by a
    jupyter_bokeh.BokehModel.

    Returns empty assets for non-BokehModel widgets and for BokehModels that
    only reference core bokeh models.
    """
    if getattr(w, "_model_module", None) != "@bokeh/jupyter_bokeh":
        return ExtensionAssets([], [], {})

    model = getattr(w, "_model", None)
    if model is None:
        return ExtensionAssets([], [], {})

    ext_pkgs = {type(m).__view_module__.split(".")[0] for m in model.references()} - {
        "bokeh"
    }
    if not ext_pkgs:
        return ExtensionAssets([], [], {})

    js_urls, css_urls, modules = bokeh_extension_urls(model, ext_pkgs)
    return extension_assets(js_urls, css_urls, modules, session)


def bokeh_extension_urls(
    model: Any, ext_pkgs: Set[str]
) -> Tuple[List[str], List[str], Dict[str, List[str]]]:
    """
    Compute scripts, styles, and module exports for the bokeh document, excluding
    base bokeh assets (already provided by bokeh_dependency()).
    """
    from bokeh.resources import Resources

    resources = Resources(mode="server", root_url="")

    if "panel" in ext_pkgs:
        try:
            from panel.io.resources import bundle_resources
        except ImportError:
            pass
        else:
            try:
                bundle = bundle_resources([model], resources)
            except Exception:
                # bundle_resources() scans *all* registered bokeh model classes
                # (not just the document's), so an unrelated unimportable
                # extension class can break it. Fall back to the scoped,
                # generic bokeh path below.
                pass
            else:
                js_urls = filter_bokeh_core([str(u) for u in bundle.js_files])
                css_urls = filter_bokeh_core([str(u) for u in bundle.css_files])
                modules = {str(url): [] for url in bundle.js_modules}
                for name, url in bundle.js_module_exports.items():
                    modules.setdefault(str(url), []).append(name)
                return js_urls, css_urls, modules

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
        return [], [], {}

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

    return js_urls, css_urls, {}


def extension_assets(
    js_urls: List[str],
    css_urls: List[str],
    modules: Dict[str, List[str]],
    session: Session,
) -> ExtensionAssets:
    """
    Convert bokeh-server-style extension URLs (static/extensions/<pkg>/<path>)
    into browser-loadable assets; pass through remote (http/https) URLs.
    """
    deps = extension_urls_to_dependencies(js_urls, css_urls, session)

    module_urls: List[str] = []
    module_exports: Dict[str, str] = {}
    for url, names in modules.items():
        resolved = serve_extension_url(url, session)
        if resolved is None:
            continue
        served_url, mount = resolved
        if mount is not None:
            deps.append(mount)
        if names:
            for name in names:
                module_exports[name] = served_url
        else:
            module_urls.append(served_url)

    return ExtensionAssets(deps, module_urls, module_exports)


def extension_urls_to_dependencies(
    js_urls: List[str],
    css_urls: List[str],
    session: Session,
) -> List[HTMLDependency]:
    """
    Convert bokeh-server-style extension URLs (static/extensions/<pkg>/<path>)
    into HTMLDependencies; pass through remote (http/https) URLs.

    Local assets are served from a per-package mount: the returned
    ``bokeh-ext-<pkg>`` dependency has no script/stylesheet entries of its own,
    but causes Shiny to serve the package's dist directory when it's processed
    (e.g., via ``session._process_ui()``).

    Assets are loaded via head_content() (i.e., raw <script>/<link> tags)
    rather than script/stylesheet entries on a dependency. The tag's HTML is
    delivered verbatim (even over the websocket) and appended to <head> by
    Shiny's client, so URLs aren't subject to the double-encoding that
    HTMLDependency.as_dict() (urllib.parse.quote) plus the client's encodeURI()
    would otherwise produce (e.g., '@' -> '%40' -> '%2540'). As a bonus,
    head_content() names its dependency by hashing the content, so Shiny's
    client-side deduplication (by dependency name) prevents the same asset
    from loading twice across renders.
    """
    deps: List[HTMLDependency] = []
    for urls, is_script in ((js_urls, True), (css_urls, False)):
        for url in urls:
            deps.extend(
                extension_url_to_dependencies(url, is_script=is_script, session=session)
            )
    return deps


def extension_url_to_dependencies(
    url: str, *, is_script: bool, session: Session
) -> List[HTMLDependency]:
    resolved = serve_extension_url(url, session)
    if resolved is None:
        return []
    served_url, mount = resolved
    deps = [mount] if mount is not None else []
    return [*deps, asset_loader(served_url, is_script=is_script)]


def serve_extension_url(
    url: str, session: Session
) -> Optional[Tuple[str, Optional[HTMLDependency]]]:
    """
    Resolve an extension asset URL to a servable URL, plus the mount
    dependency (for local assets) that makes Shiny serve it. Remote
    (http/https) URLs pass through with no mount. Returns None (with a
    warning) if a local asset can't be located.
    """
    if url.startswith(("http://", "https://")):
        return url, None
    return local_extension_url(url, session)


def local_extension_url(
    url: str, session: Session
) -> Optional[Tuple[str, HTMLDependency]]:
    """
    Map a bokeh-server-style extension URL (static/extensions/<pkg>/<path>)
    to a locally-served URL, plus the HTMLDependency that (once processed by
    Shiny) mounts the package's dist directory at that URL's prefix.

    Returns None (with a warning) if the asset can't be located.
    """
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

    mount = HTMLDependency(
        f"bokeh-ext-{pkg}",
        pkg_version(pkg),
        source=HTMLDependencySource(subdir=dist),
        all_files=True,
    )
    href = mount.source_path_map(lib_prefix=session.app.lib_prefix)["href"]
    return posixpath.join(href, asset), mount


def asset_loader(url: str, *, is_script: bool) -> HTMLDependency:
    """Load a JS/CSS asset via a raw <script>/<link> tag in the document <head>."""
    if is_script:
        return head_content(tags.script(src=url))
    return head_content(tags.link(rel="stylesheet", href=url))


def guard_widget_close(w: Widget) -> None:
    """
    Make a widget's close() safe to call more than once.

    jupyter_bokeh's BokehModel.close() removes its document change callback
    unconditionally, so a second close() raises KeyError (and its __del__
    calls close() as well). Wrap close() so only the first call runs, and so
    a close notification arriving while close() is running can't re-enter it.
    """
    close = w.close
    closing = False
    closed = False

    def close_once() -> None:
        nonlocal closing, closed
        if closing or closed:
            return
        closing = True
        try:
            close()
            closed = True
        finally:
            closing = False

    w.close = close_once  # type: ignore[method-assign]


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


def pkg_version(pkg: str) -> str:
    try:
        version = getattr(importlib.import_module(pkg), "__version__", "0.0")
        return str(version)
    except Exception:
        return "0.0"
