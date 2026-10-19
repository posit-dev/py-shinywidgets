from __future__ import annotations

from playwright.sync_api import Page, expect


# Hide the panel, change an input the hidden widget's
# render depends on, then show it again. While hidden, the widget's render is
# invalidated and its old widget closed, but the output doesn't re-render
# (it's suspended). On re-bind, Shiny replays the output's last client value,
# which names the now-closed model. The client used to wait the full 30s
# model-waiter timeout for a model that would never arrive, so the widget
# never came back and the page looked stuck.
def test_widget_reappears_after_hidden_input_change(page: Page, local_app) -> None:
    errors: list[str] = []
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(local_app.url)
    page.wait_for_selector("#w .widget-button", timeout=15000)

    page.uncheck("#show")
    expect(page.locator("#w")).to_have_count(0)

    page.evaluate("() => Shiny.setInputValue('n', 3, {priority: 'event'})")
    page.wait_for_timeout(500)

    page.check("#show")
    widget = page.locator("#w .widget-button")
    # A tight timeout: on unfixed code this hangs for ~30s instead of failing fast.
    expect(widget).to_be_visible(timeout=5000)
    expect(widget).to_contain_text("n = 3")

    assert not any("timeout waiting for widget model" in e.lower() for e in errors), (
        errors
    )
