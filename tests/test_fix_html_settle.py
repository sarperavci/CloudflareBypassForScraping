import asyncio

import pytest

from cf_bypasser.core import bypasser as bypasser_mod
from cf_bypasser.core.bypasser import CloakBypasser


class FakePage:
    """page.content() returns a body whose size follows `sizes` (last value repeats)."""
    def __init__(self, sizes):
        self._sizes = list(sizes)
        self.calls = 0

    async def wait_for_load_state(self, *a, **k):
        return None

    async def content(self):
        i = min(self.calls, len(self._sizes) - 1)
        self.calls += 1
        return "x" * self._sizes[i]


class GrowingPage:
    """Never stabilizes: every content() read is larger than the last."""
    def __init__(self):
        self.calls = 0

    async def wait_for_load_state(self, *a, **k):
        return None

    async def content(self):
        self.calls += 1
        return "x" * (10 * self.calls)


def make_bypasser(tmp_path):
    return CloakBypasser(log=False, cache_file=str(tmp_path / "cache.json"))


@pytest.fixture(autouse=True)
def fast_poll(monkeypatch):
    monkeypatch.setattr(bypasser_mod, "HTML_SETTLE_POLL_SECONDS", 0.01)
    monkeypatch.setattr(bypasser_mod, "HTML_SETTLE_STABLE_ROUNDS", 2)
    monkeypatch.setattr(bypasser_mod, "HTML_SETTLE_MAX_SECONDS", 5)


async def test_returns_after_dom_stabilizes(tmp_path):
    page = FakePage([10, 20, 30, 30, 30])  # grows then holds at 30
    html = await make_bypasser(tmp_path)._stable_html(page)
    assert len(html) == 30


async def test_stable_immediately(tmp_path):
    page = FakePage([42, 42, 42])
    html = await make_bypasser(tmp_path)._stable_html(page)
    assert len(html) == 42
    assert page.calls == 3  # initial read + 2 confirming rounds


async def test_caps_at_max_and_does_not_hang(tmp_path, monkeypatch):
    monkeypatch.setattr(bypasser_mod, "HTML_SETTLE_MAX_SECONDS", 0.1)
    page = GrowingPage()
    html = await asyncio.wait_for(make_bypasser(tmp_path)._stable_html(page), timeout=3)
    assert len(html) > 0
    assert page.calls < 100  # bounded by the deadline, never infinite


async def test_disabled_when_rounds_zero(tmp_path, monkeypatch):
    monkeypatch.setattr(bypasser_mod, "HTML_SETTLE_STABLE_ROUNDS", 0)
    page = FakePage([10, 20, 30])
    html = await make_bypasser(tmp_path)._stable_html(page)
    assert len(html) == 10      # returns the first read, no polling
    assert page.calls == 1
