import unittest
import os
import sqlite3
from unittest.mock import patch, AsyncMock
from core.storage import init_db, save_gig, DB_NAME
from datetime import datetime
import asyncio # Import asyncio

class TestStorage(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Ensure a clean database for each test
        """
        Prepare a clean SQLite database before each test.
        
        Removes any existing database file at DB_NAME and initializes a fresh database schema for the test.
        """
        if os.path.exists(DB_NAME):
            os.remove(DB_NAME)
        init_db()

    async def asyncTearDown(self):
        # Clean up the database file after each test
        """
        Remove the test database file if it exists.
        
        Executed after each test to delete the SQLite database file specified by `DB_NAME`, ensuring a clean environment for subsequent tests.
        """
        if os.path.exists(DB_NAME):
            os.remove(DB_NAME)

    async def test_init_db(self):
        # Verify that the table is created correctly
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("PRAGMA table_info(gigs)")
        columns = [info[1] for info in c.fetchall()]
        self.assertIn("source", columns)
        self.assertIn("title", columns)
        self.assertIn("link", columns)
        self.assertIn("snippet", columns)
        self.assertIn("price", columns)
        self.assertIn("full_description", columns)
        self.assertIn("timestamp", columns)
        self.assertIn("contact_info", columns)
        self.assertIn("category", columns)
        conn.close()

    @patch('core.storage.send_notification', new_callable=AsyncMock) # Corrected patch target
    async def test_save_new_gig(self, mock_send_notification):
        # Test saving a new gig
        """
        Verifies that saving a new gig inserts a record with the expected fields into the database and triggers a single notification.
        
        Saves a gig with all fields provided, queries the `gigs` table for the record by link, and asserts each stored column (source, title, link, snippet, price, full_description, timestamp, contact_info, category) matches the expected values (timestamp must be present). Also asserts that `send_notification` was called exactly once with the expected positional arguments (source, title, link, snippet).
        """
        await save_gig(
            source="Test Source",
            title="Test Title",
            link="http://test.com/1",
            snippet="Test Snippet",
            price="$100",
            full_description="Full description text",
            contact_info="test@example.com",
            category="Development"
        )

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM gigs WHERE link='http://test.com/1'")
        gig = c.fetchone()
        conn.close()

        self.assertIsNotNone(gig)
        self.assertEqual(gig[1], "Test Source")
        self.assertEqual(gig[2], "Test Title")
        self.assertEqual(gig[3], "http://test.com/1")
        self.assertEqual(gig[4], "Test Snippet")
        self.assertEqual(gig[5], "$100")
        self.assertEqual(gig[6], "Full description text")
        self.assertIsNotNone(gig[7]) # timestamp should be generated
        self.assertEqual(gig[8], "test@example.com")
        self.assertEqual(gig[9], "Development")
        
        mock_send_notification.assert_called_once()
        args, kwargs = mock_send_notification.call_args
        self.assertEqual(args[0], "Test Source")
        self.assertEqual(args[1], "Test Title")
        self.assertEqual(args[2], "http://test.com/1")
        self.assertEqual(args[3], "Test Snippet")

    @patch('core.storage.send_notification', new_callable=AsyncMock) # Corrected patch target
    async def test_save_duplicate_gig(self, mock_send_notification):
        # Test saving a duplicate gig (same source and link)
        """
        Verify that saving a gig ignores duplicate inserts for the same source and link and triggers a notification only once.
        
        Saves an initial gig, attempts to save a second gig with the same source and link but different fields, then asserts the database contains a single entry for that link and that send_notification was called exactly once.
        """
        await save_gig(
            source="Test Source",
            title="Test Title",
            link="http://test.com/duplicate",
            snippet="Test Snippet"
        )
        await save_gig(
            source="Test Source",
            title="Test Title Duplicate",
            link="http://test.com/duplicate",
            snippet="Test Snippet Duplicate"
        ) # Attempt to save duplicate

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM gigs WHERE link='http://test.com/duplicate'")
        count = c.fetchone()[0]
        conn.close()

        self.assertEqual(count, 1) # Only one entry should be present
        mock_send_notification.assert_called_once() # Notification should only be sent once for the first gig

    @patch('core.storage.send_notification', new_callable=AsyncMock) # Corrected patch target
    async def test_save_gig_with_provided_timestamp(self, mock_send_notification):
        # Test saving a gig with a provided timestamp
        custom_timestamp = "2023-01-01T12:00:00.000000"
        await save_gig(
            source="Test Source",
            title="Timestamp Gig",
            link="http://test.com/timestamp",
            snippet="Snippet",
            timestamp=custom_timestamp
        )

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT timestamp FROM gigs WHERE link='http://test.com/timestamp'")
        retrieved_timestamp = c.fetchone()[0]
        conn.close()

        self.assertEqual(retrieved_timestamp, custom_timestamp)
        mock_send_notification.assert_called_once()

    @patch('core.storage.send_notification', new_callable=AsyncMock) # Corrected patch target
    async def test_save_different_source_same_link(self, mock_send_notification):
        # Test saving the same link from a different source (should be allowed)
        await save_gig(
            source="Source A",
            title="Title A",
            link="http://test.com/shared_link",
            snippet="Snippet A"
        )
        await save_gig(
            source="Source B",
            title="Title B",
            link="http://test.com/shared_link",
            snippet="Snippet B"
        )

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM gigs WHERE link='http://test.com/shared_link'")
        count = c.fetchone()[0]
        conn.close()
        
        self.assertEqual(count, 2) # Both should be saved due to UNIQUE(source, link)
        self.assertEqual(mock_send_notification.call_count, 2) # Notification sent for both

if __name__ == '__main__':
    unittest.main()