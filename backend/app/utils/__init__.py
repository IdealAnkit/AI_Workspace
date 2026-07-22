"""
Utilities package.

Re-exports all utility functions for convenient importing.
"""

import uuid


def generate_id() -> str:
    """Generate a URL-safe unique identifier."""
    return str(uuid.uuid4())


__all__ = ["generate_id"]
