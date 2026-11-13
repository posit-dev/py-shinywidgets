"""Browser checks for the rendered website (the site's test suite).

Serves ``website/_site`` under ``/py-shinywidgets/`` (the GitHub Pages subpath), so a
root-absolute URL anywhere in the site shows up as a 404. Each check gets a fresh page and
returns a list of problems; every check also fails on any HTTP status >= 400, failed
same-origin request, or uncaught page error it sees.

    uv run --no-sync python website/_tools/check_site.py [--only NAME ...]
"""

from __future__ import annotations

import argparse
import functools
import http.server
import re
import socket
import sys
import threading
import urllib.parse
from collections.abc import Callable
from pathlib import Path

import yaml
from playwright.sync_api import Browser, Locator, Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

SITE = Path(__file__).resolve().parents[1] / "_site"
PREFIX = "/py-shinywidgets"
SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")

CheckFn = Callable[[Page, str], list[str]]
CHECKS: dict[str, CheckFn] = {}

# Problems seen by monitored pages during the current check.
observed: list[str] = []


def check(name: str) -> Callable[[CheckFn], CheckFn]:
    def register(fn: CheckFn) -> CheckFn:
        CHECKS[name] = fn
        return fn

    return register


def open_page(page: Page, **context_options: object) -> Page:
    """A monitored page in a new browser context (e.g. ``color_scheme="dark"``)."""
    browser = page.context.browser
    assert browser is not None
    return new_page(browser, **context_options)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="+", metavar="NAME", choices=sorted(CHECKS))
    args = parser.parse_args()
    if not (SITE / "index.html").exists():
        print(f"FAIL setup: {SITE} has no index.html; run `make docs` first")
        return 1

    names = args.only or list(CHECKS)
    server, base = serve(SITE)
    failures = 0
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for name in names:
                observed.clear()
                page = new_page(browser)
                try:
                    problems = CHECKS[name](page, base)
                except Exception as e:  # a crashing check is a failing check
                    problems = [f"{type(e).__name__}: {e}"]
                problems = problems + sorted(set(observed))
                for problem in problems:
                    print(f"FAIL {name}: {problem}")
                print(f"{'ok  ' if not problems else 'FAIL'} {name}")
                failures += bool(problems)
                for context in browser.contexts:
                    context.close()
            browser.close()
    finally:
        server.shutdown()
    return 1 if failures else 0


# Checks -------------------------------------------------------------------------------


@check("smoke")
def smoke(page: Page, base: str) -> list[str]:
    response = page.goto(base + "index.html")
    if response is None or response.status != 200:
        return [f"index.html returned {response and response.status}"]
    return []


@check("theme")
def theme(page: Page, base: str) -> list[str]:
    problems: list[str] = []
    for scheme, expected in [
        ("light", "rgb(251, 251, 253)"),
        ("dark", "rgb(7, 8, 12)"),
    ]:
        themed = open_page(page, color_scheme=scheme)
        themed.goto(
            base + "widgets/plotly/index.html"
        )  # docs pages follow the OS theme
        bg = body_background(themed)
        if bg != expected:
            problems.append(f"{scheme}: body background {bg}, expected {expected}")
    return problems


WIDGET_GROUPS = [
    "Charts",
    "Tables & grids",
    "Data exploration",
    "Maps & geospatial",
    "3D",
    "Scientific",
    "Networks",
    "Input & drawing",
]

SIDEBAR_SECTIONS_JS = """
() => [...document.querySelectorAll('#quarto-sidebar li.sidebar-item-section')].map(li => ({
  text: li.querySelector(':scope > .sidebar-item-container .sidebar-item-text').textContent.trim(),
  parent: li.parentElement.closest('li.sidebar-item-section')
    ?.querySelector(':scope > .sidebar-item-container .sidebar-item-text').textContent.trim() ?? null,
  expanded: li.querySelector(':scope > ul').classList.contains('show'),
}))
"""


