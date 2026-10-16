"""Shared helper: run a browser test against its own isolated KAVACH server.

Roadmap Rule 5 forbids erasing, overwriting, rotating or exposing existing keys,
databases or historical audit events. The browser scripts used to default to a
fixed local URL, so running them against a developer's live server silently wrote
sessions and audit events into the live runtime database. That happened once during
development and is why every browser test now starts its own server on a temporary
data directory instead.

Usage:
    from _isolated_server import isolated_server
    with isolated_server() as base:
        page.goto(base)
"""
import contextlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def isolated_server(startup_timeout: float = 40.0):
    """Yield a base URL for a server backed by a throwaway data directory."""
    port = _free_port()
    base = f'http://127.0.0.1:{port}'
    with tempfile.TemporaryDirectory(prefix='kavach-browser-') as directory:
        environment = dict(os.environ, KAVACH_DATA_DIR=directory)
        # Belt and braces: never inherit a live data directory or a privileged flag.
        environment.pop('KAVACH_DATA_DIR', None)
        environment['KAVACH_DATA_DIR'] = directory
        environment.pop('KAVACH_ALLOW_POLICY_ADMIN', None)
        process = subprocess.Popen(
            [sys.executable, '-m', 'backend', '--port', str(port)],
            cwd=ROOT, env=environment,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.time() + startup_timeout
            healthy = False
            while time.time() < deadline:
                if process.poll() is not None:
                    break
                try:
                    with urllib.request.urlopen(base + '/api/health', timeout=5) as r:
                        if json.load(r).get('status') == 'online':
                            healthy = True
                            break
                except (urllib.error.URLError, OSError, json.JSONDecodeError):
                    pass
                time.sleep(0.25)
            if not healthy:
                raise RuntimeError(f'isolated server on port {port} did not become healthy')
            yield base
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
