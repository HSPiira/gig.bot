import discord
import os
import asyncio
from core.filters import looks_like_gig
from core.storage import save_gig
from core.logger import logger
from core.throttler import async_randomized_delay
from core.scraper_base import scraper_lifecycle # This will be implemented later
import time
from datetime import datetime

# --- Configuration ---
CHANNEL_IDS = [123456789012345678]

# intents = discord.Intents.default() # Moved inside scrape_discord
# intents.messages = True
# intents.message_content = True

# client = discord.Client(intents=intents) # Moved inside scrape_discord

@scraper_lifecycle("discord") # This decorator will handle lifecycle
async def scrape_discord():
    """
    Start and run the Discord client and manage its lifecycle.

    This function instantiates a Discord client, registers event handlers, and
    runs the bot until stopped. The `@scraper_lifecycle` decorator handles
    timing, error handling, health updates and performance logging.
    """
    # Read token at runtime (allows tests to modify env after import)
    discord_token = os.environ.get("DISCORD_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    if discord_token == "YOUR_BOT_TOKEN_HERE" or not discord_token:
        logger.error("🛑 Please set your DISCORD_BOT_TOKEN as an environment variable.")
        raise ValueError("Discord bot token not set.")

    # Intents must be defined before client instantiation
    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True
    
    scraper_client = discord.Client(intents=intents)

    @scraper_client.event
    async def on_ready():
        logger.info(f'Logged in as {scraper_client.user}')
        logger.info('Monitoring channels:')
        for channel_id in CHANNEL_IDS:
            channel = scraper_client.get_channel(channel_id)
            if channel:
                logger.info(f'- {channel.name} in {channel.guild.name}')
            else:
                logger.warning(f'- Unknown channel: {channel_id}')

    @scraper_client.event
    async def on_message(message):
        if message.author == scraper_client.user:
            return

        if message.channel and message.channel.id in CHANNEL_IDS:
            full_description = message.content
            if looks_like_gig(full_description):
                channel_name = message.channel.name if message.channel else "Unknown Channel"
                link = message.jump_url
                timestamp = message.created_at.isoformat() if message.created_at else None
                category = channel_name

                logger.info(f"Potential gig found in '{channel_name}': {link}")
                await async_randomized_delay()
                await save_gig(
                    source="Discord",
                    title=full_description[:100],
                    link=link,
                    snippet=full_description[:200],
                    full_description=full_description,
                    timestamp=timestamp,
                    category=category
                )

    logger.info("Starting Discord bot...")
    await scraper_client.start(discord_token)
    await scraper_client.wait_until_ready()
    # Use run_until_disconnected so tests can mock and return
    await scraper_client.run_until_disconnected()

    # Ensure clean shutdown if not already closed. Some test mocks return
    # non-awaitable MagicMocks for `.close()`, so detect coroutine before awaiting.
    if not scraper_client.is_closed():
        close_result = scraper_client.close()
        if asyncio.iscoroutine(close_result):
            await close_result


if __name__ == '__main__':
    try:
        asyncio.run(scrape_discord())
    except KeyboardInterrupt:
        logger.info("Shutting down Discord bot...")