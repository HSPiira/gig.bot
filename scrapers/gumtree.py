"""
Gumtree Computers/IT Services Scraper

Scrapes computer and IT service gigs from Gumtree across UK, Australia, South Africa.
Major classifieds platform in Commonwealth countries.

Features:
- Multi-country support (UK, AU, ZA)
- High volume in target markets
- robots.txt compliance
- Rate limiting
"""

import requests
from bs4 import BeautifulSoup
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


# Default countries and URLs
DEFAULT_COUNTRIES = {
    "uk": "https://www.gumtree.com/computers-telecoms-services",
    "au": "https://www.gumtree.com.au/s-computer-it-services/k0c18493",
    "za": "https://www.gumtree.co.za/s-computer-it/v1c9205",
}


async def scrape_gumtree_country(country: str, url: str, max_pages: int = 2) -> int:
    """
    Scrape computer/IT services from a specific Gumtree country site.

    Args:
        country: Country code (e.g., "uk", "au", "za")
        url: Base URL for computer services in that country
        max_pages: Maximum number of pages to scrape (default: 2)

    Returns:
        Number of gigs found and saved
    """
    headers = {"User-Agent": get_random_user_agent()}
    proxy = get_proxy() if config.use_proxies else None
    gigs_found = 0

    logger.info(f"Scraping Gumtree {country.upper()} computer services...")

    # Check robots.txt
    if not await is_url_allowed(url, user_agent=headers["User-Agent"]):
        logger.warning(f"Scraping of {url} disallowed by robots.txt. Skipping.")
        return 0

    # Scrape multiple pages
    for page in range(1, max_pages + 1):
        # Gumtree pagination varies by country
        if country == "uk":
            page_url = f"{url}?page={page}" if page > 1 else url
        else:  # AU, ZA use different format
            page_url = f"{url}/page-{page}" if page > 1 else url

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

        # Find all listings
        # Gumtree uses different structures across countries
        listings = (
            soup.find_all("div", class_=re.compile(r"listing|result|ad-item")) or
            soup.find_all("li", class_=re.compile(r"listing|result|natural")) or
            soup.find_all("article", class_=re.compile(r"listing|tile"))
        )

        if not listings:
            logger.info(f"No more listings found for {country} on page {page}")
            break

        logger.info(f"Found {len(listings)} listings on page {page} for {country}")

        # Process each listing
        for listing in listings:
            try:
                # Extract title
                title_elem = (
                    listing.find("a", class_=re.compile(r"title|listing-title")) or
                    listing.find("h3") or
                    listing.find("h2")
                )
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
                    base_domain = url.split("/s-")[0] if "/s-" in url else url.split("/computers")[0]
                    link = f"{base_domain}{link}" if link.startswith("/") else f"{base_domain}/{link}"

                # Extract snippet/description
                desc_elem = (
                    listing.find("div", class_=re.compile(r"description|snippet|desc")) or
                    listing.find("p")
                )
                snippet = desc_elem.get_text(strip=True)[:300] if desc_elem else title

                # Extract price if available
                price = None
                price_elem = listing.find("span", class_=re.compile(r"price|amount"))
                if price_elem:
                    price = price_elem.get_text(strip=True)
                else:
                    # Try regex extraction
                    price_patterns = [r'£\d+', r'\$\d+', r'R\s?\d+']  # GBP, AUD/USD, ZAR
                    for pattern in price_patterns:
                        match = re.search(pattern, f"{title} {snippet}")
                        if match:
                            price = match.group(0)
                            break

                # Extract location if available
                location_elem = listing.find("span", class_=re.compile(r"location|area"))
                location = location_elem.get_text(strip=True) if location_elem else None

                # Combine text for filtering
                combined_text = f"{title} {snippet}"
                if location:
                    combined_text += f" {location}"

                # Filter: Check if it looks like a developer gig
                if not looks_like_gig(combined_text):
                    logger.debug(f"Filtered out (not a gig): {title}")
                    continue

                # Save the gig
                await save_gig(
                    source=f"Gumtree ({country.upper()})",
                    title=title,
                    link=link,
                    snippet=snippet,
                    price=price,
                    full_description=None,
                    timestamp=None,
                    contact_info=None,
                    category="computer_it_services"
                )

                gigs_found += 1
                logger.debug(f"Saved gig from {country}: {title}")

            except Exception as e:
                logger.error(f"Error processing listing from {country}: {e}", exc_info=True)
                continue

    logger.info(f"Completed {country}: Found {gigs_found} gigs")
    return gigs_found


@scraper_lifecycle("gumtree")
async def scrape_gumtree():
    """
    Scrape computer/IT services from multiple Gumtree country sites.

    Countries are configured in settings.json under scrapers.gumtree.countries,
    or defaults to UK, Australia, South Africa.

    The scraper:
    1. Checks robots.txt for each country
    2. Scrapes up to max_pages (default: 2) per country
    3. Filters listings using NLP + keyword scoring
    4. Saves relevant developer gigs to database

    Returns:
        Total number of gigs found across all countries
    """
    # Get configuration
    scraper_config = config.get("scrapers", {}).get("gumtree", {})
    countries_config = scraper_config.get("countries", DEFAULT_COUNTRIES)
    max_pages = scraper_config.get("max_pages", 2)

    logger.info(f"Starting Gumtree scraper for {len(countries_config)} countries")

    total_gigs = 0

    # Scrape each country
    for country, url in countries_config.items():
        try:
            country_gigs = await scrape_gumtree_country(country, url, max_pages)
            total_gigs += country_gigs
        except Exception as e:
            logger.error(f"Failed to scrape Gumtree {country}: {e}", exc_info=True)
            continue

    logger.info(f"Gumtree scraping complete: {total_gigs} total gigs found")
    return total_gigs


if __name__ == "__main__":
    """Test the Gumtree scraper."""
    import asyncio

    async def test():
        logger.info("Testing Gumtree scraper...")
        result = await scrape_gumtree_country("uk", DEFAULT_COUNTRIES["uk"], max_pages=1)
        logger.info(f"Test complete: {result} gigs found")

    asyncio.run(test())
