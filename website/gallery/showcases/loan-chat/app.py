# Title: Lending Club loans, in plain English
# Bucket: showcase (~242 lines)
# Description: querychat (Claude, via chatlas) filters and queries 10,000
#   Lending Club loans in plain English; a compact stat strip and three
#   plotly cards always track its current result set. Lasso a rate band on
#   the full-width hero scatter and a registered chatlas tool lets Claude
#   describe exactly what you selected.
# Run: shiny run app.py
#   (needs ANTHROPIC_API_KEY to chat; the dashboard renders either way)
# Data: OpenIntro loans_full_schema.csv -- 10,000 Lending Club loans issued
#   Q1 2018 (CC BY-SA). Trimmed to 15 columns (plus a synthetic loan_id) by
#   prep_data.py into a committed data/loans.parquet.

import os
from pathlib import Path

import chatlas
import pandas as pd
import plots
import querychat
from shiny import App, Inputs, Outputs, Session, reactive, render, ui
from shinywidgets import output_widget, render_plotly

HERE = Path(__file__).parent
loans = pd.read_parquet(HERE / "data" / "loans.parquet")

MODEL = "claude-haiku-5-5"
HAS_KEY = bool(os.environ.get("ANTHROPIC_API_KEY"))
EXTRA_INSTRUCTIONS = """\
Keep every answer concise: start with a direct one-sentence answer, then at
most 3 short bullet points with the key numbers (commas for thousands, one
decimal place and a % sign for rates). Do not add generic caveats like
"treat this as a hypothesis" or suggest further verification unless the
user explicitly asks for caveats. When the user asks about "the loans I
selected" or "these N loans", call the describe_selected_loans tool rather
than guessing -- it reads the live lasso selection, not a stale snapshot."""

qc = (
    querychat.QueryChat(
        loans,
        "loans",
        tools=("filter", "query"),
        greeting=(HERE / "greeting.md").read_text(),
        data_description=(HERE / "data_description.md").read_text(),
        extra_instructions=EXTRA_INSTRUCTIONS,
    )
    if HAS_KEY
    else None
)

sidebar = (
    qc.sidebar(width=440)
    if qc is not None
    else ui.sidebar(
        ui.markdown(
            "**Chat needs `ANTHROPIC_API_KEY`.** Set the environment "
            "variable and restart the app to filter or ask questions about "
            "this data in plain English — the dashboard below works "
            "either way."
        ),
        width=440,
    )
)

THEME = ui.Theme().add_defaults(
    primary=plots.ACCENT,
    font_family_base=plots.FONT_FAMILY,
    font_family_sans_serif=plots.FONT_FAMILY,
)

LOWER_CARD_HEIGHT = "300px"
# querychat's chat centers an empty conversation's greeting vertically
# (shinychat's own .shiny-chat-greeting{margin-block:auto} rule, scoped to
# ":empty" conversations); overriding that one rule, scoped to this app's
# chat id, starts the greeting near the top instead. The value boxes keep
# their natural height (a fixed one squeezes the title under the value) and
# trim bslib's default padding instead.
APP_CSS = """
#querychat_loans-chat .shiny-chat-greeting { margin-block: 0 !important; }
.bslib-value-box .value-box-area { padding: 0.25rem 0.5rem; }
"""


def ask_selection_header(title: str) -> ui.Tag:
    return ui.div(
        ui.span(title),
        ui.output_ui("ask_selection_ui"),
        class_="d-flex align-items-center justify-content-between gap-2 w-100",
    )


