"""
anywidget teardown evidence (plan 3, task 11).

anywidget calls a view's cleanup synchronously on removal but never awaits a
promise it returns: observable owned cleanup (the view removal) is covered by
mount disposal; hidden third-party async cleanup is not, and that's the
documented upstream limit.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc
from tests.playwright.conftest import open_lifecycle_page


def test_anywidget_cleanup_runs_on_view_removal(
    page: Page, local_app: ShinyAppProc
) -> None:
    open_lifecycle_page(page, local_app)
    expect(page.locator("#widget")).to_have_text("anywidget content")
    page.click("#rerender")
    page.wait_for_function("() => window.anywidgetCleanups === 1")
    expect(page.locator("#widget")).to_have_text("anywidget content")
    # Disposal settles with exactly one presentation and no lingering tasks.
    snapshot = page.evaluate(
        """() => window.widgetLifecycle.mountSnapshot(
            document.querySelector('#widget')
        )"""
    )
    assert snapshot["tasks"] == 0


def test_unawaited_async_cleanup_does_not_block_disposal(
    page: Page, local_app: ShinyAppProc
) -> None:
    open_lifecycle_page(page, local_app)
    expect(page.locator("#widget")).to_have_text("anywidget content")
    # n=1 mounts the pending-cleanup widget; n=2 replaces it.
    page.click("#rerender")
    page.wait_for_function(
        """() => window.widgetLifecycle.mountIdentity(
            document.querySelector('#widget')
        ).claim_seq === 2"""
    )
    page.click("#rerender")
    # The replaced view's cleanup *function* was invoked (synchronously)...
    page.wait_for_function("() => window.anywidgetPendingCleanups === 1")
    # ...but disposal completed without waiting for its never-settling
    # promise: the upstream unreturned-cleanup limit.
    page.wait_for_timeout(1000)
    snapshot = page.evaluate(
        """() => window.widgetLifecycle.mountSnapshot(
            document.querySelector('#widget')
        )"""
    )
    assert snapshot["tasks"] == 0
    expect(page.locator("#widget")).to_have_text("anywidget content")
