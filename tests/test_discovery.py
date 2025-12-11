#!/usr/bin/env python
"""Test scraper discovery logic."""
import importlib
import inspect
import pkgutil
import scrapers
from core.config import config
from core.logger import logger

logger.info("Testing scraper discovery...")

sync_scrapers = []
async_scrapers = []

# Discover all scraper functions
for importer, modname, ispkg in pkgutil.iter_modules(scrapers.__path__):
    if not ispkg:
        if modname not in config.enabled_scrapers:
            logger.info(f"Skipping disabled scraper: {modname}")
            continue

        logger.info(f"Checking module: {modname}")
        module = importlib.import_module(f"scrapers.{modname}")

        # Only look for the main entry point function: scrape_{modname}
        main_func_name = f"scrape_{modname}"

        if hasattr(module, main_func_name):
            scraper_func = getattr(module, main_func_name)

            if inspect.iscoroutinefunction(scraper_func):
                async_scrapers.append(scraper_func)
                logger.info(f"  ✓ Found async scraper: {main_func_name}")
            elif callable(scraper_func):
                sync_scrapers.append(scraper_func)
                logger.info(f"  ✓ Found sync scraper: {main_func_name}")
        else:
            logger.warning(f"  ✗ Module {modname} does not have a {main_func_name} function")

print("\n" + "="*60)
print("DISCOVERY RESULTS")
print("="*60)
print(f"Enabled scrapers in config: {config.enabled_scrapers}")
print(f"\nDiscovered {len(async_scrapers)} async scrapers:")
for scraper in async_scrapers:
    print(f"  - {scraper.__name__}")

print(f"\nDiscovered {len(sync_scrapers)} sync scrapers:")
for scraper in sync_scrapers:
    print(f"  - {scraper.__name__}")

print("\n" + "="*60)
print("TEST PASSED ✓" if (len(async_scrapers) + len(sync_scrapers)) == len(config.enabled_scrapers) else "WARNING: Mismatch in counts")
print("="*60)
