from __future__ import annotations

from playwright.sync_api import Page, expect


def test_fileupload_preserves_uploaded_bytes(page: Page, local_app) -> None:
    page.goto(local_app.url)

    status = page.locator("#status")
    expect(status).to_have_text("empty", timeout=30000)

    with page.expect_file_chooser(timeout=30000) as chooser_info:
        page.locator("#uploader button.widget-upload.jupyter-button").click()
    chooser = chooser_info.value
    chooser.set_files(
        files=[
            {
                "name": "hello.txt",
                "mimeType": "text/plain",
                "buffer": b"hello shinywidgets",
            }
        ]
    )

    expect(page.locator("#status")).to_have_text("uploaded", timeout=30000)
    expect(page.locator("#name")).to_have_text("hello.txt", timeout=30000)
    expect(
        page.locator("#size")
    ).to_have_text(str(len(b"hello shinywidgets")), timeout=30000)
    expect(
        page.locator("#content")
    ).to_have_text("hello shinywidgets", timeout=30000)
