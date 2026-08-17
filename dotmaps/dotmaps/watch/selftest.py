"""SELFTEST — a real, local, disposable target (queen/assure.py's
watch-oracle claim, W3).

`queen/assure.py`'s claim 11 needs to re-prove the watch mechanism
against something it can sabotage on command, hermetically — the same
reason `check_ui_endpoints_serve`/`check_work_order_gate_fails_closed`
spin up their own ephemeral instances rather than depending on the
network or a fixture that could drift. `WatchSite` is a genuine
ThreadingHTTPServer on an ephemeral port (real fetch.get round-trips, not
mocked) whose page table can be mutated live — sabotage a page, take one
down entirely, heal it back — so the exact three WATCH BRIEF done-tests
can be re-run inside `dotmaps assure` itself.

H3 (HARDENING_BRIEF): production fetch.get is SSRF-hardened
(net/safefetch.py) and refuses loopback/private targets by construction —
which this harness's own target (127.0.0.1) would otherwise trip.
start()/stop() register and deregister this one ephemeral port with
safefetch's narrow, self-expiring test-loopback allowance, so the REAL
fetch mechanism is still what gets exercised (no mock, no bypassed tool),
without opening that door for any real, user-supplied Watch/traveler URL.
"""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ..net.safefetch import allow_loopback_for_testing, disallow_loopback_for_testing


class WatchSite:
    def __init__(self) -> None:
        self.pages: dict[str, tuple[int, str]] = {
            "/": (200, (
                '<html><head><title>Home | Test Golf Co</title></head><body>'
                '<a href="/about">About</a> <a href="/contact">Contact</a>'
                '<img src="/logo.png"><form action="/search" method="get">'
                '<input name="q"></form></body></html>')),
            "/about": (200, '<html><head><title>About Us</title></head>'
                            '<body><script src="/app.js"></script>About page.</body></html>'),
            "/contact": (200, '<html><head><title>Contact</title></head>'
                              '<body>Contact page.</body></html>'),
            "/search": (200, '<html><head><title>Search</title></head>'
                             '<body>results</body></html>'),
            "/logo.png": (200, "fake-png-bytes"),
            "/app.js": (200, "console.log(1)"),
        }
        self._lock = threading.Lock()
        self.httpd: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> str:
        site = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                with site._lock:
                    status, body = site.pages.get(self.path, (404, "not found"))
                data = body.encode()
                self.send_response(status)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, fmt, *args) -> None:  # noqa: A002
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        port = self.httpd.socket.getsockname()[1]
        allow_loopback_for_testing(port)
        return f"http://127.0.0.1:{port}/"

    def stop(self) -> None:
        if self.httpd:
            disallow_loopback_for_testing(self.httpd.socket.getsockname()[1])
            self.httpd.shutdown()
            self.httpd.server_close()
        if self.thread:
            self.thread.join(timeout=5)

    def sabotage(self, path: str = "/about") -> None:
        with self._lock:
            status, body = self.pages[path]
            self.pages[path] = (status, body.replace("About Us", "GONE"))

    def heal(self, path: str = "/about") -> None:
        with self._lock:
            status, body = self.pages[path]
            self.pages[path] = (status, body.replace("GONE", "About Us"))

    def take_down(self, path: str = "/about") -> None:
        with self._lock:
            self.pages[path] = (503, "service unavailable")
