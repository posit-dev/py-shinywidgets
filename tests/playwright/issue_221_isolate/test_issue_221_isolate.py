from __future__ import annotations

import time

from playwright.sync_api import Page


def test_widgets_render_inside_and_outside_isolate(page: Page, local_app) -> None:
    errors: list[str] = []
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(local_app.url, wait_until="networkidle")
    page.wait_for_selector("#plot_out .js-plotly-plot", timeout=30000)
    page.wait_for_selector("#slider_out .widget-slider", timeout=30000)
    time.sleep(3.5)

    assert page.locator("#plot_in .js-plotly-plot").count() == 1
    assert page.locator("#plot_out .js-plotly-plot").count() == 1
    assert page.locator("#slider_in .widget-slider").count() == 1
    assert page.locator("#slider_out .widget-slider").count() == 1
    assert not any("no comm channel defined" in err.lower() for err in errors)
