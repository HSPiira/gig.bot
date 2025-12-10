import requests
from bs4 import BeautifulSoup
import time # Import time for measuring duration

from core.filters import looks_like_gig
from core.storage import save_gig, update_scraper_health, log_scraper_performance # Import log_scraper_performance
from core.proxies import get_proxy, get_random_user_agent
from core.logger import logger
from core.throttler import randomized_delay, async_randomized_delay
from core.http_utils import fetch_url_with_retries
from core.robots import is_url_allowed
from core.config import config

BASE_URL = "https://jiji.ug/search?query=website"

async def scrape_jiji():
    """
    Scrapes Jiji Uganda for gig listings and saves detected gigs, optionally fetching and storing detailed gig pages.
    
    Performs a search on the Jiji site, filters listings that look like gigs, and persists each matching gig via save_gig. The function respects robots.txt for both the search page and individual gig pages, applies randomized asynchronous delays to throttle requests, and optionally routes requests through a proxy when enabled in configuration. After a successful run it updates scraper health and always logs run performance (duration, status, and error message if any).
    """
    scraper_name = "jiji"
    start_time = time.time()
    status = "success"
    error_message = None

    headers = {
        "User-Agent": get_random_user_agent()
    }
    
    proxy = None
    if config.use_proxies:
        proxy = get_proxy()

    try:
        logger.info(f"Scraping {scraper_name}...")

        if not await is_url_allowed(BASE_URL, user_agent=headers["User-Agent"]):
            logger.warning(f"Scraping of {BASE_URL} disallowed by robots.txt. Skipping {scraper_name}.")
            status = "skipped_robots"
            return

        await async_randomized_delay() # Use async delay before initial request
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
                        await async_randomized_delay() # Delay before fetching gig detail page
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
                            # Jiji's timestamp format might need more robust parsing
                            timestamp = timestamp_element.get_text(strip=True)
                        
                        # Extract contact info (e.g., from a 'show phone' button or similar)
                        # This is highly dependent on how Jiji displays contact info
                        contact_element = gig_soup.find("a", class_="js-toggle-phone") # Example selector
                        if contact_element:
                            contact_info = contact_element.get_text(strip=True)
                            
                        # Extract category
                        category_element = gig_soup.find("a", class_="b-advert-info__category-link")
                        if category_element:
                            category = category_element.get_text(strip=True)

                except Exception as gig_e:
                    logger.error(f"[JIJI GIG DETAIL ERROR] Could not fetch/parse gig detail for {href}: {gig_e}")
                
                await save_gig( # Await save_gig
                    source="Jiji",
                    title=title,
                    link=href,
                    snippet=title[:200], # Keep snippet as first 200 chars of title
                    price=price,
                    full_description=full_description,
                    timestamp=timestamp,
                    contact_info=contact_info,
                    category=category
                )
        
        update_scraper_health(scraper_name) # Update health after successful run

    except Exception as e:
        logger.error(f"[{scraper_name.upper()} ERROR] {e}")
        status = "failed"
        error_message = str(e)
    finally:
        duration = time.time() - start_time
        log_scraper_performance(scraper_name, duration, status, error_message)