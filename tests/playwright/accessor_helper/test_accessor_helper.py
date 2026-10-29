from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import expose_manager

# Ten changes 50 ms apart (well inside the 250 ms window) to each model.
DRAG_JS = """async (ids) => {
  const models = await Promise.all(ids.map((id) => window.widgetManager.get_model(id)));
  for (let v = 1; v <= 10; v++) {
    for (const m of models) { m.set("value", v); m.save_changes(); }
    await new Promise((r) => setTimeout(r, 50));
  }
}"""


def count(page: Page, id: str) -> int:
    return int(page.locator(f"#{id}").inner_text())


def test_accessor_reads_state_and_debounces_by_default(page: Page, local_app) -> None:
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    for id in ("fast_model", "slow_model", "policy_model"):
        expect(page.locator(f"#{id}")).not_to_have_text("", timeout=30000)
    ids = [
        page.locator(f"#{id}").inner_text()
        for id in ("fast_model", "slow_model", "policy_model")
    ]
    # Let the initial renders settle before counting.
    expect(page.locator("#slow_value")).to_have_text("None", timeout=10000)
    before = {k: count(page, f"{k}_count") for k in ("fast", "slow", "raw", "policy")}

    page.evaluate(DRAG_JS, ids)

    for id in ("fast_value", "slow_value", "raw_slow", "policy_value"):
        expect(page.locator(f"#{id}")).to_have_text("10", timeout=5000)
    page.wait_for_timeout(500)

    n = {k: count(page, f"{k}_count") - before[k] for k in before}
    assert n["slow"] == 1  # one debounced publish
    assert n["policy"] == 1  # renderer kwarg debounces reactive_read
    assert n["fast"] > n["slow"]  # rate_delay=0: follows the stream
    assert n["raw"] > n["slow"]  # reactive_read untouched by an accessor's default
