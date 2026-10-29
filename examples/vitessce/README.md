# vitessce example

Run with:

```sh
pip install -r requirements.txt
shiny run app.py
```

Requires an internet connection: the demo config, the zarr data, and the
viewer's JavaScript are all fetched from remote servers at run time.

What `@render_vitessce` offers: a coordinated multi-view
[Vitessce](https://vitessce.io) single-cell/spatial-omics explorer as a
Shiny output that is also an *input* — every pan, zoom, lasso, and gene/cell
selection syncs the entire view config back to the `_config` trait, so
`reactive_read(widget, "_config")` lets other outputs react to where the
user is looking. Picking a gene in the sidebar updates the viewer from
Python (note the `uid` bump in the config edit — the viewer applies a new
config by remounting, and a top-level `uid` change is what reliably
triggers that remount).

Two things to know about:

- The widget's `height` is fixed pixels, read once at mount — choose
  `config.widget(height=...)` to match `output_widget(height=...)`.
  Setting `widget.height` after mount does nothing.
- Python→browser config updates remount the viewer (view state resets), so
  use them for deliberate changes (like the gene picker), not high-frequency
  updates.
