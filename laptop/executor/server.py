"""Optional local HTTP wrapper so the GUI loop can talk to the executor by JSON."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from contracts.dump import dump
from contracts.models import ExecRequest
from executor.fake import FakeExecutor


def serve(executor: FakeExecutor, host: str = "127.0.0.1", port: int = 8771) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            result = executor.execute(ExecRequest.model_validate(body))
            payload = json.dumps(dump(result)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt: str, *args) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    return server
