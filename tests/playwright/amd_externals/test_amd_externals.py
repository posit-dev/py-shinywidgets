import json
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import Page, Route
from shiny.html_dependencies import require_deps
from shinywidgets._dependencies import amd_require_config


def test_widgets_load_their_own_amd_and_umd_siblings(
    page: Page, tmp_path: Path
) -> None:
    bundles = {
        "amd-widget": 'define(function(){return {build:"amd-build"}});',
        "umd-widget": """
            (function(global, factory) {
                if (typeof define === "function" && define.amd)
                    define(["exports"], factory);
                else
                    factory(global.THREE = {});
            })(this, function(exports) { exports.build = "umd-build"; });
        """,
    }
    configs: list[dict[str, object]] = []
    for name, bundle in bundles.items():
        module_dir = tmp_path / name
        module_dir.mkdir()
        (module_dir / "index.js").write_text(
            'define(["three"], function(three) { return three; });',
            encoding="utf-8",
        )
        (module_dir / "three.js").write_text(bundle, encoding="utf-8")
        config, _ = amd_require_config(name, str(module_dir), f"/{name}")
        configs.append(config)

    def serve_bundle(route: Route) -> None:
        path = urlparse(route.request.url).path
        if path == "/":
            route.fulfill(content_type="text/html", body="<html></html>")
        else:
            route.fulfill(
                content_type="application/javascript",
                path=tmp_path / path.lstrip("/"),
            )

    page.route("http://amd-externals.test/**", serve_bundle)
    page.goto("http://amd-externals.test/")
    require_dir = Path(require_deps().source_path_map()["source"])
    page.add_script_tag(path=require_dir / "require.min.js")
    for config in configs:
        page.add_script_tag(content=f"window.require.config({json.dumps(config)});")

    builds = page.evaluate(
        """() => new Promise((resolve, reject) => {
            window.require(["amd-widget", "umd-widget"], (amd, umd) => {
                resolve({
                    amd: amd.build,
                    umd: umd.build,
                    distinct: amd !== umd
                });
            }, reject);
        })"""
    )

    assert builds == {"amd": "amd-build", "umd": "umd-build", "distinct": True}
