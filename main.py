import asyncio
import importlib
import inspect
import pkgutil
import threading
import scrapers
from core.storage import init_db

def main():
    print("Starting Gig Bot...")
    init_db()

    print("Discovering and running all scrapers...")

    sync_scrapers = []
    async_scrapers = []

    # Discover all scraper functions
    for importer, modname, ispkg in pkgutil.iter_modules(scrapers.__path__):
        if not ispkg:
            module = importlib.import_module(f"scrapers.{modname}")
            for item_name in dir(module):
                if item_name.startswith("scrape_"):
                    scraper_func = getattr(module, item_name)
                    if inspect.iscoroutinefunction(scraper_func):
                        async_scrapers.append(scraper_func)
                    else:
                        sync_scrapers.append(scraper_func)

    # Run synchronous scrapers in separate threads
    for scraper in sync_scrapers:
        print(f"-> Starting synchronous scraper: {scraper.__name__}")
        thread = threading.Thread(target=scraper)
        thread.start()

    # Run asynchronous scrapers in an asyncio event loop
    if async_scrapers:
        print(f"-> Starting asynchronous scrapers: {[s.__name__ for s in async_scrapers]}")
        loop = asyncio.get_event_loop()
        tasks = [loop.create_task(scraper()) for scraper in async_scrapers]
        
        try:
            loop.run_until_complete(asyncio.gather(*tasks))
        except KeyboardInterrupt:
            print("Shutting down...")
            for task in tasks:
                task.cancel()
            loop.close()

    print("All scrapers are running.")

if __name__ == "__main__":
    main()
