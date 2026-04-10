import pytest
import shinywidgets._output_widget as ow
from htmltools import HTMLDependency
from shinywidgets._cdn import SHINYWIDGETS_CDN_ONLY
from shinywidgets._output_widget import output_widget


def test_output_widget_structure_and_head_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ow, "resolve_id", lambda x: "resolved-id")

    tag = output_widget("x", width="100%", height="400px", fill=False, fillable=False)

    assert tag.attrs["id"] == "resolved-id"
    cls = tag.attrs["class"]
    assert "shiny-ipywidget-output" in cls
    assert "shiny-report-size" in cls
    assert "shiny-report-theme" in cls

    style = tag.attrs["style"]
    assert "width:" in style
    assert "height:" in style

    deps = tag.get_dependencies()
    head_html = "".join(
        str(d.head) for d in deps if getattr(d, "head", None) is not None
    )
    assert 'data-jupyter-widgets-cdn="' in head_html
    if SHINYWIDGETS_CDN_ONLY:
        assert "data-jupyter-widgets-cdn-only" in head_html
    else:
        assert "data-jupyter-widgets-cdn-only" not in head_html


def test_output_widget_fill_and_fillable_default_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ow, "resolve_id", lambda x: "resolved-id")

    def mark_fill(x):
        x.attrs["data-test-fill"] = "1"
        return x

    def mark_fillable(x):
        x.attrs["data-test-fillable"] = "1"
        return x

    monkeypatch.setattr(ow, "as_fill_item", mark_fill)
    monkeypatch.setattr(ow, "as_fillable_container", mark_fillable)

    tag = output_widget("x")
    assert tag.attrs.get("data-test-fill") == "1"
    assert tag.attrs.get("data-test-fillable") == "1"

    tag = output_widget("x", height="100px")
    assert "data-test-fill" not in tag.attrs
    assert "data-test-fillable" not in tag.attrs

    tag = output_widget("x", height="100px", fill=True, fillable=True)
    assert tag.attrs.get("data-test-fill") == "1"
    assert tag.attrs.get("data-test-fillable") == "1"

    tag = output_widget("x", height="100px", fill=False, fillable=True)
    assert "data-test-fill" not in tag.attrs
    assert tag.attrs.get("data-test-fillable") == "1"


def test_output_widget_includes_output_binding_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ow, "resolve_id", lambda x: "resolved-id")
    monkeypatch.setattr(
        ow,
        "output_binding_dependency",
        lambda: HTMLDependency(
            name="sentinel",
            version="1.0",
            source={"href": "https://example.invalid"},
            script=[],
            stylesheet=[],
        ),
    )

    tag = output_widget("x", height="100px", fill=False, fillable=False)
    assert "sentinel" in [d.name for d in tag.get_dependencies()]
