import sqlite3
import csv
import json
from datetime import datetime
from core.logger import logger
from core.storage import DB_NAME # Assuming DB_NAME is accessible from storage

def fetch_all_gigs():
    """
    Retrieve all records from the `gigs` table as a list of dictionaries.
    
    Returns:
        list[dict]: A list where each item is a dictionary mapping column names to their values for a gig. Returns an empty list if the table has no rows.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # This allows access to columns by name
    c = conn.cursor()
    c.execute("SELECT * FROM gigs")
    gigs = c.fetchall()
    conn.close()
    return [dict(gig) for gig in gigs] # Convert rows to dictionaries

def export_to_csv(gigs, filename=None):
    """
    Write a sequence of gig dictionaries to a CSV file.
    
    If `gigs` is empty the function logs an informational message and returns without creating a file. When `filename` is None a timestamped filename in the form `gigs_export_YYYYMMDD_HHMMSS.csv` is generated. Column headers are taken from the keys of the first gig. The file is written with UTF-8 encoding; IO errors during writing are caught and logged.
    
    Parameters:
        gigs (list[dict]): List of gig records where each item is a dictionary of column name to value.
        filename (str | None): Path to the output CSV file; if None a timestamped filename is created.
    """
    if not gigs:
        logger.info("No gigs to export to CSV.")
        return

    if filename is None:
        filename = f"gigs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    # Get column names from the first gig
    fieldnames = gigs[0].keys()

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(gigs)
        logger.info(f"Successfully exported {len(gigs)} gigs to {filename}")
    except IOError as e:
        logger.error(f"Error writing CSV file {filename}: {e}")

def export_to_json(gigs, filename=None):
    """
    Write a list of gig dictionaries to a JSON file.
    
    If `filename` is None a timestamped file named `gigs_export_YYYYMMDD_HHMMSS.json` is created.
    If `gigs` is empty the function logs an informational message and returns without creating a file.
    
    Parameters:
        gigs (list[dict]): List of gig records to serialize to JSON.
        filename (str | None): Optional output file path; when omitted a timestamped filename is used.
    """
    if not gigs:
        logger.info("No gigs to export to JSON.")
        return

    if filename is None:
        filename = f"gigs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(gigs, jsonfile, indent=4, ensure_ascii=False)
        logger.info(f"Successfully exported {len(gigs)} gigs to {filename}")
    except IOError as e:
        logger.error(f"Error writing JSON file {filename}: {e}")

if __name__ == "__main__":
    # Example usage (requires gigs.db to exist with some data)
    from core.storage import init_db, save_gig
    init_db() # Ensure DB is initialized

    # Add some dummy gigs for testing if DB is empty
    test_gigs = fetch_all_gigs()
    if not test_gigs:
        logger.info("Adding dummy gigs for exporter testing.")
        save_gig("TestSource1", "Test Gig Title 1", "http://test1.com", "Snippet 1", price="$100", full_description="Full description 1", timestamp=datetime.utcnow().isoformat(), category="Development")
        save_gig("TestSource2", "Test Gig Title 2", "http://test2.com", "Snippet 2", price="$200", full_description="Full description 2", timestamp=datetime.utcnow().isoformat(), category="Design")
        gigs_to_export = fetch_all_gigs()
    else:
        gigs_to_export = test_gigs

    if gigs_to_export:
        logger.info(f"Exporting {len(gigs_to_export)} gigs...")
        export_to_csv(gigs_to_export)
        export_to_json(gigs_to_export)
    else:
        logger.warning("No gigs found in database for export testing.")