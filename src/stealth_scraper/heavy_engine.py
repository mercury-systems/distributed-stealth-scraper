"""Heavy tier: Playwright Chromium with stealth patches."""

import asyncio
import time
from typing import Optional, Tuple, Dict

from .exceptions import ChallengeNotSolvedError
from .proxy import ProxyPool
from .session import SessionVault


class HeavyEngine:
    def __init__(self, proxy_pool: ProxyPool, session_vault: SessionVault,
                 user_agent: str, headless: bool = True, timeout: float = 60.0):
        self._proxy_pool = proxy_pool
        self._session_vault = session_vault
        self._user_agent = user_agent
        self._headless = headless
        self._timeout = timeout
        self._playwright = None
        self._browser = None
        self._context = None

    async def initialize(self):
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise RuntimeError("Playwright not installed. Run: pip install playwright>=1.40.0 && playwright install chromium") from e

        self._playwright = await async_playwright().start()

        launch_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ]

        self._browser = await self._playwright.chromium.launch(headless=self._headless, args=launch_args)
        self._context = await self._browser.new_context(
            user_agent=self._user_agent,
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            geolocation={"latitude": 40.7128, "longitude": -74.0060},
            permissions=["geolocation"],
        )

        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            const origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
            CanvasRenderingContext2D.prototype.getImageData = function(...args) {
                const imageData = origGetImageData.apply(this, args);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i] = (imageData.data[i] + 1) % 256;
                }
                return imageData;
            };
            const getParam = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParam.apply(this, [parameter]);
            };
        """)

    async def close(self):
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def fetch(self, url: str) -> Tuple[int, str, Dict[str, str]]:
        if not self._context:
            raise RuntimeError("Heavy engine not initialized")

        domain = url.split("/")[2]
        page = None

        try:
            cookies = self._session_vault.get_cookies(domain)
            if cookies:
                await self._context.add_cookies([
                    {"name": k, "value": v, "domain": domain, "path": "/"}
                    for k, v in cookies.items()
                ])

            page = await self._context.new_page()
            response = await page.goto(url, wait_until="networkidle", timeout=self._timeout * 1000)

            challenge_selectors = [
                "#cf-challenge-running", ".dd-captcha", ".px-captcha",
                "#rc-anchor-container", ".h-captcha", "[data-cf-modified]",
            ]

            for selector in challenge_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=3000)
                    await asyncio.sleep(5)
                    break
                except Exception:
                    continue

            await asyncio.sleep(2)
            html = await page.content()
            headers = {k: v for k, v in response.headers.items()} if response else {}
            status = response.status if response else 0

            browser_cookies = await self._context.cookies()
            for cookie in browser_cookies:
                expires = cookie.get("expires")
                if expires and isinstance(expires, (int, float)):
                    expires = int(expires)
                self._session_vault.set_cookie(
                    cookie.get("domain", domain),
                    cookie["name"],
                    cookie["value"],
                    path=cookie.get("path", "/"),
                    expires=expires,
                    secure=cookie.get("secure", False),
                    http_only=cookie.get("httpOnly", False),
                )

            await self._extract_tokens(page, domain)

            if status == 0:
                status = 200

            return status, html, headers

        finally:
            if page:
                await page.close()

    async def _extract_tokens(self, page, domain: str):
        try:
            tokens = await page.evaluate("""() => {
                const result = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    if (key && (key.includes('token') || key.includes('auth') || key.includes('session'))) {
                        result[key] = localStorage.getItem(key);
                    }
                }
                return result;
            }""")
            for token_type, value in tokens.items():
                if value:
                    self._session_vault.set_token(domain, token_type, value)
        except Exception:
            pass
