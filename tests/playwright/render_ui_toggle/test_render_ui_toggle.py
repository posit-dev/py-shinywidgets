from __future__ import annotations

from playwright.sync_api import Page, expect


# Regression test: hiding the panel while an input changes closes the widget
# without re-rendering; on re-show, Shiny replays the output's last value,
# which names the closed model. The client used to wait 30s for that model,
# so the widget never came back.
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
