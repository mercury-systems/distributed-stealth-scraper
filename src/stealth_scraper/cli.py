"""Command-line interface."""

import argparse
import asyncio
import json
import logging
import sys
import time
from typing import List

from .engine import StealthScraper, ScraperConfig, FetchResult
from .challenge import ChallengeType


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s | %(levelname)-8s | %(message)s" if verbose else "%(message)s"
    logging.basicConfig(level=level, format=fmt, datefmt="%H:%M:%S")


def print_banner():
    print("=" * 72)
    print("  MERCURY-OPS  |  Distributed Stealth Scraper  v2.0.0")
    print("=" * 72)
    print()


def print_result(result: FetchResult, index: int = 0):
    tier_icon = "⚡" if result.tier == "light" else "🔥"
    challenge_icon = "🛡️" if result.challenge == ChallengeType.NONE else "⚠️"
    print(f"  [{index + 1}] {tier_icon} {result.url}")
    print(f"      Status: {result.status} | {challenge_icon} Challenge: {result.challenge.name}")
    print(f"      Tier: {result.tier.upper()} | Latency: {result.latency:.2f}s | Size: {len(result.html)} bytes")
    print()


def print_summary(results: List[FetchResult], elapsed: float):
    total = len(results)
    success = sum(1 for r in results if r.status == 200)
    light_count = sum(1 for r in results if r.tier == "light")
    heavy_count = sum(1 for r in results if r.tier == "heavy")
    error_count = sum(1 for r in results if r.tier == "error")
    total_bytes = sum(len(r.html) for r in results)
    avg_latency = sum(r.latency for r in results) / total if total else 0

    print("-" * 72)
    print("  MISSION REPORT")
    print("-" * 72)
    print(f"  ✅ {success}/{total} pages scraped successfully")
    print(f"  ⚡ {light_count} light-tier ({light_count/total*100:.0f}%)")
    print(f"  🔥 {heavy_count} heavy-tier ({heavy_count/total*100:.0f}%)")
    if error_count:
        print(f"  ❌ {error_count} errors")
    print(f"  📊 {total_bytes/1000:.1f}KB total data extracted")
    print(f"  ⏱️  Batch completed in {elapsed:.1f}s (avg {avg_latency:.2f}s per request)")
    print("-" * 72)
    print()


async def run_single(args):
    config = ScraperConfig(
        proxy_list=tuple(args.proxy) if args.proxy else (),
        max_retries=args.retries,
        request_timeout=args.timeout,
        headless=not args.visible,
        enable_heavy=not args.light_only,
    )
    scraper = StealthScraper(config)
    await scraper.initialize()

    try:
        print(f"  → Target: {args.url}")
        print()
        result = await scraper.fetch(args.url, force_heavy=args.heavy)
        print_result(result)

        if args.output:
            output_data = {
                "url": result.url, "status": result.status,
                "html_length": len(result.html), "headers": result.headers,
                "challenge": result.challenge.name, "tier": result.tier,
                "latency": result.latency,
            }
            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)
            print(f"  💾 Saved to {args.output}")

    finally:
        await scraper.close()


async def run_batch(args):
    urls = []
    if args.url_file:
        with open(args.url_file) as f:
            urls = [line.strip() for line in f if line.strip()]
    elif args.urls:
        urls = args.urls
    else:
        print("❌ No URLs provided. Use --url or --url-file.")
        sys.exit(1)

    config = ScraperConfig(
        proxy_list=tuple(args.proxy) if args.proxy else (),
        max_retries=args.retries,
        request_timeout=args.timeout,
        headless=not args.visible,
        enable_heavy=not args.light_only,
    )
    scraper = StealthScraper(config)
    await scraper.initialize()

    try:
        print(f"  → Batch: {len(urls)} URLs | Concurrency: {args.concurrency}")
        print()
        start = time.time()
        results = await scraper.fetch_batch(urls, concurrency=args.concurrency, force_heavy=args.heavy)
        elapsed = time.time() - start

        for i, result in enumerate(results):
            print_result(result, index=i)

        print_summary(results, elapsed)

        if args.output:
            output_data = [
                {"url": r.url, "status": r.status, "html_length": len(r.html),
                 "challenge": r.challenge.name, "tier": r.tier, "latency": r.latency}
                for r in results
            ]
            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)
            print(f"  💾 Saved to {args.output}")

    finally:
        await scraper.close()


def main():
    parser = argparse.ArgumentParser(
        description="Distributed Stealth Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s single https://example.com
  %(prog)s --heavy single https://example.com
  %(prog)s batch --urls https://a.com https://b.com --concurrency 5
  %(prog)s batch --url-file urls.txt --output results.json
        """
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--proxy", action="append", help="Proxy URL (repeatable)")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--light-only", action="store_true", help="Disable heavy engine")
    parser.add_argument("--heavy", action="store_true", help="Force heavy engine")
    parser.add_argument("--visible", action="store_true", help="Show browser window")

    subparsers = parser.add_subparsers(dest="command", required=True)

    single_parser = subparsers.add_parser("single", help="Scrape a single URL")
    single_parser.add_argument("url", help="Target URL")
    single_parser.add_argument("--output", "-o", help="Save result to JSON")

    batch_parser = subparsers.add_parser("batch", help="Scrape multiple URLs")
    batch_parser.add_argument("--urls", nargs="+", help="Space-separated URLs")
    batch_parser.add_argument("--url-file", help="File with one URL per line")
    batch_parser.add_argument("--concurrency", type=int, default=3)
    batch_parser.add_argument("--output", "-o", help="Save results to JSON")

    args = parser.parse_args()
    setup_logging(args.verbose)
    print_banner()

    if args.command == "single":
        asyncio.run(run_single(args))
    elif args.command == "batch":
        asyncio.run(run_batch(args))


if __name__ == "__main__":
    main()
