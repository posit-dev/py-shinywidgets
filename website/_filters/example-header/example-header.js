// Collapse, copy, and open-in-Shinylive for example code headers (see example-header.lua).
(function () {
  const SHINYLIVE = "https://shinylive.io/py/editor/#code=";
  let bundles;

  function shinyliveUrl(key) {
    if (bundles === undefined) {
      const el = document.getElementById("sw-example-bundles");
      bundles = el ? JSON.parse(el.textContent) : null;
    }
    const files = bundles && bundles[key];
    if (!files || typeof LZString === "undefined") return null;
    return SHINYLIVE + LZString.compressToEncodedURIComponent(JSON.stringify(files));
  }

  function toggle(example) {
    const collapsed = example.classList.toggle("sw-collapsed");
    example.querySelector(".sw-example-toggle").setAttribute("aria-expanded", String(!collapsed));
  }

  function flash(button, text) {
    const label = button.getAttribute("title");
    button.setAttribute("title", text);
    button.setAttribute("aria-label", text);
    setTimeout(() => {
      button.setAttribute("title", label);
      button.setAttribute("aria-label", label);
    }, 1200);
  }

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;

    const live = target.closest('[data-action="shinylive"], a.sw-shinylive-link');
    if (live) {
      // No bundle or LZString: fall through to the raw .py href.
      const url = shinyliveUrl(live.getAttribute("data-example"));
      if (url) {
        event.preventDefault();
        window.open(url, "_blank", "noopener");
      }
      return;
    }

    const example = target.closest(".sw-example");
    if (!example) return;

    const copy = target.closest('[data-action="copy"]');
    if (copy) {
      const code = example.querySelector(".sw-example-code code");
      navigator.clipboard.writeText(code ? code.textContent : "").then(() => flash(copy, "Copied!"));
      return;
    }

    if (target.closest(".sw-example-toggle")) {
      toggle(example);
    } else if (target.closest(".sw-example-bar") && !target.closest("a, button")) {
      toggle(example);
    }
  });
})();
