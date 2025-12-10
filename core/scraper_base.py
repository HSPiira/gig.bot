"""
Base scraper utilities including lifecycle management decorator.

This module provides a decorator pattern to handle common scraper lifecycle
tasks such as timing, error handling, health tracking, and performance logging.
"""
import functools
import time
from core.types import ScraperStatus
from core.storage import update_scraper_health, log_scraper_performance
from core.logger import logger


def scraper_lifecycle(scraper_name: str):
    """
    Decorator to handle scraper lifecycle (timing, error handling, health tracking).

    This decorator wraps scraper functions to automatically:
    - Track execution time
    - Handle exceptions gracefully
    - Update scraper health on success
    - Log performance metrics
    - Provide consistent logging

    Args:
        scraper_name: Identifier for the scraper (e.g., "jiji", "reddit")

    Usage:
        @scraper_lifecycle("jiji")
        async def scrape_jiji():
            # Just scraping logic, no boilerplate
            pass

    Returns:
        A decorator function that wraps the scraper with lifecycle management.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = ScraperStatus.SUCCESS
            error_message = None

            logger.info(f"Starting scraper: {scraper_name}")

            try:
                result = await func(*args, **kwargs)

                # If the scraper returned a ScraperStatus indicating it was skipped
                # (for example due to robots.txt), don't mark it as healthy.
                if result == ScraperStatus.SKIPPED_ROBOTS or (
                    isinstance(result, str) and result == ScraperStatus.SKIPPED_ROBOTS.value
                ):
                    status = ScraperStatus.SKIPPED_ROBOTS
                    logger.warning(f"Scraper '{scraper_name}' skipped (robots or config): {status.value}")
                    return result

                update_scraper_health(scraper_name)
                logger.info(f"✅ Scraper '{scraper_name}' completed successfully")
                return result

            except Exception as e:
                status = ScraperStatus.FAILED
                error_message = str(e)
                logger.error(f"[{scraper_name.upper()} ERROR] {e}", exc_info=True)
                # Don't re-raise to allow other scrapers to continue

            finally:
                duration = time.time() - start_time
                try:
                    log_scraper_performance(scraper_name, duration, status.value, error_message)
                except Exception:
                    logger.exception("Failed to log scraper performance")

                logger.info(f"Scraper '{scraper_name}' finished in {duration:.2f}s (Status: {status.value})")

        return wrapper
    return decorator


if __name__ == "__main__":
    import asyncio

    # Example usage
    @scraper_lifecycle("test_scraper")
    async def test_scraper():
        """Test scraper function."""
        logger.info("Doing some scraping work...")
        await asyncio.sleep(1)
        return "Success"

    # Run the test
    asyncio.run(test_scraper())
