# A small, hand-written anywidget used by several examples in this guide
# (03_anywidget_trait_sync.py, 04_anywidget_messages.py, 07_accessor_helper.py,
# 11_coordinate_brush_to_table.py, 12_coordinate_table_to_widget.py). Defined
# once here so each example stays short; none of this file is Shiny-specific
# -- it is exactly what you'd write for plain Jupyter too.
from __future__ import annotations

import anywidget
import traitlets

_JS = r"""
function render({ model, el }) {
  const canvas = document.createElement("canvas");
  canvas.width = 320;
  canvas.height = 90;
  // shinywidgets gives a fill output's direct child `flex: 1 1 auto` so
  // generic (e.g. <div>-based) widgets stretch to fill their card. A
  // <canvas>'s width/height ATTRIBUTES (its drawing-buffer resolution)
  // don't count as a CSS size for that purpose, so without an explicit
  // style.width/height a canvas gets stretched to fill the card while its
  // pixel buffer stays at 320x90 -- a blurry, upscaled line. Pinning the
  // CSS size to match keeps it crisp (see "Layout and sizing" in the
  // guide for the fill-aware alternative: a ResizeObserver that redraws at
  // the new size).
  canvas.style.width = canvas.width + "px";
  canvas.style.height = canvas.height + "px";
  canvas.style.cursor = "pointer";
  el.appendChild(canvas);
  const ctx = canvas.getContext("2d");

  function draw() {
    const values = model.get("values");
    const highlight = model.get("highlight") || [];
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (values.length < 2) return;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    const xy = (i) => [
      (i / (values.length - 1)) * canvas.width,
      canvas.height - ((values[i] - min) / span) * (canvas.height - 10) - 5,
    ];

    ctx.beginPath();
    values.forEach((_, i) => {
      const [x, y] = xy(i);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.strokeStyle = "#2a6f97";
    ctx.lineWidth = 2;
    ctx.stroke();

    // Rows in `highlight` (e.g. a linked table's selection) get a dot.
    highlight.forEach((i) => {
      if (i < 0 || i >= values.length) return;
      const [x, y] = xy(i);
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, 2 * Math.PI);
      ctx.fillStyle = "#e85d04";
      ctx.fill();
    });
  }

  // Python -> JS: redraw whenever `values` or `highlight` changes, in place
  // (no new widget, no re-sent JS bundle -- see "Updating the widget from
  // Python" in the guide).
  model.on("change:values", draw);
  model.on("change:highlight", draw);

  // JS -> Python: a click (or a drag -- see mousemove below) reports the
  // nearest point's index via a synced trait. `save_changes()` is what
  // actually flushes the `model.set()` call to Python;
  // `spark.read("clicked_index")` on the Python side picks it up (see
  // "Reacting to user interaction").
  // The canvas's CSS size (it stretches to fill its card) differs from its
  // drawing-buffer size (canvas.width/height, used by draw() above), so
  // input handlers must convert through the rendered bounding box, not the
  // intrinsic pixel size.
  function indexAt(e) {
    const values = model.get("values");
    const rect = canvas.getBoundingClientRect();
    const frac = (e.clientX - rect.left) / rect.width;
    const i = Math.round(frac * (values.length - 1));
    return Math.max(0, Math.min(values.length - 1, i));
  }
  function reportNearest(e) {
    model.set("clicked_index", indexAt(e));
    model.save_changes();
  }
  canvas.addEventListener("click", reportNearest);

  // A held-down drag reports a rapid stream of updates -- used by the rate
  // limiting example to compare an unthrottled vs. a debounced reader. It
  // also reports the drag's start..end index range as `brush` once released
  // -- used by the "coordinating multiple views" brush-to-table example.
  let dragStart = null;
  canvas.addEventListener("mousedown", (e) => (dragStart = indexAt(e)));
  window.addEventListener("mouseup", (e) => {
    if (dragStart === null) return;
    const end = indexAt(e);
    model.set("brush", [Math.min(dragStart, end), Math.max(dragStart, end)]);
    model.save_changes();
    dragStart = null;
  });
  canvas.addEventListener("mousemove", (e) => {
    if (dragStart !== null) reportNearest(e);
  });

  // Custom messages, JS -> Python: model.send() for a one-off event that
  // isn't really "state" (see "Custom messages" in the guide).
  canvas.addEventListener("dblclick", () => {
    model.send({ type: "reset-requested" });
  });

  // Custom messages, Python -> JS: widget.send() on the Python side arrives
  // here as a "msg:custom" model event.
  model.on("msg:custom", (msg) => {
    if (msg.type === "flash") {
      canvas.style.filter = "brightness(1.6)";
      setTimeout(() => {
        canvas.style.filter = "";
      }, 200);
    }
  });

  draw();
}
export default { render };
"""

_CSS = """
.sparkline-widget canvas { display: block; }
"""


class Sparkline(anywidget.AnyWidget):
    """A tiny canvas line chart. See sparkline_widget.py for the full source."""

    _esm = _JS
    _css = _CSS
    values = traitlets.List(traitlets.Float()).tag(sync=True)
    highlight = traitlets.List(traitlets.Int()).tag(sync=True)
    clicked_index = traitlets.Int(allow_none=True, default_value=None).tag(sync=True)
    brush = traitlets.List(traitlets.Int()).tag(sync=True)


class BinarySparkline(anywidget.AnyWidget):
    """
    Same chart, but `values` is a packed float32 buffer (`numpy.ndarray.tobytes()`)
    instead of a JSON list -- see 05_anywidget_binary_trait.py.
    """

    _esm = r"""
    function render({ model, el }) {
      const canvas = document.createElement("canvas");
      canvas.width = 320;
      canvas.height = 90;
      // See the matching comment in Sparkline's _esm above: pin the CSS size
      // to the drawing-buffer size so the fill layout can't stretch (and
      // blur) this canvas.
      canvas.style.width = canvas.width + "px";
      canvas.style.height = canvas.height + "px";
      el.appendChild(canvas);
      const ctx = canvas.getContext("2d");

      function draw() {
        // A `Bytes` trait arrives as a DataView; read it as float32.
        const buf = model.get("values");
        const values = new Float32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        if (values.length < 2) return;
        let min = Infinity, max = -Infinity;
        for (const v of values) { if (v < min) min = v; if (v > max) max = v; }
        const span = max - min || 1;
        ctx.beginPath();
        values.forEach((v, i) => {
          const x = (i / (values.length - 1)) * canvas.width;
          const y = canvas.height - ((v - min) / span) * (canvas.height - 10) - 5;
          i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        });
        ctx.strokeStyle = "#9d4edd";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
      model.on("change:values", draw);
      draw();
    }
    export default { render };
    """
    _css = _CSS
    values = traitlets.Bytes().tag(sync=True)
