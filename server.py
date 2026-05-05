from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from tracker.sec_client import load_snapshot


ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "public"
DATA_DIR = ROOT / "data"


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/portfolio":
            query = parse_qs(parsed.query)
            refresh = query.get("refresh", ["0"])[0] == "1"
            self._send_json(load_snapshot(DATA_DIR, refresh=refresh))
            return
        if parsed.path == "/health":
            self._send_json({"ok": True})
            return
        super().do_GET()

    def _send_json(self, payload: dict, status: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8787), DashboardHandler)
    print("Dashboard: http://127.0.0.1:8787")
    server.serve_forever()


if __name__ == "__main__":
    main()