@check("sidebar")
def sidebar(page: Page, base: str) -> list[str]:
    problems: list[str] = []
    page = open_page(
        page, color_scheme="light", viewport={"width": 1440, "height": 900}
    )
    page.goto(base + "widgets/k3d/index.html")
    sections = page.evaluate(SIDEBAR_SECTIONS_JS)
    groups = [s["text"] for s in sections if s["parent"] == "Widgets"]
    if groups != WIDGET_GROUPS:
        problems.append(f"Widgets groups are {groups}")
    expanded = {s["text"]: s["expanded"] for s in sections}
    if not expanded.get("3D"):
        problems.append("3D group is not expanded on the K3D page")
    if expanded.get("Charts", True):
        problems.append("Charts group is expanded on the K3D page")
    active = page.locator("#quarto-sidebar a.sidebar-link.active")
    if active.count() != 1 or active.inner_text().strip() != "K3D":
        problems.append(f"active sidebar links: {active.all_inner_texts()}")
    box = page.locator("#quarto-sidebar").bounding_box()
    if box is None or box["x"] != 0:
        problems.append(f"sidebar left edge at {box and box['x']}, expected 0")
    bg = page.evaluate(
        "getComputedStyle(document.querySelector('#quarto-sidebar')).backgroundColor"
    )
    if bg != "rgb(245, 246, 249)":
        problems.append(f"sidebar background {bg}")
    return problems


@check("pages")
def pages(page: Page, base: str) -> list[str]:
    problems: list[str] = []
    page.goto(base + "widgets/plotly/index.html")
    hrefs = page.evaluate(
        "[...document.querySelectorAll('#quarto-sidebar a.sidebar-link[href]')].map(a => a.href)"
    )
    if len(hrefs) != 57:  # 14 guide pages + 43 widget guides
        problems.append(f"{len(hrefs)} sidebar links, expected 57")
    for href in dict.fromkeys(hrefs):
        page.goto(href)
        h1s = page.locator("h1").count()
        if h1s != 1:
            problems.append(f"{href.removeprefix(base)} has {h1s} <h1> elements")
    # Quarto's draft-mode "gone" leaves an empty stub page and strips every link to it.
    if "<body" in page.request.get(base + "widgets/vitessce/index.html").text():
        problems.append(
            "widgets/vitessce/index.html has content (it should be a draft)"
        )
    linking = [
        p.relative_to(SITE)
        for p in SITE.rglob("*.html")
        if "vitessce/index.html" in p.read_text()
    ]
    if linking:
        problems.append(f"pages link to the vitessce draft: {linking}")
    return problems


@check("anchors")
def anchors(page: Page, base: str) -> list[str]:
    """Every in-site link's #fragment names an element on its target page (read from disk)."""
    ids: dict[Path, set[str]] = {}

    def ids_of(path: Path) -> set[str]:
        if path not in ids:
            ids[path] = (
                set(re.findall(r'\sid="([^"]+)"', path.read_text()))
                if path.exists()
                else set()
            )
        return ids[path]

    problems: list[str] = []
    for html in sorted(SITE.rglob("*.html")):
        if "site_libs" in html.parts:
            continue
        for href in re.findall(r'<a [^>]*href="([^"]*#[^"]+)"', html.read_text()):
            target, _, frag = href.partition("#")
            if SCHEME.match(target) or target.startswith("/"):
                continue
            target_file = (html.parent / target).resolve() if target else html
            if target_file.suffix == ".html" and urllib.parse.unquote(
                frag
            ) not in ids_of(target_file):
                problems.append(
                    f"{html.relative_to(SITE)}: #{frag} not found in {target or 'this page'}"
                )
    return problems


SOURCE_LINK = re.compile(
    r"^https://github\.com/posit-dev/py-shinywidgets/blob/main/shinywidgets/_render_widget\.py#L\d+-L\d+$"
)


