# Distributed Stealth Scraper

Dual-mode web scraper. Light tier uses curl_cffi with JA3 spoofing. Heavy tier uses Playwright with stealth patches. Auto-escalates when WAF challenges are detected.

## Installation

```bash
git clone https://github.com/mercury-systems/distributed-stealth-scraper.git
cd distributed-stealth-scraper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

For the heavy engine (Playwright-based browser automation):

```bash
pip install -r requirements-heavy.txt
playwright install chromium
```

> **Note:** Always activate the virtual environment (`source .venv/bin/activate`) before working with this project.

Usage:

    stealth-scraper single https://httpbin.org/html
    stealth-scraper --heavy single https://example.com
    stealth-scraper batch --urls https://a.com https://b.com --concurrency 3

API example:

    import asyncio
    from stealth_scraper import StealthScraper, ScraperConfig

    async def main():
        scraper = StealthScraper(ScraperConfig())
        await scraper.initialize()
        result = await scraper.fetch("https://example.com")
        print(result.status, len(result.html))
        await scraper.close()

    asyncio.run(main())

Docker:

    docker compose up --build

Test:

    make test

MIT licensed.
