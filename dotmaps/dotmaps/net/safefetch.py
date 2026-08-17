"""SAFEFETCH — H3 (HARDENING_BRIEF): one egress door for Watch + traveler fetch.

The audit's P0 finding: `runtime/traveler.py`'s `ToolBox._fetch_get` accepted
any http(s) URL and handed it to plain `urllib.request.urlopen`, which resolves
DNS and follows redirects with no notion of "private network." A traveler or a
Watch target (a URL a user hands the system, or a redirect a hostile page can
issue) could reach `localhost`, RFC1918 space, link-local addresses, or a cloud
metadata endpoint (`169.254.169.254`), and a two-step DNS-rebind (public IP at
validation time, private IP at connect time) would bypass even a naive hostname
check.

`safe_get()` is the single, stdlib-only replacement, called from exactly one
place — `runtime/traveler.py`'s `ToolBox._fetch_get` — which both `watch/
oracle.py` (via `grow.banking.run_steps` -> `ToolBox.call("fetch.get", ...)`)
and every other traveler fetch already route through, so fixing this one
function closes the door for both call sites the brief names.

Contract preserved exactly: `"HTTP <code>\\n<body>"` on any completed HTTP
exchange (matching or not), `"ERROR: ..."` on anything blocked or unreachable —
`watch/oracle.py`'s green/red/amber split reads this string, unchanged.

Defense, in order:
  1. scheme allowlist — http(s) only.
  2. resolve via `socket.getaddrinfo`; every candidate address must be
     `ipaddress.*.is_global` and not multicast (this stdlib version already
     correctly excludes RFC1918, loopback, link-local incl. cloud metadata,
     and the 100.64.0.0/10 shared/CGNAT range some older versions miss).
  3. RESOLVE-THEN-PIN: connect directly to ONE validated address (never
     re-resolving the hostname mid-connection) — this is what defeats
     DNS-rebind, since a second resolution never happens.
  4. redirects followed MANUALLY, one hop at a time, each `Location` fully
     re-validated (scheme, resolve, pin) from scratch before being fetched —
     never urllib's automatic follow, which would re-trust the hostname.
  5. size and wall-clock caps.
"""
from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urljoin, urlparse

MAX_BYTES = 65536
TIMEOUT_S = 10
MAX_REDIRECTS = 5
_REDIRECT_CODES = {301, 302, 303, 307, 308}

# A narrow, explicit, self-expiring exception for exactly one legitimate
# local target: watch/selftest.py's WatchSite, the developer-owned ephemeral
# HTTP server queen/assure.py's watch-oracle claim and tests/test_watch.py
# use to prove the REAL fetch.get mechanism end-to-end (not a mock). Only a
# port THIS process itself just bound can ever land here — never a port
# named by a URL a user or a skill supplies — and WatchSite removes its own
# port the moment it tears down. Production Watch/traveler fetches (real,
# possibly-hostile, user-supplied URLs) are never affected: this set starts
# and stays empty outside that one trusted harness.
_TEST_LOOPBACK_PORTS: set[int] = set()


def allow_loopback_for_testing(port: int) -> None:
    """Called only by watch/selftest.py's WatchSite.start(). See the
    module-level comment on `_TEST_LOOPBACK_PORTS` for why this exists and
    why it cannot be reached from an untrusted URL."""
    _TEST_LOOPBACK_PORTS.add(port)


def disallow_loopback_for_testing(port: int) -> None:
    """Called only by watch/selftest.py's WatchSite.stop()."""
    _TEST_LOOPBACK_PORTS.discard(port)


class _Blocked(Exception):
    """Internal — always caught and turned into the "ERROR: ..." string
    contract; never leaks a traceback to the caller."""


def _validate_scheme(url: str) -> str:
    scheme = urlparse(url).scheme.lower()
    if scheme not in ("http", "https"):
        raise _Blocked(f"scheme {scheme!r} is not allowed (http/https only)")
    return scheme


