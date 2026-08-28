"""Heavy engine integration tests — requires Playwright."""

import pytest
from stealth_scraper import StealthScraper, ScraperConfig


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.heavy
async def test_heavy_engine_httpbin():
    config = ScraperConfig(proxy_list=(), max_retries=2, enable_heavy=True, headless=True)
    scraper = StealthScraper(config)
    await scraper.initialize()
    try:
        result = await scraper.fetch("https://httpbin.org/html", force_heavy=True)
        assert result.status == 200
        assert len(result.html) > 0
        assert result.tier == "heavy"
    finally:
        await scraper.close()
