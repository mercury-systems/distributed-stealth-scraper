#!/usr/bin/env python3
"""
MQNA Stealth Scraper – Patched and Hardened v1.1
"""
import asyncio
import json
import os
import random
import time
import sqlite3
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from curl_cffi.requests import AsyncSession
from playwright.async_api import async_playwright, BrowserContext
from playwright_stealth import Stealth

CONFIG = {
    # "direct" tells the pool to run raw local ISP network requests for testing
    "proxy_list": ["direct"],
    "max_light_workers": 5,
    "max_heavy_workers": 2,
    "heavy_retry_limit": 2,
    "light_retry_limit": 2,
    "challenge_keywords": [
        "cf-chl-bypass", "challenge-platform", "datadome", "/incapsula",
        "turnstile", "cf_clearance", "__ddg", "akamai"
    ],
    "browser_profile_dir_base": "./browser_profiles",
    "cookie_db_path": "./cookies.db",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "impersonate_target": "chrome131",
    "request_timeout": 30,
    "proxy_cooldown": 300,
    "max_proxy_fails": 3,
}

# ---- Cookie Store (JSON Serialization) ----
class CookieStore:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("""CREATE TABLE IF NOT EXISTS cookies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            proxy TEXT NOT NULL,
            ua TEXT NOT NULL,
            cookie_json TEXT NOT NULL,
            created_at REAL DEFAULT (strftime('%s','now')),
            UNIQUE(domain, proxy, ua)
        )""")
        self.conn.commit()

    def save_cookies(self, domain: str, proxy: str, ua: str, cookies: List[Dict]):
        blob = json.dumps(cookies)
        self.conn.execute(
            "INSERT OR REPLACE INTO cookies (domain, proxy, ua, cookie_json) VALUES (?, ?, ?, ?)",
            (domain, proxy, ua, blob))
        self.conn.commit()

    def load_cookies(self, domain: str, proxy: str, ua: str) -> Optional[List[Dict]]:
        row = self.conn.execute(
            "SELECT cookie_json FROM cookies WHERE domain=? AND proxy=? AND ua=? ORDER BY created_at DESC LIMIT 1",
            (domain, proxy, ua)).fetchone()
        if row:
            return json.loads(row[0])
        return None

# ---- Non-Crashing Retry Proxy Pool ----
class ProxyEntry:
    def __init__(self, url: str):
        self.url = url
        self.healthy = True
        self.fail_count = 0
        self.cooldown_until = 0.0

class ProxyPool:
    def __init__(self, urls: List[str]):
        self.proxies = {url: ProxyEntry(url) for url in urls}
        self.lock = asyncio.Lock()

    async def get_proxy(self) -> str:
        while True:
            async with self.lock:
                now = time.monotonic()
                available = [p for p in self.proxies.values() if p.healthy and now >= p.cooldown_until]
                if available:
                    return random.choice(available).url
            print("[Pool] No proxies available. Workers holding for 5 seconds...")
            await asyncio.sleep(5)

    async def mark_bad(self, url: str):
        if url == "direct":
            return
        async with self.lock:
            if url in self.proxies:
                entry = self.proxies[url]
                entry.fail_count += 1
                if entry.fail_count >= CONFIG["max_proxy_fails"]:
                    entry.healthy = False
                entry.cooldown_until = time.monotonic() + CONFIG["proxy_cooldown"]
                print(f"[Pool] Marked bad: {url} (Fail count: {entry.fail_count})")

    async def mark_good(self, url: str):
        if url == "direct":
            return
        async with self.lock:
            if url in self.proxies:
                entry = self.proxies[url]
                entry.fail_count = max(0, entry.fail_count - 1)
                if entry.fail_count < CONFIG["max_proxy_fails"]:
                    entry.healthy = True
                    entry.cooldown_until = 0.0

# ---- Challenge Detection ----
def is_challenge(text: str) -> bool:
    low = text.lower()
    return any(kw in low for kw in CONFIG["challenge_keywords"])

# ---- Light Engine ----
class LightEngine:
    def __init__(self):
        self.session = AsyncSession(
            impersonate=CONFIG["impersonate_target"],
            timeout=CONFIG["request_timeout"]
        )

    async def fetch(self, url: str, proxy: str, cookies: Optional[Dict] = None) -> Tuple[int, str]:
        proxy_arg = None if proxy == "direct" else proxy
        try:
            resp = await self.session.get(
                url,
                proxy=proxy_arg,
                cookies=cookies,
                headers={"User-Agent": CONFIG["user_agent"]},
                allow_redirects=True
            )
            return resp.status_code, resp.text
        except Exception as e:
            return 0, str(e)

