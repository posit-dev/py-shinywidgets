from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc


def test_cached_plotly_preserves_updates_and_callbacks_after_redisplay(
    page: Page, local_app: ShinyAppProc
) -> None:
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on(
        "console",
        lambda message: (
            errors.append(message.text) if message.type == "error" else None
        ),
    )
    page.add_init_script(
        """(() => {
            window.readyPlots = new WeakSet();
            document.addEventListener('plotlywidget-after-render', event => {
                window.readyPlots.add(event.detail.element);
            });
        })();"""
    )
    page.goto(local_app.url)
    output = page.locator("#cached_plot")
    expect(output.locator(".gtitle")).to_have_text("A")
    first_id = output.get_attribute("data-shinywidgets-model-id")
    assert first_id is not None

    click_first_point(page)
    expect(page.locator("#click_count")).to_have_text("1")
    page.locator("#update").click()
    expect(output.locator(".gtitle")).to_have_text("updated A")

    page.locator("#dataset").select_option("B")
    expect(output.locator(".gtitle")).to_have_text("B")
    page.locator("#dataset").select_option("A")
    expect(output.locator(".gtitle")).to_have_text("updated A")
    assert output.get_attribute("data-shinywidgets-model-id") == first_id

    click_first_point(page)
    expect(page.locator("#click_count")).to_have_text("2")
    page.locator("#title").fill("A after redisplay")
    expect(page.locator("#requested_title")).to_have_text("A after redisplay")
    page.locator("#update").click()
    expect(page.locator("#update_status")).to_have_text(f"{first_id}:A after redisplay")
    expect(output.locator(".gtitle")).to_have_text("A after redisplay")
    assert not errors, errors


def click_first_point(page: Page) -> None:
    page.wait_for_function(
        """() => {
            const plot = document.querySelector('#cached_plot .js-plotly-plot');
            return plot && window.readyPlots.has(plot) &&
                getComputedStyle(plot).visibility !== 'hidden';
        }"""
    )
    point = page.locator("#cached_plot .point").first
    expect(point).to_be_visible()
    bounds = point.bounding_box()
    assert bounds is not None
    # Plotly's drag layer receives pointer events above the SVG points.
    page.mouse.click(
        bounds["x"] + bounds["width"] / 2,
        bounds["y"] + bounds["height"] / 2,
    )
