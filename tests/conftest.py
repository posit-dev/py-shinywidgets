from __future__ import annotations

import socket
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path
from typing import Generator

import pytest


def find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return int(sock.getsockname()[1])


def wait_for_server(port: int, timeout: float = 30.0) -> None:
    start = time.time()
    while time.time() - start < timeout:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            try:
                sock.connect(("127.0.0.1", port))
                return
            except OSError:
                time.sleep(0.1)
    raise RuntimeError(f"Timed out waiting for server on port {port}")


class ShinyApp:
    def __init__(self, app_path: Path, repo_root: Path):
        self.app_path = app_path
        self.repo_root = repo_root
        self.port = find_free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        self.process: subprocess.Popen[str] | None = None

    def start(self) -> None:
        env = {
            **dict(),
            **__import__("os").environ,
            "PYTHONPATH": str(self.repo_root),
        }
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "shiny",
                "run",
                "--port",
                str(self.port),
                str(self.app_path),
            ],
            cwd=str(self.repo_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        wait_for_server(self.port)

    def stop(self) -> None:
        if self.process is None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
        self.process = None

    def __enter__(self) -> ShinyApp:
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def isolate_context_app(repo_root: Path) -> Generator[ShinyApp, None, None]:
    app_path = repo_root / "tests" / "apps" / "issue_221_isolate_app.py"
    with ShinyApp(app_path=app_path, repo_root=repo_root) as app:
        yield app


@pytest.fixture
def plotly_rerender_app(repo_root: Path) -> Generator[ShinyApp, None, None]:
    app_path = repo_root / "tests" / "apps" / "issue_223_plotly_rerender_app.py"
    with ShinyApp(app_path=app_path, repo_root=repo_root) as app:
        yield app
