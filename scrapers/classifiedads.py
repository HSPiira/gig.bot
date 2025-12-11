"""
ClassifiedAds.com Computer Services Scraper

Scrapes computer/IT service gigs from ClassifiedAds.com.
Simple, clean HTML structure with consistent dev gig postings.

Features:
- US-focused classifieds
- Clean HTML parsing
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


BASE_URL = "https://www.classifiedads.com/computer_services/"


async def scrape_classifiedads_page(page: int = 1) -> int:
    """
    Scrape a single page of ClassifiedAds computer services.

    Args:
        page: Page number to scrape (default: 1)

    Returns:
        Number of gigs found and saved
    """
    headers = {"User-Agent": get_random_user_agent()}
    proxy = get_proxy() if config.use_proxies else None
    gigs_found = 0

    # Build page URL
    url = f"{BASE_URL}?page={page}" if page > 1 else BASE_URL

    logger.debug(f"Fetching ClassifiedAds page {page}: {url}")

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
        return 0

    # Parse HTML
    soup = BeautifulSoup(response.text, "html.parser")

    # Find all listings
    # ClassifiedAds uses various selectors, try multiple
    listings = (
        soup.find_all("div", class_=re.compile(r"listing|ad-card|item")) or
        soup.find_all("article") or
        soup.find_all("li", class_=re.compile(r"result|item"))
    )

    if not listings:
        logger.info(f"No listings found on page {page}")
        return 0

    logger.info(f"Found {len(listings)} listings on page {page}")

    # Process each listing
    for listing in listings:
        try:
            # Extract title
            title_elem = (
                listing.find("h3") or
                listing.find("h2") or
                listing.find("a", class_=re.compile(r"title"))
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
                link = f"https://www.classifiedads.com{link}" if link.startswith("/") else f"https://www.classifiedads.com/{link}"

            # Extract snippet/description
            desc_elem = listing.find("p") or listing.find("div", class_=re.compile(r"desc|snippet|summary"))
            snippet = desc_elem.get_text(strip=True)[:300] if desc_elem else title

            # Extract price if available
            price = None
            price_elem = listing.find("span", class_=re.compile(r"price|amount"))
            if price_elem:
                price = price_elem.get_text(strip=True)
            else:
                # Try regex extraction
                price_match = re.search(r'\$\d+(?:[-to]+\$?\d+)?', f"{title} {snippet}")
                if price_match:
                    price = price_match.group(0)

            # Extract location if available
            location_elem = listing.find("span", class_=re.compile(r"location|city"))
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
                source="ClassifiedAds",
                title=title,
                link=link,
                snippet=snippet,
                price=price,
                full_description=None,
                timestamp=None,
                contact_info=None,
                category="computer_services"
            )

            gigs_found += 1
            logger.debug(f"Saved gig: {title}")

        except Exception as e:
            logger.error(f"Error processing listing: {e}", exc_info=True)
            continue

    return gigs_found


@scraper_lifecycle("classifiedads")
async def scrape_classifiedads():
    """
    Scrape computer service gigs from ClassifiedAds.com.

    Scrapes up to max_pages (default: 3) from the computer services category.

    The scraper:
    1. Checks robots.txt
    2. Scrapes configured number of pages
    3. Filters listings using NLP + keyword scoring
    4. Saves relevant developer gigs to database

    Returns:
        Total number of gigs found
    """
    # Get configuration
    scraper_config = config.get("scrapers", {}).get("classifiedads", {})
    max_pages = scraper_config.get("max_pages", 3)

    logger.info(f"Starting ClassifiedAds scraper (max {max_pages} pages)")

    # Check robots.txt
    headers = {"User-Agent": get_random_user_agent()}
    if not await is_url_allowed(BASE_URL, user_agent=headers["User-Agent"]):
        logger.warning(f"Scraping of {BASE_URL} disallowed by robots.txt. Skipping.")
        return 0

    total_gigs = 0

    # Scrape multiple pages
    for page in range(1, max_pages + 1):
        try:
            page_gigs = await scrape_classifiedads_page(page)
            total_gigs += page_gigs

            # Stop if no gigs found (end of listings)
            if page_gigs == 0:
                break

        except Exception as e:
            logger.error(f"Failed to scrape ClassifiedAds page {page}: {e}", exc_info=True)
            continue

    logger.info(f"ClassifiedAds scraping complete: {total_gigs} total gigs found")
    return total_gigs


if __name__ == "__main__":
    """Test the ClassifiedAds scraper."""
    import asyncio

    async def test():
        logger.info("Testing ClassifiedAds scraper...")
        result = await scrape_classifiedads()
        logger.info(f"Test complete: {result} gigs found")

    asyncio.run(test())
