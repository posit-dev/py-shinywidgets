from types import SimpleNamespace
from typing import cast

from shiny import Session
from shinywidgets._bokeh import extension_urls_to_dependencies


def test_websocket_extension_urls_keep_at_signs() -> None:
    session = cast(Session, SimpleNamespace(app=SimpleNamespace(lib_prefix="lib")))
    deps = extension_urls_to_dependencies(
        ["https://example.invalid/widget@1.0.0/index.js"],
        ["https://example.invalid/widget@1.0.0/style.css"],
        session,
    )
    heads = [d["head"] for d in (dep.as_dict() for dep in deps) if d.get("head")]

    # The URLs must reach the browser un-encoded: websocket-delivered
    # dependencies get encodeURI()'d by Shiny's client, so any server-side
    # pre-encoding ('@' -> '%40') would become double-encoded ('%2540').
    assert (
        '<script src="https://example.invalid/widget@1.0.0/index.js"></script>' in heads
    )
    assert 'href="https://example.invalid/widget@1.0.0/style.css"' in heads[1]
    assert not any("%40" in head for head in heads)
