# Python's standard library, as an import graph -- showcase
# Click a module (or type into the sidebar) and the graph recolors: red/halo
# for the focused module, orange for what it imports, blue for what imports
# it. Node size is in-degree (how many other modules depend on it). The graph
# is built by statically parsing each module's own source with `ast`, so it
# needs no downloads and no network access -- just the interpreter running
# this app. The camera is carried across every re-render, so clicking around
# doesn't reset your pan/zoom.
#
# Run: uv run shiny run app.py
# Data: ast-parsed import statements from a curated set of ~80 pure-Python
# modules in this interpreter's own standard library (one directory level of
# each package, not fully recursive -- see build_import_graph() below).
from __future__ import annotations

import ast
import glob
import importlib.util
import os

import networkx as nx
from ipysigma import Sigma
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_ipysigma

CURATED_MODULES = sorted(
    {
        "abc", "argparse", "array", "ast", "asyncio", "base64", "bisect",
        "calendar", "collections", "concurrent", "configparser", "contextlib",
        "copy", "csv", "dataclasses", "datetime", "decimal", "dis", "email",
        "enum", "fnmatch", "functools", "gc", "glob", "gzip", "hashlib",
        "heapq", "hmac", "html", "http", "importlib", "inspect", "ipaddress",
        "itertools", "json", "logging", "math", "multiprocessing", "operator",
        "os", "pathlib", "pickle", "platform", "queue", "random", "re",
        "secrets", "selectors", "shlex", "shutil", "signal", "socket", "sqlite3",
        "ssl", "stat", "statistics", "string", "struct", "subprocess", "sys",
        "tarfile", "tempfile", "textwrap", "threading", "time", "traceback",
        "typing", "unicodedata", "unittest", "urllib", "uuid", "warnings",
        "weakref", "wsgiref", "xml", "zipfile",
    }
)


def module_files(name: str) -> list[str]:
    spec = importlib.util.find_spec(name)
    if spec is None:
        return []
    if spec.submodule_search_locations:  # a package: scan one directory level
        return [
            f
            for loc in spec.submodule_search_locations
            for f in glob.glob(os.path.join(loc, "*.py"))
        ]
    if spec.origin and spec.origin.endswith(".py"):
        return [spec.origin]
    return []


def direct_imports(name: str) -> set[str]:
    tops: set[str] = set()
    for path in module_files(name):
        try:
            tree = ast.parse(open(path, encoding="utf-8", errors="ignore").read())
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                tops.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                tops.add(node.module.split(".")[0])
    return {t for t in tops if t in CURATED_MODULES and t != name}


def build_import_graph() -> nx.DiGraph:
    G = nx.DiGraph()
    G.add_nodes_from(CURATED_MODULES)
    for name in CURATED_MODULES:
        G.add_edges_from((name, dep) for dep in direct_imports(name))
    return G


G = build_import_graph()
nx.set_node_attributes(G, dict(G.in_degree()), "importers")
POS = nx.forceatlas2_layout(G, max_iter=200, seed=0)
LAYOUT = {n: {"x": float(x), "y": float(y)} for n, (x, y) in POS.items()}

FOCUS_COLOR, IMPORTS_COLOR, IMPORTED_BY_COLOR, DEFAULT_COLOR = (
    "#e41a1c", "#ff7f00", "#377eb8", "#bbbbbb",
)

ui.page_opts(title="Python stdlib import graph", fillable=True)

with ui.layout_sidebar():
    with ui.sidebar(width=320):
        ui.input_selectize("focus", "Module", list(CURATED_MODULES), selected="asyncio")

        @render.ui
        def summary():
            name = input.focus()
            imports = sorted(G.successors(name))
            imported_by = sorted(G.predecessors(name))
            return ui.TagList(
                ui.h5(f"import {name}"),
                ui.p(f"Imports {len(imports)} of these modules directly."),
                ui.p(f"Imported by {len(imported_by)} of these modules."),
                ui.p("Depends on: ", ui.tags.small(", ".join(imports) or "none")),
            )

    with ui.card(full_screen=True):
        ui.card_header("Click a node to focus it (stays in sync with the sidebar)")

        camera = reactive.value({"x": 0.5, "y": 0.5, "ratio": 1.2, "angle": 0})

        @reactive.effect
        def _track_camera():
            # graph.read() cancels (like req(False)) before the first render,
            # so no explicit req(graph.widget) is needed here
            camera.set(graph.read("camera_state"))

        @reactive.effect
        def _select_to_focus():
            # Clicking a node (or ipysigma's own search box) updates the
            # sidebar's selectize, which triggers a re-render below
            raw = graph.read("selected_node")
            if raw is not None and raw != input.focus():
                ui.update_selectize("focus", selected=raw)

        @render_ipysigma
        def graph():
            focus = input.focus()
            imports = set(G.successors(focus))
            imported_by = set(G.predecessors(focus))

            def color_for(node: str) -> str:
                if node == focus:
                    return FOCUS_COLOR
                if node in imports:
                    return IMPORTS_COLOR
                if node in imported_by:
                    return IMPORTED_BY_COLOR
                return DEFAULT_COLOR

            with reactive.isolate():
                cam = camera.get()
            return Sigma(
                G,
                layout=LAYOUT,
                camera_state=cam,
                selected_node=focus,
                # raw_node_color (not node_color) takes literal CSS colors
                # instead of mapping them through a categorical palette
                raw_node_color={n: color_for(n) for n in G.nodes},
                node_size="importers",
                hide_edges_on_move=True,
            )
