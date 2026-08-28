"""CLI parsing tests."""

import sys
from unittest.mock import patch
from stealth_scraper.cli import main


class TestCLI:
    def test_single_command(self):
        with patch.object(sys, "argv", ["stealth-scraper", "--light-only", "single", "https://example.com"]):
            with patch("stealth_scraper.cli.asyncio.run") as mock_run:
                try:
                    main()
                except SystemExit:
                    pass
                assert mock_run.called

    def test_batch_command(self):
        with patch.object(sys, "argv", ["stealth-scraper", "batch", "--urls", "https://a.com", "https://b.com"]):
            with patch("stealth_scraper.cli.asyncio.run") as mock_run:
                try:
                    main()
                except SystemExit:
                    pass
                assert mock_run.called
