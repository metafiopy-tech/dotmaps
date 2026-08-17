"""H7 (HARDENING_BRIEF): identity hardening. The audit's two regression
tests, verbatim: same host / different Watch path -> distinct watcher IDs;
long same-prefix questions -> distinct chat map IDs."""
from pathlib import Path

from dotmaps.queen import chat as chat_mod
from dotmaps.queen import identity as identity_mod
from dotmaps.watch import compiler as watch_compiler


def test_stable_id_readable_prefix_hash_of_full_identity():
    a = identity_mod.stable_id("example.com", "https://example.com/a")
    b = identity_mod.stable_id("example.com", "https://example.com/b")
    assert a != b
    assert a.startswith("example-com-")
    assert b.startswith("example-com-")


def test_stable_id_deterministic():
    a1 = identity_mod.stable_id("x", "same-identity")
    a2 = identity_mod.stable_id("x", "same-identity")
    assert a1 == a2


# --------------------------------------------------------------------------- #
# same host, different path -> distinct watcher IDs                          #
# --------------------------------------------------------------------------- #

def test_same_host_different_path_gives_distinct_watcher_ids():
    slug_a = watch_compiler.watcher_id("https://example.com/products")
    slug_b = watch_compiler.watcher_id("https://example.com/support")
    assert slug_a != slug_b
    # both still carry a human-readable netloc prefix
    assert slug_a.startswith("example-com")
    assert slug_b.startswith("example-com")


def test_compile_health_map_of_two_paths_on_same_host_are_distinct_watchers(monkeypatch):
    """Full compile_health_map(), not just watcher_id() — a dead target
    still compiles (see compiler.py's own docstring), so no live server
    is needed to prove the two resulting slugs differ."""
    hm_a = watch_compiler.compile_health_map("http://127.0.0.1:1/products")
    hm_b = watch_compiler.compile_health_map("http://127.0.0.1:1/support")
    assert hm_a["slug"] != hm_b["slug"]


# --------------------------------------------------------------------------- #
# long same-prefix questions -> distinct chat map IDs                        #
# --------------------------------------------------------------------------- #

def test_long_same_prefix_questions_give_distinct_chat_slugs():
    prefix = "does anyone happen to know if there is a class available for "
    q1 = prefix + "putting on Tuesdays this spring"
    q2 = prefix + "chipping on Thursdays this fall"
    assert q1[:40] == q2[:40], "test setup: both must share the OLD 40-char truncation prefix"
    slug1 = chat_mod._slug(q1)
    slug2 = chat_mod._slug(q2)
    assert slug1 != slug2, "two questions sharing a 40-char prefix must not collide"


def test_chat_slug_deterministic_and_readable():
    q = "is there a putting class in the spring schedule"
    assert chat_mod._slug(q) == chat_mod._slug(q)
    assert chat_mod._slug(q).startswith("is-there-a-putting-class")
