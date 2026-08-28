"""Proxy pool with rotation and health tracking."""

import asyncio
import random
import time
from dataclasses import dataclass
from typing import List, Optional, Dict

from .exceptions import ProxyExhaustedError


@dataclass
class ProxyStatus:
    url: str
    healthy: bool = True
    last_used: float = 0.0
    fail_count: int = 0
    success_count: int = 0
    avg_latency: float = 0.0
    last_error: Optional[str] = None


class ProxyPool:
    def __init__(self, proxies: List[str], max_failures: int = 3, recovery_interval: float = 300.0):
        self._proxies: Dict[str, ProxyStatus] = {p: ProxyStatus(url=p) for p in proxies}
        self._max_failures = max_failures
        self._recovery_interval = recovery_interval
        self._index = 0
        self._lock = asyncio.Lock()

    @property
    def has_proxies(self) -> bool:
        return len(self._proxies) > 0

    @property
    def healthy_count(self) -> int:
        return sum(1 for s in self._proxies.values() if s.healthy)

    def _get_available(self) -> List[ProxyStatus]:
        now = time.time()
        available = []
        for status in self._proxies.values():
            if status.healthy:
                available.append(status)
            elif now - status.last_used > self._recovery_interval:
                status.healthy = True
                status.fail_count = 0
                available.append(status)
        return available

    async def next(self) -> Optional[str]:
        async with self._lock:
            if not self._proxies:
                return None
            available = self._get_available()
            if not available:
                raise ProxyExhaustedError("All proxies exhausted")
            available.sort(key=lambda s: s.avg_latency + random.uniform(0, 0.1))
            proxy = available[self._index % len(available)]
            self._index += 1
            proxy.last_used = time.time()
            return proxy.url

    def mark_success(self, proxy: str, latency: float):
        if proxy in self._proxies:
            status = self._proxies[proxy]
            status.success_count += 1
            status.fail_count = max(0, status.fail_count - 1)
            alpha = 0.3
            status.avg_latency = alpha * latency + (1 - alpha) * status.avg_latency
            status.healthy = True

    def mark_failed(self, proxy: str, error: Optional[str] = None):
        if proxy in self._proxies:
            status = self._proxies[proxy]
            status.fail_count += 1
            status.last_error = error
            status.last_used = time.time()
            if status.fail_count >= self._max_failures:
                status.healthy = False

    def get_stats(self) -> Dict[str, dict]:
        return {
            url: {
                "healthy": s.healthy,
                "successes": s.success_count,
                "failures": s.fail_count,
                "avg_latency_ms": round(s.avg_latency * 1000, 1),
                "last_error": s.last_error,
            }
            for url, s in self._proxies.items()
        }
