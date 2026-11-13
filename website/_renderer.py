"""quartodoc renderer for the shinywidgets reference: GreatDocs-like page anatomy.

Each object page reads: monospace title + kind badge, italic one-line summary, a
"Usage" signature panel with a link to the source on GitHub, then the docstring
(parameters as a description list), then methods. Sphinx roles in docstrings
(:meth:`x`, :func:`~pkg.y`) become links instead of raw text.
"""

from __future__ import annotations

import re
from typing import Union

from quartodoc._griffe_compat import dataclasses as dc
from quartodoc._griffe_compat import docstrings as ds
from plum import dispatch
from quartodoc import MdRenderer, layout
from quartodoc import ast as qast

import shinywidgets

REPO = "https://github.com/posit-dev/py-shinywidgets/blob/main"
ROLE = re.compile(r":(?:py:)?(meth|func|class|attr|obj|data):`(~?)([\w.]+)`")
EXPORTED = set(shinywidgets.__all__)


class Renderer(MdRenderer):
    style = "shinywidgets"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._page_members: dict[str, str] = {}

    # Page: collect link targets, then rewrite Sphinx roles in the finished markdown

    @dispatch
    def render(self, el: layout.Page):
        self._page_members = {}
        for doc in el.contents:
            for member in getattr(doc, "members", None) or []:
                self._page_members[member.name] = member.anchor
        body = resolve_roles(super().render(el), self._page_members, EXPORTED)
        # An explicit title keeps the kind badge (part of the H1) out of the sidebar,
        # breadcrumbs, and window title; the H1 itself stays as the visible heading.
        if len(el.contents) == 1:
            name = el.contents[0].name
            return f'---\ntitle: "{name}"\ntitle-block-style: none\n---\n\n{body}'
        return body

    # Object pages

    @dispatch
    def render(self, el: Union[layout.DocClass, layout.DocFunction]):
        target = resolve_alias(el.obj)
        is_top = self.crnt_header_level == self.header_level
        summary, body = self._summary_and_body(el)

        parts = [self.render_header(el)]
        if is_top and summary:
            parts.append(f"[{summary}]{{.ref-summary}}")
        if self.show_signature:
            parts.append(self._usage(el, target, label=is_top))
        if not is_top and summary:
            parts.append(summary)
        if body:
            parts.append(body)
        if isinstance(el, layout.DocClass):
            parts.extend(self._members(el))
        return "\n\n".join(parts)

    @dispatch
    def render_header(self, el: layout.Doc) -> str:
        target = resolve_alias(el.obj)
        hashes = "#" * self.crnt_header_level
        if self.crnt_header_level == self.header_level:
            kind = "class" if target.is_class else "function"
            return f"{hashes} {el.name} [{kind}]{{.ref-kind .ref-kind-{kind}}} {{#{el.anchor} .ref-title .unlisted}}"
        return f"{hashes} {el.name}() {{#{el.anchor} .ref-member}}"

    # Sections

    @dispatch
    def render(self, el: qast.DocstringSectionSeeAlso):
        # quartodoc turns roles here into interlinks we don't use; resolve them ourselves.
        return resolve_roles(el.value, self._page_members, EXPORTED)

    @dispatch
    def summarize(self, el: layout.Doc, path: str | None = None, shorten: bool = False):
        name = f"`{el.name}()`" if resolve_alias(el.obj).is_function else f"`{el.name}`"
        link = f"[{name}](#{el.anchor})" if path is None else f"[{name}]({path}.qmd#{el.anchor})"
        doc = resolve_alias(el.obj).docstring
        summary = first_paragraph(doc.value) if doc is not None else ""
        return self._summary_row(link, resolve_roles(summary, self._page_members, EXPORTED))

    # Helpers

    def _summary_and_body(self, el: layout.Doc) -> tuple[str, str]:
        doc = el.obj.docstring
        if doc is None:
            return "", ""
        sections = list(doc.parsed)
        summary = ""
        if sections and isinstance(sections[0], ds.DocstringSectionText):
            summary = first_paragraph(sections[0].value)
            _, _, rest = sections[0].value.partition("\n\n")
            if rest.strip():
                sections[0] = ds.DocstringSectionText(rest)
            else:
                sections = sections[1:]
        with self._increment_header():
            body = "\n\n".join(self._render_section(s) for s in qast.transform(sections))
        return summary, body

    def _render_section(self, section) -> str:
        title = section.title or section.kind.value
        text = self.render(section)
        if title == "text":
            return text
        return f"{self.render_header(section)}\n\n{text}"

    def _usage(self, el: layout.Doc, target, label: bool) -> str:
        sig = self.signature(el)
        if not label:
            return f"::: {{.ref-usage .ref-usage-member}}\n{sig}\n:::"
        path = getattr(target, "relative_package_filepath", None)
        src = f"[Source]({REPO}/{path}#L{target.lineno}-L{target.endlineno}){{.ref-source}}" if path else ""
        return f"::: {{.ref-usage}}\n[Usage]{{.ref-usage-label}} {src}\n\n{sig}\n:::"

    def _members(self, el: layout.DocClass) -> list[str]:
        meths = [m for m in el.members if resolve_alias(m.obj).is_function]
        if not meths:
            return []
        rows = "\n".join(self.summarize(m) for m in meths)
        out = [f"{'#' * (self.crnt_header_level + 1)} Methods {{.ref-methods}}\n\n| | |\n| --- | --- |\n{rows}"]
        with self._increment_header(1 if el.flat else 2):
            out.extend(self.render(m) for m in meths)
        return out



def first_paragraph(text: str) -> str:
    """A docstring's first paragraph as one line: the object's summary."""
    return " ".join(text.strip().partition("\n\n")[0].split())


def resolve_roles(text: str, page_members: dict[str, str], exported: set[str]) -> str:
    """Turn Sphinx roles (:meth:`x`, :func:`~pkg.y`, ...) into Markdown links or code.

    A method on this page links to its anchor; a shinywidgets export links to its page;
    anything else (a foreign class, an unknown name) becomes plain code.
    """

    def repl(m: re.Match[str]) -> str:
        role, _tilde, target = m.groups()
        name = target.split(".")[-1]
        shown = f"`{name}()`" if role in {"meth", "func"} else f"`{name}`"
        if role == "meth" and name in page_members:
            return f"[{shown}](#{page_members[name]})"
        ours = "." not in target or target.startswith("shinywidgets.")
        if ours and name in exported:
            return f"[{shown}]({name}.qmd)"
        return shown

    return ROLE.sub(repl, text)


def resolve_alias(obj: Union[dc.Object, dc.Alias]):
    return obj.final_target if isinstance(obj, dc.Alias) else obj
