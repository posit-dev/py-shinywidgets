from __future__ import annotations

from typing import Any

from playwright.sync_api import Page, Route, expect
from shiny.run import ShinyAppProc


# Patches the served output.js so the page's OutputManager is reachable as
# window.widgetManager (same pattern as tests/playwright/widget_view_retention).
# `_models` and each model's `.views` exist in production, so no bundle change
# is needed.
def expose_manager(route: Route) -> None:
    response = route.fetch()
    text = response.text()
    original = "const manager = new OutputManager({ loader: shinyRequireLoader });"
    assert original in text
    route.fulfill(
        response=response,
        body=text.replace(
            original,
            "const manager = window.widgetManager = new OutputManager({ loader: shinyRequireLoader });",
        ),
    )


LIVE_VIEWS_JS = "() => window.widgetManager._liveViews.size"

# True when the live-view count matches the previous poll's (i.e., async view
# registration has settled). Keeps the last count on the window between polls.
_VIEWS_STABLE_JS = """() => {
  const n = window.widgetManager._liveViews.size;
  const stable = window.__shinywidgetsLastViewCount === n;
  window.__shinywidgetsLastViewCount = n;
  return stable;
}"""


def wait_for_stable_view_count(page: Page, timeout: int = 30000) -> int:
    """Return the live-view count once it stops changing between polls.

    Widget views register asynchronously after first paint, so sampling
    `_liveViews.size` as soon as an output appears can catch a partially
    populated registry -- and a later equality check against that sample then
    fails spuriously. Requires the `expose_manager` route.
    """
    page.wait_for_function(_VIEWS_STABLE_JS, polling=500, timeout=timeout)
    return page.evaluate(LIVE_VIEWS_JS)


_MODELS_JS = """async () => {
    const models = await Promise.all(
        Object.values(window.widgetManager._models).map((p) => p.catch(() => null))
    );
    return models.filter((m) => m).map((m) => ({
        name: m.get('_model_name'),
        views: Object.keys(m.views || {}).length,
    }));
}"""


def client_models(page: Page) -> list[dict[str, Any]]:
    """Per-model summary (class name + live view count) of the browser's widget registry."""
    return page.evaluate(_MODELS_JS)


# Sum of live views across every model with the given class name. Views are
# attached/detached asynchronously, so the sum can lag behind what the DOM
# already shows.
_MODEL_VIEWS_JS = """async (modelName) => {
    const models = await Promise.all(
        Object.values(window.widgetManager._models).map((p) => p.catch(() => null))
    );
    return models
        .filter((m) => m && m.get('_model_name') === modelName)
        .reduce((sum, m) => sum + Object.keys(m.views || {}).length, 0);
}"""

# True when the per-model view count matches the previous poll's (i.e., async
# view registration/disposal has settled). Keeps the last count per model name
# on the window between polls (and across calls, which is fine: an unchanged
# count is the settled value we're after).
_MODEL_VIEWS_STABLE_JS = """async (modelName) => {
    const models = await Promise.all(
        Object.values(window.widgetManager._models).map((p) => p.catch(() => null))
    );
    const n = models
        .filter((m) => m && m.get('_model_name') === modelName)
        .reduce((sum, m) => sum + Object.keys(m.views || {}).length, 0);
    const last = window.__shinywidgetsLastModelViewCounts || {};
    const stable = last[modelName] === n;
    last[modelName] = n;
    window.__shinywidgetsLastModelViewCounts = last;
    return stable;
}"""


def wait_for_stable_model_view_count(
    page: Page, model_name: str, timeout: int = 30000
) -> int:
    """Return the summed live-view count for `model_name` once it stops changing.

    Per-model counterpart to `wait_for_stable_view_count()`: widget views
    register and dispose asynchronously, so sampling `client_models()` as soon
    as an output appears in the DOM can catch a partially populated (or not yet
    cleaned up) registry -- and a later equality check against that sample then
    fails spuriously. Requires the `expose_manager` route.
    """
    page.wait_for_function(
        _MODEL_VIEWS_STABLE_JS, arg=model_name, polling=500, timeout=timeout
    )
    return page.evaluate(_MODEL_VIEWS_JS, model_name)


