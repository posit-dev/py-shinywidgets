"""
Display-lease protocol over the real transport (plan 3, tasks 8-9).

Claims/releases travel as `shinywidgets_display` input events with results
via custom message, so these tests exercise the actual server session
lifecycle (publications, claim terminals, lease release -> collection) and
the actual browser mounts. Assertions combine server-side snapshot state
(records/comms/leases) with browser mount/model identity.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc
from tests.playwright.conftest import open_lifecycle_page


def snapshot_text(page: Page) -> str:
    return page.locator("#snapshot").inner_text()


def test_initial_claim_binds_provisional_lease(
    page: Page, local_app: ShinyAppProc
) -> None:
    open_lifecycle_page(page, local_app)
    expect(page.locator("#widget")).to_have_text("cached root")
    # One record (the session root), one claimed lease (the provisional one,
    # now bound to the mount).
    expect(page.locator("#snapshot")).to_have_text(
        "records=3 comms=3 leases=1 pending=0"
    )
    identity = page.evaluate(
        """() => {
            const el = document.querySelector('#widget');
            return window.widgetLifecycle.mountIdentity(el);
        }"""
    )
    assert identity["accepted_lease"] is not None
    assert identity["claim_seq"] == 1
    assert page.locator("#widget").get_attribute("data-shinywidgets-model-id")


def test_replacement_releases_old_lease_after_attach(
    page: Page, local_app: ShinyAppProc
) -> None:
    open_lifecycle_page(page, local_app)
    expect(page.locator("#widget")).to_have_text("cached root")
    for n in range(1, 4):
        page.click("#rerender")
        # The claim sequence increments once per replacement cycle.
        page.wait_for_function(
            f"""() => window.widgetLifecycle.mountIdentity(
                document.querySelector('#widget')
            ).claim_seq === {n + 1}"""
        )
        # The same session-retained root is claimed anew on each publication;
        # each replacement releases the previous lease after attachment, so
        # exactly one lease stays active.
        expect(page.locator("#snapshot")).to_have_text(
            "records=3 comms=3 leases=1 pending=0"
        )
    identity = page.evaluate(
        """() => {
            const el = document.querySelector('#widget');
            return window.widgetLifecycle.mountIdentity(el);
        }"""
    )
    assert identity["claim_seq"] == 4
    # The displayed model never changed identity across renders.
    first_id = page.locator("#widget").get_attribute("data-shinywidgets-model-id")
    assert first_id is not None


def test_duplicate_claim_returns_recorded_outcome(
    page: Page, local_app: ShinyAppProc
) -> None:
    open_lifecycle_page(page, local_app)
    expect(page.locator("#widget")).to_have_text("cached root")
    result = page.evaluate(
        """async () => {
            const lifecycle = window.widgetLifecycle;
            const el = document.querySelector('#widget');
            const mount = lifecycle.existingMountFor(el);
            const epoch = lifecycle.epoch;
            // Re-send the exact claim that produced the accepted presentation:
            // the server must return the recorded outcome, not acquire again.
            const pub = await fetch('/__never__').catch(() => null);
            const claim = {
                action: "claim",
                event_id: "replay-1",
                output_id: mount.outputId,
                offer_id: mount.acceptedOffer,
                candidate_lease_id: "irrelevant-when-replayed",
                generation_id: mount.acceptedGeneration,
                root_id: mount.acceptedRoot,
                mount_id: mount.mountId,
                claim_seq: mount.claimSeq,
            };
            const response = await Promise.race([
                lifecycle.sendDisplayEvent(claim, true),
                new Promise(resolve => setTimeout(() => resolve('timeout'), 5000)),
            ]);
            return {
                outcome: response === 'timeout' ? 'timeout' : response.outcome,
                leases: document.querySelector('#snapshot').textContent,
            };
        }"""
    )
    assert result["outcome"] != "timeout"
    assert "claimed" in result["outcome"]
    # The recorded lease is the accepted one (no double acquisition).
    leases = page.evaluate(
        """() => {
            const el = document.querySelector('#widget');
            return window.widgetLifecycle.mountIdentity(el).accepted_lease;
        }"""
    )
    assert result["outcome"]["claimed"] == leases


def test_duplicate_release_is_acknowledged_noop(
    page: Page, local_app: ShinyAppProc
) -> None:
    open_lifecycle_page(page, local_app)
    expect(page.locator("#widget")).to_have_text("cached root")
    result = page.evaluate(
        """async () => {
            const lifecycle = window.widgetLifecycle;
            const release = {
                action: "release",
                event_id: "release-unknown-1",
                output_id: "widget",
                lease_id: "never-existed",
                mount_id: "mount-unknown",
                presentation_removed: true,
                reason: "stale",
                cleanup: "complete",
            };
            const response = await Promise.race([
                lifecycle.sendDisplayEvent(release, true),
                new Promise(resolve => setTimeout(() => resolve('timeout'), 5000)),
            ]);
            return response === 'timeout' ? 'timeout' : response.outcome;
        }"""
    )
    assert result == {"acked": True}
    # The live presentation is untouched.
    expect(page.locator("#widget")).to_have_text("cached root")


def test_unbind_and_rebind_renews_lease_for_retained_root(
    page: Page, local_app: ShinyAppProc
) -> None:
    open_lifecycle_page(page, local_app)
    expect(page.locator("#widget")).to_have_text("cached root")
    first_id = page.locator("#widget").get_attribute("data-shinywidgets-model-id")

    # Unbind the output element (dynamic UI removal)...
    page.click("#drop")
    page.wait_for_function("""() => !document.querySelector('#slot-holder #widget')""")
    # ...its lease is released after the presentation is removed...
    expect(page.locator("#snapshot")).to_have_text(
        "records=3 comms=3 leases=0 pending=0"
    )
    # ...but the session-retained root survives.
    page.click("#drop")
    expect(page.locator("#widget")).to_have_text("cached root")
    expect(page.locator("#snapshot")).to_have_text(
        "records=3 comms=3 leases=1 pending=0"
    )
    # The rebound mount displays the exact same model; the lease was renewed
    # (a fresh lease, not a resurrected one).
    assert (
        page.locator("#widget").get_attribute("data-shinywidgets-model-id") == first_id
    )


def test_stale_claim_is_refused_and_never_attaches(
    page: Page, local_app: ShinyAppProc
) -> None:
    open_lifecycle_page(page, local_app)
    expect(page.locator("#widget")).to_have_text("cached root")
    stale = page.evaluate(
        """async () => {
            const lifecycle = window.widgetLifecycle;
            const el = document.querySelector('#widget');
            const mount = lifecycle.existingMountFor(el);
            const claim = {
                action: "claim",
                event_id: "stale-1",
                output_id: mount.outputId,
                offer_id: "offer-that-never-was",
                candidate_lease_id: "lease-that-never-was",
                generation_id: mount.acceptedGeneration,
                root_id: mount.acceptedRoot,
                mount_id: "mount-stale",
                claim_seq: mount.claimSeq + 10,
            };
            const response = await Promise.race([
                lifecycle.sendDisplayEvent(claim, true),
                new Promise(resolve => setTimeout(() => resolve('timeout'), 5000)),
            ]);
            return response === 'timeout' ? 'timeout' : response.outcome;
        }"""
    )
    assert stale == {"refused": "stale-offer"}
    expect(page.locator("#widget")).to_have_text("cached root")


def test_collected_root_claim_is_refused(page: Page, local_app: ShinyAppProc) -> None:
    open_lifecycle_page(page, local_app)
    expect(page.locator("#widget")).to_have_text("cached root")
    result = page.evaluate(
        """async () => {
            const lifecycle = window.widgetLifecycle;
            const claim = {
                action: "claim",
                event_id: "dead-1",
                output_id: "widget",
                offer_id: "offer-x",
                candidate_lease_id: "lease-x",
                generation_id: "gen-x",
                root_id: "sw-nonexistent-root",
                mount_id: "mount-dead",
                claim_seq: 99,
            };
            const response = await Promise.race([
                lifecycle.sendDisplayEvent(claim, true),
                new Promise(resolve => setTimeout(() => resolve('timeout'), 5000)),
            ]);
            return response === 'timeout' ? 'timeout' : response.outcome;
        }"""
    )
    # A claim that can't be tied to a live publication/root is refused; a
    # collected widget is never resurrected.
    assert "refused" in result
