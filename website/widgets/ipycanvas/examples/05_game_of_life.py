import numpy as np
from ipycanvas import Canvas
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_ipycanvas

ui.page_opts(title="Game of Life", fillable=True)

N, CELL = 60, 6  # an N x N grid of CELL-pixel-square cells
rng = np.random.default_rng(3)
grid = rng.random((N, N)) < 0.25


def step(g: np.ndarray) -> np.ndarray:
    neighbors = sum(
        np.roll(np.roll(g, dy, 0), dx, 1)
        for dy in (-1, 0, 1)
        for dx in (-1, 0, 1)
        if (dy, dx) != (0, 0)
    )
    return (neighbors == 3) | (g & (neighbors == 2))


def grid_to_rgba(g: np.ndarray) -> np.ndarray:
    rgba = np.where(g[..., None], np.uint8([34, 139, 87, 255]), np.uint8([245, 245, 240, 255]))
    return np.kron(rgba, np.ones((CELL, CELL, 1), dtype=np.uint8))


with ui.card(full_screen=True):
    ui.input_action_button("toggle", "Play/pause", class_="mb-2")

    @render_ipycanvas
    def life():
        c = Canvas(width=N * CELL, height=N * CELL)
        c.put_image_data(grid_to_rgba(grid), 0, 0)
        return c

    running = reactive.value(True)

    @reactive.effect
    @reactive.event(input.toggle)
    def _():
        running.set(not running())

    @reactive.effect
    def _tick():
        global grid
        reactive.invalidate_later(0.15)
        if not running():
            return
        grid = step(grid)
        c = life.widget
        if c is not None:
            c.put_image_data(grid_to_rgba(grid), 0, 0)
