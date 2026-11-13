# Conway's Game of Life: click cells to seed a pattern, then let a Shiny
# timer step the simulation. A clean starting point for any canvas app that
# mixes click-to-edit state with a Python-driven animation loop.
# bucket: template
# run: uv run shiny run template_game_of_life.py
# data: none (synthetic cellular automaton)

import numpy as np
from ipycanvas import Canvas
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_ipycanvas

ui.page_opts(title="Conway's Game of Life", fillable=True)

N, CELL = 50, 10
ALIVE = np.uint8([34, 139, 87, 255])
DEAD = np.uint8([245, 245, 240, 255])

# The grid itself is plain mutable state (not a reactive.value): every writer
# below redraws the canvas directly afterwards, so nothing needs to *react*
# to it changing.
grid = np.zeros((N, N), dtype=bool)
generation = 0
running = reactive.value(False)


def step(g: np.ndarray) -> np.ndarray:
    neighbors = sum(
        np.roll(np.roll(g, dy, 0), dx, 1)
        for dy in (-1, 0, 1)
        for dx in (-1, 0, 1)
        if (dy, dx) != (0, 0)
    )
    return (neighbors == 3) | (g & (neighbors == 2))


def to_rgba(g: np.ndarray) -> np.ndarray:
    rgba = np.where(g[..., None], ALIVE, DEAD)
    return np.kron(rgba, np.ones((CELL, CELL, 1), dtype=np.uint8))


def redraw(c: Canvas) -> None:
    c.put_image_data(to_rgba(grid), 0, 0)
    c.fill_style = "#222"
    c.font = "14px monospace"
    c.fill_text(f"Generation: {generation}", 6, N * CELL - 8)


with ui.layout_columns(col_widths=(9, 3)):
    with ui.card(full_screen=True):
        ui.p("Click cells to seed a pattern (while paused), then press Play.")

        @render_ipycanvas
        def canvas():
            c = Canvas(width=N * CELL, height=N * CELL)
            redraw(c)

            def on_click(x, y):
                global grid
                if running():
                    return
                i, j = int(y // CELL), int(x // CELL)
                grid = grid.copy()
                grid[i, j] = not grid[i, j]
                redraw(c)

            c.on_mouse_down(on_click)
            return c

    with ui.card():
        ui.card_header("Controls")
        ui.input_action_button("toggle", "Play / pause", class_="mb-2")
        ui.input_action_button("randomize", "Randomize", class_="mb-2")
        ui.input_action_button("clear", "Clear", class_="mb-2")


@reactive.effect
@reactive.event(input.toggle)
def _():
    running.set(not running())


@reactive.effect
@reactive.event(input.randomize)
def _():
    global grid, generation
    rng = np.random.default_rng()
    grid = rng.random((N, N)) < 0.3
    generation = 0
    c = canvas.widget
    if c is not None:
        redraw(c)


@reactive.effect
@reactive.event(input.clear)
def _():
    global grid, generation
    grid = np.zeros((N, N), dtype=bool)
    generation = 0
    c = canvas.widget
    if c is not None:
        redraw(c)


# The one effect responsible for pushing `grid` to the browser: reading
# `.widget` here (not inside the render function above) means toggling,
# randomizing, clearing, and ticking all update the same canvas in place --
# the render function above only ever runs once.
@reactive.effect
def _tick():
    global grid, generation
    reactive.invalidate_later(0.12)
    if not running():
        return
    grid = step(grid)
    generation += 1
    c = canvas.widget
    if c is not None:
        redraw(c)
