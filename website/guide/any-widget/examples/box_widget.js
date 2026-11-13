// The identical widget as 06_esm_sources.py's inline `_esm` string, as a
// sibling file -- pass `_esm=Path(__file__).parent / "box_widget.js"` instead
// of a string to load from here. anywidget re-reads the file on every new
// widget model, so editing this file and re-rendering (no Python restart
// needed) is the point: a faster edit loop than an inline string.
function render({ model, el }) {
  const box = document.createElement("div");
  box.textContent = "click me";
  box.style.cssText =
    "display:flex;align-items:center;justify-content:center;" +
    "width:160px;height:90px;border-radius:8px;cursor:pointer;" +
    "background:#2a6f97;color:white;font:14px sans-serif;";
  let n = 0;
  box.addEventListener("click", () => {
    n += 1;
    box.textContent = `clicked ${n}x`;
    model.set("clicks", n);
    model.save_changes();
  });
  el.appendChild(box);
}
export default { render };
