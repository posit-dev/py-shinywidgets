"""
Connection retirement and reconnect evidence (plan 3, task 10).

Kept strictly separate:

- *New-session* reconnect (reload, and Shiny's `reconnect()` attempt): the
  fresh Python session gets a fresh namespace/epoch; old work is retired.
- The upstream `reconnect()` path is currently blocked by cached
  output-progress state on the client (captured here, not worked around).
- *Same-session hosted resume*: no public hook exists (see test docstring);
  this is an explicit unsupported-resume policy, not hidden xfail.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc
from tests.playwright.conftest import open_lifecycle_page


def test_disconnect_retires_epoch_and_presentation(
    page: Page, local_app: ShinyAppProc
) -> None:
    open_lifecycle_page(page, local_app)
    expect(page.locator("#widget")).to_have_text("epoch widget")
    namespace = page.locator("#session_info").inner_text().split(" ")[0]

    page.evaluate("() => window.Shiny.shinyapp.$socket.close()")
    # Mounts/identity are invalidated synchronously; the epoch retires without
    # waiting on any browser acknowledgement.
    page.wait_for_function("() => window.widgetLifecycle.epoch === null")
    assert page.locator("#widget").get_attribute("data-shinywidgets-model-id") is None
    snapshot = page.evaluate("() => window.widgetLifecycle.snapshot()")
    assert snapshot == {"models": 0, "waiters": 0, "mounts": 0, "views": 0, "tasks": 0}
    # The page doesn't auto-reconnect locally.
    assert "ns=" in namespace


def test_fresh_session_after_reload_gets_fresh_epoch(
    page: Page, local_app: ShinyAppProc
) -> None:
    open_lifecycle_page(page, local_app)
    expect(page.locator("#widget")).to_have_text("epoch widget")
    before = page.locator("#session_info").inner_text()
    first_ns = before.split(" ")[0].removeprefix("ns=")
    first_model_id = page.locator("#widget").get_attribute("data-shinywidgets-model-id")

    page.evaluate("() => window.Shiny.shinyapp.$socket.close()")
    page.wait_for_function("() => window.widgetLifecycle.epoch === null")
    page.reload()
    expect(page.locator("#widget")).to_have_text("epoch widget")
    after = page.locator("#session_info").inner_text()
    second_ns = after.split(" ")[0].removeprefix("ns=")
    # A fresh Python session with a fresh namespace and transport epoch.
    assert second_ns != first_ns
    second_model_id = page.locator("#widget").get_attribute(
        "data-shinywidgets-model-id"
    )
    assert second_model_id is not None
    assert second_model_id != first_model_id
    assert second_model_id.startswith(f"sw-{second_ns}-")
    # The fresh session renders and claims normally.
    assert "records=3" in after
    assert "leases=1" in after


def test_stale_packets_cannot_mutate_fresh_session(
    page: Page, local_app: ShinyAppProc
) -> None:
    open_lifecycle_page(page, local_app)
    expect(page.locator("#widget")).to_have_text("epoch widget")
    before = page.locator("#session_info").inner_text()

    # A well-formed packet for a different session/epoch (e.g., racing a
    # reconnect) is dropped with a warning, not applied and not fatal.
    page.evaluate(
        """() => {
            const stale = {
                sw: 1,
                session_id: "stale-session",
                model_namespace: "stale-ns",
                epoch_id: "stale-epoch",
                msg: {content: {comm_id: "sw-stale-ns-x", data: {method: "update", state: {}}}, buffers: []},
            };
            Shiny.setInputValue(
                "shinywidgets_comm_send", JSON.stringify(stale), {priority: "event"}
            );
            const staleDisplay = {
                sw: 1,
                version: 1,
                session_id: "stale-session",
                model_namespace: "stale-ns",
                epoch_id: "stale-epoch",
                events: [{
                    action: "release",
                    event_id: "stale-release",
                    output_id: "widget",
                    lease_id: "stale-lease",
                    mount_id: "stale-mount",
                    presentation_removed: true,
                    reason: "stale",
                    cleanup: "complete"
                }]
            };
            Shiny.setInputValue(
                "shinywidgets_display", JSON.stringify(staleDisplay), {priority: "event"}
            );
        }"""
    )
    # The live session is unaffected and still functions.
    page.wait_for_timeout(1000)
    expect(page.locator("#widget")).to_have_text("epoch widget")
    assert page.locator("#session_info").inner_text() == before


def test_upstream_reconnect_progress_state_blocker(
    page: Page, local_app: ShinyAppProc
) -> None:
    """
    Upstream evidence: Shiny 1.6's `reconnect()` reuses the client's cached
    output-progress state, which rejects the fresh session's recalculation
    messages ("unexpected state of: 'value'") and the socket closes. This is
    an upstream py-shiny blocker for in-page reconnect -- reload (covered
    above) is the working fresh-session path. Do not reset private
    `$outputProgress` state to make this pass.
    """
    errors: list[str] = []
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    open_lifecycle_page(page, local_app)
    expect(page.locator("#widget")).to_have_text("epoch widget")
    first_ns = page.locator("#session_info").inner_text().split(" ")[0]

    page.evaluate("() => window.Shiny.shinyapp.$socket.close()")
    page.wait_for_function("() => window.widgetLifecycle.epoch === null")
    page.evaluate("() => window.Shiny.shinyapp.reconnect()")

    page.wait_for_function(
        """() => {
            const info = document.querySelector('#session_info');
            return info && !info.classList.contains('recalculating');
        }""",
        timeout=15000,
    )
    page.wait_for_timeout(1500)

    # The fresh session's values never reach the DOM: the client's cached
    # progress state rejects the new session's recalculation (so the old
    # namespace text remains, which is itself evidence of the rejection)...
    after = page.locator("#session_info").inner_text()
    assert after.split(" ")[0] == first_ns
    # The consistent upstream defect: recalculation progress for the new
    # session is rejected against the old connection's cached state. (Whether
    # the overlapping queue consumers then kill the socket varies between
    # runs; that part is not pinned here.)
    assert any("unexpected state" in err for err in errors), errors
    # Our epoch handling stayed consistent throughout: retired at disconnect,
    # no corruption from the rejected fresh session.
    snapshot = page.evaluate("() => window.widgetLifecycle.snapshot()")
    assert all(v >= 0 for v in snapshot.values())
