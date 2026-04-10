from __future__ import annotations

from playwright.sync_api import Page, expect


def test_widgets_render_inside_and_outside_isolate(page: Page, local_app) -> None:
    errors: list[str] = []
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(local_app.url)
    page.wait_for_selector("#plot_out .js-plotly-plot", timeout=30000)
    page.wait_for_selector("#slider_out .widget-slider", timeout=30000)

    expect(page.locator("#plot_in .js-plotly-plot")).to_have_count(1, timeout=30000)
    expect(page.locator("#plot_out .js-plotly-plot")).to_have_count(1, timeout=30000)
    expect(page.locator("#slider_in .widget-slider")).to_have_count(1, timeout=30000)
    expect(page.locator("#slider_out .widget-slider")).to_have_count(1, timeout=30000)
    assert not any("no comm channel defined" in err.lower() for err in errors)
