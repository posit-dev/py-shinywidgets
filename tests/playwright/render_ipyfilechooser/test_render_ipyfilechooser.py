from __future__ import annotations

from playwright.sync_api import Page, expect
from tests.playwright.conftest import (
    assert_no_unexpected_errors,
    client_models,
    collect_errors,
    expose_manager,
    wait_for_stable_model_view_count,
)

# The ipyfilechooser VBox root (its layout width drives the rendered width)
CHOOSER_ROOT = "#chooser .widget-box.widget-vbox"
# The chooser is a collapsed dialog: the file listing is hidden until the
# Select button opens it (and a second click confirms the selection)
DIRCONTENT = "#chooser .widget-select select"
SELECT_BUTTON = "#chooser button"


def open_dialog(page: Page) -> None:
    page.locator(SELECT_BUTTON, has_text="Select").click()
    expect(page.locator(DIRCONTENT)).to_be_visible()


def test_filechooser_renders(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator(CHOOSER_ROOT)).to_be_visible(timeout=30000)
    # The dialog starts collapsed: just the Select button and label
    expect(page.locator(DIRCONTENT)).to_be_hidden()

    open_dialog(page)
    # The fixture directory's entries are listed
    dircontent = page.locator(DIRCONTENT)
    expect(dircontent.locator("option", has_text="aaa.txt")).to_have_count(1)
    expect(dircontent.locator("option", has_text="bbb.csv")).to_have_count(1)

    assert_no_unexpected_errors(errors, failed_requests)


def test_filechooser_selection_roundtrips_to_python(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator("#selected")).to_have_text("none", timeout=30000)

    # Pick a file in the listing, then confirm with the Select button: the
    # button's on_click reaches Python over the comm, where the
    # register_callback() callback feeds `fc.selected` into a reactive.value
    open_dialog(page)
    page.locator(DIRCONTENT).select_option("aaa.txt")
    page.locator(SELECT_BUTTON, has_text="Select").click()
    expect(page.locator("#selected")).to_contain_text("aaa.txt", timeout=30000)
    # Confirming closes the dialog and relabels the button
    expect(page.locator(DIRCONTENT)).to_be_hidden()
    expect(page.locator(SELECT_BUTTON, has_text="Change")).to_be_visible()

    # A second selection updates it again (the button keeps its "Change"
    # label while the dialog is reopened and re-confirmed)
    page.locator(SELECT_BUTTON, has_text="Change").click()
    expect(page.locator(DIRCONTENT)).to_be_visible()
    page.locator(DIRCONTENT).select_option("bbb.csv")
    page.locator(SELECT_BUTTON, has_text="Change").click()
    expect(page.locator("#selected")).to_contain_text("bbb.csv", timeout=30000)

    assert_no_unexpected_errors(errors, failed_requests)


def test_filechooser_rerender_lifecycle(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.route("**/output.js", expose_manager)
    page.goto(local_app.url)

    expect(page.locator(CHOOSER_ROOT)).to_be_visible(timeout=30000)
    expect(page.locator("#render_count")).to_have_text("0")

    for i in range(1, 4):
        old_root = page.locator(CHOOSER_ROOT).first.element_handle()
        page.click("#rerender")
        expect(page.locator("#render_count")).to_have_text(str(i))
        page.wait_for_function("(el) => !el.isConnected", arg=old_root)
        expect(page.locator(CHOOSER_ROOT)).to_be_visible(timeout=30000)

    # Re-rendering replaces the widget; the retired tree's views must be
    # disposed and its models dropped (the only VBoxModels left are the two
    # chooser outputs, one view each)
    expect(page.locator(CHOOSER_ROOT)).to_have_count(1)
    assert wait_for_stable_model_view_count(page, "VBoxModel") == 2
    vbox_models = [m for m in client_models(page) if m["name"] == "VBoxModel"]
    assert len(vbox_models) == 2
    assert sum(m["views"] for m in vbox_models) == 2

    assert not any("widget is not attached" in err.lower() for err in errors)
    assert not any("no comm channel" in err.lower() for err in errors)
    assert_no_unexpected_errors(errors, failed_requests)


def test_filechooser_sizing(page: Page, local_app) -> None:
    errors, failed_requests = collect_errors(page)
    page.goto(local_app.url)

    expect(page.locator(CHOOSER_ROOT)).to_be_visible(timeout=30000)

    # A default-constructed chooser keeps ipyfilechooser's own 500px default
    # width (the import-time default Layout is swapped for a per-instance copy)
    box = page.locator(CHOOSER_ROOT).bounding_box()
    assert box is not None
    assert abs(box["width"] - 500) <= 1

    # The chooser is a form control: it keeps its natural height instead of
    # stretching to fill its 600px card
    assert box["height"] < 500

    # A user-supplied layout width wins
    wide = page.locator("#wide .widget-box.widget-vbox").bounding_box()
    assert wide is not None
    assert abs(wide["width"] - 700) <= 1

    assert_no_unexpected_errors(errors, failed_requests)
