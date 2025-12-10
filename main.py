import asyncio
import importlib
import inspect
import pkgutil
import threading
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone # Added import for datetime and timezone

import scrapers
from core.storage import init_db, check_scraper_health # Import check_scraper_health
from core.logger import logger
from core.config import config, ConfigValidationError # Import config and ConfigValidationError
from core.exporter import fetch_all_gigs, export_to_csv, export_to_json # Import exporter functions

async def export_gigs_job():
    """
    Export gigs from the database to configured file formats in the configured export directory.
    
    Checks the export enable flag in config.export_settings and exits early if exporting is disabled or if there are no gigs to export. Ensures the configured export directory exists, then writes exported gigs in each format listed in config.export_settings.export_formats (supports "csv" and "json") using timestamped filenames of the form "gigs_export_<timestamp>.<ext>". Logs a warning for any unsupported formats and logs progress and completion.
    """
    if not config.export_settings.get("enable_export", False):
        logger.info("Exporting is disabled in settings.")
        return

    logger.info("Starting gig export job...")
    gigs = fetch_all_gigs()

    if not gigs:
        logger.info("No gigs to export.")
        return

    export_dir = config.export_settings.get("export_directory", "exports")
    os.makedirs(export_dir, exist_ok=True)

    export_formats = config.export_settings.get("export_formats", [])
    for fmt in export_formats:
        if fmt == "csv":
            export_to_csv(gigs, filename=os.path.join(export_dir, f"gigs_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"))
        elif fmt == "json":
            export_to_json(gigs, filename=os.path.join(export_dir, f"gigs_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"))
        else:
            logger.warning(f"Unsupported export format: {fmt}")
    logger.info("Gig export job finished.")


async def main():
    """
    Initialize application state, discover available scrapers, schedule periodic jobs, and run the scheduler until shutdown.
    
    Discovers scraper callables in the scrapers package (only modules listed in config.enabled_scrapers) and schedules:
    - synchronous scrapers to run every 10 minutes (executed off the event loop),
    - asynchronous scrapers to run every 10 minutes,
    - an optional gig export job at the configured export interval when enabled,
    - a periodic health-check job at the configured interval.
    
    Starts the AsyncIO scheduler and blocks until a KeyboardInterrupt or SystemExit is received, then shuts down the scheduler gracefully.
    """
    logger.info("Starting Gig Bot...")
    init_db()

    scheduler = AsyncIOScheduler()

    logger.info("Discovering and scheduling scrapers...")

    sync_scrapers = []
    async_scrapers = []

    # Discover all scraper functions
    for importer, modname, ispkg in pkgutil.iter_modules(scrapers.__path__):
        if not ispkg:
            if modname not in config.enabled_scrapers:
                logger.info(f"Skipping disabled scraper: {modname}")
                continue

            module = importlib.import_module(f"scrapers.{modname}")
            for item_name in dir(module):
                if item_name.startswith("scrape_"):
                    scraper_func = getattr(module, item_name)
                    if inspect.iscoroutinefunction(scraper_func):
                        async_scrapers.append(scraper_func)
                    else:
                        sync_scrapers.append(scraper_func)

    # Schedule synchronous scrapers
    for scraper in sync_scrapers:
        logger.info(f"-> Scheduling synchronous scraper: {scraper.__name__} to run every 10 minutes.")
        scheduler.add_job(
            lambda s=scraper: asyncio.create_task(asyncio.to_thread(s)), 
            IntervalTrigger(minutes=10), 
            id=f"sync_scraper_{scraper.__name__}"
        )

    # Schedule asynchronous scrapers
    for scraper in async_scrapers:
        logger.info(f"-> Scheduling asynchronous scraper: {scraper.__name__} to run every 10 minutes.")
        scheduler.add_job(
            scraper, 
            IntervalTrigger(minutes=10), 
            id=f"async_scraper_{scraper.__name__}"
        )
            
    # Schedule export job
    if config.export_settings.get("enable_export", False):
        export_interval = config.export_settings.get("export_interval_minutes", 60)
        logger.info(f"-> Scheduling gig export job to run every {export_interval} minutes.")
        scheduler.add_job(
            export_gigs_job,
            IntervalTrigger(minutes=export_interval),
            id="gig_exporter_job"
        )
    else:
        logger.info("Gig export job is disabled in settings.")
    
    # Schedule health check job
    health_check_interval = config.get("health_check_interval_minutes", 30)
    logger.info(f"-> Scheduling health check job to run every {health_check_interval} minutes.")
    scheduler.add_job(
        check_scraper_health, # Pass the coroutine function directly
        IntervalTrigger(minutes=health_check_interval),
        args=[health_check_interval], # Pass arguments using args
        id="health_check_job"
    )

    scheduler.start()
    logger.info("Scheduler started. Press Ctrl+C to exit.")

    try:
        await asyncio.Future()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down due to KeyboardInterrupt.")
        scheduler.shutdown()
        logger.info("Scheduler shut down.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ConfigValidationError as e:
        logger.critical(f"Configuration error: {e}")
        import sys
        sys.exit(1)