app_ui = ui.page_sidebar(
    sidebar,
    ui.tags.style(APP_CSS),
    ui.layout_columns(
        ui.value_box(
            "Loans shown",
            ui.output_text("vb_count"),
            theme="text-primary",
        ),
        ui.value_box(
            "Avg. interest rate",
            ui.output_text("vb_rate"),
            theme="text-primary",
        ),
        ui.value_box(
            "Total loan amount",
            ui.output_text("vb_total"),
            theme="text-primary",
        ),
        fill=False,
    ),
    ui.card(
        ui.card_header(ask_selection_header("Interest rate vs. loan amount")),
        output_widget("scatter_chart"),
        full_screen=True,
        height="440px",
    ),
    ui.layout_columns(
        ui.card(
            ui.card_header("What people borrow for"),
            output_widget("purpose_chart"),
            full_screen=True,
            height=LOWER_CARD_HEIGHT,
        ),
        ui.card(
            ui.card_header("Riskier grades pay more"),
            output_widget("rate_chart"),
            full_screen=True,
            height=LOWER_CARD_HEIGHT,
        ),
        ui.card(
            ui.card_header("Which states pay more?"),
            output_widget("state_chart"),
            full_screen=True,
            height=LOWER_CARD_HEIGHT,
        ),
        col_widths=[4, 4, 4],
    ),
    title="Lending Club loans, in plain English",
    fillable=True,
    theme=THEME,
)


def server(input: Inputs, output: Outputs, session: Session):
    qc_vals = (
        qc.server(client=chatlas.ChatAnthropic(model=MODEL)) if qc is not None else None
    )

    def current_df() -> pd.DataFrame:
        return qc_vals.df() if qc_vals is not None else loans

    @render.text
    def vb_count():
        return plots.fmt_count(len(current_df()))

    @render.text
    def vb_rate():
        df = current_df()
        return plots.fmt_pct(float(df["interest_rate"].mean()) if len(df) else None)

    @render.text
    def vb_total():
        df = current_df()
        return plots.fmt_money(float(df["loan_amount"].sum()), millions=True)

    @render_plotly(listen_to=["selected"])
    def scatter_chart():
        return plots.rate_amount_fig(current_df()), {"displayModeBar": False}

    @render_plotly
    def purpose_chart():
        return plots.purpose_fig(current_df()), {"displayModeBar": False}

    @render_plotly
    def rate_chart():
        return plots.rate_by_grade_fig(current_df()), {"displayModeBar": False}

    @render_plotly
    def state_chart():
        return plots.state_rate_fig(current_df()), {"displayModeBar": False}

    @reactive.calc
    def selected_loans() -> pd.DataFrame:
        return scatter_chart.selected_rows(current_df(), key="loan_id")

    @render.ui
    def ask_selection_ui():
        if qc_vals is None:
            return None
        n = len(selected_loans())
        if n == 0:
            return ui.span(
                "Lasso a band to ask about it",
                class_="text-secondary small fw-normal",
            )
        return ui.input_action_button(
            "ask_selected", f"Ask about these {n:,} loans",
            class_="btn-sm btn-primary rounded-pill",
        )  # fmt: skip

    @reactive.effect
    @reactive.event(input.ask_selected)
    def _ask_about_selection():
        if qc_vals is None:
            return
        n = len(selected_loans())
        qc_vals.chat.update_user_input(
            value=f"What stands out about the {n:,} loans I selected on the scatter plot?",
            submit=True,
        )

    def describe_selected_loans() -> str:
        """
        Describe the loans currently lassoed on the interest-rate-vs-loan-
        amount scatter plot. Reflects the live selection under the CURRENT
        filter -- call this instead of guessing whenever the user refers to
        "the loans I selected" or "these N loans".
        """
        with reactive.isolate():
            rows = selected_loans()
        if rows.empty:
            return "Nothing is currently selected on the scatter plot."
        purposes = ", ".join(
            f"{p} ({n})" for p, n in rows["loan_purpose"].value_counts().head(3).items()
        )
        grades = rows["grade"].value_counts().reindex(plots.GRADE_ORDER).dropna()
        grade_mix = ", ".join(f"{g}: {int(n)}" for g, n in grades.items())
        return (
            f"{len(rows)} loans selected. Median loan amount "
            f"${rows['loan_amount'].median():,.0f}, median interest rate "
            f"{rows['interest_rate'].median():.1f}%, median annual income "
            f"${rows['annual_income'].median():,.0f}. Top purposes: {purposes}. "
            f"Grade mix: {grade_mix}."
        )  # fmt: skip

    if qc_vals is not None:
        qc_vals.client.register_tool(describe_selected_loans)


app = App(app_ui, server)
