"""Database module for podcast processing."""

from .db import DatabaseManager
from .schema import SCHEMA_VERSION

__all__ = ["DatabaseManager", "SCHEMA_VERSION"]
