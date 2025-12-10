import discord
import os
import asyncio
import time # Import time for measuring duration
from core.filters import looks_like_gig
from core.storage import save_gig, update_scraper_health, log_scraper_performance # Import log_scraper_performance
from core.logger import logger
from core.throttler import async_randomized_delay
from datetime import datetime # Import datetime

# --- Configuration ---
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL_IDS = [123456789012345678]

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    logger.info(f'Logged in as {client.user}')
    logger.info('Monitoring channels:')
    for channel_id in CHANNEL_IDS:
        channel = client.get_channel(channel_id)
        if channel:
            logger.info(f'- {channel.name} in {channel.guild.name}')
        else:
            logger.warning(f'- Unknown channel: {channel_id}')
    update_scraper_health("discord") # Update health after bot is ready

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.channel.id in CHANNEL_IDS:
        full_description = message.content
        if looks_like_gig(full_description):
            channel_name = message.channel.name if message.channel else "Unknown Channel"
            link = message.jump_url
            timestamp = message.created_at.isoformat() if message.created_at else None
            category = channel_name

            logger.info(f"Potential gig found in '{channel_name}': {link}")
            await async_randomized_delay()
            await save_gig( # Await save_gig
                source="Discord",
                title=full_description[:100], # Use first 100 chars of description as title
                link=link,
                snippet=full_description[:200],
                full_description=full_description,
                timestamp=timestamp,
                category=category
            )

async def scrape_discord():
    scraper_name = "discord"
    start_time = time.time()
    status = "success"
    error_message = None

    if DISCORD_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or not DISCORD_BOT_TOKEN:
        logger.error("🛑 Please set your DISCORD_BOT_TOKEN in scrapers/discord.py or as an environment variable.")
        status = "failed"
        error_message = "Discord bot token not set."
        # Log performance for this "failed" attempt to start
        log_scraper_performance(scraper_name, time.time() - start_time, status, error_message)
        return

    logger.info("Starting Discord bot...")
    try:
        await client.start(DISCORD_BOT_TOKEN)
        await client.wait_until_ready()
        await asyncio.Future() # Keep the bot running in the background
    except discord.LoginFailure as e:
        logger.error("🛑 Discord login failed. Please check your bot token.")
        status = "failed"
        error_message = str(e)
    except Exception as e:
        logger.error(f"🛑 An error occurred with the Discord bot: {e}")
        status = "failed"
        error_message = str(e)
    finally:
        if not client.is_closed():
            await client.close()
        # Log performance at the end of the scrape_discord function's lifecycle
        log_scraper_performance(scraper_name, time.time() - start_time, status, error_message)


if __name__ == '__main__':
    try:
        asyncio.run(scrape_discord())
    except KeyboardInterrupt:
        logger.info("Shutting down Discord bot...")
