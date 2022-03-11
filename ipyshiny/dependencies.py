import importlib
import json
import os
import re
import sys
from warnings import warn
from types import ModuleType
from typing import List, Dict, Optional, TypedDict
from typing_extensions import NotRequired

from htmltools import HTMLDependency, HTML
from ipywidgets._version import __html_manager_version__
from shiny.utils import package_dir

from .__init__ import __version__

# TODO: scripts/static_download.R should produce/update these
def _core() -> List[HTMLDependency]:
    return [
        HTMLDependency(
            name="requirejs",
            version="2.3.4",
            source={"package": "ipyshiny", "subdir": "static"},
            script={"src": "require.min.js"},
        ),
        HTMLDependency(
            name="ipywidget-libembed-amd",
            version=re.sub("^\\D*", "", __html_manager_version__),
            source={"package": "ipyshiny", "subdir": "static"},
            script={"src": "libembed-amd.js"},
        ),
    ]


def _output_binding() -> HTMLDependency:
    return HTMLDependency(
        name="ipywidget-output-binding",
        version=__version__,
        source={"package": "ipyshiny", "subdir": "static"},
        script={"src": "output.js"},
    )


def _input_binding() -> HTMLDependency:
    return HTMLDependency(
        name="ipywidget-input-binding",
        version=__version__,
        source={"package": "ipyshiny", "subdir": "static"},
        script={"src": "input.js"},
    )

# Both the source location of static files and the target requirejs module are configurable
# https://github.com/jupyter-widgets/widget-cookiecutter/blob/master/%7B%7Bcookiecutter.github_project_name%7D%7D/%7B%7Bcookiecutter.python_package_name%7D%7D/__init__.py
class _Paths(TypedDict):
  src: str
  dest: str

def _require_deps(pkg: str) -> List[HTMLDependency]:
    # Approximates what jupyter does to find the source location of static files for a package
    # https://github.com/jupyterlab/jupyterlab/blob/ea1529b/jupyterlab/federated_labextensions.py#L374-L380
    mod = importlib.import_module(pkg)
    paths: _Paths = []
    if hasattr(mod, '_jupyter_nbextension_paths'):
        paths = mod._jupyter_nbextension_paths()
    elif hasattr(mod, '_jupyter_labextension_paths'):
        paths = mod._jupyter_labextension_paths()
    else:
        warn(f"Unable to locally serve JS/CSS assets for ipywidget package '{pkg}'".format(pkg))
        return []

    # TODO: we should verify that the jupyter paths are actually well defined.
    # For example, ipyleaflet has a _jupyter_labextension_paths() that returns
    # points to a labextension/ src, but that folder doesn't actually contain an 
    # index (I think it that case, Jupyter must fallback to the nbextension path)

    version = getattr(mod, "__version__", "0.1")
    deps = []
    for p in paths:
        src = p["src"]
        name = f"ipyshiny-{pkg}-{src}-config" 
        source = {"package": pkg, "subdir": src}
        # Get the location where the dependency files will be mounted by shiny
        # and use that to inform the requirejs import path
        dep = HTMLDependency(name, version, source=source)
        href = dep.source_path_map()["href"]
        config = {"paths": {p["dest"]: os.path.join(href, "index")}}
        dep = HTMLDependency(
          name, version, source=source, all_files=True,
          head=HTML(f"<script>window.require.config({json.dumps(config)})</script>")
        )
        deps.append(dep)

    return deps
