#!/usr/bin/env python3
"""Live demo against real targets."""

import asyncio
import logging

from stealth_scraper import StealthScraper, ScraperConfig

logging.basicConfig(level=logging.INFO, format="%(message)s")

TARGETS = [
    ("https://httpbin.org/html", "Baseline — no protection"),
    ("https://quotes.toscrape.com/", "Scraper-friendly"),
    ("https://httpbin.org/headers", "Header mirror"),
    ("https://docs.python.org/3/", "Production docs — CDN fronted"),
]


async def main():
    print("=" * 72)
    print("  MERCURY-OPS  |  Distributed Stealth Scraper  |  Live Demo")
    print("=" * 72)
    print()

    config = ScraperConfig(proxy_list=(), max_retries=2, request_timeout=30.0, headless=True, enable_heavy=True)
    scraper = StealthScraper(config)
    await scraper.initialize()

    try:
        for i, (url, desc) in enumerate(TARGETS, 1):
            print(f"  [{i}/4] {desc}")
            print(f"        URL: {url}")
            print("-" * 50)

            try:
                result = await scraper.fetch(url)
                tier_icon = "⚡" if result.tier == "light" else "🔥"
                challenge_icon = "🛡️" if result.challenge.name == "NONE" else "⚠️"
                print(f"        {tier_icon} Tier: {result.tier.upper()}")
                print(f"        📡 Status: {result.status}")
                print(f"        {challenge_icon} Challenge: {result.challenge.name}")
                print(f"        📏 Size: {len(result.html)} bytes")
                print(f"        ⏱️  Latency: {result.latency:.2f}s")
                print()
            except Exception as e:
                print(f"        ❌ {type(e).__name__}: {e}")
                print()

        stats = scraper.get_stats()
        print("=" * 72)
        print("  MISSION REPORT")
        print("=" * 72)
        print(f"  ✅ {len(TARGETS)} real targets tested")
        print(f"  🛡️  Session vault: {stats['session_stats']['cookies']} cookies stored")
        print(f"  🔧 Heavy engine: {'AVAILABLE' if stats['heavy_available'] else 'UNAVAILABLE'}")
        print()

    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
