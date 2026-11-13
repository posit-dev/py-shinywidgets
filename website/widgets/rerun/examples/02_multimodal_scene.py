from __future__ import annotations

import os

if "RERUN_NOTEBOOK_ASSET" not in os.environ:
    os.environ["RERUN_NOTEBOOK_ASSET"] = "serve-local"

import numpy as np
import rerun as rr
from rerun.notebook import Viewer
from shiny.express import ui

from shinywidgets import render_rerun

N_STEPS = 60


def make_path() -> np.ndarray:
    t = np.linspace(0, 4 * np.pi, N_STEPS)
    r = 1.5 + 0.12 * t
    return np.column_stack([r * np.cos(t), r * np.sin(t), np.zeros(N_STEPS)])


def camera_frame(step: int) -> np.ndarray:
    # A synthetic 32x24 camera frame (sky/ground gradient plus a bright marker
    # that drifts across the frame), standing in for a tracked object.
    img = np.zeros((24, 32, 3), dtype=np.uint8)
    img[:12] = (135, 206, 235)
    img[12:] = (120, 100, 70)
    x = int((np.sin(step / 6) * 0.5 + 0.5) * 26)
    img[8:14, x : x + 4] = (255, 80, 80)
    return img


OBSTACLES = np.array([[2.4, 1.2, 0.3], [-1.6, -2.6, 0.3], [3.2, -1.4, 0.3]])

ui.page_opts(title="A multimodal robot scene", fillable=True)

with ui.card(full_screen=True):

    @render_rerun
    def viewer():
        rec = rr.RecordingStream(application_id="multimodal_scene")
        path = make_path()

        rec.log("world/path", rr.LineStrips3D([path]), static=True)
        rec.log(
            "world/obstacles",
            rr.Boxes3D(centers=OBSTACLES, half_sizes=[(0.4, 0.4, 0.6)] * 3, colors=[(239, 71, 111)]),
            static=True,
        )
        # The pinhole's intrinsics don't change over time, so log them once;
        # the frustum then rides whatever transform its parent entity has at
        # each timeline step.
        rec.log(
            "world/robot/camera",
            rr.Pinhole(width=32, height=24, focal_length=28, image_plane_distance=0.6),
            static=True,
        )

        for i in range(N_STEPS):
            rec.set_time("step", sequence=i)
            dx, dy, _ = path[min(i + 1, N_STEPS - 1)] - path[i]
            heading = np.arctan2(dy, dx)
            rec.log(
                "world/robot",
                rr.Transform3D(
                    translation=path[i],
                    rotation=rr.RotationAxisAngle(axis=[0, 0, 1], radians=heading),
                ),
            )
            rec.log("world/robot/camera/image", rr.Image(camera_frame(i)))
            rec.log("robot/speed", rr.Scalars(1.0 + 0.3 * np.sin(i / 5)))
            rec.log("robot/battery", rr.Scalars(100 - i * 0.6))
            if i == N_STEPS // 3:
                rec.log("robot/log", rr.TextLog("obstacle sighted", level="INFO"))
            if i == 2 * N_STEPS // 3:
                rec.log("robot/log", rr.TextLog("waypoint reached", level="INFO"))

        return Viewer(width="auto", height="auto", recording=rec)
