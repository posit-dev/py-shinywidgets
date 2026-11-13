import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _renderer import first_paragraph, resolve_roles  # noqa: E402

MEMBERS = {"hover": "shinywidgets.render_plotly.hover"}
EXPORTED = {"reactive_read", "render_plotly"}


def test_method_links_to_anchor_on_page():
    out = resolve_roles(":meth:`hover`", MEMBERS, EXPORTED)
    assert out == "[`hover()`](#shinywidgets.render_plotly.hover)"


def test_exported_function_links_to_its_page():
    out = resolve_roles(":func:`~shinywidgets.reactive_read`", MEMBERS, EXPORTED)
    assert out == "[`reactive_read()`](reactive_read.qmd)"


def test_py_prefixed_role_and_bare_name():
    out = resolve_roles(":py:class:`render_plotly`", MEMBERS, EXPORTED)
    assert out == "[`render_plotly`](render_plotly.qmd)"


def test_foreign_class_is_code_not_link():
    assert resolve_roles(":class:`ipywidgets.Widget`", MEMBERS, EXPORTED) == "`Widget`"


def test_unknown_bare_name_is_code_not_link():
    assert resolve_roles(":func:`not_exported`", MEMBERS, EXPORTED) == "`not_exported()`"


def test_missing_method_is_code_not_link():
    assert resolve_roles(":meth:`missing`", MEMBERS, EXPORTED) == "`missing()`"


def test_surrounding_text_kept():
    out = resolve_roles("Use :meth:`hover` or :attr:`x`.", MEMBERS, EXPORTED)
    assert out == "Use [`hover()`](#shinywidgets.render_plotly.hover) or `x`."


def test_first_paragraph_joins_wrapped_lines():
    text = "Create an output container for a Shiny widget (i.e., a placeholder for an\nipywidget).\n\nMore detail."
    assert first_paragraph(text) == "Create an output container for a Shiny widget (i.e., a placeholder for an ipywidget)."


def test_first_paragraph_of_empty_text():
    assert first_paragraph("") == ""
