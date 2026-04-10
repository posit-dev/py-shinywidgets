from __future__ import annotations

from playwright.sync_api import Page, expect


def test_buffer_transport_round_trip(page: Page, local_app) -> None:
    page.goto(local_app.url)

    update_status = page.locator("#update_status")
    update_payload = page.locator("#update_payload")
    custom_status = page.locator("#custom_status")
    custom_payload = page.locator("#custom_payload")

    expect(update_status).to_have_text("empty", timeout=30000)
    expect(update_payload).to_have_text("none", timeout=30000)
    expect(custom_status).to_have_text("empty", timeout=30000)
    expect(custom_payload).to_have_text("none", timeout=30000)

    page.get_by_test_id("update-buffer-button").click()
    expect(update_status).to_have_text("14 bytes", timeout=30000)
    expect(update_payload).to_have_text("00000UPDATE000", timeout=30000)
    expect(custom_status).to_have_text("empty", timeout=30000)
    expect(custom_payload).to_have_text("none", timeout=30000)

    page.get_by_test_id("custom-buffer-button").click()
    expect(custom_status).to_have_text("6 bytes", timeout=30000)
    expect(custom_payload).to_have_text("CUSTOM", timeout=30000)
    expect(update_status).to_have_text("14 bytes", timeout=30000)
    expect(update_payload).to_have_text("00000UPDATE000", timeout=30000)
