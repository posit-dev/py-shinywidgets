from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    LUMA_REINIT,
    assert_no_unexpected_errors,
    collect_errors,
)

LOAD_TIMEOUT = 60000

HEIGHTS_JS = """(id) => {
  const out = document.getElementById(id);
  const kepler = out && out.querySelector('.kepler-gl');
  if (!kepler) return null;
  return { container: out.clientHeight, kepler: kepler.getBoundingClientRect().height };
}"""

KEPLER_MATCHES_CONTAINER_JS = """(id) => {
  const out = document.getElementById(id);
  const kepler = out && out.querySelector('.kepler-gl');
  return !!kepler && Math.abs(kepler.getBoundingClientRect().height - out.clientHeight) <= 1;
}"""


def test_redisplayed_widget_keeps_filling(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#cached_map .kepler-gl")).to_be_visible(timeout=LOAD_TIMEOUT)
    page.wait_for_function(KEPLER_MATCHES_CONTAINER_JS, arg="cached_map", timeout=10000)

    # The browser has now written the measured height into the widget's `height`
    # trait. Displaying the same instance again must still fill, so the map has to
    # follow a container that changed in the meantime.
    page.evaluate("document.getElementById('cached_card').style.height = '350px'")
    page.wait_for_function(KEPLER_MATCHES_CONTAINER_JS, arg="cached_map", timeout=10000)
    page.click("#rerender")
    expect(page.locator("#render_count")).to_have_text("1")
    page.evaluate("document.getElementById('cached_card').style.height = '300px'")
    page.wait_for_function(
        "() => { const c = document.getElementById('cached_map').clientHeight;"
        " return c < 300 && Math.abs(document.querySelector('#cached_map .kepler-gl')"
        ".getBoundingClientRect().height - c) <= 1; }",
        timeout=10000,
    )

    assert_no_unexpected_errors(errors, failed_requests, allowed_errors=(LUMA_REINIT,))


def test_widget_with_own_height_after_filling_render_is_respected(
    page: Page, local_app
) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    expect(page.locator("#swapped_map .kepler-gl")).to_be_visible(timeout=LOAD_TIMEOUT)
    page.wait_for_function(
        KEPLER_MATCHES_CONTAINER_JS, arg="swapped_map", timeout=10000
    )
    assert page.evaluate(HEIGHTS_JS, "swapped_map")["kepler"] > 400

    # The output is still stretched by the card, but the new widget isn't filling,
    # so the earlier render's fill behavior must not resize it
    old = page.locator("#swapped_map .kepler-gl").element_handle()
    page.click("#rerender")
    page.wait_for_function("(el) => !el.isConnected", arg=old, timeout=LOAD_TIMEOUT)
    expect(page.locator("#swapped_map .kepler-gl")).to_be_visible(timeout=LOAD_TIMEOUT)
    page.wait_for_timeout(1000)
    heights = page.evaluate(HEIGHTS_JS, "swapped_map")
    assert heights["container"] > 400
    assert abs(heights["kepler"] - 250) <= 1

    assert_no_unexpected_errors(errors, failed_requests, allowed_errors=(LUMA_REINIT,))
