from __future__ import annotations

from playwright.sync_api import Page, expect


def test_module_rerender_closes_old_widget(page: Page, local_app) -> None:
    # A @render_widget inside a module must close its previous widget when the
    # output re-renders. Before the render context moved off the session, the
    # render wrote it to the module's session proxy while init_shiny_widget()
    # read it from the root session, so old widgets were never closed and
    # leaked server-side (the client looked fine).
    page.goto(local_app.url)
    expect(page.locator("#mod-count")).to_have_text(
        "renders=0 widgets=1", timeout=30000
    )
    expect(page.locator("#mod-w .lm-Widget")).to_have_count(1)

    for i in range(1, 4):
        page.click("#mod-rerender")
        expect(page.locator("#mod-count")).to_have_text(
            f"renders={i} widgets=1", timeout=30000
        )

    expect(page.locator("#mod-w .lm-Widget")).to_have_count(1)
