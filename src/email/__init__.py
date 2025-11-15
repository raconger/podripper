"""Email notification module."""

from .email_sender import EmailSender
from .summary_generator import WeeklySummaryGenerator

__all__ = ["EmailSender", "WeeklySummaryGenerator"]
