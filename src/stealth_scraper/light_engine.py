"""Light tier: curl_cffi with JA3 spoofing."""

import asyncio
import random
import time
from typing import Optional, Tuple, Dict

from .exceptions import ProxyError, TimeoutError, UnknownFetchError
from .proxy import ProxyPool
from .session import SessionVault


class LightEngine:
    _USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]

    _ACCEPT_LANGS = [
        "en-US,en;q=0.9",
        "en-GB,en;q=0.8",
        "en-CA,en;q=0.7,fr;q=0.3",
    ]

    def __init__(self, proxy_pool: ProxyPool, session_vault: SessionVault,
                 max_retries: int = 3, request_timeout: float = 30.0):
        self._proxy_pool = proxy_pool
        self._session_vault = session_vault
        self._max_retries = max_retries
        self._request_timeout = request_timeout
        self._session: Optional = None

    async def initialize(self):
        try:
            import curl_cffi.requests as curl_requests
            self._session = curl_requests.AsyncSession(impersonate="chrome120", timeout=self._request_timeout)
        except ImportError as e:
            raise RuntimeError("curl_cffi not installed. Run: pip install curl-cffi>=0.6.0") from e

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    def _build_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": random.choice(self._USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": random.choice(self._ACCEPT_LANGS),
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Sec-CH-UA": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"',
            "Cache-Control": "max-age=0",
        }

    async def fetch(self, url: str) -> Tuple[int, str, Dict[str, str]]:
        if not self._session:
            raise RuntimeError("Light engine not initialized")

        last_error = None
        domain = url.split("/")[2]

        for attempt in range(self._max_retries):
            proxy = None
            if self._proxy_pool.has_proxies:
                try:
                    proxy = await self._proxy_pool.next()
                except Exception:
                    pass

            try:
                headers = self._build_headers()
                cookies = self._session_vault.get_cookies(domain)
                if cookies:
                    headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())

                kwargs = {"headers": headers}
                if proxy:
                    kwargs["proxy"] = proxy

                start = time.time()
                response = await asyncio.wait_for(self._session.get(url, **kwargs), timeout=self._request_timeout)
                latency = time.time() - start

                if hasattr(response, "cookies"):
                    for name, value in response.cookies.items():
                        self._session_vault.set_cookie(domain, name, value)

                if proxy:
                    self._proxy_pool.mark_success(proxy, latency)

                return response.status_code, response.text, dict(response.headers)

            except asyncio.TimeoutError as e:
                last_error = TimeoutError(f"Request timed out: {e}")
                if proxy:
                    self._proxy_pool.mark_failed(proxy, "timeout")

            except Exception as e:
                error_msg = str(e).lower()
                code = getattr(e, "code", None)
                if code in (5, 7) or "proxy" in error_msg:
                    last_error = ProxyError(f"Proxy failed: {e}")
                    if proxy:
                        self._proxy_pool.mark_failed(proxy, str(e))
                elif code == 28 or "timeout" in error_msg:
                    last_error = TimeoutError(f"Request timed out: {e}")
                    if proxy:
                        self._proxy_pool.mark_failed(proxy, "timeout")
                else:
                    last_error = UnknownFetchError(f"Fetch failed: {e}")

            if attempt < self._max_retries - 1:
                await asyncio.sleep((2 ** attempt) + random.uniform(0, 1))

        raise last_error or UnknownFetchError("All retries exhausted")
