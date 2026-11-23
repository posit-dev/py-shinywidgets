"""Figure builders and stylers for the county-clusters showcase.

Builders take the data they need and return a plotly figure; the matching
updater mutates a live `FigureWidget` in place (so zoom and selection survive
a re-cluster). Nothing here knows about Shiny or reactivity.
"""

import re
from typing import Any, cast

import pandas as pd
import plotly.graph_objects as go
from segments import Clustering

FigConfig = tuple[go.Figure, dict[str, bool]]

TRANSPARENT = "rgba(0,0,0,0)"
SURFACE = "#1a1a19"
TEXT_PRIMARY = "#f0efec"
TEXT_SECONDARY = "#c3c2b7"
GRID = "#2c2c2a"
BASELINE = "#383835"
FONT_FAMILY = "system-ui, -apple-system, 'Segoe UI', sans-serif"
SELECTED_COLOR = "#f0efec"
TWIN_COLOR = "#eda100"
ACCENT = TWIN_COLOR
DIMMED_OPACITY = 0.32
# Categorical palette (dark-mode slots), extended with two hand-picked hues
# (teal, brown) past the eight that are validated for all-pairs discriminability.
SEGMENT_COLORS = [
    "#3987e5", "#d95926", "#199e70", "#c98500",
    "#d55181", "#0ca30c", "#9085e9", "#e66767",
    "#4fb3b3", "#a9815f",
]  # fmt: skip
HEATMAP_LABELS = {
    "median_income": "Median<br>income", "pct_rural": "%<br>rural",
    "pct_65_older": "%<br>65+", "some_college": "%<br>college",
    "broadband": "%<br>broadband", "uninsured": "%<br>uninsured",
    "life_expectancy": "Life<br>expectancy", "adult_obesity": "%<br>obesity",
}  # fmt: skip
COUNTY_SUFFIX_RE = re.compile(
    r"\s+(County|Parish|Borough|Municipality|Census Area|Planning Region|city)$"
)
# Shared chart chrome: every figure sits directly on its card (transparent, no colorbar).
BASE_LAYOUT = dict(
    paper_bgcolor=TRANSPARENT, plot_bgcolor=TRANSPARENT,
    font=dict(color=TEXT_PRIMARY, family=FONT_FAMILY, size=12), showlegend=False,
)  # fmt: skip
CARTESIAN_AXIS = dict(color=TEXT_SECONDARY, automargin=True)


def build_centroids(geojson: dict[str, Any]) -> dict[str, tuple[float, float]]:
    return {
        f["id"]: ring_centroid(largest_ring(f["geometry"]))[:2]
        for f in geojson["features"]
    }


def build_map(
    c: Clustering, geojson: dict[str, Any], counties: pd.DataFrame
) -> FigConfig:
    fips = counties["fips"].tolist()
    base = go.Choropleth(
        geojson=geojson, locations=fips, featureidkey="id", z=c.labels.tolist(), customdata=fips,
        text=segment_hover_text(c, counties), hovertemplate="%{text}<extra></extra>", showscale=False,
        colorscale=discrete_colorscale(SEGMENT_COLORS[: c.k]), zmin=-0.5, zmax=c.k - 0.5,
        marker=dict(line=dict(color=BASELINE, width=0.4), opacity=1.0),
    )  # fmt: skip
    lines = go.Scattergeo(
        lon=[], lat=[], mode="lines", line=dict(color=TWIN_COLOR, width=1.3),
        opacity=0.55, hoverinfo="skip",
    )  # fmt: skip
    # Selected county + its twins, as one trace: marker/text styling is arrayOK per point,
    # with the selected county always first (solid, larger marker) and twins after (rings).
    points = go.Scattergeo(
        lon=[], lat=[], mode="markers+text", text=[], textposition=[], hoverinfo="skip",
        textfont=dict(size=11, family=FONT_FAMILY, color=[]),
        marker=dict(size=[], color=[], symbol=[], line=dict(color=SURFACE, width=2)),
    )  # fmt: skip
    fig = go.Figure([base, lines, points])
    fig.update_geos(
        scope="usa", projection_type="albers usa", showland=True, landcolor=SURFACE,
        showlakes=False, bgcolor=TRANSPARENT, showsubunits=False, showcountries=False, showframe=False,
    )  # fmt: skip
    fig.update_layout(dict(BASE_LAYOUT, margin=dict(l=0, r=0, t=6, b=0), dragmode=False))  # fmt: skip
    return fig, {"displayModeBar": False}


