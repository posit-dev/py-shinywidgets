# drawdata example

Run with:

```sh
pip install -r requirements.txt
shiny run app.py
```

What `@render_drawdata` offers over a static plot: the
[drawdata](https://github.com/koaning/drawdata) canvas becomes a first-class
Shiny input. Users draw a dataset with the brush (up to 4 classes on
`ScatterWidget`, or drag histogram bars on `BarWidget`), and Python sees every
batch through `reactive_read(widget, "data")` -- this app re-fits a k-NN
classifier on your drawing and re-renders the decision boundary live.

Two things to know about:

- `ScatterWidget` syncs drawn data to Python **one batch behind**: the first
  stroke only reaches Python when a second is drawn (upstream drawdata
  [issue #40](https://github.com/koaning/drawdata/issues/40), which affects
  Jupyter too). The undo and reset buttons sync immediately.
- Both widgets have an intrinsic pixel size, so the output hugs the widget
  instead of filling its container. Size the drawing surface through the
  constructor (`ScatterWidget(width=1000, height=500)`); `BarWidget` renders
  a fixed-size SVG that doesn't shrink, so give it room (and note it
  overwrites constructor-provided `data` at first render and ignores later
  Python-side trait updates until the next re-render).
