import unittest
import os
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone

# Assuming config is initialized globally or can be mocked
from core.config import config, ConfigValidationError

# Mock scraper functions for individual testing
class MockScraperModule:
    pass

# Patch requests at the module level in core.http_utils
@patch('core.http_utils.requests')
@patch('core.storage.save_gig', new_callable=AsyncMock)
@patch('core.storage.update_scraper_health')
@patch('core.storage.log_scraper_performance')
@patch('core.robots.is_url_allowed', return_value=True) # Assume URLs are allowed by robots.txt by default
class TestJijiScraper(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Ensure config has necessary values for testing
        config._data = {
            "use_proxies": False,
            "user_agents": ["Test-Agent"],
            "delay_range": [0, 0], # No delay during tests
            "retry_attempts": 1, # Set a minimal retry attempt for tests
            "http_timeout": 5 # Set a timeout for tests
        }
        self.mock_jiji_module = MockScraperModule()
        self.mock_jiji_module.scrape_jiji = AsyncMock()

    async def test_jiji_scrape_success(self, mock_is_url_allowed, mock_log_performance, mock_update_health, mock_save_gig, mock_requests):
        # Import inside the test to ensure mocks are active when module is loaded
        from scrapers.jiji import scrape_jiji

        # Mock the requests.get response for the initial search page
        mock_response_search = MagicMock()
        mock_response_search.text = """
        <html><body>
            <div class="b-list-advert__item">
                <div class="b-list-advert__item-title">Need Python Developer for Project</div>
                <a class="b-list-advert__item-title-link" href="https://jiji.ug/ad/123-python"></a>
            </div>
            <div class="b-list-advert__item">
                <div class="b-list-advert__item-title">Selling old car</div>
                <a class="b-list-advert__item-title-link" href="https://jiji.ug/ad/456-car"></a>
            </div>
        </body></html>
        """
        # Mock the requests.get response for the gig detail page
        mock_response_detail = MagicMock()
        mock_response_detail.text = "<html><body><div class=\"b-advert-info__description-text\">Full description here.</div></body></html>"
        
        mock_requests.get.side_effect = [
            mock_response_search, # First call for BASE_URL
            mock_response_detail  # Second call for gig detail
        ]
        
        # Mock looks_like_gig to return True for the relevant title
        with patch('scrapers.jiji.looks_like_gig', return_value=True) as mock_looks_like_gig:
            await scrape_jiji()

            # Assertions
            self.assertEqual(mock_requests.get.call_count, 2) # Two requests should be made
            mock_looks_like_gig.assert_called_with("Need Python Developer for Project")
            mock_save_gig.assert_called_once()
            mock_save_gig.assert_called_with(
                source='Jiji',
                title='Need Python Developer for Project',
                link='https://jiji.ug/ad/123-python',
                snippet='Need Python Developer for Project',
                price=None,
                full_description='Full description here.',
                timestamp=unittest.mock.ANY, # Timestamp is generated in save_gig
                contact_info=None,
                category=None
            )
            mock_update_health.assert_called_once_with("jiji")
            mock_log_performance.assert_called_once_with("jiji", unittest.mock.ANY, "success", None)

    async def test_jiji_scrape_robots_blocked(self, mock_is_url_allowed, mock_log_performance, mock_update_health, mock_save_gig, mock_requests):
        # Import inside the test to ensure mocks are active when module is loaded
        from scrapers.jiji import scrape_jiji
        mock_is_url_allowed.return_value = False # Block by robots.txt

        await scrape_jiji()

        mock_is_url_allowed.assert_called_once()
        mock_requests.get.assert_not_called() # No requests should be made
        mock_save_gig.assert_not_called()
        mock_update_health.assert_not_called()
        mock_log_performance.assert_called_once_with("jiji", unittest.mock.ANY, "skipped_robots", None)


# Patch requests at the module level in core.http_utils
@patch('core.http_utils.requests')
@patch('core.storage.save_gig', new_callable=AsyncMock)
@patch('core.storage.update_scraper_health')
@patch('core.storage.log_scraper_performance')
@patch('core.robots.is_url_allowed', return_value=True)
class TestRedditScraper(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        config._data = {
            "use_proxies": False,
            "user_agents": ["Test-Agent"],
            "delay_range": [0, 0], # No delay during tests
            "retry_attempts": 1, # Set a minimal retry attempt for tests
            "http_timeout": 5 # Set a timeout for tests
        }

    async def test_reddit_scrape_success(self, mock_is_url_allowed, mock_log_performance, mock_update_health, mock_save_gig, mock_requests):
        # Import inside the test to ensure mocks are active when module is loaded
        from scrapers.reddit import scrape_reddit

        # Mock Reddit API response
        mock_response_reddit = MagicMock()
        mock_response_reddit.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "Hiring a freelance web developer",
                            "selftext": "Looking for someone to build a website.",
                            "permalink": "/r/forhire/comments/123",
                            "created_utc": 1672531200, # Jan 1, 2023 00:00:00 UTC
                            "subreddit": "forhire"
                        }
                    }
                ]
            }
        }
        mock_requests.get.return_value = mock_response_reddit
        
        with patch('scrapers.reddit.looks_like_gig', return_value=True) as mock_looks_like_gig:
            await scrape_reddit()

            mock_requests.get.assert_called()
            mock_looks_like_gig.assert_called_with("Hiring a freelance web developer Looking for someone to build a website.")
            mock_save_gig.assert_called_once()
            mock_save_gig.assert_called_with(
                source='Reddit (r/forhire)',
                title='Hiring a freelance web developer',
                link='https://www.reddit.com/r/forhire/comments/123',
                snippet='Hiring a freelance web developer',
                full_description='Looking for someone to build a website.',
                timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc).isoformat(),
                category='forhire',
                price=None, # Not extracted by Reddit scraper
                contact_info=None # Not extracted by Reddit scraper
            )
            # update_scraper_health should be called for each subreddit scraped
            mock_update_health.assert_called_with("reddit.forhire")
            mock_log_performance.assert_called() # Should be called for each subreddit

    async def test_reddit_scrape_robots_blocked(self, mock_is_url_allowed, mock_log_performance, mock_update_health, mock_save_gig, mock_requests):
        # Import inside the test to ensure mocks are active when module is loaded
        from scrapers.reddit import scrape_reddit
        mock_is_url_allowed.return_value = False

        await scrape_reddit()

        mock_is_url_allowed.assert_called() # Called for each subreddit's BASE_URL
        mock_requests.get.assert_not_called()
        mock_save_gig.assert_not_called()
        mock_update_health.assert_not_called()
        mock_log_performance.assert_called() # Called for each subreddit with 'skipped_robots' status


