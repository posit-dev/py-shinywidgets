from shinywidgets._dependencies import extension_urls_to_dependencies


def test_websocket_extension_urls_keep_at_signs() -> None:
    deps = extension_urls_to_dependencies(
        ["https://example.invalid/widget@1.0.0/index.js"],
        ["https://example.invalid/widget@1.0.0/style.css"],
    )
    urls = [
        asset.get("src", asset.get("href"))
        for dep in deps
        for asset in dep.as_dict()["script"] + dep.as_dict()["stylesheet"]
    ]

    assert urls == [
        "https://example.invalid/widget@1.0.0/index.js",
        "https://example.invalid/widget@1.0.0/style.css",
    ]
