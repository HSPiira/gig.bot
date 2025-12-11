"""
Craigslist Computer Gigs Scraper

Scrapes computer gigs from Craigslist across multiple US cities.
Targets the /search/cpg endpoint (computer gigs category).

Features:
- Multi-city support (top tech hubs)
- Pagination (first 3 pages per city)
- Price extraction
- robots.txt compliance
- Rate limiting
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import List, Optional
import re

from core.filters import looks_like_gig
from core.storage import save_gig
from core.proxies import get_proxy, get_random_user_agent
from core.logger import logger
from core.throttler import async_randomized_delay
from core.http_utils import fetch_url_with_retries
from core.robots import is_url_allowed
from core.config import config
from core.scraper_base import scraper_lifecycle
from core.types import ScraperStatus


# Top 15 US tech cities for developer gigs
DEFAULT_CITIES = [
    "sfbay",        # San Francisco Bay Area
    "newyork",      # New York City
    "seattle",      # Seattle
    "losangeles",   # Los Angeles
    "boston",       # Boston
    "austin",       # Austin
    "chicago",      # Chicago
    "denver",       # Denver
    "portland",     # Portland
    "sandiego",     # San Diego
    "atlanta",      # Atlanta
    "phoenix",      # Phoenix
    "dallas",       # Dallas
    "miami",        # Miami
    "washingtondc", # Washington DC
]


def extract_price_from_text(text: str) -> Optional[str]:
    """
    Extract price from Craigslist listing text.

    Craigslist typically shows prices like "$50", "$100-200", "100".

    Args:
        text: The text to search for price patterns

    Returns:
        Extracted price string or None if no price found

    Examples:
        "$50" -> "$50"
        "100" -> "$100"
        "$100-200" -> "$100-200"
    """
    if not text:
        return None

    # Pattern: $50, $100-200, 50, 100-200
    price_pattern = r'\$?\d+(?:-\$?\d+)?'
    match = re.search(price_pattern, text)

    if match:
        price = match.group(0)
        # Add $ prefix if not present
        if not price.startswith('$'):
            price = f"${price}"
        return price

    return None


async def scrape_craigslist_city(city: str, max_pages: int = 3) -> int:
    """
    Scrape computer gigs from a specific Craigslist city.

    Args:
        city: Craigslist city subdomain (e.g., "sfbay", "newyork")
        max_pages: Maximum number of pages to scrape (default: 3)

    Returns:
        Number of gigs found and saved

    Raises:
        requests.RequestException: If HTTP request fails after retries
    """
    base_url = f"https://{city}.craigslist.org/search/cpg"
    headers = {"User-Agent": get_random_user_agent()}
    proxy = get_proxy() if config.use_proxies else None

    gigs_found = 0

    logger.info(f"Scraping Craigslist {city} computer gigs...")

    # Check robots.txt for the city subdomain
    if not await is_url_allowed(base_url, user_agent=headers["User-Agent"]):
        logger.warning(f"Scraping of {base_url} disallowed by robots.txt. Skipping.")
        return 0

    # Scrape multiple pages
    for page in range(max_pages):
        # Craigslist uses offset-based pagination (0, 120, 240, ...)
        offset = page * 120
        url = f"{base_url}?s={offset}" if offset > 0 else base_url

        logger.debug(f"Fetching {city} page {page + 1}/{max_pages}: {url}")

        # Throttle requests
        await async_randomized_delay()

        try:
            response = fetch_url_with_retries(
                requests.get,
                url,
                headers=headers,
                proxies={"http": proxy, "https": proxy} if proxy else None
            )
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            continue

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Find all listing items
        # Craigslist uses <li class="result-row"> for each listing
        listings = soup.find_all("li", class_="result-row")

        if not listings:
            logger.info(f"No more listings found for {city} on page {page + 1}")
            break

        logger.info(f"Found {len(listings)} listings on page {page + 1} for {city}")

        # Process each listing
        for listing in listings:
            try:
                # Extract title
                title_elem = listing.find("a", class_="result-title")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                link = title_elem.get("href")

                # Make link absolute if relative
                if link and not link.startswith("http"):
                    link = f"https://{city}.craigslist.org{link}"

                # Extract price (optional)
                price = None
                price_elem = listing.find("span", class_="result-price")
                if price_elem:
                    price = price_elem.get_text(strip=True)

                # Extract timestamp (optional)
                timestamp = None
                time_elem = listing.find("time", class_="result-date")
                if time_elem and time_elem.get("datetime"):
                    timestamp = time_elem.get("datetime")

                # Extract snippet/description (if available)
                snippet = title  # Use title as fallback

                # Some listings have a description preview
                desc_elem = listing.find("span", class_="result-hood")
                if desc_elem:
                    location = desc_elem.get_text(strip=True)
                    snippet = f"{title} - {location}"

                # Filter: Check if it looks like a developer gig
                combined_text = f"{title} {snippet}"
                if not looks_like_gig(combined_text):
                    logger.debug(f"Filtered out (not a gig): {title}")
                    continue

                # Save the gig
                await save_gig(
                    source=f"Craigslist ({city})",
                    title=title,
                    link=link,
                    snippet=snippet,
                    price=price,
                    full_description=None,  # Would need detail page fetch
                    timestamp=timestamp,
                    contact_info=None,
                    category="computer_gigs"
                )

                gigs_found += 1
                logger.debug(f"Saved gig from {city}: {title}")

            except Exception as e:
                logger.error(f"Error processing listing from {city}: {e}", exc_info=True)
                continue

    logger.info(f"Completed {city}: Found {gigs_found} gigs")
    return gigs_found


@scraper_lifecycle("craigslist")
async def scrape_craigslist():
    """
    Scrape computer gigs from multiple Craigslist cities.

    Cities are configured in settings.json under scrapers.craigslist.cities,
    or defaults to top 15 US tech cities.

    The scraper:
    1. Checks robots.txt for each city
    2. Scrapes up to max_pages (default: 3) per city
    3. Filters listings using NLP + keyword scoring
    4. Saves relevant developer gigs to database
    5. Sends notifications for new gigs

    Returns:
        Total number of gigs found across all cities
    """
    # Get cities from config or use defaults
    scraper_config = config.get("scrapers", {}).get("craigslist", {})
    cities = scraper_config.get("cities", DEFAULT_CITIES)
    max_pages = scraper_config.get("max_pages", 3)

    logger.info(f"Starting Craigslist scraper for {len(cities)} cities")

    total_gigs = 0

    # Scrape each city
    for city in cities:
        try:
            city_gigs = await scrape_craigslist_city(city, max_pages)
            total_gigs += city_gigs
        except Exception as e:
            logger.error(f"Failed to scrape Craigslist {city}: {e}", exc_info=True)
            continue

    logger.info(f"Craigslist scraping complete: {total_gigs} total gigs found")
    return total_gigs


if __name__ == "__main__":
    """Test the Craigslist scraper."""
    import asyncio

    # Test with a single city
    async def test():
        logger.info("Testing Craigslist scraper...")
        result = await scrape_craigslist_city("sfbay", max_pages=1)
        logger.info(f"Test complete: {result} gigs found")

    asyncio.run(test())
