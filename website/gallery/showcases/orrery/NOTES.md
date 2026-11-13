# NOTES: orrery

- Promoted from `docs/widget-guides/pythreejs/gallery/showcase_orrery.py`, unchanged except
  the `# run:` header line.
- Re-verified 2026-11-02 in `main-wt`: pythreejs 2.4.2, already in the shared venv. No
  `--with` overlay needed.
- The pythreejs guide's own finding (DirectionalLight/SpotLight default target/shadow leak a
  few browser-created models per re-render) does not apply here: this showcase's clock
  effect never re-renders the scene (it mutates `.position` on existing meshes), so the leak
  path is never exercised during normal playback. A user-triggered re-render (e.g. changing
  an input that rebuilds `scene_graph`) isn't part of this app's UI.

## Verification table

| Gesture | Driven | Server-state confirmed |
|---|---|---|
| Load + scene renders (planets orbiting) | yes (Playwright, swiftshader WebGL flags) | `#scene canvas` visible, `img/hero.webp` |
| Real click at canvas center | yes | `#picked` changed from `"click a planet"` to `"clicked the sun"`, `img/after_click.webp` |

An earlier attempt aimed at a specific planet's expected position (read off the hero
screenshot) missed, since the planets had moved by click time (the clock keeps running
during the gesture); switched to a canvas-center click, which reliably hits the sun since it
sits at the scene origin. Did not separately re-verify the Speed/Playing controls or the
Reset-view button in this pass.

## Judgment calls

- None beyond the header-line edit.
