from __future__ import annotations

from playwright.sync_api import Page, expect


def test_altair_fills_explicit_output_height(page: Page, local_app) -> None:
    page.goto(local_app.url)
    marks = page.locator("#fixed svg.marks")
    expect(marks).to_be_visible(timeout=30000)

    box = marks.bounding_box()
    assert box is not None
    assert box["height"] > 250


def test_altair_selection_observers_fire(page: Page, local_app) -> None:
    page.goto(local_app.url)
    marks = page.locator("#observed svg.marks")
    expect(marks).to_be_visible(timeout=30000)
    expect(page.locator("#brushes")).to_have_text("brushes: 0")

    box = marks.bounding_box()
    assert box is not None
    page.mouse.move(box["x"] + 0.2 * box["width"], box["y"] + 0.2 * box["height"])
    page.mouse.down()
    page.mouse.move(
        box["x"] + 0.6 * box["width"], box["y"] + 0.6 * box["height"], steps=5
    )
    page.mouse.up()

    expect(page.locator("#brushes")).not_to_have_text("brushes: 0")
