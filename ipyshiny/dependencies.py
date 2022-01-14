import importlib
import json
import os
import re
import sys
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
def _require_deps(pkg: str) -> Optional[List[HTMLDependency]]:
    paths = _get_nb_paths(pkg)
    if not _has_src_paths(paths, pkg):
        return None
    
    version = getattr(sys.modules[pkg], "__version__", "0.1")

    deps: List[HTMLDependency] = []
    for p in paths:
        name = f"ipyshiny-{pkg}-{p['src']}-config" 
        src = {"package": pkg, "subdir": p["src"]}
        # Get the location where the dependency files will be mounted by shiny
        # and use that to inform the requirejs import path
        dep = HTMLDependency(name, version, source=src)
        href = dep.source_path_map()["href"]
        # Based on https://github.com/jupyter-widgets/widget-cookiecutter/blob/969471848/%7B%7Bcookiecutter.github_project_name%7D%7D/js/lib/extension.js#L13-L19
        config = {
            "map": {
                "*": {
                    p["dest"]: os.path.join(href, "index")
                }
            }
        }
        dep = HTMLDependency(
          name, version, 
          source=src,
          all_files=True,
          head=HTML(f"<script>window.require.config({json.dumps(config)})</script>")
        )
        deps.append(dep)

    return deps


class _requirePaths(TypedDict):
    src: str
    dest: str

def _get_nb_paths(pkg: str) -> _requirePaths:
    defaults = {'src': 'nbextension', 'dest': pkg}
    try:
        return sys.modules[pkg]._jupyter_nbextension_paths()
    except:
        return [defaults]

# TODO: I'm not sure yet if we can reliably support jupyterlab extensions
# since more of the configuration/registration happens in JS 
#def _get_lab_paths(pkg: str) -> _requirePaths:
#  defaults = {'src': 'labextension', 'dest': pkg}
#  try:
#      return sys.modules[pkg]._jupyter_labextension_paths()
#  except:
#      return [defaults]

def _has_src_paths(paths: _requirePaths, package: str) -> bool:
    for x in paths:
        src = os.path.join(package_dir(package), x["src"])
        if not os.path.exists(src):
            return False
    return True
