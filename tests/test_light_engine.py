"""Light engine integration tests — requires network."""

import pytest
from stealth_scraper import StealthScraper, ScraperConfig


@pytest.mark.asyncio
@pytest.mark.integration
async def test_light_engine_httpbin():
    config = ScraperConfig(proxy_list=(), max_retries=2, enable_heavy=False)
    scraper = StealthScraper(config)
    await scraper.initialize()
    try:
        result = await scraper.fetch("https://httpbin.org/html")
        assert result.status == 200
        assert len(result.html) > 0
        assert "<html" in result.html.lower()
        assert result.tier == "light"
    finally:
        await scraper.close()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_light_engine_headers():
    config = ScraperConfig(proxy_list=(), max_retries=2, enable_heavy=False)
    scraper = StealthScraper(config)
    await scraper.initialize()
    try:
        result = await scraper.fetch("https://httpbin.org/headers")
        assert result.status == 200
    finally:
        await scraper.close()
