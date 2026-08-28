"""Challenge detection tests."""

import pytest
from stealth_scraper.challenge import ChallengeType, detect_challenge


class TestChallengeDetection:
    def test_cloudflare_body(self):
        html = "<html>Just a moment... Checking your browser</html>"
        assert detect_challenge(html, {}) == ChallengeType.CLOUDFLARE

    def test_cloudflare_header(self):
        assert detect_challenge("", {"cf-ray": "abc123"}) == ChallengeType.CLOUDFLARE

    def test_datadome(self):
        html = '<div class="dd-captcha">Please verify</div>'
        assert detect_challenge(html, {}) == ChallengeType.DATADOME

    def test_perimeterx(self):
        html = '<div class="px-captcha">Bot check</div>'
        assert detect_challenge(html, {}) == ChallengeType.PERIMETERX

    def test_recaptcha(self):
        html = '<div class="g-recaptcha" data-sitekey="abc"></div>'
        assert detect_challenge(html, {}) == ChallengeType.RECAPTCHA

    def test_hcaptcha(self):
        html = '<div class="h-captcha"></div>'
        assert detect_challenge(html, {}) == ChallengeType.HCAPTCHA

    def test_no_challenge(self):
        html = "<html><body>Hello World</body></html>"
        assert detect_challenge(html, {}) == ChallengeType.NONE

    def test_akamai(self):
        html = "<script>akamai</script>"
        assert detect_challenge(html, {}) == ChallengeType.AKAMAI

    def test_imperva(self):
        html = "<div>incapsula</div>"
        assert detect_challenge(html, {}) == ChallengeType.IMPERVA
