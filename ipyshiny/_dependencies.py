import importlib
import json
import os
import re
from types import ModuleType
import warnings
from typing import List, TypedDict

from ipywidgets._version import __html_manager_version__

from htmltools import HTMLDependency, tags
from htmltools._core import PackageHTMLDependencySource
from shiny import Session

from . import __version__

# TODO: scripts/static_download.R should produce/update these
def core() -> List[HTMLDependency]:
    return [
        # Load 3rd party widget dependencies at runtime via requirejs. One of the benefits of doing it 
        # this way is that for whatever reason, if we can't find the widgets statically assets locally,
        # the requireLoader we use client side will fallback to loading the dependencies from a CDN.
        HTMLDependency(
            name="requirejs",
            version="2.3.4",
            source={"package": "ipyshiny", "subdir": "static"},
            script={"src": "require.min.js"},
        ),
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
        HTMLDependency(
            name="ipywidget-libembed-amd",
            version=re.sub("^\\D*", "", __html_manager_version__),
            source={"package": "ipyshiny", "subdir": "static"},
            script={"src": "libembed-amd.js"},
        )
    ]


def output_binding() -> HTMLDependency:
  return HTMLDependency(
      name="ipywidget-output-binding",
      version=__version__,
      source={"package": "ipyshiny", "subdir": "static"},
      script={"src": "output.js"},
  )


def require_deps(pkg: str, session: Session) -> List[HTMLDependency]:
    # ipywidgets dependencies come with libembed-amd.js (i.e., _core() dependencies)
    if pkg == "ipywidgets": 
        return []

    mod = importlib.import_module(pkg)
    paths = get_paths(mod)

    deps = []
    for p in paths:
        dep = require_dependency(
            module_name=p["dest"],
            module_version=getattr(mod, "__version__", "0.1"),
            pkg_source={"package": None, "subdir": p["src"]},
            session=session
        )
        deps.append(dep)

    return deps

class Path(TypedDict):
  src: str
  dest: str

# Approximates what `jupyter nbextension install` does to discover and copy source files for the extension.
# https://github.com/jupyter-server/jupyter_server/blob/e70e7be/notebook/nbextensions.py#L211-L212
# https://github.com/jupyter-widgets/widget-cookiecutter/blob/master/%7B%7Bcookiecutter.github_project_name%7D%7D/%7B%7Bcookiecutter.python_package_name%7D%7D/__init__.py
#
# N.B. for now, we're only supporting the notebook extension (not the lab extension) model since it's
# simpler to understand and maps onto the HTMLDependency() model a bit better (i.e., it doesn't require
# node and/or widget registry implementation details).
def get_paths(mod: ModuleType) -> List[Path]:
    paths = []

    if hasattr(mod, '_jupyter_nbextension_paths'):
        paths = _index_paths(mod._jupyter_nbextension_paths(), mod)
    
    if not paths:
        paths = _index_paths([{"src": "nbextension", "dest": mod.__name__}], mod)

    if len(paths) == 0:
        warnings.warn(f"Failed to discover JavaScript dependencies for {mod.__name__}")
        return []

    return paths

# Return only the path configs point to an existant directory with an index.js file
# (If the paths config doesn't satisfy this requirement, there's no way it'll work 
# in the browser with the default requireLoader).
def _index_paths(paths: List[Path], mod: ModuleType) -> List[Path]:
    res = []
    base_path = os.path.split(mod.__file__)[0]

    for p in paths:
      p["src"] = os.path.join(base_path, p["src"])
      if not os.path.exists(p["src"]):
          continue
      index = [f for f in os.listdir(p["src"]) if f.startswith("index") and f.endswith(".js")]
      if len(index) > 0:
          res.append(p)

    return res


def require_dependency(module_name: str, module_version: str, pkg_source: PackageHTMLDependencySource, session: Session) -> HTMLDependency:
    dep = HTMLDependency(name=module_name, version=module_version, source=pkg_source)
    # Get the location where the dependency files will be mounted by the shiny app
    # and use that to inform the requirejs import path
    href = dep.source_path_map(lib_prefix=session.app.LIB_PREFIX)["href"]
    config = {"paths": {module_name: os.path.join(href, "index")}}
    # Basically our equivalent of the extension.js file provided by the cookiecutter
    # https://github.com/jupyter-widgets/widget-cookiecutter/blob/master/%7B%7Bcookiecutter.github_project_name%7D%7D/js/lib/extension.js
    return HTMLDependency(
      module_name, module_version, source=pkg_source, all_files=True,
      head=tags.script(f"window.require.config({json.dumps(config)})")
    )

# -----------------------------------------------------------------------------
# Note to future self:
# If we decide we want to use the labextension instead of nbextension approach,
# some of the code below may be helpful for getting information about the extensions
# -----------------------------------------------------------------------------
# from jupyter_core.paths import jupyter_path
# jupyter_path("labextensions") # directory to install labextensions
# from jupyterlab.commands import _AppHandler
# app = _AppHandler(options={})
# ext = app.info["extensions"] # various metadata about the extensions
