import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telegram import Bot
import asyncio

from core.logger import logger
from core.config import config

async def send_email_notification(source, title, link, snippet):
    """
    Sends an email notification for a new gig, using settings from config.
    """
    if not config.notification_settings.get("enable_email_notifications", False):
        return

    smtp_server = config.notification_settings.get("smtp_server")
    smtp_port = config.notification_settings.get("smtp_port")
    smtp_user = config.notification_settings.get("smtp_username")
    smtp_password = config.notification_settings.get("smtp_password")
    recipient_emails = config.notification_settings.get("email_recipients", [])

    if not all([smtp_server, smtp_port, smtp_user, smtp_password, recipient_emails]):
        logger.warning("Email notification is enabled but SMTP settings are incomplete in config.")
        return

    logger.info(f"📧 Sending email notification for: {title}")

    message = MIMEMultipart()
    message["From"] = smtp_user
    message["To"] = ", ".join(recipient_emails)
    message["Subject"] = f"New Gig Found on {source}: {title}"

    body = f"""
    A new potential gig has been found!

    Source: {source}
    Title: {title}
    Link: {link}

    Snippet:
    {snippet}
    """
    message.attach(MIMEText(body, "plain"))

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server: # Use SMTP_SSL for implicit TLS
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipient_emails, message.as_string())
        logger.info("✅ Notification email sent!")
    except Exception as e:
        logger.error(f"🛑 Error sending notification email: {e}")

async def send_telegram_notification(source, title, link, snippet):
    """
    Sends a Telegram message notification for a new gig, using settings from config.
    """
    if not config.notification_settings.get("enable_telegram_notifications", False):
        return

    bot_token = config.notification_settings.get("telegram_bot_token")
    chat_id = config.notification_settings.get("telegram_chat_id")

    if not all([bot_token, chat_id]):
        logger.warning("Telegram notification is enabled but bot token or chat ID is missing in config.")
        return

    logger.info(f"💬 Sending Telegram notification for: {title}")
    
    message_text = f"""
*New Gig Found!*
*Source:* {source}
*Title:* {title}
*Link:* {link}

*Snippet:*
{snippet}
    """
    
    try:
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=chat_id, text=message_text, parse_mode='Markdown')
        logger.info("✅ Notification Telegram message sent!")
    except Exception as e:
        logger.error(f"🛑 Error sending Telegram notification: {e}")

async def send_notification(source, title, link, snippet):
    """
    Sends notifications based on enabled settings in config.
    """
    email_task = None
    telegram_task = None

    if config.notification_settings.get("enable_email_notifications", False):
        email_task = asyncio.create_task(send_email_notification(source, title, link, snippet))
    
    if config.notification_settings.get("enable_telegram_notifications", False):
        telegram_task = asyncio.create_task(send_telegram_notification(source, title, link, snippet))

    if email_task or telegram_task:
        await asyncio.gather(*filter(None, [email_task, telegram_task]))


if __name__ == '__main__':
    # For testing the notification function
    # You would need to update settings.json with valid credentials
    async def test_notifications():
        logger.info("Testing notifications...")
        await send_notification(
            source="Test Source",
            title="Test Gig Title",
            link="http://example.com",
            snippet="This is a test snippet for a gig."
        )
        logger.info("Notification testing complete.")

    # Need to run in an asyncio event loop
    try:
        asyncio.run(test_notifications())
    except KeyboardInterrupt:
        logger.info("Notification test interrupted.")
