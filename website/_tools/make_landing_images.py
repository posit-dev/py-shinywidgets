"""Generate the landing page's images, and the gallery's card images, from tracked screenshots.

    uv run --no-sync python website/_tools/make_landing_images.py           # (re)write images
    uv run --no-sync python website/_tools/make_landing_images.py --check   # size budget + references

Every image is cut from a screenshot that a page already shows, so re-shooting a guide's
screenshots and re-running this keeps the landing page and gallery cards in sync. Gallery
cards are written beside each app's page as img/card.webp (its front matter `image:`). Crop boxes are
(left, top, right, bottom) fractions of the source image, chosen so small cards show the
widget rather than app chrome.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from PIL import Image

WEBSITE = Path(__file__).resolve().parents[1]
OUT = WEBSITE / "assets/landing/img"
DATA_JS = WEBSITE / "assets/landing/landing-data.js"
BUDGET_BYTES = 4 * 1024 * 1024
QUALITY = 78
WALL_WIDTH = 640
MAX_WIDTH = 1400

Box = tuple[float, float, float, float]
FULL: Box = (0.0, 0.0, 1.0, 1.0)

# Hero wall: guide heroes, in the order the wall's six columns take them.
WALL = [
    "datashader", "keplergl", "maplibre", "nglview", "niivue", "perspective",
    "vizarr", "lonboard", "pyvista", "mols2grid", "k3d", "plotly",
    "embedding-atlas", "jscatter", "ipysigma", "reactable", "rerun", "altair",
    "ipycytoscape", "holoviews", "mosaic", "pydeck", "ipyvolume", "bokeh",
]  # fmt: skip



def guide_hero(slug: str) -> str:
    """The `hero:` image a widget guide's front matter names, relative to website/."""
    return f"widgets/{slug}/{front_matter_hero(WEBSITE / 'widgets' / slug / 'index.md')}"


def front_matter_hero(page: Path) -> str:
    """The `hero:` image a page's front matter names, relative to the page's directory."""
    m = re.search(r"^hero:\s*(\S+)", page.read_text(), re.M)
    if m is None:
        raise ValueError(f"{page} has no hero")
    return m.group(1)


