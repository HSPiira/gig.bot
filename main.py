from core.storage import init_db
from scrapers.jiji import scrape_jiji

def main():
    print("Starting Gig Bot...")

    init_db()

    scrape_jiji()

    print("Done.")

if __name__ == "__main__":
    main()
