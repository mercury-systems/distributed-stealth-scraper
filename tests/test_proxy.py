"""Proxy pool tests."""

import asyncio
import pytest
from stealth_scraper.proxy import ProxyPool, ProxyExhaustedError


class TestProxyPool:
    def test_rotation(self):
        async def run():
            pool = ProxyPool(["http://p1:8080", "http://p2:8080"])
            p1 = await pool.next()
            p2 = await pool.next()
            p3 = await pool.next()
            assert p1 == p3
        asyncio.run(run())

    def test_mark_failed(self):
        async def run():
            pool = ProxyPool(["http://p1:8080"], max_failures=2)
            pool.mark_failed("http://p1:8080")
            pool.mark_failed("http://p1:8080")
            with pytest.raises(ProxyExhaustedError):
                await pool.next()
        asyncio.run(run())

    def test_stats(self):
        pool = ProxyPool(["http://p1:8080"])
        pool.mark_success("http://p1:8080", 0.5)
        stats = pool.get_stats()
        assert stats["http://p1:8080"]["successes"] == 1
        assert stats["http://p1:8080"]["avg_latency_ms"] == 150.0
