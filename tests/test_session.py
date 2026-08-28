"""Session vault tests."""

import tempfile
import time
from stealth_scraper.session import SessionVault


class TestSessionVault:
    def test_cookie_roundtrip(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            vault = SessionVault(f.name)
            vault.set_cookie("example.com", "session", "abc123", expires=int(time.time()) + 3600)
            cookies = vault.get_cookies("example.com")
            assert cookies["session"] == "abc123"

    def test_cookie_expiration(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            vault = SessionVault(f.name)
            vault.set_cookie("example.com", "old", "gone", expires=int(time.time()) - 10)
            cookies = vault.get_cookies("example.com")
            assert "old" not in cookies

    def test_token_roundtrip(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            vault = SessionVault(f.name)
            vault.set_token("example.com", "csrf", "token123")
            assert vault.get_token("example.com", "csrf") == "token123"

    def test_clear_domain(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            vault = SessionVault(f.name)
            vault.set_cookie("example.com", "a", "1")
            vault.set_cookie("other.com", "b", "2")
            vault.clear_domain("example.com")
            assert vault.get_cookies("example.com") == {}
            assert vault.get_cookies("other.com") == {"b": "2"}
