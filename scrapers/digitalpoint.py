"""
DigitalPoint Forums Programming Jobs Scraper

Scrapes programming job postings from DigitalPoint forums.
One of the oldest developer job boards with high-quality gigs.

Features:
- Forum structure parsing
- Thread-based listings
- robots.txt compliance
- Rate limiting
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
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


BASE_URL = "https://forums.digitalpoint.com/forums/programming.34/"


async def scrape_digitalpoint_page(page: int = 1) -> int:
    """
    Scrape a single page of DigitalPoint programming forum.

    Args:
        page: Page number to scrape (default: 1)

    Returns:
        Number of gigs found and saved
    """
    headers = {"User-Agent": get_random_user_agent()}
    proxy = get_proxy() if config.use_proxies else None
    gigs_found = 0

    # Build page URL
    # DigitalPoint uses page-X format
    url = f"{BASE_URL}page-{page}" if page > 1 else BASE_URL

    logger.debug(f"Fetching DigitalPoint page {page}: {url}")

    # Throttle requests (forums need more respect)
    await async_randomized_delay()

    try:
        response = fetch_url_with_retries(
            requests.get,
            url,
            headers=headers,
            proxies={"http": proxy, "https": proxy} if proxy else None,
            timeout=15  # Forums can be slower
        )
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return 0

    # Parse HTML
    soup = BeautifulSoup(response.text, "html.parser")

    # Find all thread listings
    # Forums typically use <div class="structItem"> or similar
    threads = (
        soup.find_all("div", class_=re.compile(r"structItem|threadbit|discussionListItem")) or
        soup.find_all("li", class_=re.compile(r"discussionListItem|thread")) or
        soup.find_all("ol", class_="discussionListItems")
    )

    # If we got a container, extract individual items
    if len(threads) == 1 and threads[0].name == "ol":
        threads = threads[0].find_all("li")

    if not threads:
        logger.info(f"No threads found on page {page}")
        return 0

    logger.info(f"Found {len(threads)} threads on page {page}")

    # Process each thread
    for thread in threads:
        try:
            # Extract thread title
            title_elem = (
                thread.find("a", class_=re.compile(r"title|thread-title")) or
                thread.find("h3", class_="title") or
                thread.find("a", attrs={"data-preview-url": True})
            )
            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)

            # Extract thread link
            link = title_elem.get("href")
            if not link:
                continue

            # Make link absolute if relative
            if link and not link.startswith("http"):
                link = f"https://forums.digitalpoint.com{link}" if link.startswith("/") else f"https://forums.digitalpoint.com/{link}"

            # Extract thread starter/author
            author_elem = thread.find("a", class_=re.compile(r"username|author"))
            author = author_elem.get_text(strip=True) if author_elem else "Unknown"

            # Extract timestamp
            timestamp = None
            time_elem = thread.find("time", attrs={"datetime": True})
            if time_elem:
                timestamp = time_elem.get("datetime")

            # Extract snippet/preview
            snippet_elem = (
                thread.find("div", class_=re.compile(r"snippet|preview|message")) or
                thread.find("div", class_="structItem-title")
            )
            snippet = snippet_elem.get_text(strip=True)[:300] if snippet_elem else title

            # Extract reply count (indicator of engagement)
            replies_elem = thread.find("dd", class_=re.compile(r"replies"))
            replies = replies_elem.get_text(strip=True) if replies_elem else "0"

            # Combine text for filtering
            combined_text = f"{title} {snippet}"

            # Filter: Check if it looks like a developer gig
            if not looks_like_gig(combined_text):
                logger.debug(f"Filtered out (not a gig): {title}")
                continue

            # Additional forum-specific filtering
            # Skip threads that look like discussions rather than job posts
            discussion_indicators = [
                "what do you think",
                "discussion:",
                "poll:",
                "how to",
                "tutorial",
                "question",
            ]
            title_lower = title.lower()
            if any(indicator in title_lower for indicator in discussion_indicators):
                logger.debug(f"Filtered out (discussion thread): {title}")
                continue

            # Save the gig
            await save_gig(
                source="DigitalPoint",
                title=title,
                link=link,
                snippet=f"{snippet} (by {author}, {replies} replies)",
                price=None,  # Forums rarely have price in listing
                full_description=None,
                timestamp=timestamp,
                contact_info=author,
                category="programming_forum"
            )

            gigs_found += 1
            logger.debug(f"Saved thread: {title}")

        except Exception as e:
            logger.error(f"Error processing thread: {e}", exc_info=True)
            continue

    return gigs_found


@scraper_lifecycle("digitalpoint")
async def scrape_digitalpoint():
    """
    Scrape programming job threads from DigitalPoint forums.

    Scrapes up to max_pages (default: 3) from the programming section.

    The scraper:
    1. Checks robots.txt
    2. Scrapes configured number of pages
    3. Filters threads using NLP + keyword scoring
    4. Saves relevant developer gig threads to database

    Returns:
        Total number of gigs found
    """
    # Get configuration
    scraper_config = config.get("scrapers", {}).get("digitalpoint", {})
    max_pages = scraper_config.get("max_pages", 3)

    logger.info(f"Starting DigitalPoint scraper (max {max_pages} pages)")

    # Check robots.txt
    headers = {"User-Agent": get_random_user_agent()}
    if not await is_url_allowed(BASE_URL, user_agent=headers["User-Agent"]):
        logger.warning(f"Scraping of {BASE_URL} disallowed by robots.txt. Skipping.")
        return 0

    total_gigs = 0

    # Scrape multiple pages
    for page in range(1, max_pages + 1):
        try:
            page_gigs = await scrape_digitalpoint_page(page)
            total_gigs += page_gigs

            # Stop if no gigs found
            if page_gigs == 0:
                break

        except Exception as e:
            logger.error(f"Failed to scrape DigitalPoint page {page}: {e}", exc_info=True)
            continue

    logger.info(f"DigitalPoint scraping complete: {total_gigs} total gigs found")
    return total_gigs


if __name__ == "__main__":
    """Test the DigitalPoint scraper."""
    import asyncio

    async def test():
        logger.info("Testing DigitalPoint scraper...")
        result = await scrape_digitalpoint()
        logger.info(f"Test complete: {result} gigs found")

    asyncio.run(test())
