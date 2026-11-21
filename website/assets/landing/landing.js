// Landing page behavior: the hero wall, the code tabs, and the gallery stage.
// Data comes from landing-data.js (WALL, TABS, SHOWCASES), loaded first.
(() => {
  const IMG = "assets/landing/img/";
  const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (id) => document.getElementById(id);

  // Hero wall: columns of tiles, each column's set repeated once so the drift
  // loops seamlessly. The drift translates a column up by half its height, so
  // each half must stay taller than the wall (plus slack for the wall's
  // rotate/scale) through the whole loop — a fixed four tiles per column leaves
  // tall, narrow windows with empty space at the bottom.
  const wall = $("wall");
  const narrow = window.matchMedia("(max-width: 900px)");
  function buildWall() {
    const cols = narrow.matches ? 3 : 6;
    const tileH = ((wall.clientWidth - (cols - 1) * 14) / cols) * 0.75 + 14;
    const per = Math.max(4, Math.ceil((wall.clientHeight * 1.3) / tileH));
    wall.replaceChildren();
    for (let c = 0; c < cols; c++) {
      const col = document.createElement("div");
      col.className = "col";
      for (let r = 0; r < 2; r++)
        for (let i = 0; i < per; i++) {
          const tile = document.createElement("div");
          tile.className = "tile";
          tile.style.backgroundImage = `url(${IMG}wall-${WALL[(c * per + i) % WALL.length]}.webp)`;
          col.appendChild(tile);
        }
      wall.appendChild(col);
    }
  }
  buildWall();
  let wallTimer;
  window.addEventListener("resize", () => {
    clearTimeout(wallTimer);
    wallTimer = setTimeout(buildWall, 200);
  });

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
  // before to after), then advance. It waits until the screen is in view, and coming
  // back into view restarts the current app. Hovering the screenshot pauses it
  // mid-gesture and leaving resumes it; the app list doesn't pause, so a picked app
  // plays. Reduced motion shows each app's "after" state directly.
  const DUR = 7000;
  const STEPS = [
    [1600, () => screen.classList.add("gesture")],
    [2600, () => screen.classList.add("after")],
    [5600, () => screen.classList.remove("gesture")],
    [DUR, () => go((cur + 1) % SHOWCASES.length)],
  ];
  const picker = $("picker"), screen = $("screen"), stage = $("stage");
  const browser = stage.querySelector(".browser");
  let cur = 0, timers = [], paused = false, visible = false, started = 0;
  // While paused mid-gesture: how far into it (ms), and the CSS animations/transitions
  // frozen with it.
  let held = null, frozen = [];
  const clear = () => { timers.forEach(clearTimeout); timers = []; };
  function play(from) {
    clear();
    started = performance.now() - from;
    for (const [t, f] of STEPS) if (t > from) timers.push(setTimeout(f, t - from));
  }
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
    // A paused animation outlives the CSS that started it (it would stay frozen, or
    // keep running on the inactive bar once played), so drop it.
    frozen.forEach((a) => a.cancel());
    frozen = [];
    held = null;
    if (calm) {
      screen.className = "screen after gesture";
      return;
    }
    screen.className = "screen";
    if (!visible) return;
    void screen.offsetWidth;
    screen.classList.add("zoom");
    play(0);
  }
  // Pointer over the screenshot, or keyboard focus inside it, pauses autoplay. (Focus
  // a click leaves on its link doesn't, or it would stay paused off hover.)
  const pause = () => {
    paused = true;
    stage.classList.add("paused");
    if (!timers.length) return;
    held = performance.now() - started;
    clear();
    // Finished animations are left alone: play() would rewind them.
    frozen = [
      ...screen.getAnimations({ subtree: true }),
      ...picker.querySelector("li.on .bar i").getAnimations(),
    ].filter((a) => a.playState === "running");
    frozen.forEach((a) => a.pause());
  };
  const resume = () => {
    if (!paused || browser.matches(":hover") || browser.querySelector(":focus-visible")) return;
    paused = false;
    stage.classList.remove("paused");
    if (held === null) return go(cur);
    frozen.forEach((a) => a.play());
    frozen = [];
    play(held);
    held = null;
  };
  browser.addEventListener("mouseenter", pause);
  browser.addEventListener("mouseleave", resume);
  browser.addEventListener("focusin", (e) => {
    if (e.target.matches(":focus-visible")) pause();
  });
  browser.addEventListener("focusout", () => setTimeout(resume));
  if (calm) stage.classList.add("calm");
  stage.classList.add("offscreen");
  go(0);
  new IntersectionObserver(([e]) => {
    // isIntersecting stays true while the ratio falls from 0.5 to 0, so gate on
    // the ratio itself: otherwise scrolling away restarts the showcase and
    // autoplay keeps running below the 50% threshold.
    visible = e.intersectionRatio >= 0.5;
    stage.classList.toggle("offscreen", !visible);
    if (visible) {
      if (!paused) go(cur);
    } else {
      clear();
      held = null;
    }
  }, { threshold: 0.5 }).observe(screen);
})();
