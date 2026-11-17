"""Shared helpers for requirement tests.

Many requirement subjects (``profiles``, ``preflight``, ``contracts``,
``security``, ``cost``, ``eval``) do not exist yet. ``require`` imports a subject
module or skips the calling test with a clear reason, so the suite stays green
while every requirement stays visible and traceable.
"""

from __future__ import annotations

import importlib

import pytest


def require(module: str):
    """Import ``module`` or skip the test until it exists."""
    try:
        return importlib.import_module(module)
    except ModuleNotFoundError:
        pytest.skip(f"awaiting implementation: {module} not present")