# Test for Discord Scraper
@patch('scrapers.discord.discord.Client') # Patch the discord.Client class itself
@patch('core.storage.save_gig', new_callable=AsyncMock)
@patch('core.storage.update_scraper_health')
@patch('core.storage.log_scraper_performance')
class TestDiscordScraper(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        config._data = {
            "enabled_scrapers": ["discord"], # Ensure discord is enabled
            "notification_settings": {
                "telegram_api_id": 12345,
                "telegram_api_hash": "test_hash"
            }
        }

    async def test_scrape_discord_starts_client(self, mock_log_performance, mock_update_health, mock_save_gig, MockDiscordClient):
        from scrapers.discord import scrape_discord
        
        # Configure the mocked client instance
        mock_client_instance = MockDiscordClient.return_value
        mock_client_instance.start = AsyncMock(return_value=None) # Make it immediately return
        mock_client_instance.wait_until_ready = AsyncMock(return_value=None)
        mock_client_instance.run_until_disconnected = AsyncMock(return_value=None)
        mock_client_instance.is_closed.return_value = False # Assume not closed for finally block

        # Ensure that DISCORD_BOT_TOKEN is set for the test
        with patch.dict(os.environ, {'DISCORD_BOT_TOKEN': 'TEST_TOKEN'}):
            await scrape_discord()
            
            mock_client_instance.start.assert_called_once_with('TEST_TOKEN')
            mock_client_instance.wait_until_ready.assert_called_once()
            mock_log_performance.assert_called_once_with("discord", unittest.mock.ANY, "success", None)
            mock_client_instance.close.assert_called_once() # Should be called in finally

    async def test_scrape_discord_no_token(self, mock_log_performance, mock_update_health, mock_save_gig, MockDiscordClient):
        from scrapers.discord import scrape_discord
        # Ensure DISCORD_BOT_TOKEN is NOT set for this test
        with patch.dict(os.environ, clear=True): # Clear environment variables
            await scrape_discord()
            
            MockDiscordClient.assert_not_called() # Client should not even be instantiated
            mock_log_performance.assert_called_once_with("discord", unittest.mock.ANY, "failed", unittest.mock.ANY)
            mock_update_health.assert_not_called() # Should not be updated on failure to start

# Test for Telegram Scraper
@patch('scrapers.telegram.TelegramClient') # Patch the TelegramClient class
@patch('core.storage.save_gig', new_callable=AsyncMock)
@patch('core.storage.update_scraper_health')
@patch('core.storage.log_scraper_performance')
class TestTelegramScraper(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        config._data = {
            "enabled_scrapers": ["telegram"], # Ensure telegram is enabled
            "notification_settings": {
                "telegram_api_id": 12345,
                "telegram_api_hash": "test_hash"
            }
        }
        
    async def test_scrape_telegram_starts_client(self, mock_log_performance, mock_update_health, mock_save_gig, MockTelegramClient):
        from scrapers.telegram import scrape_telegram

        # Configure the mocked client instance
        mock_client_instance = MockTelegramClient.return_value
        mock_client_instance.start = AsyncMock(return_value=None) # Make it immediately return
        mock_client_instance.run_until_disconnected = AsyncMock(return_value=None) # Make it immediately return
        mock_client_instance.is_connected.return_value = False # Assume not connected for finally block

        # Ensure that TELEGRAM_API_ID and TELEGRAM_API_HASH are set for the test
        with patch.dict(os.environ, {'TELEGRAM_API_ID': '12345', 'TELEGRAM_API_HASH': 'TEST_HASH'}):
            await scrape_telegram()
            
            # Assert that start was called with the correct arguments (including the phone lambda)
            mock_client_instance.start.assert_called_once()
            # We can't assert the exact lambda, but we can check it received a keyword arg 'phone'
            call_args, call_kwargs = mock_client_instance.start.call_args
            self.assertIn('phone', call_kwargs)
            self.assertTrue(callable(call_kwargs['phone'])) # Assert it's a callable (the lambda)

            mock_client_instance.run_until_disconnected.assert_called_once()
            mock_update_health.assert_called_once_with("telegram")
            mock_log_performance.assert_called_once_with("telegram", unittest.mock.ANY, "success", None)
            mock_client_instance.disconnect.assert_called_once() # Should be called in finally

    async def test_scrape_telegram_no_api_credentials(self, mock_log_performance, mock_update_health, mock_save_gig, MockTelegramClient):
        from scrapers.telegram import scrape_telegram
        # Ensure API credentials are NOT set for this test
        with patch.dict(os.environ, clear=True): # Clear environment variables
            await scrape_telegram()
            
            # Since client instantiation is now conditional, MockTelegramClient should not be called
            MockTelegramClient.assert_not_called()
            mock_log_performance.assert_called_once_with("telegram", unittest.mock.ANY, "failed", unittest.mock.ANY)
            mock_update_health.assert_not_called() # Should not be updated on failure to start


if __name__ == '__main__':
    unittest.main()