@check("reference")
def reference(page: Page, base: str) -> list[str]:
    problems: list[str] = []
    page.goto(base + "reference/render_plotly.html")
    if page.locator(".ref-kind").first.inner_text().strip() != "class":
        problems.append("render_plotly's kind badge is not 'class'")
    if not page.locator(".ref-summary").first.inner_text().strip():
        problems.append("render_plotly has no summary line")
    href = page.locator("a.ref-source").first.get_attribute("href") or ""
    if not SOURCE_LINK.match(href):
        problems.append(f"source link is {href!r}")
    if page.locator("dl dt .parameter-name").count() == 0:
        problems.append("parameters are not a description list")
    if "hover()" not in " ".join(page.locator("table").all_inner_texts()):
        problems.append("methods table does not list hover()")
    # Every reference page, including the index's summary table, is free of raw Sphinx roles.
    for html in sorted((SITE / "reference").glob("*.html")):
        page.goto(base + f"reference/{html.name}")
        if role := re.search(
            r":(?:py:)?(?:meth|func|class|attr|obj|data):",
            page.locator("main").inner_text(),
        ):
            problems.append(f"reference/{html.name} shows a raw {role.group(0)} role")
    page.goto(base + "reference/render_plotly.html")
    if any(h.is_visible() for h in page.locator("#title-block-header").all()):
        problems.append("#title-block-header is visible")
    visible_h1 = [h for h in page.locator("h1").all() if h.is_visible()]
    if len(visible_h1) != 1:
        problems.append(f"{len(visible_h1)} visible <h1> elements")
    page.goto(base + "reference/reactive_read.html")
    if page.locator(".ref-kind").first.inner_text().strip() != "function":
        problems.append("reactive_read's kind badge is not 'function'")
    return problems


@check("gallery")
def gallery(page: Page, base: str) -> list[str]:
    problems: list[str] = []
    page.goto(base + "gallery/index.html")
    items = page.locator(".quarto-listing .quarto-grid-item")
    if items.count() != 30:
        problems.append(f"{items.count()} gallery items, expected 30")
    # Cards show a crop of each app's widgets (img/card.webp), not the whole-app screenshot.
    srcs = page.evaluate(
        "[...document.querySelectorAll('.quarto-grid-item img.thumbnail-image')].map(i => i.getAttribute('src'))"
    )
    if whole := [s for s in srcs if not s.endswith("/img/card.webp")]:
        problems.append(
            f"{len(whole)} gallery cards don't use their cropped card image, e.g. {whole[0]}"
        )
    # Category labels read like "3D (3)"; "All" is Quarto's reset entry.
    labels = page.locator(".quarto-listing-category .category").all_inner_texts()
    shown = {re.sub(r"\s*\(\d+\)$", "", t).strip() for t in labels} - {"All"}
    expected = gallery_categories()
    if shown != expected:
        problems.append(f"category filter {sorted(shown)}, expected {sorted(expected)}")
    page.locator(".quarto-listing-category .category", has_text="3D").first.click()
    page.wait_for_timeout(300)
    visible = [i for i in items.all() if i.is_visible()]
    untagged = [
        i.locator(".listing-title").inner_text()
        for i in visible
        if "3D" not in i.inner_text()
    ]
    if not visible or untagged:
        problems.append(
            f"after filtering to 3D: {len(visible)} visible, untagged: {untagged}"
        )
    return problems


@check("changelog")
def changelog(page: Page, base: str) -> list[str]:
    page.goto(base + "changelog.html")
    problems = (
        []
        if "0.8.2" in page.locator("main").inner_text()
        else ["changelog has no 0.8.2 entry"]
    )
    if page.locator("h1").count() != 1:
        problems.append(f"changelog has {page.locator('h1').count()} <h1> elements")
    return problems


LANDING_TABS = [
    "plotly", "altair", "mosaic", "bokeh", "holoviews", "matplotlib",
    "itables", "reactable", "lonboard", "maplibre", "any widget",
]  # fmt: skip
LANDING_BG = "rgb(7, 8, 12)"
LIGHT_BG = "rgb(251, 251, 253)"

IMAGES_LOADED_JS = "[...document.querySelectorAll('.sw-landing img')].filter(i => i.offsetParent && i.complete && i.naturalWidth === 0).map(i => i.src)"


