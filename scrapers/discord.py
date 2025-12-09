import discord
import os
from core.filters import looks_like_gig
from core.storage import save_gig

# --- Configuration ---
# IMPORTANT: You need to replace these with your own values.
# 1. Get your Discord Bot Token from the Discord Developer Portal.
# 2. Get the IDs of the channels you want to monitor.
#    - Enable Developer Mode in Discord (Settings > Advanced).
#    - Right-click the channel and select "Copy Channel ID".
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHANNEL_IDS = [123456789012345678]  # Replace with your channel IDs

# --- Discord Bot Implementation ---

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    print('Monitoring channels:')
    for channel_id in CHANNEL_IDS:
        channel = client.get_channel(channel_id)
        if channel:
            print(f'- {channel.name} in {channel.guild.name}')
        else:
            print(f'- Unknown channel: {channel_id}')

@client.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    # Only process messages from the specified channels
    if message.channel.id in CHANNEL_IDS:
        content = message.content
        if looks_like_gig(content):
            print(f"Potential gig found in '{message.channel.name}': {message.jump_url}")
            # Create a unique link to the message
            link = message.jump_url
            save_gig("Discord", content[:100], link, content)

async def scrape_discord():
    """
    Starts the Discord bot to monitor for gigs.
    """
    if DISCORD_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or not DISCORD_BOT_TOKEN:
        print("🛑 Please set your DISCORD_BOT_TOKEN in scrapers/discord.py or as an environment variable.")
        return

    print("Starting Discord bot...")
    try:
        await client.start(DISCORD_BOT_TOKEN)
        await client.wait_until_ready()
        # Keep the bot running in the background
        await asyncio.Future()
    except discord.LoginFailure:
        print("🛑 Discord login failed. Please check your bot token.")
    except Exception as e:
        print(f"🛑 An error occurred with the Discord bot: {e}")
    finally:
        if not client.is_closed():
            await client.close()

if __name__ == '__main__':
    import asyncio
    # This allows running the scraper directly for testing
    # You would need to set the environment variable DISCORD_BOT_TOKEN
    try:
        asyncio.run(scrape_discord())
    except KeyboardInterrupt:
        print("Shutting down Discord bot...")