def _is_public(ip_str: str, port: int | None = None) -> bool:
    if port is not None and ip_str in ("127.0.0.1", "::1") and port in _TEST_LOOPBACK_PORTS:
        return True
    ip = ipaddress.ip_address(ip_str)
    return ip.is_global and not ip.is_multicast


def _resolve_public_address(host: str, port: int) -> str:
    """Resolve `host`, require at least one candidate to be a public,
    globally-routable address (or the narrow test-loopback exception
    above), and return that ONE address to pin the connection to. Every
    candidate is checked (a hostname resolving to a mix of public+private
    addresses is still refused unless the address we actually pick is
    public) — but only the picked address is ever connected to, so the
    check and the connection can never disagree."""
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise _Blocked(f"could not resolve {host}: {e}") from e
    for family, _type, _proto, _canon, sockaddr in infos:
        addr = sockaddr[0]
        if _is_public(addr, port):
            return addr
    raise _Blocked(f"{host} resolves only to non-public address space "
                   f"({sorted({s[4][0] for s in infos})}) — refused")


def _pinned_connection(scheme: str, host: str, port: int, pinned_ip: str,
                       timeout: float) -> http.client.HTTPConnection:
    """The resolve-then-pin technique: build an http.client connection whose
    socket is manually connected to `pinned_ip` (never re-resolving `host`),
    then hand that pre-validated socket to the connection object so its own
    `.request()` skips its normal connect()-by-hostname path entirely."""
    sock = socket.create_connection((pinned_ip, port), timeout=timeout)
    if scheme == "https":
        ctx = ssl.create_default_context()
        sock = ctx.wrap_socket(sock, server_hostname=host)
        conn: http.client.HTTPConnection = http.client.HTTPSConnection(
            host, port, timeout=timeout, context=ctx)
    else:
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
    conn.sock = sock
    return conn


def _fetch_once(url: str, *, timeout: float, max_bytes: int) -> tuple[int, str, str | None]:
    """One HTTP exchange against a fully-validated, pinned address. Returns
    (status, body, redirect_location_or_None)."""
    scheme = _validate_scheme(url)
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        raise _Blocked(f"no host in url {url!r}")
    port = parsed.port or (443 if scheme == "https" else 80)
    pinned_ip = _resolve_public_address(host, port)

    conn = _pinned_connection(scheme, host, port, pinned_ip, timeout)
    try:
        path = urlparse(url)._replace(scheme="", netloc="").geturl() or "/"
        conn.request("GET", path, headers={"Host": host, "User-Agent": "dotmaps-traveler/0.1"})
        resp = conn.getresponse()
        body = resp.read(max_bytes).decode("utf-8", errors="replace")
        location = resp.getheader("Location") if resp.status in _REDIRECT_CODES else None
        return resp.status, body, location
    finally:
        conn.close()


def safe_get(url: str, timeout: float = TIMEOUT_S, max_bytes: int = MAX_BYTES,
            max_redirects: int = MAX_REDIRECTS) -> str:
    """Read-only HTTP GET, SSRF-hardened. Same string contract as the old
    urllib-based fetch: "HTTP <code>\\n<body>" on any completed exchange,
    "ERROR: ..." on anything blocked/unreachable. Never raises."""
    current = url
    for _ in range(max_redirects + 1):
        try:
            status, body, location = _fetch_once(current, timeout=timeout, max_bytes=max_bytes)
        except _Blocked as e:
            return f"ERROR: {e}"
        except (OSError, http.client.HTTPException, ssl.SSLError) as e:
            return f"ERROR: could not reach {current}: {e}"
        if location:
            # every redirect hop is re-validated from scratch — scheme,
            # resolution, pinning — never trusted off the prior hop.
            current = urljoin(current, location)
            continue
        return f"HTTP {status}\n{body}"
    return f"ERROR: too many redirects (> {max_redirects}) starting from {url}"
