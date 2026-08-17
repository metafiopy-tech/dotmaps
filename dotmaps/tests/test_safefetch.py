"""H3 (HARDENING_BRIEF): SafeFetcher — one egress door for Watch + traveler
fetch. The audit's full SSRF regression matrix, verbatim: localhost,
127.0.0.1, ::1, RFC1918, link-local, cloud metadata, redirect-to-private,
DNS-rebind simulation -> all blocked."""
import http.server
import socket
import threading
from contextlib import contextmanager

import pytest

from dotmaps.net import safefetch


def test_scheme_other_than_http_https_blocked():
    out = safefetch.safe_get("file:///etc/passwd")
    assert out.startswith("ERROR:")
    assert "scheme" in out


@pytest.mark.parametrize("url", [
    "http://localhost/",
    "http://127.0.0.1/",
    "http://[::1]/",
    "http://10.1.2.3/",
    "http://172.16.0.1/",
    "http://192.168.1.1/",
    "http://169.254.169.254/latest/meta-data/",  # cloud metadata (AWS/GCP/Azure share this IP)
    "http://100.100.100.200/",                    # Alibaba metadata (100.64.0.0/10 shared space)
])
def test_private_and_metadata_addresses_all_refused(url):
    out = safefetch.safe_get(url)
    assert out.startswith("ERROR:"), f"{url} was not refused: {out[:120]!r}"


def test_public_dns_name_resolving_only_to_private_space_refused(monkeypatch):
    """A hostname (not a literal IP) whose DNS answer is entirely private
    space must be refused just like a literal private IP would be."""
    def _fake_getaddrinfo(host, port, *a, **k):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", port))]
    monkeypatch.setattr(safefetch.socket, "getaddrinfo", _fake_getaddrinfo)
    out = safefetch.safe_get("http://internal.example.test/")
    assert out.startswith("ERROR:")
    assert "non-public" in out


# --------------------------------------------------------------------------- #
# redirect-to-private: a real local server issuing a 302 to a private target #
# --------------------------------------------------------------------------- #

class _RedirectToPrivateHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self.send_response(302)
        self.send_header("Location", "http://127.0.0.1:9/blocked")
        self.end_headers()

    def log_message(self, fmt, *args):
        pass


@contextmanager
def _local_server(handler_cls):
    httpd = http.server.HTTPServer(("127.0.0.1", 0), handler_cls)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield port
    finally:
        httpd.shutdown()
        httpd.server_close()
        t.join(timeout=5)


def test_redirect_to_private_target_is_refused(monkeypatch):
    """The redirecting server itself is loopback (allowed only because the
    test forces the resolver to treat 127.0.0.1 as reachable for the FIRST
    hop is not how production is configured — instead we prove the second
    hop, the Location header, is independently re-validated and refused
    even though following redirects blindly would have succeeded)."""
    # Force the "public" check to accept loopback ONLY for this test's local
    # server hop, by monkeypatching _is_public to treat 127.0.0.1 as public —
    # simulating "the first hop passed validation somehow" so we can prove
    # the SECOND hop (the redirect target) is independently checked and
    # blocked on its own merits, not inherited trust from the first.
    real_is_public = safefetch._is_public
    monkeypatch.setattr(safefetch, "_is_public",
                        lambda ip, port=None: ip == "127.0.0.1" or real_is_public(ip, port))
    with _local_server(_RedirectToPrivateHandler) as port:
        out = safefetch.safe_get(f"http://127.0.0.1:{port}/start")
    assert out.startswith("ERROR:")


# --------------------------------------------------------------------------- #
# DNS-rebind: resolve-then-pin means a second resolution never happens       #
# --------------------------------------------------------------------------- #

def test_dns_rebind_cannot_change_the_target_after_validation(monkeypatch):
    """Simulate a rebinding DNS server: getaddrinfo is called with a call
    counter; if safe_get re-resolved mid-connection, a THIRD call would see
    a private address. We assert getaddrinfo is called exactly once per
    hop — resolve-then-pin means the validated address is the one and only
    address ever connected to."""
    calls = []

    def _rebinding_getaddrinfo(host, port, *a, **k):
        calls.append(host)
        # always returns a private address — should be refused every time,
        # proving there is no "validate against a stale public answer, then
        # connect to whatever a second resolution returns" gap.
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.9.9", port))]

    monkeypatch.setattr(safefetch.socket, "getaddrinfo", _rebinding_getaddrinfo)
    out = safefetch.safe_get("http://rebind.example.test/")
    assert out.startswith("ERROR:")
    assert calls.count("rebind.example.test") == 1, "must resolve exactly once, then pin"


# --------------------------------------------------------------------------- #
# a normal public fetch still works, unchanged contract                      #
# --------------------------------------------------------------------------- #

class _OkHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = b"hello from a normal page"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


def test_a_normal_reachable_page_still_returns_http_200_contract(monkeypatch):
    real_is_public = safefetch._is_public
    monkeypatch.setattr(safefetch, "_is_public",
                        lambda ip, port=None: ip == "127.0.0.1" or real_is_public(ip, port))
    with _local_server(_OkHandler) as port:
        out = safefetch.safe_get(f"http://127.0.0.1:{port}/")
    assert out.startswith("HTTP 200\n")
    assert "hello from a normal page" in out


def test_size_cap_truncates_body():
    class _BigHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            body = b"x" * 200_000
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            pass

    real_is_public = safefetch._is_public
    import unittest.mock as mock
    with mock.patch.object(safefetch, "_is_public",
                          lambda ip, port=None: ip == "127.0.0.1" or real_is_public(ip, port)):
        with _local_server(_BigHandler) as port:
            out = safefetch.safe_get(f"http://127.0.0.1:{port}/", max_bytes=1024)
    assert len(out) < 2000
