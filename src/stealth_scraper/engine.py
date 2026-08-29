"""Main orchestrator."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, List

from .challenge import ChallengeType, detect_challenge
from .exceptions import InvalidURLError
from .proxy import ProxyPool
from .session import SessionVault
from .light_engine import LightEngine
from .heavy_engine import HeavyEngine

logger = logging.getLogger(__name__)


@dataclass
class ScraperConfig:
    max_retries: int = 3
    request_timeout: float = 30.0
    proxy_list: Tuple[str, ...] = field(default_factory=tuple)
    cookie_db: str = "cookies.db"
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    headless: bool = True
    heavy_engine_timeout: float = 60.0
    enable_heavy: bool = True


@dataclass
class FetchResult:
    url: str
    status: int
    html: str
    headers: Dict[str, str]
    challenge: ChallengeType
    tier: str
    latency: float
    proxy_used: Optional[str]
    timestamp: float


class StealthScraper:
    def __init__(self, config: Optional[ScraperConfig] = None):
        self._config = config or ScraperConfig()
        self._proxy_pool = ProxyPool(list(self._config.proxy_list))
        self._session_vault = SessionVault(self._config.cookie_db)
        self._light: Optional[LightEngine] = None
        self._heavy: Optional[HeavyEngine] = None
        self._heavy_available = False

    async def initialize(self):
        self._light = LightEngine(
            self._proxy_pool, self._session_vault,
            max_retries=self._config.max_retries,
            request_timeout=self._config.request_timeout,
        )
        await self._light.initialize()

        if self._config.enable_heavy:
            try:
                self._heavy = HeavyEngine(
                    self._proxy_pool, self._session_vault,
                    user_agent=self._config.user_agent,
                    headless=self._config.headless,
                    timeout=self._config.heavy_engine_timeout,
                )
                await self._heavy.initialize()
                self._heavy_available = True
                logger.info("Heavy engine initialized")
            except Exception as e:
                logger.warning(f"Heavy engine unavailable: {e}")
                self._heavy_available = False

    async def close(self):
        if self._light:
            await self._light.close()
        if self._heavy:
            await self._heavy.close()

    async def fetch(self, url: str, force_heavy: bool = False) -> FetchResult:
        if not url.startswith(("http://", "https://")):
            raise InvalidURLError(f"URL must start with http:// or https://: {url}")

        start_time = time.time()

        if force_heavy and self._heavy_available:
            status, html, headers = await self._heavy.fetch(url)
            challenge = detect_challenge(html, headers)
            return FetchResult(
                url=url, status=status, html=html, headers=headers,
                challenge=challenge, tier="heavy",
                latency=time.time() - start_time,
                proxy_used=None, timestamp=time.time()
            )

        try:
            status, html, headers = await self._light.fetch(url)
            challenge = detect_challenge(html, headers)

            if challenge != ChallengeType.NONE and self._heavy_available:
                logger.info(f"Challenge detected: {challenge.name}. Escalating to heavy engine...")
                status, html, headers = await self._heavy.fetch(url)
                challenge = detect_challenge(html, headers)
                tier = "heavy"
            else:
                tier = "light"

            return FetchResult(
                url=url, status=status, html=html, headers=headers,
                challenge=challenge, tier=tier,
                latency=time.time() - start_time,
                proxy_used=None, timestamp=time.time()
            )

        except Exception as e:
            if self._heavy_available:
                logger.warning(f"Light engine failed ({e}), falling back to heavy engine")
                status, html, headers = await self._heavy.fetch(url)
                challenge = detect_challenge(html, headers)
                return FetchResult(
                    url=url, status=status, html=html, headers=headers,
                    challenge=challenge, tier="heavy",
                    latency=time.time() - start_time,
                    proxy_used=None, timestamp=time.time()
                )
            raise

    async def fetch_batch(self, urls: List[str], concurrency: int = 3, force_heavy: bool = False) -> List[FetchResult]:
        semaphore = asyncio.Semaphore(concurrency)

        async def _fetch_one(url):
            async with semaphore:
                try:
                    return await self.fetch(url, force_heavy=force_heavy)
                except Exception:
                    return FetchResult(
                        url=url, status=0, html="", headers={},
                        challenge=ChallengeType.UNKNOWN, tier="error",
                        latency=0.0, proxy_used=None, timestamp=time.time()
                    )

        tasks = [_fetch_one(url) for url in urls]
        return await asyncio.gather(*tasks)

    def get_stats(self) -> Dict:
        return {
            "proxy_stats": self._proxy_pool.get_stats(),
            "session_stats": self._session_vault.stats(),
            "heavy_available": self._heavy_available,
        }
