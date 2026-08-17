"""COMPILER — turn a URL into a HEALTH MAP (W1).

"Compile a HEALTH MAP for the target — v0 predicate set, derived not
hardcoded." The predicate SET is fixed and small (five kinds below); the
VALUES a given target's dots check — which pages exist, what their titles
actually say, which forms and assets are declared — are discovered by a
real crawl, once, at compile time. Every dot that comes out is already
shaped as a bank rule (`method.steps` + `check.predicate/value`), so
`watch/oracle.py` runs it with the exact machinery `bank/route.py` and
`bank/certify.py` use for every other skill — no parallel check language.

v0 scope, stated plainly:
  - crawl depth 1: the target page, plus every internal link found on it
  - internal = same netloc as the target
  - predicate kinds: PAGE_RESPONDS (200, exact), PAGE_TITLE (the actual
    crawled title text must still appear), FORM_RESPONDS (any completed
    HTTP exchange — forms often 405 a bare GET; that's a real answer, not
    a network failure), ASSET_LOADS (200, exact)
"""
from __future__ import annotations

import hashlib
import re
import time
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

from ..grow.banking import run_steps
from ..queen import identity as identity_mod
from .oracle import DUMMY_WORKSPACE

MAX_INTERNAL_PAGES = 6   # crawl-1-level cap: homepage + up to this many links
MAX_ASSETS_PER_PAGE = 4
MAX_FORMS_PER_PAGE = 3

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def slugify(url: str) -> str:
    """A readable label only — NOT the persistent watcher identity (see
    H7 below). Kept for anywhere a short display name is wanted."""
    net = urlparse(url).netloc or url
    return "".join(c if c.isalnum() else "-" for c in net).strip("-").lower() or "target"


def watcher_id(normalized_url: str) -> str:
    """H7 (HARDENING_BRIEF): the audit's P1 finding — `slugify()` alone
    used netloc ONLY, so two different Watch targets on the same host
    (different paths) collided into the same persistent watcher namespace.
    The readable netloc stays as a prefix; a hash of the FULL normalized
    URL is what actually makes the id unique."""
    return identity_mod.stable_id(slugify(normalized_url), normalized_url)


def _normalize(url: str) -> str:
    """Canonical form for identity/dedup — "https://x.com" and
    "https://x.com/" (a self-link the home page nearly always has, in a
    logo or nav) are the same resource; without this a real site's
    trailing-slash-optional home link compiles as two separate pages."""
    p = urlparse(url)
    path = p.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return f"{p.scheme}://{p.netloc}{path}" + (f"?{p.query}" if p.query else "")


def _dot_id(kind: str, url: str) -> str:
    """Stable across recompiles of the same target: identity is (kind, url),
    not crawl order — a health map can be recompiled fresh every watch
    session without every dot losing its check history."""
    return hashlib.sha256(f"{kind}::{url}".encode()).hexdigest()[:10]