@check("landing")
def landing(page: Page, base: str) -> list[str]:
    problems: list[str] = []
    for scheme in ("light", "dark"):
        themed = open_page(
            page, color_scheme=scheme, viewport={"width": 1440, "height": 900}
        )
        themed.goto(base + "index.html")
        if (bg := body_background(themed)) != LANDING_BG:
            problems.append(f"{scheme}: landing body background {bg}")

    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(base + "index.html")
    if (
        h1 := page.locator("h1").first.inner_text().strip()
    ) != "Bring your Jupyter widgets to Shiny.":
        problems.append(f"hero H1 is {h1!r}")
    header_bg = page.evaluate(
        "getComputedStyle(document.querySelector('#quarto-header .navbar')).backgroundColor"
    )
    if not re.match(r"rgba\(.*, 0\)$|transparent", header_bg):
        problems.append(
            f"header background at the top is {header_bg}, expected transparent"
        )

    h2 = page.locator(".sw-landing h2").first.inner_text()
    if "integrations" not in h2:
        problems.append(f"section 2 heading is {h2!r}")
    cats = page.locator(".sw-landing a.cat").all()
    if len(cats) != 8:
        problems.append(f"{len(cats)} category cards, expected 8")
    for cat in cats:
        href = cat.evaluate("a => a.href")
        if page.request.get(href).status != 200:
            problems.append(f"category card links to {href}, which isn't a page")

    tabs = page.locator(".sw-landing .tab")
    if (labels := tabs.all_inner_texts()) != LANDING_TABS:
        problems.append(f"tab labels {labels}")
    for i in range(tabs.count()):
        tabs.nth(i).click()
        for state in page.locator("#ctrl button").all():
            if state.is_visible():
                state.click()
                page.wait_for_timeout(150)
        page.wait_for_load_state("networkidle")
        if broken := page.evaluate(IMAGES_LOADED_JS):
            problems.append(f"tab {LANDING_TABS[i]}: images failed to load: {broken}")

    picker = page.locator("#picker li")
    if picker.count() != 7:
        problems.append(f"{picker.count()} showcases in the stage, expected 7")
    else:
        picker.nth(5).click()
        if "Terrain explorer" not in page.locator("#picker li.on").inner_text():
            problems.append("clicking the 6th showcase doesn't select Terrain explorer")
        page.wait_for_load_state("networkidle")
        if broken := page.evaluate(IMAGES_LOADED_JS):
            problems.append(f"stage images failed to load: {broken}")

    # Keyboard: stage items are focusable, Enter selects one, and focus pauses autoplay.
    page.goto(base + "index.html")
    item = page.locator("#picker li button").nth(2)
    if item.count() == 0:
        problems.append("stage items aren't keyboard-focusable buttons")
    else:
        item.focus()
        page.keyboard.press("Enter")
        if "World development" not in page.locator("#picker li.on").inner_text():
            problems.append(
                "Enter on the 3rd stage item doesn't select World development"
            )
        if "paused" not in (page.locator("#stage").get_attribute("class") or ""):
            problems.append("keyboard focus in the stage doesn't pause autoplay")

    # A visitor who picks light on a docs page still gets the dark landing page, and
    # their docs pages stay light.
    docs = open_page(page, color_scheme="dark", viewport={"width": 1440, "height": 900})
    docs.goto(base + "widgets/plotly/index.html")
    docs.locator(".quarto-color-scheme-toggle").first.click()
    if (bg := body_background(docs)) != LIGHT_BG:
        problems.append(f"toggling to light on a docs page gives body background {bg}")
    docs.goto(base + "index.html")
    if (bg := body_background(docs)) != LANDING_BG:
        problems.append(f"after choosing light, the landing background is {bg}")
    docs.goto(base + "widgets/plotly/index.html")
    if (bg := body_background(docs)) != LIGHT_BG:
        problems.append(
            f"after visiting the landing page, docs background is {bg} (light choice lost)"
        )
    return problems


@check("motion")
def motion(page: Page, base: str) -> list[str]:
    problems: list[str] = []
    calm = open_page(
        page, reduced_motion="reduce", viewport={"width": 1440, "height": 900}
    )
    calm.goto(base + "index.html")
    names = calm.evaluate(
        "[...document.querySelectorAll('.sw-landing .col')].map(c => getComputedStyle(c).animationName)"
    )
    if not names or set(names) != {"none"}:
        problems.append(f"hero wall columns animate under reduced motion: {set(names)}")
    before = calm.locator("#picker li.on").inner_text()
    calm.wait_for_timeout(8000)
    if calm.locator("#picker li.on").inner_text() != before:
        problems.append("the stage auto-advances under reduced motion")

    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(base + "index.html")
    first = page.locator("#picker li.on").inner_text()
    page.wait_for_timeout(8000)
    if page.locator("#picker li.on").inner_text() == first:
        problems.append("the stage doesn't auto-advance with motion allowed")
    return problems


