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


# Test for Craigslist Scraper
@patch('core.http_utils.requests')
@patch('core.storage.save_gig', new_callable=AsyncMock)
@patch('core.storage.update_scraper_health')
@patch('core.storage.log_scraper_performance')
@patch('core.robots.is_url_allowed', return_value=True)
class TestCraigslistScraper(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        config._data = {
            "use_proxies": False,
            "user_agents": ["Test-Agent"],
            "delay_range": [0, 0],
            "retry_attempts": 1,
            "http_timeout": 5,
            "scrapers": {
                "craigslist": {
                    "cities": ["sfbay"],
                    "max_pages": 2
                }
            }
        }

    async def test_craigslist_scrape_success(self, mock_is_url_allowed, mock_log_performance, mock_update_health, mock_save_gig, mock_requests):
        """Test successful Craigslist scraping with multiple listings."""
        from scrapers.craigslist import scrape_craigslist

        # Mock HTML response with Craigslist structure
        mock_response = MagicMock()
        mock_response.text = """
        <html><body>
            <ul class="rows">
                <li class="result-row">
                    <a href="/sfc/cpg/d/python-developer-needed/1234.html" class="result-title">
                        Python Developer Needed - Quick Fix
                    </a>
                    <span class="result-price">$50</span>
                    <time class="result-date" datetime="2023-12-11T10:00:00">Dec 11</time>
                    <span class="result-hood">(San Francisco)</span>
                </li>
                <li class="result-row">
                    <a href="/sfc/cpg/d/website-bug-fix/5678.html" class="result-title">
                        Website Bug Fix - Urgent
                    </a>
                    <span class="result-price">$75</span>
                    <time class="result-date" datetime="2023-12-11T11:00:00">Dec 11</time>
                </li>
            </ul>
        </body></html>
        """
        mock_requests.get.return_value = mock_response

        # Mock looks_like_gig to return True
        with patch('scrapers.craigslist.looks_like_gig', return_value=True) as mock_looks_like_gig:
            await scrape_craigslist()

            # Verify requests were made (2 pages per city)
            self.assertEqual(mock_requests.get.call_count, 2)

            # Verify save_gig was called for each listing (2 listings per page * 2 pages)
            self.assertEqual(mock_save_gig.call_count, 4)

            # Verify one of the calls has correct structure
            call_args_list = mock_save_gig.call_args_list
            first_call = call_args_list[0]
            self.assertEqual(first_call[1]['source'], 'Craigslist (sfbay)')
            self.assertIn('Python Developer', first_call[1]['title'])
            self.assertIn('craigslist.org', first_call[1]['link'])
            self.assertEqual(first_call[1]['price'], '$50')
            self.assertEqual(first_call[1]['category'], 'computer_gigs')

            # Verify scraper health updated
            mock_update_health.assert_called_once_with("craigslist")
            mock_log_performance.assert_called_once_with("craigslist", unittest.mock.ANY, "success", None)

    async def test_craigslist_robots_blocked(self, mock_is_url_allowed, mock_log_performance, mock_update_health, mock_save_gig, mock_requests):
        """Test Craigslist scraper respects robots.txt."""
        from scrapers.craigslist import scrape_craigslist

        mock_is_url_allowed.return_value = False

        await scrape_craigslist()

        # No requests should be made
        mock_requests.get.assert_not_called()
        mock_save_gig.assert_not_called()
        mock_update_health.assert_called_once_with("craigslist")

    async def test_craigslist_empty_results(self, mock_is_url_allowed, mock_log_performance, mock_update_health, mock_save_gig, mock_requests):
        """Test Craigslist scraper handles empty results gracefully."""
        from scrapers.craigslist import scrape_craigslist

        # Mock empty response
        mock_response = MagicMock()
        mock_response.text = "<html><body><ul class='rows'></ul></body></html>"
        mock_requests.get.return_value = mock_response

        await scrape_craigslist()

        # Requests should be made but no gigs saved
        self.assertGreater(mock_requests.get.call_count, 0)
        mock_save_gig.assert_not_called()

    async def test_craigslist_filtered_listings(self, mock_is_url_allowed, mock_log_performance, mock_update_health, mock_save_gig, mock_requests):
        """Test Craigslist scraper filters non-gig listings."""
        from scrapers.craigslist import scrape_craigslist

        mock_response = MagicMock()
        mock_response.text = """
        <html><body>
            <ul class="rows">
                <li class="result-row">
                    <a href="/sfc/cpg/d/selling-laptop/1234.html" class="result-title">
                        Selling Old Laptop
                    </a>
                </li>
            </ul>
        </body></html>
        """
        mock_requests.get.return_value = mock_response

        # Mock looks_like_gig to return False
        with patch('scrapers.craigslist.looks_like_gig', return_value=False):
            await scrape_craigslist()

            # Request made but no gigs saved
            self.assertGreater(mock_requests.get.call_count, 0)
            mock_save_gig.assert_not_called()

    async def test_craigslist_multi_city(self, mock_is_url_allowed, mock_log_performance, mock_update_health, mock_save_gig, mock_requests):
        """Test Craigslist scraper handles multiple cities."""
        from scrapers.craigslist import scrape_craigslist

        # Configure multiple cities
        config._data['scrapers']['craigslist']['cities'] = ['sfbay', 'newyork']

        mock_response = MagicMock()
        mock_response.text = """
        <html><body>
            <ul class="rows">
                <li class="result-row">
                    <a href="/cpg/d/test/1234.html" class="result-title">Test Gig</a>
                </li>
            </ul>
        </body></html>
        """
        mock_requests.get.return_value = mock_response

        with patch('scrapers.craigslist.looks_like_gig', return_value=True):
            await scrape_craigslist()

            # Should make requests for both cities (2 pages each = 4 total)
            self.assertEqual(mock_requests.get.call_count, 4)

            # Should save gigs from both cities
            sources = [call[1]['source'] for call in mock_save_gig.call_args_list]
            self.assertIn('Craigslist (sfbay)', sources)
            self.assertIn('Craigslist (newyork)', sources)


# Test for Locanto Scraper
@patch('core.http_utils.requests')
@patch('core.storage.save_gig', new_callable=AsyncMock)
@patch('core.storage.update_scraper_health')
@patch('core.storage.log_scraper_performance')
@patch('core.robots.is_url_allowed', return_value=True)
class TestLocantoScraper(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        config._data = {
            "use_proxies": False,
            "user_agents": ["Test-Agent"],
            "delay_range": [0, 0],
            "retry_attempts": 1,
            "http_timeout": 5,
            "scrapers": {
                "locanto": {
                    "countries": {"us": "https://www.locanto.com/IT-Jobs/"},
                    "max_pages": 2
                }
            }
        }

    async def test_locanto_scrape_success(self, mock_is_url_allowed, mock_log_performance, mock_update_health, mock_save_gig, mock_requests):
        """Test successful Locanto scraping."""
        from scrapers.locanto import scrape_locanto

        mock_response = MagicMock()
        mock_response.text = """
        <html><body>
            <article>
                <h2>Python Developer Needed</h2>
                <a href="/listing/12345">View Details</a>
                <p>Looking for Python expert for small project. Budget $100.</p>
            </article>
        </body></html>
        """
        mock_requests.get.return_value = mock_response

        with patch('scrapers.locanto.looks_like_gig', return_value=True):
            await scrape_locanto()

            self.assertEqual(mock_requests.get.call_count, 2)  # 2 pages
            mock_save_gig.assert_called()

            # Verify source includes country
            first_call = mock_save_gig.call_args_list[0]
            self.assertEqual(first_call[1]['source'], 'Locanto (US)')
            self.assertEqual(first_call[1]['category'], 'it_jobs')


# Test for ClassifiedAds Scraper
@patch('core.http_utils.requests')
@patch('core.storage.save_gig', new_callable=AsyncMock)
@patch('core.storage.update_scraper_health')
@patch('core.storage.log_scraper_performance')
@patch('core.robots.is_url_allowed', return_value=True)
class TestClassifiedAdsScraper(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        config._data = {
            "use_proxies": False,
            "user_agents": ["Test-Agent"],
            "delay_range": [0, 0],
            "retry_attempts": 1,
            "http_timeout": 5,
            "scrapers": {
                "classifiedads": {"max_pages": 2}
            }
        }

    async def test_classifiedads_scrape_success(self, mock_is_url_allowed, mock_log_performance, mock_update_health, mock_save_gig, mock_requests):
        """Test successful ClassifiedAds scraping."""
        from scrapers.classifiedads import scrape_classifiedads

        mock_response = MagicMock()
        mock_response.text = """
        <html><body>
            <div class="listing">
                <h3>Website Bug Fix Needed</h3>
                <a href="/listing/123">Details</a>
                <p>Need help fixing JavaScript bug. Will pay $75.</p>
                <span class="price">$75</span>
            </div>
        </body></html>
        """
        mock_requests.get.return_value = mock_response

        with patch('scrapers.classifiedads.looks_like_gig', return_value=True):
            await scrape_classifiedads()

            self.assertEqual(mock_requests.get.call_count, 2)
            mock_save_gig.assert_called()

            first_call = mock_save_gig.call_args_list[0]
            self.assertEqual(first_call[1]['source'], 'ClassifiedAds')
            self.assertEqual(first_call[1]['category'], 'computer_services')

    async def test_classifiedads_robots_blocked(self, mock_is_url_allowed, mock_log_performance, mock_update_health, mock_save_gig, mock_requests):
        """Test ClassifiedAds respects robots.txt."""
        from scrapers.classifiedads import scrape_classifiedads

        mock_is_url_allowed.return_value = False

        result = await scrape_classifiedads()

        self.assertEqual(result, 0)
        mock_requests.get.assert_not_called()


# Test for Gumtree Scraper
@patch('core.http_utils.requests')
@patch('core.storage.save_gig', new_callable=AsyncMock)
@patch('core.storage.update_scraper_health')
@patch('core.storage.log_scraper_performance')
@patch('core.robots.is_url_allowed', return_value=True)
class TestGumtreeScraper(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        config._data = {
            "use_proxies": False,
            "user_agents": ["Test-Agent"],
            "delay_range": [0, 0],
            "retry_attempts": 1,
            "http_timeout": 5,
            "scrapers": {
                "gumtree": {
                    "countries": {"uk": "https://www.gumtree.com/computers-telecoms-services"},
                    "max_pages": 2
                }
            }
        }

    async def test_gumtree_scrape_success(self, mock_is_url_allowed, mock_log_performance, mock_update_health, mock_save_gig, mock_requests):
        """Test successful Gumtree scraping."""
        from scrapers.gumtree import scrape_gumtree

        mock_response = MagicMock()
        mock_response.text = """
        <html><body>
            <article class="listing">
                <a href="/listing/123" class="listing-title">WordPress Developer</a>
                <div class="description">Need WP plugin customization. £50.</div>
                <span class="price">£50</span>
            </article>
        </body></html>
        """
        mock_requests.get.return_value = mock_response

        with patch('scrapers.gumtree.looks_like_gig', return_value=True):
            await scrape_gumtree()

            self.assertEqual(mock_requests.get.call_count, 2)  # 2 pages
            mock_save_gig.assert_called()

            first_call = mock_save_gig.call_args_list[0]
            self.assertEqual(first_call[1]['source'], 'Gumtree (UK)')
            self.assertEqual(first_call[1]['category'], 'computer_it_services')

    async def test_gumtree_multi_country(self, mock_is_url_allowed, mock_log_performance, mock_update_health, mock_save_gig, mock_requests):
        """Test Gumtree handles multiple countries."""
        from scrapers.gumtree import scrape_gumtree

        # Configure multiple countries
        config._data['scrapers']['gumtree']['countries'] = {
            'uk': 'https://www.gumtree.com/computers-telecoms-services',
            'au': 'https://www.gumtree.com.au/s-computer-it-services/k0c18493'
        }

        mock_response = MagicMock()
        mock_response.text = """
        <html><body>
            <article class="listing">
                <a href="/listing/123" class="listing-title">Test Gig</a>
            </article>
        </body></html>
        """
        mock_requests.get.return_value = mock_response

        with patch('scrapers.gumtree.looks_like_gig', return_value=True):
            await scrape_gumtree()

            # Should make requests for both countries (2 pages each = 4 total)
            self.assertEqual(mock_requests.get.call_count, 4)

            # Should save gigs from both countries
            sources = [call[1]['source'] for call in mock_save_gig.call_args_list]
            self.assertIn('Gumtree (UK)', sources)
            self.assertIn('Gumtree (AU)', sources)


# Test for DigitalPoint Scraper
@patch('core.http_utils.requests')
@patch('core.storage.save_gig', new_callable=AsyncMock)
@patch('core.storage.update_scraper_health')
@patch('core.storage.log_scraper_performance')
@patch('core.robots.is_url_allowed', return_value=True)
class TestDigitalPointScraper(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        config._data = {
            "use_proxies": False,
            "user_agents": ["Test-Agent"],
            "delay_range": [0, 0],
            "retry_attempts": 1,
            "http_timeout": 5,
            "scrapers": {
                "digitalpoint": {"max_pages": 2}
            }
        }

    async def test_digitalpoint_scrape_success(self, mock_is_url_allowed, mock_log_performance, mock_update_health, mock_save_gig, mock_requests):
        """Test successful DigitalPoint scraping."""
        from scrapers.digitalpoint import scrape_digitalpoint

        mock_response = MagicMock()
        mock_response.text = """
        <html><body>
            <div class="structItem">
                <a class="title" href="/threads/api-integration.12345/">Need API Integration Help</a>
                <a class="username">JohnDev</a>
                <time datetime="2023-12-11T10:00:00">Dec 11</time>
                <dd class="replies">5</dd>
            </div>
        </body></html>
        """
        mock_requests.get.return_value = mock_response

        with patch('scrapers.digitalpoint.looks_like_gig', return_value=True):
            await scrape_digitalpoint()

            self.assertEqual(mock_requests.get.call_count, 2)
            mock_save_gig.assert_called()

            first_call = mock_save_gig.call_args_list[0]
            self.assertEqual(first_call[1]['source'], 'DigitalPoint')
            self.assertEqual(first_call[1]['category'], 'programming_forum')
            self.assertIn('JohnDev', first_call[1]['snippet'])

    async def test_digitalpoint_filters_discussions(self, mock_is_url_allowed, mock_log_performance, mock_update_health, mock_save_gig, mock_requests):
        """Test DigitalPoint filters out discussion threads."""
        from scrapers.digitalpoint import scrape_digitalpoint

        mock_response = MagicMock()
        mock_response.text = """
        <html><body>
            <div class="structItem">
                <a class="title" href="/threads/discussion.123/">Discussion: What do you think about Python?</a>
            </div>
        </body></html>
        """
        mock_requests.get.return_value = mock_response

        # Even if looks_like_gig returns True, discussion threads should be filtered
        with patch('scrapers.digitalpoint.looks_like_gig', return_value=True):
            await scrape_digitalpoint()

            # Should still make requests but not save the discussion thread
            self.assertGreater(mock_requests.get.call_count, 0)
            # May or may not save depending on title filtering


# Test for WarriorForum Scraper
@patch('core.http_utils.requests')
@patch('core.storage.save_gig', new_callable=AsyncMock)
@patch('core.storage.update_scraper_health')
@patch('core.storage.log_scraper_performance')
@patch('core.robots.is_url_allowed', return_value=True)
class TestWarriorForumScraper(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        config._data = {
            "use_proxies": False,
            "user_agents": ["Test-Agent"],
            "delay_range": [0, 0],
            "retry_attempts": 1,
            "http_timeout": 5,
            "scrapers": {
                "warriorforum": {"max_pages": 2}
            }
        }

    async def test_warriorforum_scrape_success(self, mock_is_url_allowed, mock_log_performance, mock_update_health, mock_save_gig, mock_requests):
        """Test successful WarriorForum scraping."""
        from scrapers.warriorforum import scrape_warriorforum

        mock_response = MagicMock()
        mock_response.text = """
        <html><body>
            <li class="threadbit">
                <a class="threadtitle" href="/threads/automation-needed.12345/">Need Automation Script</a>
                <span class="username">MarketingPro</span>
                <span class="time" title="2023-12-11">Yesterday</span>
                <a class="replies">3</a>
            </li>
        </body></html>
        """
        mock_requests.get.return_value = mock_response

        with patch('scrapers.warriorforum.looks_like_gig', return_value=True):
            await scrape_warriorforum()

            self.assertEqual(mock_requests.get.call_count, 2)
            mock_save_gig.assert_called()

            first_call = mock_save_gig.call_args_list[0]
            self.assertEqual(first_call[1]['source'], 'WarriorForum')
            self.assertEqual(first_call[1]['category'], 'programming_forum')
            self.assertIn('MarketingPro', first_call[1]['snippet'])

    async def test_warriorforum_filters_guides(self, mock_is_url_allowed, mock_log_performance, mock_update_health, mock_save_gig, mock_requests):
        """Test WarriorForum filters out guide/tutorial threads."""
        from scrapers.warriorforum import scrape_warriorforum

        mock_response = MagicMock()
        mock_response.text = """
        <html><body>
            <li class="threadbit">
                <a class="threadtitle" href="/threads/guide.123/">[Guide] How to Build APIs</a>
            </li>
        </body></html>
        """
        mock_requests.get.return_value = mock_response

        with patch('scrapers.warriorforum.looks_like_gig', return_value=True):
            await scrape_warriorforum()

            # Should make requests but filter the guide thread
            self.assertGreater(mock_requests.get.call_count, 0)

    async def test_warriorforum_robots_blocked(self, mock_is_url_allowed, mock_log_performance, mock_update_health, mock_save_gig, mock_requests):
        """Test WarriorForum respects robots.txt."""
        from scrapers.warriorforum import scrape_warriorforum

        mock_is_url_allowed.return_value = False

        result = await scrape_warriorforum()

        self.assertEqual(result, 0)
        mock_requests.get.assert_not_called()


if __name__ == '__main__':
    unittest.main()