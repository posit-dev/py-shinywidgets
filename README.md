shinywidgets
================

Render [ipywidgets](https://ipywidgets.readthedocs.io/en/stable/) inside a
[Shiny](https://shiny.rstudio.com/py) (for Python) app.

See the [Jupyter Widgets](https://shiny.posit.co/py/docs/jupyter-widgets.html) article on the Shiny for Python website for more details.

## Installation

```sh
pip install shinywidgets
```

## Widget lifetimes and reuse

Widgets created inside a renderer are temporary. After that render ends,
shinywidgets closes them when no live widget or display still needs them.
Widgets created in the server body receive the session lifetime and close
when the session ends.

For a cache populated inside a renderer, create its widgets inside
`session_lifetime()`. A Python dictionary or another reference alone does
not retain a temporary widget.

This complete app shows fresh widgets, server-body widgets, cached widgets,
and updates through a renderer's `.widget` property:

```python
from ipywidgets import HTML
from shiny import App, Inputs, Outputs, Session, reactive, ui
from shinywidgets import output_widget, render_widget, session_lifetime

app_ui = ui.page_fluid(
    ui.input_select("dataset", "Dataset", ["A", "B"]),
    ui.input_action_button("refresh", "Create a fresh widget"),
    ui.input_action_button("update", "Update the cached widget"),
    output_widget("fresh"),
    output_widget("persistent"),
    output_widget("cached"),
)


def server(input: Inputs, output: Outputs, session: Session) -> None:
    server_widget = HTML(value="Retained for this session")
    cache: dict[str, HTML] = {}

    @render_widget
    def fresh() -> HTML:
        return HTML(value=f"Fresh render {input.refresh()}")

    @render_widget
    def persistent() -> HTML:
        return server_widget

    @render_widget
    def cached() -> HTML:
        key = input.dataset()
        if key not in cache:
            with session_lifetime():
                cache[key] = HTML(value=f"{key}:0")
        return cache[key]

    @reactive.effect
    @reactive.event(input.update)
    def update_cached() -> None:
        widget = cached.widget
        if widget is not None:
            widget.value = f"{input.dataset()}:updated"


app = App(app_ui, server)
```

Switching from A to B and back to A preserves A's widget and its state.
Updating `.widget` changes the live widget without a new render.
The property returns `None` before the renderer has a widget.
For `render_plotly`, `.widget` is the actual `FigureWidget`, including
when the renderer returns a plain Plotly `Figure`.

`session_lifetime()` requires an active Shiny session. It affects widgets
constructed inside its block, including nested blocks. Exiting the block
restores the previous construction policy; it does not close the retained widgets.
Referencing an existing widget inside the block does not adopt it.
Likewise, creating a plain `Figure` there does not retain a widget that
the renderer creates through coercion outside the block.
Create the actual `FigureWidget` inside the block when it must survive later renders.

Widgets created in effects outside rendering also receive the session lifetime.
Removing a retained layer from a map does not revoke that lifetime.
The API does not provide automatic cache eviction or shorter application scopes.
Widgets cannot be shared across Shiny sessions.

### Migrate cached widgets

A temporary widget cannot be rendered again after its lifetime ends.
The renderer raises:

> This widget's render lifetime has ended. Create reusable widgets inside session_lifetime().

Move the widget's **construction** into `session_lifetime()`, as in the cache
example. Wrapping only the return of an existing widget does not fix its lifetime.
An explicitly closed widget also cannot be rendered again.
This is an error, not a warning-only migration.

### Dependencies and package limits

Cleanup follows actual widget references in supported serialized traits.
Shared children, Layout/Style defaults, and reference cycles participate in
this cleanup. Arbitrary Python references and strings that resemble model IDs
do not establish dependencies.

Custom serializers that hide widget references need a package adapter.
If a live root has an opaque serializer, cleanup retains records and emits
one `RuntimeWarning` per session. Complete dependency information allows cleanup
to resume. Session shutdown closes all records regardless.

Resources outside widget models need their own cleanup.
For example, a Python `link()` needs an `unlink()` disposer.
Dependency adapters and lifetime disposers are private integration APIs.
Package authors must coordinate these integrations with shinywidgets.
AnyWidget cleanup callbacks run during view removal, but upstream does not
expose completion of asynchronous callbacks.

The integration suite covers core ipywidgets, Plotly, ipyleaflet, Altair,
Bokeh/jupyter-bokeh, AnyWidget, and nested Output views.
Current pydeck 0.9.1 lacks its former widget-backed `Deck.show()` path;
`render_pydeck` reports that compatibility error.

Plotly 6.7.0 leaves model listeners registered after removal of a cached view.
After redisplay, a later update can reach the removed view and fail with
`Cannot read properties of undefined (reading '_guiEditing')`.
This upstream defect blocks reliable cached Plotly updates after redisplay.

A page reload starts a new session with new widget models.
Hosted same-session transport resume and automatic restoration of browser state
are unsupported. In-page Shiny reconnect also encounters an upstream output
progress-state error (`unexpected state of: 'value'`).

## Development

If you want to do development on `{shinywidgets}`, run:

```sh
uv sync --all-groups
uv run pre-commit install
uv run playwright install chromium
cd js && yarn watch
```

If you need the older editable-install flow for tooling compatibility, this
also works:

```sh
pip install -e ".[dev]"
```

Common Python workflows:

```sh
make py-check
make test-playwright
make py-build
```
