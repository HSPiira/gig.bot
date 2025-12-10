import asyncio
import random
import time

from core.logger import logger
from core.config import config # Import config

def randomized_delay():
    """
    Introduce a synchronous randomized delay between requests.
    
    Selects a duration uniformly from config.delay_range (min_seconds, max_seconds), logs the chosen delay, and blocks execution for that duration.
    """
    min_seconds, max_seconds = config.delay_range
    delay = random.uniform(min_seconds, max_seconds)
    logger.info(f"Throttling: Waiting for {delay:.2f} seconds...")
    time.sleep(delay)

async def async_randomized_delay():
    """
    Pause asynchronously for a random duration selected from config.delay_range.
    
    Chooses a floating-point duration between the configured minimum and maximum seconds and suspends the coroutine for that duration to provide per-request throttling.
    """
    min_seconds, max_seconds = config.delay_range
    delay = random.uniform(min_seconds, max_seconds)
    logger.info(f"Throttling: Waiting asynchronously for {delay:.2f} seconds...")
    await asyncio.sleep(delay)

# A more advanced global rate limiter would require shared state
# (e.g., a Redis counter, or a shared in-memory object with locks).
# For now, we'll focus on the per-request delay.
# Global rate limit can be added later if needed.