"""Typed exception hierarchy.

Callers and tests assert on precise failures, and no secret-bearing text is ever
put into these messages by construction.
"""

from __future__ import annotations


class QaiaError(Exception):
    """Base class for all QAIA errors."""


class InvalidFeatureError(QaiaError):
    """The input .feature is missing or malformed."""


class GenerationError(QaiaError):
    """The LLM generation step failed or returned nothing usable."""


class UnsafePathError(QaiaError):
    """A model-supplied filename tried to escape the generated-tests directory."""


class PublishError(QaiaError):
    """Opening the GitHub PR failed."""
