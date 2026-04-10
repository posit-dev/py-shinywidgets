from __future__ import annotations

from playwright.sync_api import Page


def test_bokeh_renders_when_app_is_mounted_under_prefix(
    page: Page, local_app
) -> None:
    errors: list[str] = []

    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(f"{local_app.url.rstrip('/')}/anonymous/")
    page.wait_for_selector("#plot .bk-Figure", timeout=30000)

    assert page.locator("#plot .bk-Figure").count() == 1
    assert not any("@bokeh/jupyter_bokeh" in err for err in errors)
