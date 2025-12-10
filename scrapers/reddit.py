import requests
import time # Import time for measuring duration
from core.filters import looks_like_gig
from core.storage import save_gig, update_scraper_health, log_scraper_performance # Import log_scraper_performance
from core.proxies import get_proxy, get_random_user_agent
from core.logger import logger
from core.throttler import async_randomized_delay
from core.http_utils import fetch_url_with_retries
from core.robots import is_url_allowed
from core.config import config
from datetime import datetime, timezone

# A list of subreddits to scrape
SUBREDDITS = [
    "forhire",
    "jobbit",
    "jobsearch",
    "hiring"
]
BASE_URL = "https://www.reddit.com/r/{subreddit}/search.json?q=flair%3A%22Hiring%22&restrict_sr=on&sort=new"

async def scrape_reddit():
    """
    Scrape configured Reddit subreddits for gig-like posts and persist matched results.
    
    Scans each subreddit in the module's SUBREDDITS list, respecting robots.txt and configured proxy/throttling settings; for posts that match gig criteria it saves a gig record (including source, title, link, snippet, full description, timestamp, and category), updates per-subreddit scraper health, and logs per-subreddit performance and errors.
    """
    scraper_name = "reddit"
    start_time = time.time()
    status = "success"
    error_message = None

    headers = {
        "User-Agent": get_random_user_agent()
    }
    
    proxy = None
    if config.use_proxies:
        proxy = get_proxy()

    for subreddit in SUBREDDITS: # Loop through subreddits, each is a mini-scrape
        start_time = time.time() # Reset start time for each subreddit
        try:
            logger.info(f"Scraping {scraper_name} (r/{subreddit})...")
            url = BASE_URL.format(subreddit=subreddit)
            
            if not await is_url_allowed(url, user_agent=headers["User-Agent"]):
                logger.warning(f"Scraping of {url} disallowed by robots.txt. Skipping r/{subreddit}.")
                continue

            await async_randomized_delay()
            response = await fetch_url_with_retries(requests.get, url, headers=headers, proxies=proxy if config.use_proxies else None)

            data = response.json()
            posts = data.get("data", {}).get("children", [])

            if not posts:
                logger.info(f"No posts found in r/{subreddit}.")
                continue

            for post in posts:
                post_data = post.get("data", {})
                title = post_data.get("title")
                full_description = post_data.get("selftext")
                link = "https://www.reddit.com" + post_data.get("permalink", "")
                
                # Convert Unix timestamp to ISO format
                created_utc = post_data.get("created_utc")
                timestamp = datetime.fromtimestamp(created_utc, timezone.utc).isoformat() if created_utc else None
                
                category = post_data.get("subreddit")

                content = f"{title} {full_description}"

                if looks_like_gig(content):
                    await save_gig( # Await save_gig
                        source=f"Reddit (r/{subreddit})",
                        title=title,
                        link=link,
                        snippet=title[:200], # Keep snippet as first 200 chars of title
                        full_description=full_description,
                        timestamp=timestamp,
                        category=category
                    )
        
            update_scraper_health(f"{scraper_name}.{subreddit}") # Update health for each subreddit
            status = "success" # Reset status for each subreddit run
            error_message = None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error scraping r/{subreddit}: {e}")
            status = "failed"
            error_message = str(e)
        except Exception as e:
            logger.error(f"An unexpected error occurred during r/{subreddit} scraping: {e}")
            status = "failed"
            error_message = str(e)
        finally:
            duration = time.time() - start_time # Duration for THIS subreddit's scrape
            log_scraper_performance(f"{scraper_name}.{subreddit}", duration, status, error_message)
