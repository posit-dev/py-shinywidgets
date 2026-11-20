"""Plotting and formatting helpers for the loan-chat showcase.

Pure functions: each plot builder takes the current filtered DataFrame and
returns a plotly Figure. Nothing here knows about Shiny or reactivity.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

ACCENT = "#2f6fed"
FONT_FAMILY = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'
GRADE_ORDER = ["A", "B", "C", "D", "E", "F", "G"]
GRADE_COLORS = {
    "A": "#1b7a3d",
    "B": "#5aa454",
    "C": "#9bc46d",
    "D": "#e8c547",
    "E": "#e8974a",
    "F": "#d9622f",
    "G": "#b23a2e",
}
MARGIN = dict(l=56, r=20, t=16, b=48)
FONT = dict(family=FONT_FAMILY, size=13, color="#2b2f38")


def fmt_count(n: int) -> str:
    return f"{n:,}"


def fmt_pct(x: float | None) -> str:
    return "--" if x is None or pd.isna(x) else f"{x:.1f}%"


def fmt_money(x: float | None, *, millions: bool = False) -> str:
    if x is None or pd.isna(x):
        return "--"
    if millions:
        if x == 0:
            return "$0"
        return f"${x / 1_000_000:,.1f}M" if x >= 1_000_000 else f"${x / 1_000:,.0f}K"
    return f"${x:,.0f}"


def rate_amount_fig(df: pd.DataFrame) -> go.Figure:
    """Interest rate vs. loan amount, colored by grade -- the lasso target.

    Lending Club sets a loan's rate almost entirely from its sub-grade, so
    this renders as clean horizontal color bands rather than a cloud: every
    grade is its own band, and lassoing one (or a slice across several) is
    an obvious, satisfying gesture.
    """
    if df.empty:
        return _empty_fig("No loans match this filter")
    present = [g for g in GRADE_ORDER if g in set(df["grade"])]
    # Loan amounts cluster on round numbers ($5,000, $10,000, ...), which
    # without this reads as harsh vertical stripes. A per-loan jitter (a
    # deterministic hash of loan_id, so the same loan always lands in the
    # same spot) spreads each round-number column into a band, for display
    # only -- selection still matches on loan_id, not this x position.
    jitter = (df["loan_id"] * 9973 % 1401) - 700
    plot_df = df.assign(display_amount=df["loan_amount"] + jitter)
    fig = px.scatter(
        plot_df, x="display_amount", y="interest_rate", color="grade",
        category_orders={"grade": present}, color_discrete_map=GRADE_COLORS,
        custom_data=["loan_id", "loan_amount"], opacity=0.35,
    )  # fmt: skip
    fig.update_traces(
        marker=dict(size=5, line=dict(width=0.5, color="white")),
        hovertemplate="Grade %{marker.color}<br>Loan: $%{customdata[1]:,.0f}<br>Rate: %{y:.1f}%<extra></extra>",
        selected=dict(marker=dict(opacity=1, size=7)),
        unselected=dict(marker=dict(opacity=0.06)),
        showlegend=False,
    )
    # The real traces plot at opacity=0.35 for a legible band, but a legend
    # swatch at that opacity is nearly invisible -- add one full-opacity,
    # legend-only dummy point per grade instead of relying on the data
    # traces' own (faint) legend entries.
    for grade in present:
        fig.add_trace(
            go.Scatter(
                x=[None], y=[None], mode="markers", name=grade,
                marker=dict(size=11, color=GRADE_COLORS[grade]),
                showlegend=True, hoverinfo="skip",
            )
        )  # fmt: skip
    fig.update_layout(
        dragmode="lasso",
        legend=dict(
            # traceorder must be "normal": px.scatter leaves its colored
            # traces' legend in "grouped" mode, and a "grouped" horizontal
            # legend wraps every ungrouped dummy trace (our per-grade
            # swatches, added above) onto its own row -- i.e. right back to
            # a vertical list. "normal" is what actually keeps it a single
            # horizontal row; verified via the browser's resolved
            # `gd._fullLayout.legend`, not just the Python-side figure.
            title_text="Grade", orientation="h", itemsizing="constant",
            traceorder="normal", x=1, xanchor="right", y=0.99, yanchor="top",
            bgcolor="rgba(255,255,255,0.85)", font=dict(size=12),
        ),
    )  # fmt: skip
    return (
        _base_layout(fig, margin=dict(l=64, r=16, t=16, b=56))
        .update_xaxes(title="Loan amount", tickformat="$,.0f")
        .update_yaxes(title="Interest rate", ticksuffix="%")
    )


def purpose_fig(df: pd.DataFrame, top_n: int = 8) -> go.Figure:
    if df.empty:
        return _empty_fig("No loans match this filter")
    counts = (
        (
            df["loan_purpose"]
            .value_counts()
            .rename_axis("purpose")
            .reset_index(name="count")
        )
        .nlargest(top_n, "count")
        .sort_values("count")
    )
    fig = px.bar(
        counts, x="count", y="purpose", orientation="h",
        color_discrete_sequence=[ACCENT], text="count",
    )  # fmt: skip
    fig.update_traces(
        texttemplate="%{text:,}", textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:,} loans<extra></extra>",
    )  # fmt: skip
    return (
        _base_layout(fig, margin=dict(l=132, r=48, t=16, b=16))
        .update_xaxes(visible=False)
        .update_yaxes(title=None)
    )


def rate_by_grade_fig(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty_fig("No loans match this filter")
    present = [g for g in GRADE_ORDER if g in set(df["grade"])]
    fig = px.box(
        df, x="grade", y="interest_rate", color="grade",
        category_orders={"grade": present}, color_discrete_map=GRADE_COLORS,
    )  # fmt: skip
    fig.update_traces(hovertemplate="Grade %{x}<br>Rate: %{y:.1f}%<extra></extra>")
    return (
        _base_layout(fig, showlegend=False)
        .update_xaxes(title="Grade")
        .update_yaxes(title="Interest rate", ticksuffix="%")
    )


def state_rate_fig(df: pd.DataFrame) -> go.Figure:
    """Average interest rate by state -- varies meaningfully (10.7-14.8%),
    unlike a raw dollar total, which mostly just traces population."""
    if df.empty:
        return _empty_fig("No loans match this filter")
    rates = df.groupby("state", as_index=False)["interest_rate"].mean()
    fig = px.choropleth(
        rates, locations="state", locationmode="USA-states", scope="usa",
        color="interest_rate", color_continuous_scale=[[0, "#eaf1fd"], [1, ACCENT]],
        labels={"interest_rate": "Avg. rate"},
    )  # fmt: skip
    fig.update_traces(
        hovertemplate="%{location}<br>Avg. rate: %{z:.1f}%<extra></extra>",
        marker_line_color="white",
        marker_line_width=0.5,
    )
    fig.update_coloraxes(colorbar=dict(title="Avg. rate", ticksuffix="%", len=0.8))
    return _base_layout(fig, margin=dict(l=4, r=4, t=4, b=4))


def _base_layout(
    fig: go.Figure, *, showlegend: bool | None = None, margin: dict | None = None
) -> go.Figure:
    fig.update_layout(
        template="simple_white",
        font=FONT,
        margin=margin or MARGIN,
        showlegend=showlegend if showlegend is not None else fig.layout.showlegend,
    )
    return fig


def _empty_fig(message: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        template="simple_white",
        font=FONT,
        margin=MARGIN,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text=message, xref="paper", yref="paper", x=0.5, y=0.5,
                showarrow=False, font=dict(size=14, color="#8a8f98"),
            )
        ],
    )  # fmt: skip
    return fig
