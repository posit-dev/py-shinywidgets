from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import assert_no_unexpected_errors, collect_errors

# Perspective ships a large (~6MB) ESM bundle inline in the widget state and
# compiles its WASM engine on first render, so allow generous timeouts
VIEWER = "#viewer perspective-viewer"


def test_perspective_renders_datagrid(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    viewer = page.locator(VIEWER)
    expect(viewer).to_have_count(1, timeout=60000)
    # the datagrid renders cells into (nested) shadow roots, which
    # playwright's css/text engines pierce by default
    expect(viewer.locator("td", has_text="row-0").first).to_be_visible(timeout=60000)
    expect(viewer.locator("td", has_text="row-2").first).to_be_visible()

    assert_no_unexpected_errors(errors, failed_requests)


def test_perspective_update_streams_to_browser(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    viewer = page.locator(VIEWER)
    expect(viewer.locator("td", has_text="row-2").first).to_be_visible(timeout=60000)

    # widget.update() on the Python side should stream a new row to the
    # existing view over the comm (no re-render of the output)
    page.click("#add_row")
    expect(viewer.locator("td", has_text="row-3").first).to_be_visible(timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")

    assert_no_unexpected_errors(errors, failed_requests)


def test_perspective_viewers_share_a_page(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    # Perspective's ESM registers custom elements at module scope, so a second
    # viewer in the page only initializes if redefinition is ignored
    expect(page.locator(VIEWER).locator("td", has_text="row-0").first).to_be_visible(
        timeout=60000
    )
    second = page.locator("#second_viewer perspective-viewer")
    expect(second.locator("td", has_text="other-1").first).to_be_visible(timeout=60000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_perspective_viewer_state_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    viewer = page.locator(VIEWER)
    expect(viewer.locator("td", has_text="row-0").first).to_be_visible(timeout=60000)
    expect(page.locator("#sort_state")).to_have_text("[]")

    # Changing the viewer's config in the browser (as a user would through its
    # settings panel) syncs the widget's traits back to Python
    viewer.evaluate("(el) => el.restore({ sort: [['value', 'desc']] })")
    expect(page.locator("#sort_state")).to_have_text(
        "[['value', 'desc']]", timeout=30000
    )

    assert_no_unexpected_errors(errors, failed_requests)


def test_perspective_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    viewer = page.locator(VIEWER)
    expect(viewer).to_have_count(1, timeout=60000)
    expect(viewer.locator("td", has_text="row-0").first).to_be_visible(timeout=60000)
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        old_viewer = viewer.element_handle()
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        page.wait_for_function("(el) => !el.isConnected", arg=old_viewer, timeout=30000)
        # each re-render must display the data again, not just swap the element
        expect(viewer.locator("td", has_text="row-2").first).to_be_visible(
            timeout=30000
        )

    # only one live view should remain after re-renders
    expect(viewer).to_have_count(1)

    assert_no_unexpected_errors(errors, failed_requests)


# The tables a viewer's browser-side client can list, plus the viewer's own table
HOSTED_TABLES_JS = """async (el) => {
  const table = await el.getTable();
  const client = await table.get_client();
  return { own: await table.get_name(), hosted: await client.get_hosted_table_names() };
}"""


def test_perspective_dataframe_tables_are_private_to_each_session(
    page: Page, local_app
) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)
    viewer = page.locator(VIEWER)
    expect(viewer.locator("td", has_text="row-0").first).to_be_visible(timeout=60000)
    first = viewer.evaluate(HOSTED_TABLES_JS)

    # A second visitor, in their own browser context (so their own session)
    assert page.context.browser is not None
    other_context = page.context.browser.new_context()
    try:
        other = other_context.new_page()
        other.goto(local_app.url)
        other_viewer = other.locator(VIEWER)
        expect(other_viewer.locator("td", has_text="row-0").first).to_be_visible(
            timeout=60000
        )
        second = other_viewer.evaluate(HOSTED_TABLES_JS)
    finally:
        other_context.close()

    # The browser can open (read and write) any table its client lists, so
    # neither the other session's tables nor the page's other viewer's table
    # may be listed
    assert first["hosted"] == [first["own"]]
    assert second["hosted"] == [second["own"]]

    assert_no_unexpected_errors(errors, failed_requests)
