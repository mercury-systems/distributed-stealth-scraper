"""Batch mode integration tests — requires network."""

import pytest
from stealth_scraper import StealthScraper, ScraperConfig


@pytest.mark.asyncio
@pytest.mark.integration
async def test_batch_fetch():
    config = ScraperConfig(proxy_list=(), max_retries=2, enable_heavy=False)
    scraper = StealthScraper(config)
    await scraper.initialize()
    try:
        urls = ["https://httpbin.org/html", "https://httpbin.org/headers"]
        results = await scraper.fetch_batch(urls, concurrency=2)
        assert len(results) == 2
        assert all(r.status == 200 for r in results)
    finally:
        await scraper.close()