# name -> (source relative to website/, crop box, max width)
IMAGES: dict[str, tuple[str, Box, int]] = {
    **{f"wall-{slug}": (guide_hero(slug), FULL, WALL_WIDTH) for slug in WALL},
    # Category cards
    "cat-charts": ("guide/first-app/img/01_render.webp", FULL, MAX_WIDTH),
    "cat-tables-grids": ("widgets/perspective/img/gallery_showcase_dark.webp", (0.27, 0.30, 0.99, 0.97), MAX_WIDTH),
    "cat-data-exploration": ("widgets/embedding-atlas/img/quickstart.webp", (0.02, 0.12, 0.60, 0.62), MAX_WIDTH),
    "cat-maps-geospatial": ("widgets/maplibre/img/hero.webp", FULL, MAX_WIDTH),
    "cat-3d": ("widgets/k3d/img/hero.webp", (0.03, 0.47, 0.48, 0.94), MAX_WIDTH),
    "cat-scientific": ("widgets/nglview/img/hero.webp", FULL, MAX_WIDTH),
    "cat-networks": ("gallery/showcases/les-miserables-network/img/after_click.webp", (0.38, 0.08, 0.76, 0.96), MAX_WIDTH),
    "cat-input-drawing": ("widgets/drawdata/img/gallery_template_classifier_playground_after.webp", (0.56, 0.21, 0.99, 0.93), MAX_WIDTH),
    # Code tabs: the example's own before/after screenshots
    "tab-plotly-0": ("guide/first-app/img/02_before.webp", FULL, MAX_WIDTH),
    "tab-plotly-1": ("guide/first-app/img/02_after.webp", FULL, MAX_WIDTH),
    "tab-altair-0": ("widgets/altair/img/04_interval_selection_before.webp", FULL, MAX_WIDTH),
    "tab-altair-1": ("widgets/altair/img/04_interval_selection_after.webp", FULL, MAX_WIDTH),
    "tab-mosaic-0": ("widgets/mosaic/img/10_linked_stats_table_before.webp", FULL, MAX_WIDTH),
    "tab-mosaic-1": ("widgets/mosaic/img/10_linked_stats_table_after.webp", FULL, MAX_WIDTH),
    "tab-bokeh-0": ("widgets/bokeh/img/15_lasso_to_histogram_before.webp", FULL, MAX_WIDTH),
    "tab-bokeh-1": ("widgets/bokeh/img/15_lasso_to_histogram_after.webp", FULL, MAX_WIDTH),
    "tab-holoviews-0": ("widgets/holoviews/img/03_link_selections_before.webp", FULL, MAX_WIDTH),
    "tab-holoviews-1": ("widgets/holoviews/img/03_link_selections_after.webp", FULL, MAX_WIDTH),
    "tab-matplotlib-0": ("widgets/matplotlib/img/accessor_clicked_before.webp", FULL, MAX_WIDTH),
    "tab-matplotlib-1": ("widgets/matplotlib/img/accessor_clicked_after.webp", FULL, MAX_WIDTH),
    "tab-itables-0": ("widgets/itables/img/08_selected_rows_accessor_before.webp", FULL, MAX_WIDTH),
    "tab-itables-1": ("widgets/itables/img/08_selected_rows_accessor_after.webp", FULL, MAX_WIDTH),
    "tab-reactable-0": ("widgets/reactable/img/15_search_to_chart_before.webp", FULL, MAX_WIDTH),
    "tab-reactable-1": ("widgets/reactable/img/15_search_to_chart_after.webp", FULL, MAX_WIDTH),
    "tab-lonboard-0": ("widgets/lonboard/img/07_accessors_before.webp", FULL, MAX_WIDTH),
    "tab-lonboard-1": ("widgets/lonboard/img/07_accessors_after.webp", FULL, MAX_WIDTH),
    "tab-maplibre-1": ("widgets/maplibre/img/extrusion_3d.webp", FULL, MAX_WIDTH),
    "tab-any-widget-1": ("guide/any-widget/img/03_trait_sync_clicked.webp", FULL, MAX_WIDTH),
    # How it works: the first-app article's three steps
    "step-1": ("guide/first-app/img/01_render.webp", FULL, MAX_WIDTH),
    "step-2": ("guide/first-app/img/02_after.webp", (0.01, 0.115, 0.99, 0.975), MAX_WIDTH),
    "step-3": ("guide/first-app/img/03_summary.webp", FULL, MAX_WIDTH),
    # The stage: each showcase's hero and the screenshot after its gesture
    "show-chat-0": ("gallery/showcases/map-chart-chat/img/hero.webp", FULL, MAX_WIDTH),
    "show-chat-1": ("gallery/showcases/map-chart-chat/img/after_fly_to.webp", FULL, MAX_WIDTH),
    "show-trade-0": ("gallery/showcases/trading-desk/img/hero.webp", FULL, MAX_WIDTH),
    "show-trade-1": ("gallery/showcases/trading-desk/img/after_pivot.webp", FULL, MAX_WIDTH),
    "show-world-0": ("gallery/showcases/world-development-dashboard/img/hero.webp", FULL, MAX_WIDTH),
    "show-world-1": ("gallery/showcases/world-development-dashboard/img/after_click.webp", FULL, MAX_WIDTH),
    "show-digits-0": ("gallery/showcases/digits-atlas/img/hero.webp", FULL, MAX_WIDTH),
    "show-digits-1": ("gallery/showcases/digits-atlas/img/after_lasso.webp", FULL, MAX_WIDTH),
    "show-cells-0": ("gallery/showcases/single-cell-atlas/img/hero.webp", FULL, MAX_WIDTH),
    "show-cells-1": ("gallery/showcases/single-cell-atlas/img/after_top.webp", FULL, MAX_WIDTH),
    "show-terrain-0": ("gallery/showcases/terrain-explorer/img/hero.webp", FULL, MAX_WIDTH),
    "show-terrain-1": ("gallery/showcases/terrain-explorer/img/after_peak.webp", FULL, MAX_WIDTH),
    "show-brain-0": ("gallery/showcases/brain-atlas-explorer/img/hero.webp", FULL, MAX_WIDTH),
    "show-brain-1": ("gallery/showcases/brain-atlas-explorer/img/after_landmark.webp", FULL, MAX_WIDTH),
    # Going further
    "more-data": ("guide/performance/img/15_bigdata_datashader_100k.webp", (0.04, 0.08, 0.78, 0.96), MAX_WIDTH),
    "more-ai": ("gallery/showcases/map-chart-chat/img/hero.webp", (0.0, 0.07, 1.0, 0.97), MAX_WIDTH),
}  # fmt: skip