@check("mobile")
def mobile(page: Page, base: str) -> list[str]:
    problems: list[str] = []
    phone = open_page(
        page, viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
    )
    # Every page, not a sample: one long inline-code span is enough to widen a page.
    paths = sorted(
        str(p.relative_to(SITE))
        for p in SITE.rglob("*.html")
        if "site_libs" not in p.parts and "<body" in p.read_text()
    )
    for path in paths:
        phone.goto(base + path, wait_until="domcontentloaded")
        phone.wait_for_timeout(100)
        width = phone.evaluate("document.documentElement.scrollWidth")
        if width != 390:
            problems.append(
                f"{path} scrolls horizontally at 390px (scrollWidth {width})"
            )
    phone.goto(base + "widgets/plotly/index.html")
    if not phone.locator(".quarto-btn-toggle").first.is_visible():
        problems.append("the sidebar toggle isn't visible on a guide page at 390px")
    return problems


@check("examples")
def examples(page: Page, base: str) -> list[str]:
    problems: list[str] = []
    ex = open_page(page, permissions=["clipboard-read", "clipboard-write"])
    # Popups go to shinylive.io; answer locally so the check runs offline.
    ex.context.route(
        "https://shinylive.io/**",
        lambda route: route.fulfill(
            status=200, content_type="text/html", body="<html></html>"
        ),
    )
    ex.goto(base + "widgets/plotly/index.html")
    if ex.locator(".sw-example").count() == 0:
        return ["widgets/plotly has no .sw-example blocks"]
    if ex.evaluate(
        "[...document.querySelectorAll('.sw-example .code-copy-button')]"
        ".some(b => getComputedStyle(b).display !== 'none')"
    ):
        problems.append("Quarto's copy button is visible inside an example block")

    block = ex.locator(".sw-example").first
    toggle = block.locator(".sw-example-toggle")
    bar = block.locator(".sw-example-bar")
    code = block.locator(".sw-example-code")
    height = bar.evaluate("el => el.offsetHeight")

    def collapsed() -> bool:
        return "sw-collapsed" in (block.get_attribute("class") or "")

    toggle.click()
    if not collapsed() or toggle.get_attribute("aria-expanded") != "false":
        problems.append("clicking the chevron didn't collapse the block")
    if code.is_visible():
        problems.append("collapsed code is still visible")
    if bar.evaluate("el => el.offsetHeight") != height:
        problems.append("the bar changed size when collapsing")
    block.locator(".sw-example-meta").click()
    if collapsed():
        problems.append("clicking empty bar space didn't expand the block")
    block.locator(".sw-example-file").evaluate(
        "a => a.addEventListener('click', e => e.preventDefault(), {once: true})"
    )
    block.locator(".sw-example-file").click()
    if collapsed():
        problems.append("clicking the file link toggled the block")

    toggle.click()  # copy and Shinylive must work while collapsed
    copy = block.locator('[data-action="copy"]')
    copy.click()
    try:
        block.locator('[data-action="copy"][title="Copied!"]').wait_for(
            state="attached", timeout=1000
        )
    except PlaywrightTimeoutError:
        problems.append("the copy button didn't say Copied!")
    copied = ex.evaluate("navigator.clipboard.readText()")
    if copied != code.locator("code").first.text_content():
        problems.append("copy didn't put the block's code on the clipboard")

    problems += shinylive_popup(ex, block.locator('[data-action="shinylive"]'))

    ex.goto(base + "guide/any-widget/index.html")
    multi = ex.locator(
        '.sw-example:has(.sw-example-extra:text("sparkline_widget.py"))'
    ).first
    problems += shinylive_popup(
        ex, multi.locator('[data-action="shinylive"]'), "sparkline_widget.py"
    )

    ex.goto(base + "widgets/maplibre/index.html")
    prose = ex.locator("a.sw-shinylive-link").first
    if prose.count() == 0:
        problems.append("widgets/maplibre has no prose Shinylive link")
    else:
        problems += shinylive_popup(ex, prose)

    ex.goto(base + "gallery/showcases/brain-atlas-explorer/index.html")
    if ex.locator('img[src$="img/hero.webp"]').count() == 0:
        problems.append("brain-atlas-explorer: hero screenshot missing")
    if ex.locator("code", has_text="uv run --with nibabel shiny run app.py").count() == 0:
        problems.append("brain-atlas-explorer: run command block missing")
    source = ex.locator('a[href$="/app.py"]:not(.sw-shinylive-link)')
    if source.count() != 1:
        problems.append("brain-atlas-explorer: plain app.py source link missing")
    showcase = ex.locator("a.sw-shinylive-link")
    if showcase.count() != 1:
        problems.append("brain-atlas-explorer: Shinylive link missing")
    else:
        problems += shinylive_popup(ex, showcase.first)

    for scheme in ["light", "dark"]:
        themed = open_page(page, color_scheme=scheme)
        themed.goto(base + "widgets/plotly/index.html")
        colors = themed.evaluate(
            "[getComputedStyle(document.querySelector('.sw-example-bar')).backgroundColor,"
            " getComputedStyle(document.querySelector('.sw-example-file')).color]"
        )
        if colors != ["rgb(21, 24, 36)", "rgb(124, 242, 201)"]:
            problems.append(f"{scheme}: bar/file-link colors are {colors}")
    return problems


