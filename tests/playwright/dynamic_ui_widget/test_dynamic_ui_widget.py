from playwright.sync_api import Page, expect


# Dynamically-inserted widget outputs (output_widget() inside @render.ui)
# failed on the ipywidgets-7-era html-manager (`HTMLStyleModel not found`)
# because the output binding's dependencies arrive after initial page load.
# Fixed by the html-manager 1.0 upgrade (#237); this covers repeated
# insertions of the same output id.
def test_dynamic_ui_widget_renders_without_errors(page: Page, local_app) -> None:
    errors: list[str] = []
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda err: errors.append(str(err)))

    page.goto(local_app.url)

    for i in range(1, 4):
        page.click("#show")
        widget = page.locator("#dyn .lm-Widget")
        expect(widget).to_have_count(1, timeout=15000)
        expect(widget).to_contain_text(f"dynamic render #{i}", timeout=15000)

    assert not errors, f"Unexpected console errors: {errors}"
