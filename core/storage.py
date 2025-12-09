import sqlite3

DB_NAME = "gigs.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS gigs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        title TEXT,
        link TEXT,
        snippet TEXT
    )
    """)

    conn.commit()
    conn.close()


def save_gig(source: str, title: str, link: str, snippet: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    INSERT INTO gigs (source, title, link, snippet)
    VALUES (?, ?, ?, ?)
    """, (source, title, link, snippet))

    conn.commit()
    conn.close()