# Gallery cards: gallery/<bucket>/<name>/img/hero.webp -> img/card.webp, cropped to the widgets.
GALLERY_CROPS: dict[str, Box] = {
    "showcases/aoi-workbench": (0.16, 0.16, 0.66, 0.74),
    "showcases/brain-atlas-explorer": (0.25, 0.10, 0.97, 0.80),
    "showcases/chemical-explorer": (0.22, 0.10, 0.92, 0.78),
    "showcases/digits-atlas": (0.00, 0.10, 0.92, 0.99),
    "showcases/les-miserables-network": (0.22, 0.18, 0.85, 0.83),
    "showcases/map-chart-chat": (0.00, 0.08, 0.88, 0.93),
    "showcases/orrery": (0.00, 0.15, 0.64, 0.83),
    "showcases/rhodopsin-in-motion": (0.33, 0.08, 0.97, 0.70),
    "showcases/single-cell-atlas": (0.33, 0.07, 0.99, 0.73),
    "showcases/stdlib-import-graph": (0.24, 0.10, 0.82, 0.80),
    "showcases/terrain-explorer": (0.00, 0.24, 0.66, 0.90),
    "showcases/trading-desk": (0.37, 0.05, 0.99, 0.66),
    "showcases/world-development-dashboard": (0.27, 0.10, 0.97, 0.80),
    "templates/altair-weather-brush": (0.00, 0.08, 0.62, 0.70),
    "templates/drawdata-classifier-playground": (0.25, 0.08, 0.95, 0.78),
    "templates/embedding-atlas-explorer": (0.02, 0.12, 0.66, 0.76),
    "templates/ipycanvas-game-of-life": (0.10, 0.12, 0.75, 0.78),
    "templates/ipycytoscape-network-explorer": (0.35, 0.17, 0.99, 0.83),
    "templates/ipydatagrid-spreadsheet": (0.00, 0.08, 0.45, 0.50),
    "templates/ipyfilechooser-data-explorer": (0.33, 0.08, 0.99, 0.75),
    "templates/ipyleaflet-spatial-explorer": (0.00, 0.08, 0.66, 0.74),
    "templates/itables-table-as-input": (0.00, 0.10, 0.64, 0.74),
    "templates/jscatter-linked-scatter": (0.00, 0.10, 0.66, 0.76),
    "templates/k3d-point-cloud-explorer": (0.15, 0.30, 0.55, 0.90),
    "templates/lonboard-city-explorer": (0.00, 0.10, 0.58, 0.72),
    "templates/map-viewport-to-chart": (0.00, 0.08, 0.66, 0.74),
    "templates/mols2grid-grid-explorer": (0.00, 0.10, 0.66, 0.76),
    "templates/mosaic-crossfilter": (0.00, 0.08, 0.58, 0.72),
    "templates/plotly-lasso-explorer": (0.02, 0.08, 0.50, 0.48),
    "templates/table-row-to-highlight": (0.48, 0.10, 0.99, 0.92),
}
CARD_WIDTH = 900


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="check the size budget and references only")
    args = parser.parse_args()
    if not args.check:
        OUT.mkdir(parents=True, exist_ok=True)
        for name, (src, box, width) in IMAGES.items():
            write(WEBSITE / src, box, width, OUT / f"{name}.webp")
        for app, box in GALLERY_CROPS.items():
            page = WEBSITE / "gallery" / app
            write(page / front_matter_hero(page / "index.md"), box, CARD_WIDTH, page / "img/card.webp")
    problems = check()
    for problem in problems:
        print(f"FAIL {problem}")
    return 1 if problems else 0


def write(src: Path, box: Box, width: int, dest: Path) -> None:
    im = Image.open(src).convert("RGB")
    w, h = im.size
    left, top, right, bottom = box
    im = im.crop((round(left * w), round(top * h), round(right * w), round(bottom * h)))
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.Resampling.LANCZOS)
    im.save(dest, quality=QUALITY, method=6)


def check() -> list[str]:
    problems: list[str] = []
    files = sorted(OUT.glob("*.webp"))
    total = sum(f.stat().st_size for f in files)
    print(f"{len(files)} images, {total / 1024 / 1024:.2f} MB (budget {BUDGET_BYTES / 1024 / 1024:.0f} MB)")
    if total > BUDGET_BYTES:
        problems.append(f"landing images total {total} bytes, over the {BUDGET_BYTES}-byte budget")
    apps = {f"{md.parent.parent.name}/{md.parent.name}" for md in (WEBSITE / "gallery").glob("*/*/index.md")}
    if missing := sorted(apps - GALLERY_CROPS.keys()):
        problems.append(f"gallery apps without a card crop: {missing}")
    for app in sorted(apps & GALLERY_CROPS.keys()):
        if not (WEBSITE / "gallery" / app / "img/card.webp").exists():
            problems.append(f"gallery/{app}/img/card.webp doesn't exist")
    for name in sorted(referenced_images()):
        if not (OUT / f"{name}.webp").exists():
            problems.append(f"the landing page uses img/{name}.webp, which doesn't exist")
    return problems


def referenced_images() -> set[str]:
    """Image names the landing page uses: literal img/<name>.webp paths in its markup, plus the
    names landing.js builds from landing-data.js (wall-<slug>, tab-<id>-N, show-<id>-N)."""
    markup = (WEBSITE / "index.qmd").read_text()
    names = set(re.findall(r"img/([\w-]+)\.webp", markup))
    if not DATA_JS.exists():
        return names
    data = DATA_JS.read_text()
    wall = re.search(r"const WALL = \[(.*?)\];", data, re.S)
    names |= {f"wall-{slug}" for slug in re.findall(r'"([\w-]+)"', wall.group(1) if wall else "")}
    for tab_id, before in re.findall(r'\{ id: "([\w-]+)", label: .*?before: (true|false)', data):
        names |= {f"tab-{tab_id}-1"} | ({f"tab-{tab_id}-0"} if before == "true" else set())
    showcases = data[data.index("const SHOWCASES") :] if "const SHOWCASES" in data else ""
    for show_id in re.findall(r'\{ id: "([\w-]+)"', showcases):
        names |= {f"show-{show_id}-0", f"show-{show_id}-1"}
    return names


if __name__ == "__main__":
    sys.exit(main())