# ---- Heavy Engine ----
class HeavyEngine:
    def __init__(self, proxy_pool: ProxyPool, cookie_store: CookieStore):
        self.proxy_pool = proxy_pool
        self.cookie_store = cookie_store
        self.playwright = None
        self.contexts: Dict[str, BrowserContext] = {}
        self.semaphore = asyncio.Semaphore(CONFIG["max_heavy_workers"])

    async def launch(self):
        self.playwright = await async_playwright().start()

    async def get_context(self, proxy: str) -> BrowserContext:
        if proxy not in self.contexts:
            profile_dir = f"{CONFIG['browser_profile_dir_base']}_{abs(hash(proxy))}"
            proxy_config = None if proxy == "direct" else {"server": proxy}
            
            context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=True,
                proxy=proxy_config,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/New_York",
                user_agent=CONFIG["user_agent"]
            )
            # Patch applied directly onto the context namespace using the v2.x API
            await Stealth().apply_stealth_async(context)
            self.contexts[proxy] = context
        return self.contexts[proxy]

    async def fetch_with_challenge(self, url: str, proxy: str, retry_count=0) -> Tuple[int, str, List[Dict]]:
        async with self.semaphore:
            context = await self.get_context(proxy)
            page = await context.new_page()
            try:
                # Basic cursor variance to bypass initial tracking triggers
                await page.mouse.move(random.randint(100, 300), random.randint(100, 300))
                response = await page.goto(url, wait_until="networkidle", timeout=CONFIG["request_timeout"] * 1000)
                await asyncio.sleep(3)
                content = await page.content()
                
                if is_challenge(content):
                    print(f"[Heavy] Challenge encountered on {url}. Triggering extended timeout...")
                    await page.wait_for_timeout(5000)
                    content = await page.content()
                    if is_challenge(content) and retry_count < CONFIG["heavy_retry_limit"]:
                        await page.close()
                        return await self.fetch_with_challenge(url, proxy, retry_count + 1)
                        
                cookies = await context.cookies()
                status = response.status if response else 0
                await page.close()
                return status, content, cookies
            except Exception as e:
                await page.close()
                return 0, str(e), []

    async def pre_warm_session(self, domain: str, proxy: str):
        url = f"https://{domain}/"
        status, _, cookies = await self.fetch_with_challenge(url, proxy)
        if cookies:
            self.cookie_store.save_cookies(domain, proxy, CONFIG["user_agent"], cookies)
            print(f"[Warm] Successfully stored session for {domain}")

# ---- Orchestrator ----
class StealthScraper:
    def __init__(self):
        self.proxy_pool = ProxyPool(CONFIG["proxy_list"])
        self.cookie_store = CookieStore(CONFIG["cookie_db_path"])
        self.light_engine = LightEngine()
        self.heavy_engine = HeavyEngine(self.proxy_pool, self.cookie_store)

    async def process_task(self, url: str, proxy: str) -> str:
        domain = urlparse(url).netloc
        saved_cookies = self.cookie_store.load_cookies(domain, proxy, CONFIG["user_agent"])
        cookie_dict = {c['name']: c['value'] for c in saved_cookies} if saved_cookies else None

        status, text = await self.light_engine.fetch(url, proxy, cookies=cookie_dict)
        if status == 200 and not is_challenge(text):
            await self.proxy_pool.mark_good(proxy)
            return text

        print(f"[Escalate] Light engine failed (Status: {status}). Invoking heavy context...")
        status, text, cookies = await self.heavy_engine.fetch_with_challenge(url, proxy)
        if status == 200 and not is_challenge(text):
            if cookies:
                self.cookie_store.save_cookies(domain, proxy, CONFIG["user_agent"], cookies)
            await self.proxy_pool.mark_good(proxy)
            return text
        else:
            await self.proxy_pool.mark_bad(proxy)
            raise Exception(f"Evasion layer breached. Status: {status}")

    async def worker(self, queue: asyncio.Queue):
        while True:
            url, retries = await queue.get()
            try:
                proxy = await self.proxy_pool.get_proxy()
                content = await self.process_task(url, proxy)
                print(f"[Success] Processed: {url} ({len(content)} bytes)")
            except Exception as e:
                if retries > 0:
                    print(f"[Retry] Queue recycle for {url} (Retries left: {retries})")
                    await queue.put((url, retries - 1))
                else:
                    print(f"[Failure] Target exhausted: {url} Error: {e}")
            finally:
                queue.task_done()

    async def run(self, urls: List[str], retries=2):
        await self.heavy_engine.launch()
        domains = {urlparse(u).netloc for u in urls}
        for dom in domains:
            try:
                proxy = await self.proxy_pool.get_proxy()
                await self.heavy_engine.pre_warm_session(dom, proxy)
            except Exception as e:
                print(f"[Warm] Failed for {dom}: {e}")

        queue = asyncio.Queue(maxsize=len(urls))
        for u in urls:
            await queue.put((u, retries))
            
        workers = [asyncio.create_task(self.worker(queue)) for _ in range(CONFIG["max_light_workers"])]
        await queue.join()
        for w in workers:
            w.cancel()
            
        for ctx in self.heavy_engine.contexts.values():
            await ctx.close()
        await self.heavy_engine.playwright.stop()

async def main():
    scraper = StealthScraper()
    # Testing with an unprotected target and a protected target in direct fallback mode
    targets = ["https://example.com/", "https://httpbin.org/status/200"]
    await scraper.run(targets)

if __name__ == "__main__":
    asyncio.run(main())
