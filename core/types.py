"""
Type definitions and enums for type-safe operations throughout the application.
"""
from enum import Enum
from typing import TypedDict, Optional


class ScraperStatus(str, Enum):
    """Status codes for scraper operations."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED_ROBOTS = "skipped_robots"
    CIRCUIT_OPEN = "circuit_open"


class BudgetType(str, Enum):
    """Types of budget information that can be extracted."""
    FIXED_PRICE = "fixed_price"
    RANGE = "range"


class GigDict(TypedDict, total=False):
    """Type definition for gig data dictionary."""
    source: str
    title: str
    link: str
    snippet: str
    price: Optional[str]
    full_description: Optional[str]
    timestamp: Optional[str]
    contact_info: Optional[str]
    category: Optional[str]


class BudgetInfo(TypedDict, total=False):
    """Type definition for extracted budget information."""
    type: BudgetType
    amount: float
    amount_min: float
    amount_max: float
    currency: Optional[str]