def assert_rerender_cleanup(
    page: Page,
    local_app: ShinyAppProc,
    ready_selector: str,
) -> None:
    errors: list[str] = []

    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(local_app.url)
    page.wait_for_selector(ready_selector, timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))

    expect(page.locator("#plot > .lm-Widget")).to_have_count(1)
    expect(page.locator(ready_selector)).to_have_count(1)
    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel defined" in err.lower() for err in errors)


# Samples canvases under a selector and returns True if any contains enough
# opaque, non-white pixels (i.e., something was actually drawn). Only works
# for 2D canvases (WebGL canvases return null from getContext('2d')).
CANVAS_HAS_PIXELS_JS = """(sel) => {
  // Collect canvases, piercing shadow roots (bokeh 3 renders into shadow DOM,
  // which querySelectorAll alone doesn't reach)
  const canvases = [];
  const walk = (root) => {
    if (root.tagName === 'CANVAS') canvases.push(root);
    for (const el of root.querySelectorAll('*')) {
      if (el.tagName === 'CANVAS') canvases.push(el);
      if (el.shadowRoot) walk(el.shadowRoot);
    }
  };
  for (const root of document.querySelectorAll(sel)) walk(root);
  for (const c of canvases) {
    let ctx = null;
    try { ctx = c.getContext('2d'); } catch (e) { continue; }
    if (!ctx || !c.width || !c.height) continue;
    const d = ctx.getImageData(0, 0, c.width, c.height).data;
    let nonblank = 0;
    // Fine stride: sparse line plots may only have a few hundred non-white
    // pixels total, so coarse sampling can miss them entirely
    for (let i = 0; i < d.length; i += 4 * 53) {
      if (d[i + 3] > 0 && (d[i] < 250 || d[i + 1] < 250 || d[i + 2] < 250)) nonblank++;
    }
    if (nonblank > 10) return true;
  }
  return false;
}"""


def collect_errors(page: Page) -> tuple[list[str], list[str]]:
    """Collect browser console errors and failed (>= 400) request URLs."""
    errors: list[str] = []
    failed_requests: list[str] = []
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))
    page.on(
        "response",
        lambda res: failed_requests.append(res.url) if res.status >= 400 else None,
    )
    return errors, failed_requests


# anywidget evaluates a widget's inline ESM once per *view* (a fresh blob
# URL per evaluation), so a page with N keplergl maps initializes luma.gl's
# page-global runtime N times; luma keeps the first initialization and logs
# this (benign) message for the rest. Whether the extra inits interleave
# badly enough to log is a timing race, so the message appears
# intermittently (mostly on loaded CI runners). Deduping the evaluation
# isn't an option: other anywidgets (e.g. mosaic-widget) keep per-view state
# in their module namespace and break when views share one.
KEPLERGL_ALLOWED_ERRORS = (
    "luma.gl: This version of luma.gl has already been initialized",
)


def assert_no_unexpected_errors(
    errors: list[str],
    failed_requests: list[str],
    allowed_404s: tuple[str, ...] = (),
    allowed_errors: tuple[str, ...] = (),
) -> None:
    """Assert no unexpected browser errors.

    Failed requests whose URL contains one of `allowed_404s` are tolerated, along
    with the generic "Failed to load resource" console error they produce (the
    console message doesn't include the URL, so it can't be matched precisely).
    Console errors containing one of the `allowed_errors` substrings are also
    tolerated (for known-benign third-party messages).
    """
    assert all(
        any(allowed in url for allowed in allowed_404s) for url in failed_requests
    )
    tolerate_resource_errors = len(failed_requests) > 0
    unexpected = [
        err
        for err in errors
        if not (tolerate_resource_errors and "Failed to load resource" in err)
        and not any(allowed in err for allowed in allowed_errors)
    ]
    assert not unexpected
