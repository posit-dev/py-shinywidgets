from __future__ import annotations

from playwright.sync_api import Page
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# Records (update number, server send time, browser receive time) for every
# label text the browser renders.
RECORD_JS = """(sel) => {
  const el = document.querySelector(sel + ' .widget-label');
  const seen = (window.__seen = window.__seen || {})[sel] = [];
  new MutationObserver(() => {
    const [n, sent] = el.textContent.split(' ').map(Number);
    if (sent) seen.push([n, sent, Date.now()]);
  }).observe(el, { childList: true, characterData: true, subtree: true });
}"""


def test_updates_published_outside_a_flush_reach_the_browser(
    page: Page, local_app
) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    for sel in ("#from_task", "#from_thread"):
        page.wait_for_selector(f"{sel} .widget-label", timeout=30000)
        page.evaluate(RECORD_JS, sel)

    # No client input from here on: the server ticks every 100ms on its own.
    page.wait_for_timeout(2000)

    for sel in ("#from_task", "#from_thread"):
        seen = page.evaluate("(sel) => window.__seen[sel]", sel)
        assert len(seen) >= 10, f"{sel}: only {len(seen)} updates in 2s"
        numbers = [n for n, _, _ in seen]
        assert numbers == sorted(numbers), f"{sel}: out of order: {numbers}"
        latencies = [received - sent for _, sent, received in seen]
        assert max(latencies) < 1000, f"{sel}: latencies {latencies}"

    assert_no_unexpected_errors(errors, failed_requests)
