"""Headless-Chromium smoke runner for a single shinywidgets app.

Usage: uv run --no-sync python docs/widget-guides/tools/smoke.py APP.py [--shot OUT.webp]
       [--gpu {none,webgl,webgpu}] [--wait SELECTOR]

Starts `python -m shiny run` on a free port, loads the page in headless Chromium, waits
for a rendered widget (".shiny-ipywidget-output .lm-Widget", or --wait), and fails
(exit 1) on a server traceback, a server-log ERROR line, a shinywidgets logger
exception, an uncaught page error, or a 60s timeout. Always stops the server before
exiting.

A widget that raises asynchronously (e.g. after the browser's first round trip)
can satisfy --wait's selector before the error surfaces -- the wait condition is
element presence, not "rendered without error". The server-log checks below catch
that case even when the page itself looks fine: a widget callback's exception is
caught by ipywidgets and logged to the `traitlets` logger (which has no handler and
would otherwise vanish silently under a Shiny server); shinywidgets'
`ClientMsgErrorFilter` (`_comm.py`) reroutes it to the `shinywidgets` logger instead,
as a line starting with "Exception in widget method". Neither logger has a configured
handler (only uvicorn's own loggers do), so the record reaches Python's
`logging.lastResort` handler with no level prefix -- hence matching on the literal
message text, not on an "ERROR:" prefix, which is why a bare "ERROR" line is checked
for separately (it catches a differently-configured deployment, or an error uvicorn
itself logs with its own prefixed formatter).
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

DEFAULT_WAIT_SELECTOR = ".shiny-ipywidget-output .lm-Widget"
WAIT_TIMEOUT_SECONDS = 60.0
POLL_INTERVAL_SECONDS = 0.5
SETTLE_SECONDS = 0.5
TRACEBACK_MARKER = "Traceback (most recent call last):"
SHINYWIDGETS_EXCEPTION_MARKER = "Exception in widget method"
ERROR_LINE_PATTERN = re.compile(r"^ERROR\b", re.MULTILINE)
PORT_PREFIX = "http://127.0.0.1:"

GPU_ARGS: dict[str, list[str]] = {
    "none": [],
    "webgl": [
        "--use-angle=swiftshader",
        "--enable-unsafe-swiftshader",
        "--ignore-gpu-blocklist",
    ],
    "webgpu": ["--enable-unsafe-webgpu", "--use-angle=metal"],
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path, help="path to the Shiny app .py file")
    parser.add_argument(
        "--shot", type=Path, default=None, help="save a screenshot here"
    )
    parser.add_argument(
        "--gpu",
        choices=sorted(GPU_ARGS),
        default="none",
        help="GPU flags to launch Chromium with",
    )
    parser.add_argument(
        "--wait",
        dest="wait_selector",
        default=DEFAULT_WAIT_SELECTOR,
        help="CSS selector to wait for",
    )
    args = parser.parse_args(argv)

    return run_smoke(args.app, args.shot, args.gpu, args.wait_selector)


def run_smoke(app: Path, shot: Path | None, gpu: str, wait_selector: str) -> int:
    log_fd, log_name = tempfile.mkstemp(prefix="shinywidgets-smoke-", suffix=".log")
    log_path = Path(log_name)
    server_process: subprocess.Popen[bytes] | None = None
    try:
        with open(log_fd, "wb") as log_file:
            server_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "shiny",
                    "run",
                    str(app),
                    "--port",
                    "0",
                    "--host",
                    "127.0.0.1",
                ],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
            return wait_for_outcome(server_process, log_path, gpu, wait_selector, shot)
    finally:
        stop_server(server_process)
        log_path.unlink(missing_ok=True)


def wait_for_outcome(
    server_process: subprocess.Popen[bytes],
    log_path: Path,
    gpu: str,
    wait_selector: str,
    shot: Path | None,
) -> int:
    deadline = time.monotonic() + WAIT_TIMEOUT_SECONDS
    port: int | None = None
    page_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=GPU_ARGS[gpu])
        try:
            page = None
            while time.monotonic() < deadline:
                if server_process.poll() is not None and port is None:
                    print(f"server exited early:\n{read_log(log_path)}")
                    return 1

                log_text = read_log(log_path)
                traceback_text = extract_traceback(log_text)
                if traceback_text is not None:
                    print(f"server traceback:\n{traceback_text}")
                    return 1

                server_error = extract_server_error(log_text)
                if server_error is not None:
                    print(f"server log error:\n{server_error}")
                    return 1

                if port is None:
                    port = find_port(log_text)
                    if port is not None:
                        page = browser.new_page(device_scale_factor=2)
                        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
                        page.goto(f"{PORT_PREFIX}{port}/")

                if page is not None:
                    if page_errors:
                        print(f"uncaught page error: {page_errors[0]}")
                        return 1
                    if page.query_selector(wait_selector) is not None:
                        # Element presence isn't "rendered without error": a widget
                        # that raises asynchronously (e.g. on a later round trip) can
                        # satisfy this selector before its own server-log error
                        # appears. Settle once more and re-check the log before
                        # declaring success.
                        time.sleep(SETTLE_SECONDS)
                        settled_log_text = read_log(log_path)
                        server_error = extract_server_error(settled_log_text)
                        if server_error is not None:
                            print(f"server log error:\n{server_error}")
                            return 1
                        if shot is not None:
                            page.screenshot(path=str(shot))
                        return 0

                time.sleep(POLL_INTERVAL_SECONDS)

            print(
                f"timed out after {WAIT_TIMEOUT_SECONDS:.0f}s waiting for {wait_selector!r}"
            )
            return 1
        finally:
            browser.close()


def find_port(log_text: str) -> int | None:
    start = log_text.find(PORT_PREFIX)
    if start == -1:
        return None
    start += len(PORT_PREFIX)
    end = start
    while end < len(log_text) and log_text[end].isdigit():
        end += 1
    return int(log_text[start:end]) if end > start else None


def extract_traceback(log_text: str) -> str | None:
    index = log_text.find(TRACEBACK_MARKER)
    return log_text[index:] if index != -1 else None


def extract_server_error(log_text: str) -> str | None:
    index = log_text.find(SHINYWIDGETS_EXCEPTION_MARKER)
    if index != -1:
        return log_text[index:]
    match = ERROR_LINE_PATTERN.search(log_text)
    if match is not None:
        line_end = log_text.find("\n", match.start())
        return log_text[match.start() : line_end if line_end != -1 else None]
    return None


def read_log(log_path: Path) -> str:
    return log_path.read_text(errors="replace")


def stop_server(server_process: subprocess.Popen[bytes] | None) -> None:
    if server_process is None:
        return
    server_process.terminate()
    try:
        server_process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        server_process.kill()
        server_process.wait(timeout=10)


if __name__ == "__main__":
    sys.exit(main())