def build_silhouette_chart(silhouette: pd.Series, k: int) -> FigConfig:
    ks = silhouette.index.to_numpy()
    colors, sizes, texts = marker_style(ks, k)
    fig = go.Figure(
        go.Scatter(
            x=ks, y=silhouette.to_numpy(), mode="lines+markers+text",
            line=dict(color=TEXT_SECONDARY, width=1.5),
            marker=dict(color=colors, size=sizes, line=dict(color=SURFACE, width=1)),
            text=texts, textposition="top center", textfont=dict(color=ACCENT, size=12),
            hovertemplate="k=%{x}: silhouette %{y:.3f}<extra></extra>",
        )
    )  # fmt: skip
    fig.update_layout(dict(
        BASE_LAYOUT, margin=dict(l=10, r=15, t=35, b=10),
        xaxis=dict(title="Number of segments", dtick=1, gridcolor=GRID, zeroline=False, **CARTESIAN_AXIS),
        yaxis=dict(title="Silhouette score", gridcolor=GRID, zeroline=False, **CARTESIAN_AXIS),
    ))  # fmt: skip
    return fig, {"displayModeBar": False}


def build_heatmap(c: Clustering) -> FigConfig:
    z = c.profile.to_numpy()
    bound = max(0.5, abs(z).max())
    fig = go.Figure(
        go.Heatmap(
            z=z, x=list(HEATMAP_LABELS.values()), y=segment_ticktext(c),
            zmid=0, zmin=-bound, zmax=bound, showscale=False,
            colorscale=[[0, "#3987e5"], [0.5, "#383835"], [1, "#e66767"]],
            text=z_text(z),
            texttemplate="%{text}", textfont=dict(size=10),
            hovertemplate="%{y}<br>%{x}: %{z:+.2f}<extra></extra>",
            xgap=2, ygap=2,
        )
    )  # fmt: skip
    fig.update_layout(dict(
        BASE_LAYOUT, margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(side="top", ticks="", showgrid=False, zeroline=False, tickfont=dict(size=11), **CARTESIAN_AXIS),
        yaxis=dict(autorange="reversed", ticks="", showgrid=False, zeroline=False, tickfont=dict(size=11), **CARTESIAN_AXIS),
    ))  # fmt: skip
    return fig, {"displayModeBar": False}


def update_map(
    w: go.FigureWidget,
    c: Clustering,
    fips: str | None,
    twin_rows: pd.DataFrame,
    counties: pd.DataFrame,
    centroids: dict[str, tuple[float, float]],
) -> None:
    base = cast(go.Choropleth, w.data[0])
    base.z = c.labels.tolist()
    base.text = segment_hover_text(c, counties)
    base.colorscale = discrete_colorscale(SEGMENT_COLORS[: c.k])
    base.zmin, base.zmax = -0.5, c.k - 0.5
    base.update(marker=dict(opacity=DIMMED_OPACITY if fips is not None else 1.0))

    lines, points = cast(go.Scattergeo, w.data[1]), cast(go.Scattergeo, w.data[2])
    if fips is None:
        lines.lon, lines.lat = [], []
        points.lon, points.lat, points.text = [], [], []
        return
    slon, slat = centroids[fips]
    twin_lonlat = [centroids[f] for f in twin_rows["fips"]]
    n = len(twin_lonlat)
    colors = [SELECTED_COLOR] + [TWIN_COLOR] * n
    twin_positions = label_positions((slon, slat), twin_lonlat)
    points.update(
        lon=[slon] + [ll[0] for ll in twin_lonlat], lat=[slat] + [ll[1] for ll in twin_lonlat],
        text=[short_label(fips, counties)] + [short_label(f, counties) for f in twin_rows["fips"]],
        textposition=["bottom center"] + twin_positions, textfont=dict(color=colors),
        marker=dict(size=[22] + [13] * n, color=colors, symbol=["circle"] + ["circle-open"] * n),
    )  # fmt: skip
    line_lon, line_lat = [], []
    for tlon, tlat in twin_lonlat:
        line_lon += [slon, tlon, None]
        line_lat += [slat, tlat, None]
    lines.lon, lines.lat = line_lon, line_lat


