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


_LIVE_VIEWS_JS = "() => window.widgetManager._liveViews.size"

# Each kepler.gl/lonboard map bundles its own copy of luma.gl, which logs this
# (harmless) console error when a page shows more than one map. How many of them
# have logged it by the time a test asserts depends on how fast the bundle loads
# (on a fast runner every map on the page initializes before the first is even
# visible), so it can't be left to timing.
LUMA_REINIT = "luma.gl: This version of luma.gl has already been initialized"


def settled_live_views(page: Page, timeout: int = 10000, quiet_ms: int = 500) -> int:
    """Return the manager's live-view count, once it has stopped changing.

    Child views (e.g. bqplot's scales, axes and marks, or the ipywidgets nglview
    builds for its GUI) are created asynchronously, so the count keeps changing
    for a moment after the DOM first looks right -- a container may even drop a
    previous render's children before the new ones are registered. Wait for a
    quiet period rather than sampling once, so comparisons are made between
    settled counts.
    """
    step = 50
    count = page.evaluate(_LIVE_VIEWS_JS)
    stable_for = 0
    waited = 0
    while waited < timeout:
        page.wait_for_timeout(step)
        waited += step
        latest = page.evaluate(_LIVE_VIEWS_JS)
        if latest == count:
            stable_for += step
            if stable_for >= quiet_ms:
                return count
        else:
            count = latest
            stable_for = 0
    return count


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
    `allowed_errors` are console messages that come from a third-party bundle
    rather than from shinywidgets (see LUMA_REINIT).
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
