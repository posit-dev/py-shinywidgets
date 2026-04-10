from __future__ import annotations

from pathlib import Path

import shinywidgets._dependencies as deps


class FakeBokehWidget:
    __module__ = "jupyter_bokeh.widgets"
    _model_module = "@bokeh/jupyter_bokeh"
    _model_module_version = "^4.0.5"


class FakeScopedWidget:
    __module__ = "fakepkg.widgets"
    _model_module = "@scope/example_widget"
    _model_module_version = "^1.2.3"


def test_bokeh_fallback_target_is_absolute_cdn_dist_index() -> None:
    resolution = deps.resolve_widget_dependency(FakeBokehWidget())

    assert resolution is not None
    assert resolution.module_name == "@bokeh/jupyter_bokeh"
    assert resolution.notebook_dest == "jupyter_bokeh"
    assert resolution.source_dir is None
    assert resolution.requirejs_target.startswith("https://")
    assert resolution.requirejs_target.endswith("/dist/index")


def test_local_mount_path_uses_notebook_destination(monkeypatch, tmp_path: Path) -> None:
    module_dir = tmp_path / "nbext"
    module_dir.mkdir()
    (module_dir / "index.js").write_text("// index", encoding="utf-8")

    monkeypatch.setattr(
        deps,
        "jupyter_extension_path",
        lambda module_name: str(module_dir) if module_name == "example_dest" else None,
    )
    monkeypatch.setattr(deps, "jupyter_extension_destination", lambda _: "example_dest")

    resolution = deps.resolve_widget_dependency(FakeScopedWidget())

    assert resolution is not None
    assert resolution.module_name == "@scope/example_widget"
    assert resolution.notebook_dest == "example_dest"
    assert resolution.source_dir == str(module_dir)
    assert resolution.requirejs_target == "nbextensions/example_dest/index"
