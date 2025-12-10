# Gig Bot – Off-Market Freelance Gig Finder

Gig Bot is a Python-based automation tool that searches the internet for **cheap, informal, and urgent programming gigs** that are not typically found on popular freelance platforms like Upwork, Fiverr, or Toptal.

It targets classified ads, forum-style posts, and public listings where people casually post small, low-budget technical tasks.

---

## Why This Exists

Many beginner developers struggle to get visibility because:
- They have no portfolio yet
- Clients don’t trust unknown profiles
- Major platforms are oversaturated

Gig Bot focuses on **off-market work** where:
- Budgets are small
- Barriers to entry are low
- Clients care more about speed than reputation

This gives you more real-world opportunities to build experience fast.

---

## Core Features

Current features:

- Scrapes public classified-style websites
- Filters posts based on:
  - Low budget indicators
  - Urgency signals
  - Developer-related keywords
- Stores results in a local SQLite database (`gigs.db`)
- Designed to be easily extendable

Planned features:

- Telegram group monitoring
- Discord server message tracking
- Email & push notifications
- Proxy rotation
- Advanced NLP filtering

---

## Configuration

⚠️ **IMPORTANT:** Copy `settings.json.example` to `settings.json` and configure your settings.
Sensitive credentials should be managed via environment variables (see `.env.example`).

---

## Project Structure