class _PageParser(HTMLParser):
    """Links/forms/assets only — title is extracted separately, by regex
    against the raw body (see `_extract_raw_title`), so its stored check
    value matches the bytes a future raw fetch actually returns."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.forms: list[tuple[str, str]] = []  # (action, method)
        self.assets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = dict(attrs)
        if tag == "a" and d.get("href"):
            self.links.append(d["href"])
        elif tag == "form":
            self.forms.append((d.get("action") or "", (d.get("method") or "get").lower()))
        elif tag == "img" and d.get("src"):
            self.assets.append(d["src"])
        elif tag == "script" and d.get("src"):
            self.assets.append(d["src"])
        elif tag == "link" and (d.get("rel") or "").lower() == "stylesheet" and d.get("href"):
            self.assets.append(d["href"])


def _extract_raw_title(body: str) -> str:
    """Title text, extracted by regex against the RAW (undecoded) body —
    deliberately NOT `_PageParser`'s `<title>` text, which `HTMLParser`
    entity-decodes (`convert_charrefs`, on by default). `oracle.py`'s
    `contains` check runs against the raw bytes `fetch.get` returns on
    every future check, so the compiled value must be a literal substring
    of THAT, not of a decoded rendering a real page (an apostrophe as
    `&#x27;` is common) would never match again."""
    m = _TITLE_RE.search(body)
    return m.group(1).strip() if m else ""


def _fetch(url: str) -> str:
    return run_steps({"steps": [{"tool": "fetch.get", "args": {"url": url}}]}, DUMMY_WORKSPACE)


def _rule(kind: str, url: str, predicate: str, value: Any) -> dict[str, Any]:
    return {
        "id": _dot_id(kind, url),
        "kind": kind,
        "url": url,
        "method": {"steps": [{"tool": "fetch.get", "args": {"url": url}}]},
        "check": {"predicate": predicate, "value": value},
    }


def compile_health_map(target_url: str,
                       max_pages: int = MAX_INTERNAL_PAGES,
                       max_assets: int = MAX_ASSETS_PER_PAGE,
                       max_forms: int = MAX_FORMS_PER_PAGE) -> dict[str, Any]:
    """One real crawl, one level deep. Never raises on a dead target — a
    target that doesn't even answer still compiles to a (failing) 1-dot
    map, honestly."""
    target_url = _normalize(target_url)
    slug = watcher_id(target_url)
    dots: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    def add(dot: dict[str, Any]) -> None:
        key = (dot["kind"], dot["url"])
        if key in seen_urls:
            return
        seen_urls.add(key)
        dots.append(dot)

    def crawl_page(url: str, label: str) -> _PageParser | None:
        obs = _fetch(url)
        add({**_rule("page_responds", url, "contains", "HTTP 200"),
            "statement": f"The {label} page responds."})
        if obs.startswith("ERROR:") or not obs.startswith("HTTP 200"):
            return None
        body = obs.split("\n", 1)[1] if "\n" in obs else ""
        p = _PageParser()
        try:
            p.feed(body)
        except Exception:
            return p
        title = _extract_raw_title(body)
        if title:
            add({**_rule("page_title", url, "contains", title),
                "statement": f"The {label} page still has a title."})
        return p

    home = crawl_page(target_url, "home")
    if home is None:
        return {"target": target_url, "slug": slug,
                "compiled_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "dots": dots}

    # internal links, crawled one level deep
    internal: list[tuple[str, str]] = []  # (abs_url, label)
    for href in home.links:
        abs_url = urljoin(target_url, href)
        parsed = urlparse(abs_url)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc != urlparse(target_url).netloc:
            continue
        clean = _normalize(abs_url.split("#")[0])
        if clean == target_url:
            continue
        label = (parsed.path.strip("/") or "home").split("/")[-1] or parsed.path
        if clean not in {u for u, _ in internal}:
            internal.append((clean, label))
        if len(internal) >= max_pages:
            break

    # (parser, base_url) pairs — kept together so a failed internal fetch
    # (filtered to None by crawl_page) can never desync a page's forms/
    # assets from the wrong base URL.
    pages: list[tuple[_PageParser, str]] = [(home, target_url)]
    for url, label in internal:
        p = crawl_page(url, label)
        if p is not None:
            pages.append((p, url))

    # forms — lenient predicate: any completed HTTP exchange counts as a
    # real response (many forms legitimately 405 a bare GET)
    seen_forms = 0
    for page, base_url in pages:
        for action, method in page.forms:
            if method != "get" or seen_forms >= max_forms:
                continue
            action_url = _normalize(urljoin(base_url, action)) if action else base_url
            add({**_rule("form_responds", action_url, "contains", "HTTP "),
                "statement": "A form on the site responds to a GET request."})
            seen_forms += 1

    # declared assets — strict 200
    seen_assets = 0
    for page, base_url in pages:
        for src in page.assets:
            if seen_assets >= max_assets:
                break
            asset_url = urljoin(base_url, src)
            if urlparse(asset_url).scheme not in ("http", "https"):
                continue
            name = asset_url.rsplit("/", 1)[-1] or asset_url
            add({**_rule("asset_loads", asset_url, "contains", "HTTP 200"),
                "statement": f"The {name} asset loads."})
            seen_assets += 1

    return {"target": target_url, "slug": slug,
            "compiled_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "dots": dots}
