from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from packaging.version import Version
from shiny import Session
from shiny.session import session_context
from shinywidgets._comm import OrphanedShinyComm


def test_orphaned_comm_has_no_kernel() -> None:
    assert OrphanedShinyComm("x").kernel is None


def test_ipyvue_does_not_cache_templates_under_shinywidgets(
    widget_session: Session, tmp_path: Path
) -> None:
    path = tmp_path / "template.vue"
    path.write_text("<template><div>hi</div></template>")

    with session_context(widget_session):
        # Importing ipyvue constructs a widget (ForceLoad), which shinywidgets
        # only allows inside a session.
        ipyvue = pytest.importorskip("ipyvue")
        if Version(ipyvue.__version__) < Version("3"):
            pytest.skip("ipyvue < 3 caches templates regardless of comm kind")

        template_module = sys.modules["ipyvue.Template"]
        first = template_module.get_template(str(path))
        second = template_module.get_template(str(path))
        try:
            assert first is not second
            assert os.path.normpath(path) not in template_module.template_registry
        finally:
            first.close()
            second.close()
