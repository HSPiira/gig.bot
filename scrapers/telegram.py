import os
from telethon import TelegramClient, events
import asyncio
import time # Import time for measuring duration

from core.filters import looks_like_gig
from core.storage import save_gig, update_scraper_health, log_scraper_performance # Import log_scraper_performance
from core.logger import logger
from core.throttler import async_randomized_delay
from datetime import datetime # Import datetime for ISO format conversion

# --- Configuration ---
API_ID = os.environ.get("TELEGRAM_API_ID", 12345)
API_HASH = os.environ.get("TELEGRAM_API_HASH", "YOUR_API_HASH_HERE")
SESSION_NAME = "gig_bot_session"
CHANNEL_USERNAMES = ["jobgram", "remoteipo"]

# --- Telegram Client Implementation ---
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

@client.on(events.NewMessage(chats=CHANNEL_USERNAMES))
async def handle_new_message(event):
    """
    Process incoming Telegram message events and persist messages that resemble a gig.
    
    When the incoming event's message text looks like a gig, this handler derives channel metadata (channel name/title, message link, timestamp, category), applies a randomized delay, and saves a gig record via save_gig.
    
    Parameters:
        event (telethon.events.newmessage.NewMessage.Event): Incoming Telethon NewMessage event containing the message to inspect.
    """
    message = event.message
    full_description = message.text
    
    if looks_like_gig(full_description):
        channel = await event.get_chat()
        channel_name = getattr(channel, 'username', None) or getattr(channel, 'title', None) or 'Unknown'
        link = f"https://t.me/{channel_name}/{message.id}"
        timestamp = message.date.isoformat() if message.date else None
        category = channel_name

        logger.info(f"Potential gig found in '{channel_name}': {link}")
        await async_randomized_delay()
        await save_gig( # Await save_gig
            source="Telegram",
            title=full_description[:100], # Use first 100 chars of description as title
            link=link,
            snippet=full_description[:200],
            full_description=full_description,
            timestamp=timestamp,
            category=category
        )

async def scrape_telegram():
    """
    Start and run the Telegram client to monitor channels for new messages and record scraper health and performance.
    
    Validates API credentials and aborts early if placeholders are detected. When running, starts the Telethon client (may prompt for a phone number), updates scraper health to indicate a healthy connection, and runs until the client disconnects. On errors or at shutdown, records scraper performance and error state; if connected, the client is disconnected before returning.
    """
    scraper_name = "telegram"
    start_time = time.time()
    status = "success"
    error_message = None

    if API_ID == 12345 or API_HASH == "YOUR_API_HASH_HERE":
        logger.error("🛑 Please set your TELEGRAM_API_ID and TELEGRAM_API_HASH in scrapers/telegram.py or as environment variables.")
        status = "failed"
        error_message = "Telegram API ID or Hash not set."
        # Log performance for this "failed" attempt to start
        log_scraper_performance(scraper_name, time.time() - start_time, status, error_message)
        return

    logger.info("Starting Telegram client...")
    try:
        await client.start(phone=lambda: input('Enter phone number: '))
        logger.info("Telegram client is running...")
        update_scraper_health("telegram") # Update health after client is running
        await client.run_until_disconnected()
    except Exception as e:
        logger.exception(f"🛑 An error occurred with the Telegram client: {e}")
        status = "failed"
        error_message = str(e)
    finally:
        if client.is_connected():
            await client.disconnect()
        # Log performance at the end of the scrape_telegram function's lifecycle
        log_scraper_performance(scraper_name, time.time() - start_time, status, error_message)

if __name__ == '__main__':
    try:
        asyncio.run(scrape_telegram())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down Telegram client...")