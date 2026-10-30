from __future__ import annotations

import pytest
import shinywidgets._k3d as sk
import shinywidgets._render_widget as rw
from shiny import Session
from shiny.session import session_context


def test_camera_cancels_until_auto_fit_reports(widget_session: Session) -> None:
    import k3d

    with session_context(widget_session):
        plot = k3d.plot()
        plot += k3d.points([[0, 0, 0]])
    r = rw.render_k3d()
    r._widget = plot  # stands in for _render()
    r._accessors.on_render(plot)
    from shiny.types import SilentException

    with pytest.raises(SilentException):
        r.camera()  # camera is [] until the browser auto-fits
    plot.camera = [1, 2, 3, 0, 0, 0, 0, 0, 1]  # what auto-fit syncs back
    assert r.camera() == [1, 2, 3, 0, 0, 0, 0, 0, 1]
    plot.camera = [9] * 9  # an orbit updates it
    assert r.camera() == [9] * 9


def test_camera_not_ready_tolerates_lists_and_arrays() -> None:
    import numpy as np

    assert sk.CAMERA.not_ready([])
    assert sk.CAMERA.not_ready(np.array([]))
    assert not sk.CAMERA.not_ready([0] * 9)
    assert not sk.CAMERA.not_ready(np.zeros(9))
