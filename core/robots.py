import urllib.parse
from robotexclusionrulesparser import RobotExclusionRulesParser
import requests
from core.logger import logger
from core.http_utils import fetch_url_with_retries

# Cache for robots.txt parsers
_robots_parsers = {}

def get_domain_from_url(url):
    """Extracts the domain (netloc) from a given URL."""
    return urllib.parse.urlparse(url).netloc

async def get_robots_parser(url):
    """
    Fetches and parses the robots.txt for a given URL's domain.
    Caches the parser for subsequent requests to the same domain.
    """
    domain = get_domain_from_url(url)
    if domain not in _robots_parsers:
        robots_txt_url = f"http://{domain}/robots.txt"
        logger.info(f"Fetching robots.txt from {robots_txt_url}")
        try:
            # Use fetch_url_with_retries for robots.txt fetching
            response = fetch_url_with_retries(requests.get, robots_txt_url, timeout=5)
            content = response.text
            parser = RobotExclusionRulesParser()
            parser.parse(content)
            _robots_parsers[domain] = parser
            logger.info(f"Successfully parsed robots.txt for {domain}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not fetch or parse robots.txt for {domain}: {e}. Assuming full access (be careful!).")
            _robots_parsers[domain] = None # Store None to avoid repeated attempts
        except Exception as e:
            logger.error(f"An unexpected error occurred while processing robots.txt for {domain}: {e}. Assuming full access (be careful!).")
            _robots_parsers[domain] = None # Store None to avoid repeated attempts
    return _robots_parsers[domain]

async def is_url_allowed(url, user_agent="*"):
    """
    Checks if a given URL is allowed to be scraped according to its robots.txt.
    """
    parser = await get_robots_parser(url)
    if parser:
        path = urllib.parse.urlparse(url).path
        allowed = parser.is_url_allowed(user_agent, url)
        if not allowed:
            logger.warning(f"URL disallowed by robots.txt: {url} for User-Agent: {user_agent}")
        return allowed
    else:
        # If no robots.txt or an error occurred, assume allowed for now (with warning)
        return True

if __name__ == "__main__":
    # Example usage for testing
    async def test_robots():
        logger.info("Testing robots.py...")
        
        # Test a site with robots.txt
        google_url = "https://www.google.com/search?q=test"
        logger.info(f"Is {google_url} allowed? {await is_url_allowed(google_url)}")

        # Test a site that likely doesn't have robots.txt or is simple
        # This will assume full access after a warning
        example_url = "http://example.com/some/path"
        logger.info(f"Is {example_url} allowed? {await is_url_allowed(example_url)}")

        # Test a disallowed path (if known)
        # You'd need to find a real example of a disallowed path for a robust test
        # For demonstration, let's assume '/admin' is disallowed on a hypothetical site
        # Note: This is purely illustrative, and depends on the actual robots.txt content
        disallowed_url = "https://www.google.com/admin"
        logger.info(f"Is {disallowed_url} allowed? {await is_url_allowed(disallowed_url)}")

    import asyncio
    asyncio.run(test_robots())
