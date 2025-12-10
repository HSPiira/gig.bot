import sqlite3
from core.notifications import send_notification # Import the unified notification function
from core.logger import logger # Import logger
from datetime import datetime, timezone, timedelta # Import datetime, timezone, timedelta for UTC
import asyncio # Import asyncio to run send_notification if save_gig is not awaited

DB_NAME = "gigs.db"

def init_db():
    """
    Initialize the SQLite database file and ensure required tables and schemas exist.
    
    Creates (if missing) the following tables in the configured DB_NAME:
    - gigs: stores scraped gig records with columns id, source, title, link, snippet, price, full_description, timestamp, contact_info, category and a UNIQUE constraint on (source, link).
    - scraper_health: stores the last run timestamp for each scraper (scraper_name primary key).
    - scraper_performance: records scraper run metrics with a composite primary key on (scraper_name, timestamp).
    
    This function commits the schema changes to disk and closes the database connection.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS gigs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        title TEXT,
        link TEXT,
        snippet TEXT,
        price TEXT,
        full_description TEXT,
        timestamp TEXT,
        contact_info TEXT,
        category TEXT,
        UNIQUE(source, link)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS scraper_health (
        scraper_name TEXT PRIMARY KEY,
        last_run TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS scraper_performance (
        scraper_name TEXT,
        timestamp TEXT,
        duration REAL,
        status TEXT,
        error_message TEXT,
        PRIMARY KEY (scraper_name, timestamp)
    )
    """)

    conn.commit()
    conn.close()

def update_scraper_health(scraper_name: str):
    """
    Record the current UTC run timestamp for a scraper in the database.
    
    Inserts or replaces the `last_run` for `scraper_name` in the `scraper_health` table using the current UTC timestamp in ISO 8601 format. Errors are logged; the function ensures the database connection is closed.
    
    Parameters:
        scraper_name (str): Identifier of the scraper whose last run time should be recorded.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        c.execute(
            "INSERT OR REPLACE INTO scraper_health (scraper_name, last_run) VALUES (?, ?)",
            (scraper_name, timestamp)
        )
        conn.commit()
        logger.debug(f"Updated health for {scraper_name}: {timestamp}")
    except Exception as e:
        logger.error(f"Error updating scraper health for {scraper_name}: {e}")
    finally:
        conn.close()

def log_scraper_performance(scraper_name: str, duration: float, status: str, error_message: str = None):
    """
    Log a scraper's performance metrics as a timestamped record in the scraper_performance table.
    
    Inserts a row containing the current UTC ISO-8601 timestamp, the scraper identifier, run duration (seconds), status, and an optional error message into persistent storage.
    
    Parameters:
        scraper_name (str): Identifier for the scraper whose performance is being recorded.
        duration (float): Execution time in seconds.
        status (str): Outcome label (for example "success", "failure", or "error").
        error_message (str, optional): A brief error description when applicable.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        c.execute(
            """INSERT INTO scraper_performance 
            (scraper_name, timestamp, duration, status, error_message) 
            VALUES (?, ?, ?, ?, ?)""",
            (scraper_name, timestamp, duration, status, error_message)
        )
        conn.commit()
        logger.debug(f"Logged performance for {scraper_name}: Status={status}, Duration={duration:.2f}s")
    except Exception as e:
        logger.error(f"Error logging scraper performance for {scraper_name}: {e}")
    finally:
        conn.close()

def get_scraper_health(scraper_name: str) -> str | None:
    """
    Get the last-run timestamp recorded for the named scraper.
    
    Returns:
        `str`: ISO 8601 UTC timestamp of the scraper's last run, or `None` if no record exists.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT last_run FROM scraper_health WHERE scraper_name = ?", (scraper_name,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

async def check_scraper_health(threshold_minutes: int):
    """
    Check scraper reporting recency and send alerts for unhealthy scrapers.
    
    Fetches each scraper's last successful run time from the database and, using UTC, compares it to the current time. If a scraper's last run is older than threshold_minutes or missing, logs an error or warning respectively and sends a health alert notification.
    
    Parameters:
        threshold_minutes (int): Maximum allowed minutes since a scraper's last successful run before it is considered unhealthy.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT scraper_name, last_run FROM scraper_health")
    all_scrapers_health = c.fetchall()
    conn.close()

    current_time_utc = datetime.now(timezone.utc)

    for scraper_name, last_run_str in all_scrapers_health:
        if last_run_str:
            last_run_time = datetime.fromisoformat(last_run_str).astimezone(timezone.utc)
            time_difference = current_time_utc - last_run_time
            if time_difference > timedelta(minutes=threshold_minutes):
                alert_message = f"🚨 Health Alert: Scraper '{scraper_name}' has not reported a successful run in {time_difference.total_seconds() / 60:.0f} minutes (threshold: {threshold_minutes} min). Last run: {last_run_str}"
                logger.error(alert_message)
                await send_notification("Health Check", alert_message, "", alert_message) # Send alert notification
            else:
                logger.debug(f"Scraper '{scraper_name}' is healthy. Last run: {last_run_str}")
        else:
            alert_message = f"🚨 Health Alert: Scraper '{scraper_name}' has no recorded successful run."
            logger.warning(alert_message)
            await send_notification("Health Check", alert_message, "", alert_message) # Send alert notification

def _sync_save_gig_db_ops(
    source: str, 
    title: str, 
    link: str, 
    snippet: str,
    price: str | None,
    full_description: str | None,
    timestamp: str | None,
    contact_info: str | None,
    category: str | None
) -> bool:
    """
    Synchronous helper function to perform SQLite database operations for saving a gig.
    This function is intended to be run in a separate thread via run_in_executor.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    try:
        c.execute("""
        INSERT INTO gigs (source, title, link, snippet, price, full_description, timestamp, contact_info, category)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (source, title, link, snippet, price, full_description, timestamp, contact_info, category))

        conn.commit()
        logger.info(f"✅ Saved gig: {title}")
        return True # Indicate success
    except sqlite3.IntegrityError:
        logger.warning(f"⏩ Skipping duplicate gig: {title}")
        return False # Indicate duplicate
    except Exception as e:
        logger.error(f"Error saving gig to DB: {e}")
        return False # Indicate failure
    finally:
        conn.close()

async def save_gig(
    source: str, 
    title: str, 
    link: str, 
    snippet: str,
    price: str | None,
    full_description: str | None,
    timestamp: str | None,
    contact_info: str | None,
    category: str | None
):
    """
    Persist a gig to the database and notify recipients about the new gig.
    
    If `timestamp` is not provided, the current UTC time in ISO 8601 format is used. If a gig with the same `source` and `link` already exists (unique constraint), the insert is skipped and a warning is logged. A notification is sent after a successful save.
    
    Parameters:
        timestamp (str | None): ISO 8601 UTC timestamp for the gig; when None, current UTC time is used.
    """
    # If timestamp is not provided, use current UTC time
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    # Run synchronous DB operations in a separate thread
    db_success = await asyncio.get_running_loop().run_in_executor(
        None, # Use default ThreadPoolExecutor
        _sync_save_gig_db_ops,
        source, title, link, snippet, price, full_description, timestamp, contact_info, category
    )

    if db_success:
        # Send a notification for the new gig only if successfully saved
        await send_notification(source, title, link, snippet)
