"""Distributed Stealth Scraper v2.0.0"""

from .engine import StealthScraper, ScraperConfig, FetchResult
from .challenge import ChallengeType, detect_challenge
from .proxy import ProxyPool, ProxyExhaustedError
from .session import SessionVault
from .exceptions import (
    InvalidURLError,
    ProxyError,
    ProxyExhaustedError,
    TimeoutError,
    UnknownFetchError,
    ChallengeNotSolvedError,
)
from .light_engine import LightEngine
from .heavy_engine import HeavyEngine

__version__ = "2.0.0"