def update_heatmap(w: go.FigureWidget, c: Clustering) -> None:
    z = c.profile.to_numpy()
    bound = max(0.5, abs(z).max())
    trace = cast(go.Heatmap, w.data[0])
    trace.z, trace.y = z, segment_ticktext(c)
    trace.zmin, trace.zmax = -bound, bound
    trace.text = z_text(z)


def restyle_silhouette(w: go.FigureWidget, silhouette: pd.Series, k: int) -> None:
    colors, sizes, texts = marker_style(silhouette.index.to_numpy(), k)
    trace = cast(go.Scatter, w.data[0])
    trace.update(marker=dict(color=colors, size=sizes), text=texts)  # fmt: skip


def label_positions(
    selected: tuple[float, float], twins: list[tuple[float, float]]
) -> list[str]:
    """Label each twin on the side facing away from the selected county (whose own label
    sits below it), nudging a label up or down when an earlier twin on that side is close
    enough on the map for the two names to collide."""
    positions: list[str] = []
    for i, (lon, lat) in enumerate(twins):
        side = "right" if lon >= selected[0] else "left"
        near = [
            plat
            for (plon, plat), pos in zip(twins[:i], positions)
            if pos.endswith(side) and abs(plon - lon) < 8 and abs(plat - lat) < 2.5
        ]
        above, below = any(p > lat for p in near), any(p < lat for p in near)
        vertical = (
            "bottom"
            if above and not below
            else "top"
            if below and not above
            else "middle"
        )
        positions.append(f"{vertical} {side}")
    return positions


def z_text(z: Any) -> list[list[str]]:
    # Round first so a tiny negative z-score reads "+0.0", not "-0.0".
    return [[f"{round(v, 1) + 0.0:+.1f}" for v in row] for row in z]


def marker_style(ks: Any, k: int) -> tuple[list[str], list[int], list[str]]:
    colors = [ACCENT if kk == k else TEXT_SECONDARY for kk in ks]
    sizes = [20 if kk == k else 11 for kk in ks]
    texts = [f"k = {kk}" if kk == k else "" for kk in ks]
    return colors, sizes, texts


def segment_hover_text(c: Clustering, counties: pd.DataFrame) -> list[str]:
    rows = zip(counties["county"], counties["state"], c.labels)
    return [f"{county}, {state}<br>{c.names[label]}" for county, state, label in rows]  # fmt: skip


def segment_ticktext(c: Clustering) -> list[str]:
    dot = '<span style="color:{}">●</span> {}'
    return [dot.format(SEGMENT_COLORS[i], name) for i, name in enumerate(c.names)]


def discrete_colorscale(colors: list[str]) -> list[list[Any]]:
    n = len(colors)
    scale: list[list[Any]] = []
    for i, color in enumerate(colors):
        scale.append([i / n, color])
        scale.append([(i + 1) / n, color])
    return scale


def short_label(fips: str, counties: pd.DataFrame) -> str:
    row = counties.loc[counties["fips"] == fips].iloc[0]
    name = COUNTY_SUFFIX_RE.sub("", row["county"])
    return f"{name}, {row['state']}"


def ring_centroid(ring: list[list[float]]) -> tuple[float, float, float]:
    """Shoelace-formula centroid and signed area of a closed lon/lat ring."""
    area = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if abs(area) < 1e-12:
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        return sum(xs) / len(xs), sum(ys) / len(ys), 0.0
    area *= 0.5
    return cx / (6 * area), cy / (6 * area), area


def largest_ring(geometry: dict[str, Any]) -> list[list[float]]:
    if geometry["type"] == "Polygon":
        return cast(list[list[float]], geometry["coordinates"][0])
    rings = [poly[0] for poly in geometry["coordinates"]]
    return max(rings, key=lambda ring: abs(ring_centroid(ring)[2]))
