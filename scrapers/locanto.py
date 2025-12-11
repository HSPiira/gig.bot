"""
Locanto IT Jobs Scraper

Scrapes IT/Computer jobs from Locanto classifieds across multiple countries.
Targets the IT-Jobs category which has many developer gigs.

Features:
- Multi-country support (US, UK, India, South Africa)
- Simple HTML structure (easy parsing)
- robots.txt compliance
- Rate limiting
"""

import requests
from bs4 import BeautifulSoup
from typing import Optional
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


# Default countries to scrape
DEFAULT_COUNTRIES = {
    "us": "https://www.locanto.com/IT-Jobs/",
    "uk": "https://www.locanto.co.uk/IT-Jobs/",
    "in": "https://www.locanto.in/IT-Jobs/",
    "za": "https://www.locanto.co.za/IT-Jobs/",
    "au": "https://www.locanto.com.au/IT-Jobs/",
}


async def scrape_locanto_country(country: str, url: str, max_pages: int = 2) -> int:
    """
    Scrape IT jobs from a specific Locanto country site.

    Args:
        country: Country code (e.g., "us", "uk", "in")
        url: Base URL for IT jobs in that country
        max_pages: Maximum number of pages to scrape (default: 2)

    Returns:
        Number of gigs found and saved
    """
    headers = {"User-Agent": get_random_user_agent()}
    proxy = get_proxy() if config.use_proxies else None
    gigs_found = 0

    logger.info(f"Scraping Locanto {country.upper()} IT jobs...")

    # Check robots.txt
    if not await is_url_allowed(url, user_agent=headers["User-Agent"]):
        logger.warning(f"Scraping of {url} disallowed by robots.txt. Skipping.")
        return 0

    # Scrape multiple pages
    for page in range(1, max_pages + 1):
        page_url = f"{url}?page={page}" if page > 1 else url

        logger.debug(f"Fetching {country} page {page}/{max_pages}: {page_url}")

        # Throttle requests
        await async_randomized_delay()

        try:
            response = fetch_url_with_retries(
                requests.get,
                page_url,
                headers=headers,
                proxies={"http": proxy, "https": proxy} if proxy else None
            )
        except Exception as e:
            logger.error(f"Failed to fetch {page_url}: {e}")
            continue

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Find all job listings
        # Locanto uses <article> tags or <div class="listing">
        listings = soup.find_all("article") or soup.find_all("div", class_=re.compile(r"listing|item"))

        if not listings:
            logger.info(f"No more listings found for {country} on page {page}")
            break

        logger.info(f"Found {len(listings)} listings on page {page} for {country}")

        # Process each listing
        for listing in listings:
            try:
                # Extract title
                title_elem = listing.find("h2") or listing.find("h3") or listing.find("a", class_=re.compile(r"title"))
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)

                # Extract link
                link_elem = listing.find("a", href=True)
                if not link_elem:
                    continue

                link = link_elem.get("href")

                # Make link absolute if relative
                if link and not link.startswith("http"):
                    base_domain = url.split("/IT-Jobs")[0]
                    link = f"{base_domain}{link}" if link.startswith("/") else f"{base_domain}/{link}"

                # Extract snippet/description
                desc_elem = listing.find("p") or listing.find("div", class_=re.compile(r"description|snippet"))
                snippet = desc_elem.get_text(strip=True)[:300] if desc_elem else title

                # Extract price if available
                price = None
                price_patterns = [r'\$\d+', r'£\d+', r'₹\d+', r'\d+\s*(?:USD|GBP|INR|ZAR|AUD)']
                combined_text = f"{title} {snippet}"
                for pattern in price_patterns:
                    match = re.search(pattern, combined_text, re.IGNORECASE)
                    if match:
                        price = match.group(0)
                        break

                # Filter: Check if it looks like a developer gig
                if not looks_like_gig(combined_text):
                    logger.debug(f"Filtered out (not a gig): {title}")
                    continue

                # Save the gig
                await save_gig(
                    source=f"Locanto ({country.upper()})",
                    title=title,
                    link=link,
                    snippet=snippet,
                    price=price,
                    full_description=None,
                    timestamp=None,
                    contact_info=None,
                    category="it_jobs"
                )

                gigs_found += 1
                logger.debug(f"Saved gig from {country}: {title}")

            except Exception as e:
                logger.error(f"Error processing listing from {country}: {e}", exc_info=True)
                continue

    logger.info(f"Completed {country}: Found {gigs_found} gigs")
    return gigs_found


@scraper_lifecycle("locanto")
async def scrape_locanto():
    """
    Scrape IT jobs from multiple Locanto country sites.

    Countries are configured in settings.json under scrapers.locanto.countries,
    or defaults to US, UK, India, South Africa, Australia.

    The scraper:
    1. Checks robots.txt for each country
    2. Scrapes up to max_pages (default: 2) per country
    3. Filters listings using NLP + keyword scoring
    4. Saves relevant developer gigs to database

    Returns:
        Total number of gigs found across all countries
    """
    # Get configuration
    scraper_config = config.get("scrapers", {}).get("locanto", {})
    countries_config = scraper_config.get("countries", DEFAULT_COUNTRIES)
    max_pages = scraper_config.get("max_pages", 2)

    logger.info(f"Starting Locanto scraper for {len(countries_config)} countries")

    total_gigs = 0

    # Scrape each country
    for country, url in countries_config.items():
        try:
            country_gigs = await scrape_locanto_country(country, url, max_pages)
            total_gigs += country_gigs
        except Exception as e:
            logger.error(f"Failed to scrape Locanto {country}: {e}", exc_info=True)
            continue

    logger.info(f"Locanto scraping complete: {total_gigs} total gigs found")
    return total_gigs


if __name__ == "__main__":
    """Test the Locanto scraper."""
    import asyncio

    async def test():
        logger.info("Testing Locanto scraper...")
        result = await scrape_locanto_country("us", DEFAULT_COUNTRIES["us"], max_pages=1)
        logger.info(f"Test complete: {result} gigs found")

    asyncio.run(test())
