# vizarr (`render_vizarr`)

## Overview

`pip install 'shinywidgets[vizarr]'`. Pan and zoom gigapixel,
multichannel bioimages (OME-Zarr/OME-NGFF) in Shiny, streamed from a
local array or a remote store. Accepts a `vizarr.Viewer` with one or more
images added via `.add_image()`. Requires an internet connection — the
widget loads its JS (vizarr, viv) from CDNs at render time.

## Quick start

```python
import numpy as np
import vizarr
from shinywidgets import render_vizarr


@render_vizarr
def viewer():
    v = vizarr.Viewer()
    v.add_image(np.random.default_rng(0).random((256, 256)))
    return v
```

`add_image()` accepts a remote URL string (the browser fetches it
directly — prefer this for large images) or a local `zarr.Array`/`Group`/
store/numpy array, whose chunks are served on demand over the widget comm,
base64-encoded (~33% inflation, since Shiny has no binary message
channel).

## Accessors

None dedicated — panning/zooming syncs the camera to the `view_state`
trait (`{"target": ..., "zoom": ...}`, debounced ~200ms): read it with
`viewer.read("view_state")`. Layer controls in the side panel (channel
colors, contrast limits, visibility) do **not** sync back to Python.

## Updating in place

`.widget.add_image(...)` adds a layer without a full re-render;
`.widget.view_state = {...}` sets the camera (add-only — no remove or
replace of existing images):

```python
from shiny import reactive


@reactive.effect
def _add_layer():
    viewer.widget.add_image(new_array)
```

## Gotchas

- In a filling layout the viewer grows/shrinks to its container; otherwise
  its own `height` trait applies (default `"500px"`, treated as unset the
  same way as other GPU widgets — set a different value for a genuinely
  fixed size).
- No accessors for layer controls — if your app needs to react to a
  contrast/channel change, there's no reactive surface for it.

**More:** <https://shinywidgets.org/widgets/vizarr/>
