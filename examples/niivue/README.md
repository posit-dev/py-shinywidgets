# niivue example

Run with:

```sh
pip install -r requirements.txt
shiny run app.py
```

The first run downloads the public NiiVue demo images (~4.5 MB) into
`~/.cache/ipyniivue-demo`; subsequent runs reuse them.

What `@render_niivue` offers: a clinical-grade
[NiiVue](https://niivue.com) neuroimaging viewer (multiplanar slices plus a
GPU 3D volume render) as a Shiny output that is also an *input* — clicking
or dragging the crosshair reports millimeter coordinates and voxel
intensities back to Python (via the widget's `on_location_change` callback;
the crosshair doesn't sync as a trait, so `reactive_read()` can't see it).
Colormap, gamma, overlay opacity, and slice-type changes apply live via
`.widget` methods, without re-sending the volume data.

Two things to know about:

- Don't pass `height=` to `NiiVue()` — the viewer fills its container (or
  follows an explicit `output_widget(height=...)`); a `NiiVue(height=...)`
  that disagrees with the output's height causes clipping or dead space.
- Each render sends the viewer's JavaScript bundle (~5 MB) plus every
  volume (base64-encoded) to the browser, so prefer `Volume(url=...)` for
  large remote volumes and in-place `.widget` updates over re-rendering.