# Helpers ------------------------------------------------------------------------------


def shinylive_popup(
    page: Page, trigger: Locator, extra: str | None = None
) -> list[str]:
    """Click `trigger`, and check the shinylive.io URL it opens carries the page's bundle."""
    key = trigger.get_attribute("data-example")
    with page.context.expect_page() as popup_info:
        trigger.click()
    url = popup_info.value.url
    popup_info.value.close()
    prefix = "https://shinylive.io/py/editor/#code="
    if not url.startswith(prefix):
        return [f"{key}: Shinylive opened {url}"]
    files = page.evaluate(
        "h => JSON.parse(LZString.decompressFromEncodedURIComponent(h))",
        url[len(prefix) :],
    )
    bundle = page.evaluate(
        "k => JSON.parse(document.getElementById('sw-example-bundles').textContent)[k]",
        key,
    )
    names = [f["name"] for f in files]
    problems: list[str] = []
    if files != bundle or names[0] != "app.py" or names[-1] != "requirements.txt":
        problems.append(f"{key}: Shinylive files {names} don't match the page's bundle")
    if extra is not None and extra not in names:
        problems.append(f"{key}: Shinylive files {names} are missing {extra}")
    return problems


def gallery_categories() -> set[str]:
    """Every category named in the gallery pages' front matter."""
    out: set[str] = set()
    for md in (SITE.parent / "gallery").glob("*/*/index.md"):
        fm = re.match(r"---\n(.*?)\n---\n", md.read_text(), re.S)
        out.update((yaml.safe_load(fm.group(1)) if fm else {}).get("categories", []))
    return out


def body_background(page: Page) -> str:
    return page.evaluate("getComputedStyle(document.body).backgroundColor")


def new_page(browser: Browser, **context_options: object) -> Page:
    context = browser.new_context(**context_options)  # pyright: ignore[reportArgumentType]
    page = context.new_page()
    page.set_default_timeout(10_000)
    page.on("pageerror", lambda e: observed.append(f"page error on {page.url}: {e}"))
    page.on(
        "response",
        lambda r: (
            observed.append(f"HTTP {r.status}: {r.url}") if r.status >= 400 else None
        ),
    )

    def on_failed(request) -> None:  # noqa: ANN001
        # ERR_ABORTED is the browser cancelling a load because the check navigated away.
        if request.url.startswith("http://127.0.0.1") and "ERR_ABORTED" not in (
            request.failure or ""
        ):
            observed.append(f"request failed: {request.url} ({request.failure})")

    page.on("requestfailed", on_failed)
    return page


class Server(http.server.ThreadingHTTPServer):
    request_queue_size = (
        128  # the default (5) resets connections when a page loads many images
    )
    daemon_threads = True


class PrefixHandler(http.server.SimpleHTTPRequestHandler):
    """Serves the site only under PREFIX, like a GitHub Pages project site."""

    def send_head(self):  # noqa: ANN201
        if not (self.path == PREFIX or self.path.startswith(PREFIX + "/")):
            self.send_error(404, "outside the site prefix")
            return None
        self.path = self.path[len(PREFIX) :] or "/"
        return super().send_head()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass


def serve(root: Path) -> tuple[Server, str]:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    handler = functools.partial(PrefixHandler, directory=str(root))
    server = Server(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{port}{PREFIX}/"


if __name__ == "__main__":
    sys.exit(main())
