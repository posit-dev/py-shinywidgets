import numpy as np
import plotly.graph_objs as go
from shiny import *
from sklearn.linear_model import LinearRegression

from shinywidgets import output_widget, render_widget

# Generate some data and fit a linear regression
n = 10000
dat = np.random.RandomState(0).multivariate_normal([0, 0], [(1, 0.5), (0.5, 1)], n).T
x = dat[0]
y = dat[1]
fit = LinearRegression().fit(x.reshape(-1, 1), dat[1])
xgrid = np.linspace(start=min(x), stop=max(x), num=30)

app_ui = ui.page_fillable(
    ui.input_checkbox("show_fit", "Show fitted line", value=True),
    output_widget("scatterplot")
)


def server(input, output, session):

    @output
    @render_widget
    def scatterplot():
        return go.FigureWidget(
            data=[
                go.Scattergl(
                    x=x,
                    y=y,
                    mode="markers",
                    marker=dict(color="rgba(0, 0, 0, 0.05)", size=5),
                ),
                go.Scattergl(
                    x=xgrid,
                    y=fit.intercept_ + fit.coef_[0] * xgrid,
                    mode="lines",
                    line=dict(color="red", width=2),
                ),
            ],
            layout={"showlegend": False},
        )

    @reactive.Effect
    def _():
        scatterplot.widget.data[1].visible = input.show_fit()



app = App(app_ui, server)
