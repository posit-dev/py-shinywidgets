# ipyfilechooser (`render_ipyfilechooser`)

## Overview

`pip install 'shinywidgets[ipyfilechooser]'`. Let a Shiny app browse and
pick files that already live on the server, sandboxed to a directory you
choose — the mirror image of Shiny's own `ui.input_file()`, which uploads
from the visitor's machine. Accepts an `ipyfilechooser.FileChooser` widget.
The chooser is a form control with a natural size — the output doesn't
fill its container; size it with the chooser's own `layout`
(`Layout(width='700px')`) or `output_widget(width=..., height=...)`.

## Quick start

```python
from ipyfilechooser import FileChooser
from shiny import reactive
from shinywidgets import render_ipyfilechooser

selection = reactive.value(None)


@render_ipyfilechooser
def chooser():
    fc = FileChooser()
    fc.register_callback(lambda fc: selection.set(fc.selected))
    return fc
```

## Accessors

None — `.selected`, `.selected_path`, `.selected_filename` are plain
Python properties (not widget traits), so `reactive_read()` can't see
them. React to a selection by passing `.widget.register_callback()` a
function that sets a `reactive.value` — the callback fires when the user
confirms or changes a selection.

## Updating in place

None documented — change the chooser's constructor arguments and
re-render.

## Gotchas

- **Unsandboxed, a visitor can browse anything the server process can
  read.** Sandbox it to a directory before pointing it at a multi-tenant
  server: `FileChooser(path="/safe/directory", sandbox_path="/safe/directory")`.

**More:** <https://shinywidgets.org/widgets/ipyfilechooser/>
