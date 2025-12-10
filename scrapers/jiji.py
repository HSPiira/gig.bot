import requests
from bs4 import BeautifulSoup

from core.filters import looks_like_gig
from core.storage import save_gig
from core.proxies import get_proxy, get_random_user_agent
from core.logger import logger
from core.throttler import async_randomized_delay
from core.http_utils import fetch_url_with_retries
from core.robots import is_url_allowed
from core.config import config
from core.scraper_base import scraper_lifecycle

BASE_URL = "https://jiji.ug/search?query=website"

@scraper_lifecycle("jiji")
async def scrape_jiji():
    """
    Scrapes Jiji Uganda for gig listings and saves detected gigs.

    Performs a search on the Jiji site, filters listings that look like gigs, and persists
    each matching gig via save_gig. The function respects robots.txt for both the search page
    and individual gig pages, applies randomized asynchronous delays to throttle requests, and
    optionally routes requests through a proxy when enabled in configuration.
    """
    headers = {"User-Agent": get_random_user_agent()}
    proxy = None
    if config.use_proxies:
        proxy = get_proxy()

    # Check robots.txt
    if not await is_url_allowed(BASE_URL, user_agent=headers["User-Agent"]):
        logger.warning(f"Scraping of {BASE_URL} disallowed by robots.txt. Skipping.")
        # Return SKIPPED_ROBOTS so lifecycle decorator records the skip appropriately
        from core.types import ScraperStatus
        return ScraperStatus.SKIPPED_ROBOTS

    # Throttle request
    await async_randomized_delay()
    response = fetch_url_with_retries(requests.get, BASE_URL, headers=headers, proxies=proxy if config.use_proxies else None)
    soup = BeautifulSoup(response.text, "html.parser")

    ads = soup.find_all("div", class_="b-list-advert__item")

    for ad in ads:
        title_element = ad.find("div", class_="b-list-advert__item-title")
        title = title_element.get_text(strip=True) if title_element else "No Title"

        link_element = ad.find("a", class_="b-list-advert__item-title-link")
        if not link_element:
            continue

        href = "https://jiji.ug" + link_element.get("href")

        full_description = None
        price = None
        timestamp = None
        contact_info = None
        category = None

        if looks_like_gig(title):
            # Fetch individual gig page for full description and other details
            try:
                if await is_url_allowed(href, user_agent=headers["User-Agent"]):
                    await async_randomized_delay()  # Delay before fetching gig detail page
                    gig_response = fetch_url_with_retries(requests.get, href, headers=headers, proxies=proxy if config.use_proxies else None)
                    gig_soup = BeautifulSoup(gig_response.text, "html.parser")

                    # Extract full description
                    description_element = gig_soup.find("div", class_="b-advert-info__description-text")
                    if description_element:
                        full_description = description_element.get_text(strip=True)

                    # Extract price
                    price_element = gig_soup.find("span", class_="b-advert-info__price-value")
                    if price_element:
                        price = price_element.get_text(strip=True)

                    # Extract timestamp
                    timestamp_element = gig_soup.find("div", class_="b-advert-info__item-date")
                    if timestamp_element:
                        timestamp = timestamp_element.get_text(strip=True)

                    # Extract contact info
                    contact_element = gig_soup.find("a", class_="js-toggle-phone")
                    if contact_element:
                        contact_info = contact_element.get_text(strip=True)

                    # Extract category
                    category_element = gig_soup.find("a", class_="b-advert-info__category-link")
                    if category_element:
                        category = category_element.get_text(strip=True)

            except Exception as gig_e:
                logger.error(f"[JIJI GIG DETAIL ERROR] Could not fetch/parse gig detail for {href}: {gig_e}")

            await save_gig(
                source="Jiji",
                title=title,
                link=href,
                snippet=title[:200],
                price=price,
                full_description=full_description,
                timestamp=timestamp,
                contact_info=contact_info,
                category=category
            )