import asyncio
from urllib.parse import urlparse

import pytest

from cf_bypasser.core import mirror as mirror_mod
from cf_bypasser.core.mirror import RequestMirror


class FakeBypasser:
    def __init__(self):
        self.cleaned = False

    async def cleanup(self):
        self.cleaned = True


def make_mirror():
    return RequestMirror(bypasser=FakeBypasser())


# ---- merge_cookies ----

def test_merge_cookies_cf_wins_over_stale_clearance():
    m = make_mirror()
    incoming = "cf_clearance=STALE; sessionid=abc"
    cf = {"cf_clearance": "FRESH"}
    out = m.merge_cookies(incoming, cf)
    parts = dict(p.split("=", 1) for p in out.split("; "))
    assert parts["cf_clearance"] == "FRESH"
    assert parts["sessionid"] == "abc"


def test_merge_cookies_passes_through_non_cf():
    m = make_mirror()
    out = m.merge_cookies("a=1; b=2", {"cf_clearance": "X"})
    parts = dict(p.split("=", 1) for p in out.split("; "))
    assert parts == {"a": "1", "b": "2", "cf_clearance": "X"}


def test_merge_cookies_empty_incoming():
    m = make_mirror()
    out = m.merge_cookies("", {"cf_clearance": "X"})
    assert out == "cf_clearance=X"


def test_merge_cookies_empty_cf():
    m = make_mirror()
    out = m.merge_cookies("a=1", {})
    assert out == "a=1"


def test_merge_cookies_all_empty():
    m = make_mirror()
    assert m.merge_cookies("", {}) == ""


# ---- build_target_url ----

def test_build_target_url_blocks_host_swap():
    m = make_mirror()
    url = m.build_target_url("good.com", "//evil.com/x", "")
    assert url == "https://good.com/evil.com/x"
    assert urlparse(url).netloc == "good.com"


def test_build_target_url_normal():
    m = make_mirror()
    url = m.build_target_url("good.com", "/api/data", "a=1")
    assert url == "https://good.com/api/data?a=1"


def test_build_target_url_collapses_leading_slashes():
    m = make_mirror()
    url = m.build_target_url("good.com", "////deep/path", "")
    assert url == "https://good.com/deep/path"


def test_build_target_url_query_appended_once():
    m = make_mirror()
    url = m.build_target_url("good.com", "/p", "x=1&y=2")
    assert url.count("?") == 1
    assert url.endswith("?x=1&y=2")


def test_build_target_url_preserves_explicit_scheme():
    m = make_mirror()
    url = m.build_target_url("http://good.com", "/p", "")
    assert url == "http://good.com/p"


def test_build_target_url_empty_path():
    m = make_mirror()
    assert m.build_target_url("good.com", "", "") == "https://good.com/"


# ---- session_cache LRU ----

class FakeSession:
    instances = []

    def __init__(self, *args, **kwargs):
        self.closed = False
        FakeSession.instances.append(self)

    async def close(self):
        self.closed = True


def test_session_cache_lru_eviction(monkeypatch):
    FakeSession.instances = []
    monkeypatch.setattr(mirror_mod, "AsyncSession", FakeSession)
    monkeypatch.setenv("CF_MAX_SESSIONS", "3")

    m = make_mirror()
    assert m.max_sessions == 3

    async def run():
        for i in range(5):
            await m.get_session(f"host{i}.com")

    asyncio.run(run())

    assert len(m.session_cache) == 3
    keys = list(m.session_cache.keys())
    assert keys == ["host2.com:no-proxy", "host3.com:no-proxy", "host4.com:no-proxy"]

    evicted = [s for s in FakeSession.instances if s.closed]
    assert len(evicted) == 2


def test_session_cache_reuse(monkeypatch):
    FakeSession.instances = []
    monkeypatch.setattr(mirror_mod, "AsyncSession", FakeSession)

    m = make_mirror()

    async def run():
        s1 = await m.get_session("a.com")
        s2 = await m.get_session("a.com")
        return s1, s2

    s1, s2 = asyncio.run(run())
    assert s1 is s2
    assert len(m.session_cache) == 1


def test_session_cache_lru_recency(monkeypatch):
    FakeSession.instances = []
    monkeypatch.setattr(mirror_mod, "AsyncSession", FakeSession)
    monkeypatch.setenv("CF_MAX_SESSIONS", "2")

    m = make_mirror()

    async def run():
        await m.get_session("a.com")
        await m.get_session("b.com")
        await m.get_session("a.com")  # bump a to most-recent
        await m.get_session("c.com")  # should evict b

    asyncio.run(run())
    keys = set(m.session_cache.keys())
    assert keys == {"a.com:no-proxy", "c.com:no-proxy"}


# ---- except-branch: deterministic errors re-raise immediately ----

def test_keyerror_not_retried(monkeypatch):
    m = make_mirror()
    calls = {"n": 0}

    def boom(*args, **kwargs):
        calls["n"] += 1
        raise KeyError("user_agent")

    monkeypatch.setattr(m, "build_target_url", boom)

    headers = {"x-hostname": "good.com"}

    async def run():
        await m.mirror_request("GET", "/p", "", headers, hostname="good.com", max_retries=2)

    with pytest.raises(KeyError):
        asyncio.run(run())

    assert calls["n"] == 1  # not retried


def test_runtime_error_is_retried(monkeypatch):
    m = make_mirror()
    calls = {"n": 0}

    def boom(*args, **kwargs):
        calls["n"] += 1
        raise RuntimeError("transient")

    monkeypatch.setattr(m, "build_target_url", boom)

    async def fast_sleep(*a, **k):
        return None

    monkeypatch.setattr(mirror_mod.asyncio, "sleep", fast_sleep)

    headers = {"x-hostname": "good.com"}

    async def run():
        await m.mirror_request("GET", "/p", "", headers, hostname="good.com", max_retries=2)

    with pytest.raises(RuntimeError):
        asyncio.run(run())

    assert calls["n"] == 3  # initial + 2 retries
