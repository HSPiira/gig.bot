import sqlite3
from .notifications import send_email_notification

DB_NAME = "gigs.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS gigs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        title TEXT,
        link TEXT UNIQUE,
        snippet TEXT
    )
    """)

    conn.commit()
    conn.close()


def save_gig(source: str, title: str, link: str, snippet: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    try:
        c.execute("""
        INSERT INTO gigs (source, title, link, snippet)
        VALUES (?, ?, ?, ?)
        """, (source, title, link, snippet))

        conn.commit()
        print(f"✅ Saved gig: {title}")
        
        # Send a notification for the new gig
        send_email_notification(source, title, link, snippet)

    except sqlite3.IntegrityError:
        # This will happen if the link is not unique
        print(f"⏩ Skipping duplicate gig: {title}")
    finally:
        conn.close()
