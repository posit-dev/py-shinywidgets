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
- Both widgets fill their container's width while preserving aspect ratio
  (upstream caps the display at the `width`/`height` traits; shinywidgets
  lifts that cap). The constructor's `width`/`height`
  (`ScatterWidget(width=1000, height=500)`) define the drawing's *data
  coordinate space* -- drawn points come back in those coordinates, y-up --
  and the aspect ratio, not the display size. Also note that `BarWidget`
  always starts empty: its frontend overwrites constructor-provided `data`
  at first render (seeding is impossible, even via a re-render) and ignores
  later Python-side trait updates until the next re-render (upstream
  drawdata [issue #42](https://github.com/koaning/drawdata/issues/42)), so
  re-render -- return a new `BarWidget` -- to change settings like
  `n_bins`. Avoid two `BarWidget`s on the same page for now: their
  collection buttons interfere
  ([issue #43](https://github.com/koaning/drawdata/issues/43)).
