"""
Pagination utilities.

Provides helpers for computing pagination metadata and slicing sequences.
"""

import math

from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.schemas.responses import PaginationMeta


def clamp_page_size(size: int) -> int:
    """Ensure page size stays within allowed bounds."""
    return max(1, min(size, MAX_PAGE_SIZE))


def compute_pagination(
    total: int,
    page: int = DEFAULT_PAGE,
    size: int = DEFAULT_PAGE_SIZE,
) -> PaginationMeta:
    """
    Build a PaginationMeta object from raw counts.

    Args:
        total:  Total number of items in the result set.
        page:   Current page number (1-indexed).
        size:   Number of items per page.

    Returns:
        PaginationMeta with page, size, total, and pages fields.
    """
    size = clamp_page_size(size)
    pages = math.ceil(total / size) if total > 0 else 0
    return PaginationMeta(page=page, size=size, total=total, pages=pages)


def get_offset(page: int, size: int) -> int:
    """Compute the SQL OFFSET for the given page and size."""
    return (max(1, page) - 1) * clamp_page_size(size)
