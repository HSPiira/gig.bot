import os
from telethon import TelegramClient, events
import asyncio

from core.filters import looks_like_gig
from core.storage import save_gig
from core.logger import logger
from core.throttler import async_randomized_delay
from core.scraper_base import scraper_lifecycle

# --- Configuration ---
API_ID = os.environ.get("TELEGRAM_API_ID", 12345)
API_HASH = os.environ.get("TELEGRAM_API_HASH", "YOUR_API_HASH_HERE")
SESSION_NAME = "gig_bot_session"
CHANNEL_USERNAMES = ["jobgram", "remoteipo"]

# --- Telegram Client Implementation ---
# Client instantiation and event handler registration moved to scrape_telegram()

async def handle_new_message(event):
    """
    Process incoming Telegram message events and persist messages that resemble a gig.

    Parameters:
        event (telethon.events.newmessage.NewMessage.Event): Incoming Telethon NewMessage event.
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
        await save_gig(
            source="Telegram",
            title=full_description[:100],
            link=link,
            snippet=full_description[:200],
            price=None,
            full_description=full_description,
            timestamp=timestamp,
            contact_info=None,
            category=category
        )

@scraper_lifecycle("telegram")
async def scrape_telegram():
    """
    Start and run the Telegram client to monitor channels for new messages.

    This is a long-running event-driven scraper that listens for new messages
    in configured Telegram channels. Validates API credentials before starting.
    """
    # Validate credentials
    if API_ID == 12345 or API_HASH == "YOUR_API_HASH_HERE":
        logger.error("🛑 Please set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env file")
        raise ValueError("Telegram API credentials not configured")

    # Instantiate client
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

    # Register event handler
    client.add_event_handler(handle_new_message, events.NewMessage(chats=CHANNEL_USERNAMES))

    try:
        await client.start(phone=lambda: input('Enter phone number: '))
        logger.info("✅ Telegram client is running and monitoring channels...")
        await client.run_until_disconnected()
    finally:
        if client.is_connected():
            await client.disconnect()
            logger.info("Telegram client disconnected")

if __name__ == '__main__':
    try:
        asyncio.run(scrape_telegram())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down Telegram client...")