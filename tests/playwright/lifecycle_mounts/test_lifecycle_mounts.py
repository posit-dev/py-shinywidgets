"""
Presentation mount ownership (plan 3, task 6).

Assertions combine real view disposal/attachment, server record/comm/lease
baselines, and mount snapshots -- a shared model must survive disposing one
of its two views, and repeated rendering returns all owned resources to a
stable baseline.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc
from tests.playwright.conftest import open_lifecycle_page

BASELINE = "records=8 comms=8 leases=3 pending=0"


def mount_snapshot(page: Page, selector: str) -> dict:
    return page.evaluate(
        f"""() => window.widgetLifecycle.mountSnapshot(
            document.querySelector('{selector}')
        )"""
    )


def test_child_views_replaced_with_mount_and_counts_return_to_baseline(
    page: Page, local_app: ShinyAppProc
) -> None:
    open_lifecycle_page(page, local_app)
    expect(page.locator("#box")).to_have_text("child 0")
    expect(page.locator("#snapshot")).to_have_text(BASELINE)
    baseline = mount_snapshot(page, "#box")

    for n in range(1, 4):
        page.evaluate(
            """() => {
                const el = document.querySelector('#box');
                window.previousBoxViews = [...window.widgetLifecycle
                    .existingMountFor(el).walkViews()];
            }"""
        )
        page.click("#rerender")
        expect(page.locator("#box")).to_have_text(f"child {n}")
        disposed = page.evaluate(
            """() => window.previousBoxViews.map(
                (v) => !v.luminoWidget || v.luminoWidget.isDisposed
            )"""
        )
        assert all(disposed), "previous child views were not disposed"
        # Server records/comms/leases return to the warmed-up baseline after
        # the old display lease is released and collected.
        expect(page.locator("#snapshot")).to_have_text(BASELINE)

    after = mount_snapshot(page, "#box")
    assert after == baseline


def test_shared_model_survives_disposing_one_view(
    page: Page, local_app: ShinyAppProc
) -> None:
    open_lifecycle_page(page, local_app)
    expect(page.locator("#shared_a")).to_have_text("shared model")
    expect(page.locator("#shared_b")).to_have_text("shared model")
    model_id = page.locator("#shared_a").get_attribute("data-shinywidgets-model-id")
    assert model_id is not None
    assert (
        page.locator("#shared_b").get_attribute("data-shinywidgets-model-id")
        == model_id
    )

    # Drop the second view: its presentation is disposed and lease released,
    # but the shared model and the first view stay functional.
    page.click("#drop")
    page.wait_for_function("() => !document.querySelector('#slot-holder #shared_b')")
    expect(page.locator("#snapshot")).to_have_text(
        "records=8 comms=8 leases=2 pending=0"
    )
    expect(page.locator("#shared_a")).to_have_text("shared model")

    # Bring the second view back: the same model is displayed again.
    page.click("#drop")
    expect(page.locator("#shared_b")).to_have_text("shared model")
    assert (
        page.locator("#shared_b").get_attribute("data-shinywidgets-model-id")
        == model_id
    )
    expect(page.locator("#snapshot")).to_have_text(BASELINE)


def test_slow_candidate_never_attaches(page: Page, local_app: ShinyAppProc) -> None:
    open_lifecycle_page(page, local_app)
    expect(page.locator("#box")).to_have_text("child 0")

    # n=1 renders slowly (2s); n=2 arrives quickly and must win. The slow
    # candidate's stale result never attaches and the mount keeps exactly one
    # presentation.
    page.click("#slow")
    page.wait_for_timeout(300)
    page.click("#rerender")
    expect(page.locator("#box")).to_have_text("child 2")
    page.wait_for_timeout(2500)
    expect(page.locator("#box")).to_have_text("child 2")
    snapshot = mount_snapshot(page, "#box")
    assert snapshot["views"] >= 1
    identity = page.evaluate(
        """() => window.widgetLifecycle.mountIdentity(
            document.querySelector('#box')
        )"""
    )
    assert identity["accepted_lease"] is not None


def test_cleanup_failure_removes_presentation_and_reports(
    page: Page, local_app: ShinyAppProc
) -> None:
    """
    A failing package-specific teardown adapter is reported, but the
    presentation is still removed and disposal settles.
    """
    errors: list[str] = []
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    open_lifecycle_page(page, local_app)
    expect(page.locator("#box")).to_have_text("child 0")

    page.evaluate(
        """() => {
            const el = document.querySelector('#box');
            const view = window.widgetLifecycle.acceptedViewFor(el);
            // An adapter that fails like a broken third-party destroy hook.
            view.destroy = () => { throw new Error('Injected teardown failure'); };
        }"""
    )
    page.click("#rerender")
    # The replacement still attaches and the mount returns to baseline.
    expect(page.locator("#box")).to_have_text("child 1")
    expect(page.locator("#snapshot")).to_have_text(BASELINE)
    assert any("error disposing replaced presentation" in err for err in errors), errors
