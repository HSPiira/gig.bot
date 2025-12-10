import asyncio
import random
import time

from core.logger import logger
from core.config import config # Import config

def randomized_delay():
    """
    Introduces a randomized delay between requests, using delay_range from config.
    """
    min_seconds, max_seconds = config.delay_range
    delay = random.uniform(min_seconds, max_seconds)
    logger.info(f"Throttling: Waiting for {delay:.2f} seconds...")
    time.sleep(delay)

async def async_randomized_delay():
    """
    Introduces an asynchronous randomized delay between requests, using delay_range from config.
    """
    min_seconds, max_seconds = config.delay_range
    delay = random.uniform(min_seconds, max_seconds)
    logger.info(f"Throttling: Waiting asynchronously for {delay:.2f} seconds...")
    await asyncio.sleep(delay)

# A more advanced global rate limiter would require shared state
# (e.g., a Redis counter, or a shared in-memory object with locks).
# For now, we'll focus on the per-request delay.
# Global rate limit can be added later if needed.
