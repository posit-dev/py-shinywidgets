from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import expose_manager

# Changes arrive faster (every 20ms) than the server handles them (100ms
# each), like a slider drag. A synchronous loop would not do: ipywidgets
# buffers it client-side even without server acks.
DRAG_JS = """async ([id, n]) => {
  const m = await window.widgetManager.get_model(id);
  let maxPending = 0;
  for (let i = 1; i <= n; i++) {
    m.set("value", i); m.save_changes();
    maxPending = Math.max(maxPending, m._pending_msgs);
    await new Promise((r) => setTimeout(r, 20));
  }
  return maxPending;
}"""

SET_JS = """async ([id, v]) => {
  const m = await window.widgetManager.get_model(id);
  m.set("value", v); m.save_changes();
}"""


def ready(page: Page, local_app) -> str:
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)
    model_id = page.locator("#model_id")
    expect(model_id).not_to_have_text("", timeout=30000)
    return model_id.inner_text()


def test_drag_coalesces_and_final_value_arrives(page: Page, local_app) -> None:
    mid = ready(page, local_app)

    assert page.evaluate(DRAG_JS, [mid, 30]) == 1

    expect(page.locator("#value")).to_have_text("30", timeout=30000)
    assert int(page.locator("#count").inner_text()) < 30
    page.wait_for_function(
        "async (id) => (await window.widgetManager.get_model(id))._pending_msgs === 0",
        arg=mid,
        timeout=10000,
    )

    # Nothing is stuck: one more change goes through.
    page.evaluate(SET_JS, [mid, 31])
    expect(page.locator("#value")).to_have_text("31", timeout=30000)


def test_unknown_ack_is_ignored(page: Page, local_app) -> None:
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    mid = ready(page, local_app)
    page.click("#bogus_ack")
    page.evaluate(SET_JS, [mid, 1])
    expect(page.locator("#value")).to_have_text("1", timeout=30000)
    assert errors == []
