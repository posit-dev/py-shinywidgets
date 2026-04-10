"""
Optional coverage.py subprocess support.

If a Python subprocess inherits `COVERAGE_PROCESS_START=/path/to/.coveragerc`,
coverage will automatically start collecting in that process.
"""

import os


def _maybe_start_coverage() -> None:
    if not os.environ.get("COVERAGE_PROCESS_START"):
        return

    try:
        import coverage
    except Exception:
        # Don't break runtime if coverage isn't installed.
        return

    try:
        coverage.process_startup()
    except Exception:
        # Be defensive: sitecustomize executes on interpreter startup.
        return


_maybe_start_coverage()

