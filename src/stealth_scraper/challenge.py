"""WAF challenge detection."""

import re
from enum import Enum, auto
from typing import Dict


class ChallengeType(Enum):
    NONE = auto()
    CLOUDFLARE = auto()
    DATADOME = auto()
    PERIMETERX = auto()
    RECAPTCHA = auto()
    HCAPTCHA = auto()
    AKAMAI = auto()
    IMPERVA = auto()
    UNKNOWN = auto()


_PATTERNS = {
    ChallengeType.CLOUDFLARE: [
        re.compile(r"just a moment", re.I),
        re.compile(r"checking your browser", re.I),
        re.compile(r"cf-ray", re.I),
        re.compile(r"__cf_bm", re.I),
        re.compile(r"cf-challenge", re.I),
        re.compile(r"turnstile", re.I),
    ],
    ChallengeType.DATADOME: [
        re.compile(r"datadome", re.I),
        re.compile(r"dd-captcha", re.I),
        re.compile(r"captcha-delivery", re.I),
    ],
    ChallengeType.PERIMETERX: [
        re.compile(r"perimeterx", re.I),
        re.compile(r"px-captcha", re.I),
        re.compile(r"pxblocking", re.I),
    ],
    ChallengeType.RECAPTCHA: [
        re.compile(r"g-recaptcha", re.I),
        re.compile(r"recaptcha", re.I),
    ],
    ChallengeType.HCAPTCHA: [
        re.compile(r"h-captcha", re.I),
        re.compile(r"hcaptcha", re.I),
    ],
    ChallengeType.AKAMAI: [
        re.compile(r"akamai", re.I),
        re.compile(r"ak_bmsc", re.I),
    ],
    ChallengeType.IMPERVA: [
        re.compile(r"imperva", re.I),
        re.compile(r"incapsula", re.I),
        re.compile(r"visid_incap", re.I),
    ],
}


def detect_challenge(html: str, headers: Dict[str, str]) -> ChallengeType:
    html_lower = html.lower() if html else ""
    headers_lower = {k.lower(): v.lower() for k, v in (headers or {}).items()}

    if "cf-ray" in headers_lower or "__cf_bm" in headers_lower:
        return ChallengeType.CLOUDFLARE
    if "x-datadome" in headers_lower:
        return ChallengeType.DATADOME
    if "x-perimeterx" in headers_lower:
        return ChallengeType.PERIMETERX

    for challenge_type, patterns in _PATTERNS.items():
        for pattern in patterns:
            if pattern.search(html_lower):
                return challenge_type

    return ChallengeType.NONE
