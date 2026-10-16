"""
User-facing lifecycle integration (plan 4, task 2): cached widgets declared
with session_lifetime() survive A -> B -> A switching with their exact model
identity and Python-side state, while temporary widgets return to a stable
server/browser baseline across repeated renders.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc
from tests.playwright.conftest import open_lifecycle_page


def test_cached_widget_returns_with_same_model(
    page: Page, local_app: ShinyAppProc
) -> None:
    page = open_lifecycle_page(page, local_app)
    output = page.locator("#cached")
    expect(output).to_have_text("A:0")
    first_id = output.get_attribute("data-shinywidgets-model-id")
    assert first_id is not None

    page.locator("#dataset").select_option("B")
    expect(output).to_have_text("B:0")
    page.locator("#dataset").select_option("A")
    expect(output).to_have_text("A:0")
    assert output.get_attribute("data-shinywidgets-model-id") == first_id

    # Updates through the existing Python object work after redisplay.
    page.click("#bump")
    expect(output).to_have_text("A:1")
    page.locator("#dataset").select_option("B")
    page.locator("#dataset").select_option("A")
    expect(output).to_have_text("A:1")
    assert output.get_attribute("data-shinywidgets-model-id") == first_id


def test_temporary_widgets_return_to_baseline_after_repeated_renders(
    page: Page,
    local_app: ShinyAppProc,
) -> None:
    page = open_lifecycle_page(page, local_app)
    expect(page.locator("#fresh_widget")).to_have_text("fresh 0")
    # Warmed-up baseline: one session-cached HTML (+layout+style), one
    # temporary HTML (+layout+style), two claimed display leases.
    baseline = "records=6 comms=6 leases=2 pending=0"
    expect(page.locator("#snapshot")).to_have_text(baseline)

    for n in range(1, 11):
        page.click("#fresh")
        expect(page.locator("#fresh_widget")).to_have_text(f"fresh {n}")

    # Ten fresh renders: server records/comms/leases return to the baseline
    # once the old presentations' leases are released and collected.
    expect(page.locator("#snapshot")).to_have_text(baseline)

    browser = page.evaluate(
        """() => {
            const snapshot = window.widgetLifecycle.snapshot();
            const mounts = window.widgetLifecycle.mountSnapshot(
                document.querySelector('#fresh_widget')
            );
            return {...snapshot, mounts: mounts.mounts, mountViews: mounts.views};
        }"""
    )
    assert browser["waiters"] == 0
    assert browser["tasks"] == 0
    # One accepted presentation (plus its layout/style child views).
    assert browser["mountViews"] <= 4


def test_cached_counts_grow_only_with_distinct_cached_widgets(
    page: Page, local_app: ShinyAppProc
) -> None:
    open_lifecycle_page(page, local_app)
    expect(page.locator("#cached")).to_have_text("A:0")
    page.locator("#dataset").select_option("B")
    expect(page.locator("#cached")).to_have_text("B:0")
    # Two cached widgets (+layouts/styles) and no temporary records while the
    # fresh output is displayed: cache growth equals distinct cached widgets.
    expect(page.locator("#snapshot")).to_have_text(
        "records=9 comms=9 leases=2 pending=0"
    )
