// Landing page behavior: the hero wall, the code tabs, and the gallery stage.
// Data comes from landing-data.js (WALL, TABS, SHOWCASES), loaded first.
(() => {
  const IMG = "assets/landing/img/";
  const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (id) => document.getElementById(id);

  // Hero wall: six columns, each its four tiles twice so the drift loops seamlessly.
  const wall = $("wall");
  for (let c = 0; c < 6; c++) {
    const col = document.createElement("div");
    col.className = "col";
    const pick = [0, 1, 2, 3].map((i) => WALL[(c * 4 + i) % WALL.length]);
    for (const slug of [...pick, ...pick]) {
      const tile = document.createElement("div");
      tile.className = "tile";
      tile.style.backgroundImage = `url(${IMG}wall-${slug}.webp)`;
      col.appendChild(tile);
    }
    wall.appendChild(col);
  }

  // "See it in code": tabs, highlighted snippet, before/after screenshot.
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const highlight = (src) =>
    esc(src).replace(
      /(⟦[^⟧]*⟧)|("(?:[^"\\]|\\.)*")|(^\s*@[\w.]+)|\b(import|from|as|def|return|for|in|if|is|None|True|with)\b/gm,
      (m, acc, str, dec, kw) =>
        acc ? `<span class="acc">${acc.slice(1, -1)}</span>`
          : str ? `<span class="str">${str}</span>`
          : dec ? `<span class="dec">${dec}</span>`
          : `<span class="kw">${kw}</span>`
    );
  const tabs = $("tabs"), shot = $("shot"), ctrl = $("ctrl"), gesture = $("gesture");
  let tab = 0;
  function showTab(i, state) {
    tab = i;
    const t = TABS[i];
    const s = t.before ? state : 1;
    $("code").innerHTML = highlight(t.code);
    const src = $("src");
    src.textContent = t.src.replace(/^(widgets|guide)\//, "").replace("/examples/", "/");
    src.href = t.src;
    shot.src = `${IMG}tab-${t.id}-${s}.webp`;
    shot.alt = `${t.label} example, ${s ? "after" : "before"} the gesture`;
    ctrl.hidden = !t.before;
    for (const b of ctrl.children) b.classList.toggle("on", +b.dataset.s === s);
    gesture.hidden = !t.gesture || !t.before;
    gesture.textContent = `gesture: ${t.gesture}`;
    [...tabs.children].forEach((b, j) => {
      b.classList.toggle("on", j === i);
      b.setAttribute("aria-selected", j === i);
    });
  }
  TABS.forEach((t, i) => {
    const b = document.createElement("button");
    b.className = "tab";
    b.type = "button";
    b.setAttribute("role", "tab");
    b.textContent = t.label;
    b.onclick = () => showTab(i, 1);
    tabs.appendChild(b);
  });
  for (const b of ctrl.children) b.onclick = () => showTab(tab, +b.dataset.s);
  showTab(0, 1);

  // The stage: every DUR ms, play the current app's gesture (caption, crossfade from
  // before to after), then advance. Hovering pauses it; reduced motion turns it off and
  // shows each app's "after" state directly.
  const DUR = 7000;
  const picker = $("picker"), screen = $("screen"), stage = $("stage");
  let cur = 0, timers = [], paused = false;
  const clear = () => { timers.forEach(clearTimeout); timers = []; };
  SHOWCASES.forEach((s, i) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="bar"><i></i></span><button type="button"><h3>${s.title}<small>${s.widgets[0]}</small></h3></button><p>${s.blurb}</p>`;
    li.onclick = () => go(i);
    picker.appendChild(li);
  });
  function go(i) {
    clear();
    cur = i;
    const s = SHOWCASES[i];
    [...picker.children].forEach((li, j) => {
      li.classList.toggle("on", j === i);
      li.querySelector("button").setAttribute("aria-current", j === i);
      li.style.setProperty("--dur", DUR + "ms");
      const bar = li.querySelector(".bar i");
      bar.style.animation = "none";
      void bar.offsetWidth;
      bar.style.animation = "";
    });
    $("s0").src = `${IMG}show-${s.id}-0.webp`;
    $("s1").src = `${IMG}show-${s.id}-1.webp`;
    $("s0").alt = `${s.title}, before: ${s.gesture}`;
    $("s1").alt = `${s.title}, after: ${s.gesture}`;
    $("url").textContent = `127.0.0.1:8000 — ${s.title}`;
    $("gest").textContent = s.gesture;
    $("wchips").innerHTML = s.widgets.map((w) => `<span>${w}</span>`).join("");
    $("meta").textContent = `${s.lines} lines · app.py`;
    $("view-src").href = s.href;
    if (calm || paused) {
      screen.className = "screen after gesture";
      return;
    }
    screen.className = "screen";
    void screen.offsetWidth;
    screen.classList.add("zoom");
    timers.push(setTimeout(() => screen.classList.add("gesture"), 1600));
    timers.push(setTimeout(() => screen.classList.add("after"), 2600));
    timers.push(setTimeout(() => screen.classList.remove("gesture"), 5600));
    timers.push(setTimeout(() => go((cur + 1) % SHOWCASES.length), DUR));
  }
  // Pointer over the stage, or keyboard focus inside it, pauses autoplay.
  const pause = () => {
    paused = true;
    clear();
    stage.classList.add("paused");
  };
  const resume = () => {
    if (stage.matches(":hover") || stage.contains(document.activeElement)) return;
    paused = false;
    stage.classList.remove("paused");
    go(cur);
  };
  stage.addEventListener("mouseenter", pause);
  stage.addEventListener("mouseleave", resume);
  stage.addEventListener("focusin", pause);
  stage.addEventListener("focusout", () => setTimeout(resume));
  if (calm) stage.classList.add("calm");
  go(0);
})();
