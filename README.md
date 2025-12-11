# Gig Bot – Off-Market Freelance Gig Finder

Gig Bot is a Python-based automation tool that searches the internet for **cheap, informal, and urgent programming gigs** that are not typically found on popular freelance platforms like Upwork, Fiverr, or Toptal.

It targets classified ads, forum-style posts, and public listings where people casually post small, low-budget technical tasks.

---

## Table of Contents

- [Why This Exists](#why-this-exists)
- [Core Features](#core-features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Development](#development)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Why This Exists

Many beginner developers struggle to get visibility because:
- They have no portfolio yet
- Clients don't trust unknown profiles
- Major platforms are oversaturated

Gig Bot focuses on **off-market work** where:
- Budgets are small
- Barriers to entry are low
- Clients care more about speed than reputation

This gives you more real-world opportunities to build experience fast.

---

## Core Features

**Current Features:**

- 🔍 **Multi-Source Scraping (10 sources):**
  - **US Classifieds:** Craigslist (15 cities), Locanto, ClassifiedAds
  - **UK/AU Classifieds:** Gumtree
  - **Global Classifieds:** Locanto (India, etc.), Jiji (Africa)
  - **Forums:** Reddit, DigitalPoint, WarriorForum
  - **Social:** Discord servers, Telegram groups
- 🧠 **Smart Filtering:**
  - Weighted keyword scoring
  - NLP-based classification (facebook/bart-large-mnli)
  - Budget extraction from freeform text
  - Negative keyword filtering
- 💾 **Data Management:**
  - SQLite database with health tracking
  - Duplicate detection
  - Performance metrics logging
- 📬 **Notifications:**
  - Email alerts (SMTP)
  - Telegram bot messages
- 🔄 **Reliability:**
  - Automatic retry with exponential backoff
  - robots.txt compliance
  - Scraper health monitoring
  - Configurable rate limiting

**Planned Features:**

- Web dashboard for browsing gigs
- Advanced NLP features (skill extraction, urgency scoring)
- More scrapers (OLX, Craigslist, Twitter/X)
- Proxy rotation and IP management
- Machine learning-based relevance scoring

---

## Installation

### Prerequisites

- **Python 3.10+** (for modern type hints and async features)
- **pip** package manager
- **2GB+ RAM** (for NLP model loading)
- **Internet connection** (for scraping and notifications)

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/gig_bot.git
   cd gig_bot
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up configuration:**
   ```bash
   # Copy example files
   cp settings.json.example settings.json
   cp .env.example .env

   # Edit configuration files with your settings
   nano settings.json  # or your preferred editor
   nano .env
   ```

5. **Initialize the database:**
   ```bash
   python -c "from core.storage import init_db; init_db()"
   ```

---

## Configuration

### Environment Variables

⚠️ **IMPORTANT:** Never commit credentials to version control. Use environment variables for sensitive data.

Create a `.env` file in the project root:

```bash
# Email Notifications
SMTP_PASSWORD=your_email_password
SMTP_USERNAME=your_email@example.com

# Telegram Notifications
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890

# Discord Bot (optional)
DISCORD_BOT_TOKEN=your_discord_token
```

### Settings.json Configuration

Edit `settings.json` to customize scraper behavior:

```json
{
  "enabled_scrapers": ["jiji", "reddit"],
  "delay_range": [1, 5],
  "use_proxies": false,
  "retry_attempts": 5,
  "http_timeout": 10,

  "weighted_keywords": {
    "freelance": 5,
    "developer": 3,
    "urgent": 4,
    "cheap": 3,
    "small project": 4
  },

  "negative_keywords": ["scam", "mlm", "pyramid"],

  "notification_settings": {
    "enable_email_notifications": true,
    "enable_telegram_notifications": false,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 465,
    "email_recipients": ["your_email@example.com"]
  },

  "nlp_settings": {
    "max_words": 300,
    "confidence_threshold": 0.4,
    "enable_caching": true,
    "cache_size": 1000
  }
}
```

### Configuration Reference

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enabled_scrapers` | array | `["jiji", "reddit"]` | List of scrapers to run |
| `delay_range` | [int, int] | `[1, 5]` | Min/max delay between requests (seconds) |
| `use_proxies` | boolean | `false` | Enable proxy rotation |
| `retry_attempts` | integer | `5` | Maximum HTTP retry attempts |
| `http_timeout` | integer | `10` | Request timeout (seconds) |
| `weighted_keywords` | object | See example | Keyword scores (higher = more relevant) |
| `negative_keywords` | array | `[]` | Blocklist keywords |
| `nlp_settings.max_words` | integer | `300` | Max words for NLP classification |
| `nlp_settings.confidence_threshold` | float | `0.4` | Minimum confidence score (0.0-1.0) |
| `nlp_settings.enable_caching` | boolean | `true` | Cache NLP results for performance |

---

## Usage

### Running the Bot

Start the bot with default settings:

```bash
python main.py
```

The bot will:
1. Load configuration and validate settings
2. Initialize the database
3. Schedule scrapers to run every 10 minutes
4. Monitor for new gigs continuously

### Testing Individual Components

**Test configuration:**
```bash
python core/config.py
```

**Test filters:**
```bash
python core/filters.py
```

**Test a specific scraper:**
```python
import asyncio
from scrapers.jiji import scrape_jiji

asyncio.run(scrape_jiji())
```

**Test notifications:**
```bash
python -m core.notifications
```

### Exporting Data

Export gigs to CSV:

```python
from core.storage import export_to_csv
export_to_csv("exports/gigs_export.csv")
```

Export gigs to JSON:

```python
from core.storage import export_to_json
export_to_json("exports/gigs_export.json")
```

---

## Project Structure

```
gig_bot/
├── core/                   # Core utility modules
│   ├── config.py          # Configuration management (singleton)
│   ├── filters.py         # Keyword & NLP filtering
│   ├── http_utils.py      # HTTP retry logic
│   ├── logger.py          # Logging configuration
│   ├── notifications.py   # Email & Telegram alerts
│   ├── proxies.py         # Proxy rotation & user agents
│   ├── robots.py          # robots.txt compliance
│   ├── scraper_base.py    # Scraper lifecycle decorator
│   ├── storage.py         # SQLite database operations
│   ├── throttler.py       # Rate limiting
│   └── types.py           # Type definitions & enums
├── scrapers/              # Scraper implementations
│   ├── discord.py         # Discord server monitoring
│   ├── jiji.py            # Jiji Uganda scraper
│   ├── reddit.py          # Reddit subreddit scraper
│   └── telegram.py        # Telegram group monitoring
├── tests/                 # Unit & integration tests
│   ├── test_filters.py    # Filter & NLP tests
│   ├── test_scrapers.py   # Scraper tests
│   └── test_storage.py    # Database tests
├── main.py                # Entry point
├── requirements.txt       # Python dependencies
├── settings.json          # User configuration
├── .env                   # Environment variables (not in git)
├── gigs.db                # SQLite database (auto-created)
└── exports/               # CSV/JSON exports
```

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     APScheduler (AsyncIO)                    │
│                    (Every 10 minutes)                        │
└───────────────────────────┬─────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
        ┌───────▼──────┐       ┌───────▼──────┐
        │ HTTP Scrapers│       │Event Scrapers│
        │ (Jiji,Reddit)│       │(Discord,Tele)│
        └───────┬──────┘       └───────┬──────┘
                │                      │
                └──────────┬───────────┘
                           │
                    ┌──────▼──────┐
                    │   Filters   │
                    │  (Keyword + │
                    │     NLP)    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Storage   │
                    │  (SQLite)   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │Notifications│
                    │(Email,Tele) │
                    └─────────────┘
```

### Key Design Patterns

1. **Singleton Pattern** - `Config` class ensures single configuration instance
2. **Decorator Pattern** - `@scraper_lifecycle` handles timing, errors, health tracking
3. **Strategy Pattern** - Pluggable scraper implementations
4. **Observer Pattern** - Event-driven notification system

### Data Flow

1. **Scraper** fetches HTML/JSON from source
2. **Parser** extracts title, link, snippet, price
3. **Filter Pipeline:**
   - Keyword scoring (weighted positive/negative keywords)
   - NLP classification (zero-shot learning)
   - Budget extraction (regex-based)
4. **Storage** saves to SQLite with duplicate detection
5. **Notification** sends alerts via configured channels

---

## Development

### Code Style

- Follow **PEP 8** style guide
- Use **type hints** for all function signatures
- Write **Google-style docstrings** for all public functions
- Run **Black** formatter before committing: `black .`

### Adding a New Scraper

1. **Create scraper file:**
   ```bash
   touch scrapers/newsource.py
   ```

2. **Implement scraper function:**
   ```python
   from core.scraper_base import scraper_lifecycle
   from core.storage import save_gig

   @scraper_lifecycle("newsource")
   async def scrape_newsource():
       """Scrapes NewSource for gig listings."""
       # 1. Check robots.txt
       # 2. Fetch HTML/JSON
       # 3. Parse listings
       # 4. Save gigs with save_gig()
       pass
   ```

3. **Add tests:**
   ```python
   # tests/test_scrapers.py
   class TestNewSourceScraper(unittest.IsolatedAsyncioTestCase):
       async def test_scrape_newsource_success(self):
           # Mock HTTP responses
           # Call scraper
           # Assert save_gig called with correct data
           pass
   ```

4. **Update configuration:**
   ```json
   {
     "enabled_scrapers": ["jiji", "reddit", "newsource"]
   }
   ```

5. **Update documentation** (this README)

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/scraper-newsource

# Make changes and test
pytest tests/

# Format and lint
black .
flake8 .

# Commit changes
git add .
git commit -m "feat: Add NewsSource scraper"

# Push and create PR
git push origin feature/scraper-newsource
```

---

## Testing

### Running Tests

Run all tests:
```bash
pytest tests/ -v
```

Run specific test file:
```bash
pytest tests/test_scrapers.py -v
```

Run with coverage report:
```bash
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html
```

### Test Structure

```
tests/
├── test_filters.py    # Keyword scoring, NLP, budget extraction
├── test_scrapers.py   # All scraper implementations
└── test_storage.py    # Database operations, health tracking
```

### Writing Tests

Use `unittest.mock` for external dependencies:

```python
import pytest
from unittest.mock import patch, AsyncMock

@patch('scrapers.jiji.fetch_url_with_retries')
@patch('scrapers.jiji.save_gig', new_callable=AsyncMock)
async def test_jiji_success(mock_save, mock_fetch):
    mock_fetch.return_value.text = "<html>...</html>"

    await scrape_jiji()

    assert mock_save.called
```

---

## Troubleshooting

### NLP Model Loading Issues

**Problem:** Model takes 10-30 seconds to load or runs out of memory

**Solutions:**
- Ensure you have 2GB+ RAM available
- Model is lazy-loaded on first classification (one-time cost)
- Consider using a smaller model in `core/filters.py`:
  ```python
  _classifier = pipeline("zero-shot-classification",
                        model="MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7")
  ```

### Database Locked Errors

**Problem:** `sqlite3.OperationalError: database is locked`

**Solutions:**
- SQLite allows only one writer at a time
- This is normal for concurrent saves
- The bot uses `asyncio.to_thread()` to handle this
- For production, consider migrating to PostgreSQL

### Scraper Failing

**Problem:** Scraper status shows "failed" in logs

**Debug steps:**
1. Check logs: `tail -f logs/gig_bot_*.log`
2. Test robots.txt: `python -c "from core.robots import is_url_allowed; print(is_url_allowed('https://example.com'))"`
3. Test HTTP: `curl -I https://example.com`
4. Run scraper manually:
   ```python
   import asyncio
   from scrapers.jiji import scrape_jiji
   asyncio.run(scrape_jiji())
   ```

### No Notifications Received

**Problem:** Gigs are saved but no alerts sent

**Debug steps:**
1. Check notification settings in `settings.json`
2. Verify environment variables: `printenv | grep SMTP`
3. Test email manually:
   ```bash
   python -m core.notifications
   ```
4. Check SMTP credentials are correct
5. For Gmail, enable "Allow less secure apps"

### Configuration Validation Errors

**Problem:** `ConfigValidationError` on startup

**Solutions:**
- Ensure all required fields are set in `settings.json`
- Check `.env` file exists and contains credentials
- Verify no placeholder values remain (e.g., `REPLACE_ME`)
- Run validation test:
  ```python
  from core.config import Config
  config = Config()  # Will raise error if invalid
  ```

---

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository** and create a feature branch
2. **Write tests** for new functionality
3. **Follow code style** (Black, PEP 8, type hints, docstrings)
4. **Update documentation** (README, docstrings, comments)
5. **Create a pull request** with a clear description

### Areas for Contribution

- **New Scrapers:** OLX, Craigslist, Twitter/X, LinkedIn
- **Performance:** Optimize NLP, parallel scraping, caching
- **Features:** Web dashboard, advanced NLP, proxy rotation
- **Testing:** Improve coverage, add integration tests
- **Documentation:** Tutorials, examples, API reference

---

## License

MIT License

Copyright (c) 2025 Gig Bot Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

**Happy Gig Hunting! 🚀**

For questions or issues, please open a GitHub issue or contact the maintainers.

