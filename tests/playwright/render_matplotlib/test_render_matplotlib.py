from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    CANVAS_HAS_PIXELS_JS,
    assert_no_unexpected_errors,
    collect_errors,
)

NEW_FIGURE_SHOWN_JS = """(old) => [
  ...document.querySelectorAll('#container .jupyter-matplotlib-figure'),
].some((el) => el !== old)"""


def test_matplotlib_actually_draws_pixels(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    # ipympl renders its figure onto a <canvas> (it also keeps an offscreen
    # canvas, so there may be more than one). A non-blank canvas proves the
    # figure's PNG buffer survived the base64 comm transport and was drawn.
    expect(page.locator("#mpl canvas").first).to_be_visible(timeout=30000)
    assert page.evaluate(CANVAS_HAS_PIXELS_JS, "#mpl")

    assert_no_unexpected_errors(errors, failed_requests)


def test_matplotlib_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#mpl canvas").first).to_be_visible(timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")

    n_canvases = page.locator("#mpl canvas").count()

    for i in range(1, 4):
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))

    # Re-rendering replaces the widget, but the old view must be disposed
    # (i.e., no accumulation of canvases) ...
    expect(page.locator("#mpl canvas")).to_have_count(n_canvases)

    # ... and the new widget still draws
    assert page.evaluate(CANVAS_HAS_PIXELS_JS, "#mpl")

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)


def test_matplotlib_canvas_removed_from_container(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    figures = page.locator("#container .jupyter-matplotlib-figure")
    expect(figures).to_have_count(1, timeout=30000)

    for _ in range(3):
        old_figure = figures.first.element_handle()
        page.click("#swap")
        page.wait_for_function(NEW_FIGURE_SHOWN_JS, arg=old_figure)

    # ipympl's canvas view overrides remove() without calling the base
    # implementation, so a container dropping it would leave it on screen
    expect(figures).to_have_count(1)

    assert_no_unexpected_errors(errors, failed_requests)
