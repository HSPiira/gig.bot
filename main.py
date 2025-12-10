import asyncio
import importlib
import inspect
import pkgutil
import threading
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

import scrapers
from core.storage import init_db, check_scraper_health # Import check_scraper_health
from core.logger import logger
from core.config import config
from core.exporter import fetch_all_gigs, export_to_csv, export_to_json # Import exporter functions

async def export_gigs_job():
    """
    Fetches gigs from the database and exports them according to config settings.
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
            export_to_csv(gigs, filename=os.path.join(export_dir, f"gigs_export_{asyncio.get_event_loop().time():.0f}.csv"))
        elif fmt == "json":
            export_to_json(gigs, filename=os.path.join(export_dir, f"gigs_export_{asyncio.get_event_loop().time():.0f}.json"))
        else:
            logger.warning(f"Unsupported export format: {fmt}")
    logger.info("Gig export job finished.")


async def main():
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
        lambda: check_scraper_health(health_check_interval), # Pass interval as argument
        IntervalTrigger(minutes=health_check_interval),
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
    asyncio.run(main())
