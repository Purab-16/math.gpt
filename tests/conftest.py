"""Shared test setup: reset caches and the rate limiter before every test."""

import pytest

from app.rate_limit import solve_rate_limiter
from app.services import ai_service, youtube_service


@pytest.fixture(autouse=True)
def reset_shared_state():
    """Clear in-memory state so tests do not affect each other."""
    solve_rate_limiter.clear()
    ai_service._solution_cache.clear()
    youtube_service._cache.clear()
    yield
