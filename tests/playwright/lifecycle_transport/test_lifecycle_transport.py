"""
Transport evidence for the lifecycle display-lease protocol (plan 3, task 1).

Establishes how the installed Shiny delivers `priority: "event"` input packets
sent in the same browser callback, and that a custom-message response is
delivered while widget output initialization is still pending. The protocol
carries a cumulative pending-event ledger so that a reactive input seeing
only the newest value still processes every pending operation.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect
from shiny.run import ShinyAppProc


def test_event_packets_sent_together_are_each_delivered(
    page: Page, local_app: ShinyAppProc
) -> None:
    page.goto(local_app.url)
    page.wait_for_function(
        """() => window.Shiny && Shiny.shinyapp && Shiny.shinyapp.isConnected()"""
    )
    page.evaluate(
        """() => {
            // Two distinct packets for the same input in one callback.
            Shiny.setInputValue("lifecycle_probe", {events: ["a"]}, {priority: "event"});
            Shiny.setInputValue("lifecycle_probe", {events: ["b"]}, {priority: "event"});
        }"""
    )
    # Installed Shiny 1.6 delivers each event-priority packet separately, so
    # the reactive effect observes both. The lease protocol still carries a
    # cumulative pending-event ledger so it stays correct if a transport ever
    # coalesces to the newest value.
    expect(page.locator("#values")).to_have_text(
        "{'events': ('a',)},{'events': ('b',)}"
    )
    expect(page.locator("#acks")).to_have_text("a,b")


def test_custom_message_response_delivered_for_event_input(
    page: Page, local_app: ShinyAppProc
) -> None:
    acks: list[str] = []
    page.expose_function("recordAck", lambda ack: acks.append(ack))
    page.goto(local_app.url)
    page.wait_for_function(
        """() => window.Shiny && Shiny.shinyapp && Shiny.shinyapp.isConnected()"""
    )
    page.evaluate(
        """() => {
            Shiny.addCustomMessageHandler("lifecycle_probe_ack", (msg) => {
                window.recordAck(JSON.parse(msg).ack);
            });
        }"""
    )
    page.evaluate(
        """() => {
            Shiny.setInputValue(
                "lifecycle_probe", {events: ["x", "y"]}, {priority: "event"}
            );
        }"""
    )
    # The acknowledgement custom messages are delivered (in order) while the
    # app also has widget output traffic in flight.
    expect(page.locator("#acks")).to_have_text("x,y")
    expect(page.locator("#widget")).to_contain_text("slow widget")
    assert acks == ["x", "y"]
