import os
from telethon import TelegramClient, events
from core.filters import looks_like_gig
from core.storage import save_gig

# --- Configuration ---
# IMPORTANT: You need to replace these with your own values.
# 1. Get your API ID and API Hash from my.telegram.org.
# 2. Get the channel usernames you want to monitor.
API_ID = os.environ.get("TELEGRAM_API_ID", 12345)  # Replace with your API ID
API_HASH = os.environ.get("TELEGRAM_API_HASH", "YOUR_API_HASH_HERE")
SESSION_NAME = "gig_bot_session"
CHANNEL_USERNAMES = ["jobgram", "remoteipo"] # Replace with your channel usernames

# --- Telegram Client Implementation ---

# Using a file-based session
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

@client.on(events.NewMessage(chats=CHANNEL_USERNAMES))
async def handle_new_message(event):
    """Handles new messages from the specified channels."""
    message = event.message
    content = message.text
    
    if looks_like_gig(content):
        channel = await event.get_chat()
        channel_name = getattr(channel, 'username', 'Unknown')
        # Construct a link to the message
        link = f"https://t.me/{channel_name}/{message.id}"
        print(f"Potential gig found in '{channel_name}': {link}")
        save_gig("Telegram", content[:100], link, content)

async def scrape_telegram():
    """
    Starts the Telegram client to monitor for gigs.
    """
    if API_ID == 12345 or API_HASH == "YOUR_API_HASH_HERE":
        print("🛑 Please set your TELEGRAM_API_ID and TELEGRAM_API_HASH in scrapers/telegram.py or as environment variables.")
        return

    print("Starting Telegram client...")
    try:
        await client.start(phone=lambda: input('Enter phone number: '))
        print("Telegram client is running...")
        await client.run_until_disconnected()
    except Exception as e:
        print(f"🛑 An error occurred with the Telegram client: {e}")
    finally:
        if client.is_connected():
            await client.disconnect()

if __name__ == '__main__':
    import asyncio
    # This allows running the scraper directly for testing
    # You would need to set the environment variables TELEGRAM_API_ID and TELEGRAM_API_HASH
    try:
        asyncio.run(scrape_telegram())
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down Telegram client...")
