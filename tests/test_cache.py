"""Tests for the shared TTL cache and the Gemini solution cache. Gemini is mocked."""

import asyncio
from unittest.mock import AsyncMock, patch

from app.cache import TTLCache
from app.schemas import GeminiMathSolution
from app.services.ai_service import solve_image, solve_text

MOCK_SOLUTION = GeminiMathSolution(
    problem="Solve x + 2 = 5",
    steps=["Step 1: Subtract 2: $x = 3$"],
    final_answer="x = 3",
    topic="Linear Equations",
    search_query="linear equations",
)

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


def test_cache_get_and_set():
    """Verify a saved value can be read back."""
    cache = TTLCache(ttl_seconds=60, max_size=10)
    cache.set("key", "value")

    assert cache.get("key") == "value"
    assert cache.get("missing") is None


def test_cache_expiry():
    """Verify values expire after the TTL."""
    cache = TTLCache(ttl_seconds=60, max_size=10)

    with patch("app.cache.time.monotonic", return_value=1000.0):
        cache.set("key", "value")

    with patch("app.cache.time.monotonic", return_value=1059.0):
        assert cache.get("key") == "value"

    with patch("app.cache.time.monotonic", return_value=1061.0):
        assert cache.get("key") is None
        assert len(cache) == 0


def test_cache_removes_oldest_when_full():
    """Verify the oldest entry is removed when the cache is full."""
    cache = TTLCache(ttl_seconds=60, max_size=2)

    with patch("app.cache.time.monotonic", return_value=1.0):
        cache.set("first", 1)
    with patch("app.cache.time.monotonic", return_value=2.0):
        cache.set("second", 2)
    with patch("app.cache.time.monotonic", return_value=3.0):
        cache.set("third", 3)
        assert cache.get("first") is None
        assert cache.get("second") == 2
        assert cache.get("third") == 3


def test_text_solution_cached():
    """Verify the same question (with extra spaces) only calls Gemini once."""
    mock_generate = AsyncMock(return_value=MOCK_SOLUTION)
    with patch("app.services.ai_service._generate_solution", new=mock_generate):
        first = asyncio.run(solve_text("Solve x + 2 = 5"))
        second = asyncio.run(solve_text("Solve   x + 2 =  5"))

    assert first == second
    assert mock_generate.call_count == 1


def test_different_options_not_shared():
    """Verify a different language or difficulty gets its own Gemini call."""
    mock_generate = AsyncMock(return_value=MOCK_SOLUTION)
    with patch("app.services.ai_service._generate_solution", new=mock_generate):
        asyncio.run(solve_text("Solve x + 2 = 5", language="english"))
        asyncio.run(solve_text("Solve x + 2 = 5", language="hinglish"))
        asyncio.run(solve_text("Solve x + 2 = 5", difficulty="detailed"))

    assert mock_generate.call_count == 3


def test_image_solution_cached():
    """Verify the same image and hint only call Gemini once."""
    mock_generate = AsyncMock(return_value=MOCK_SOLUTION)
    with patch("app.services.ai_service._generate_solution", new=mock_generate):
        asyncio.run(solve_image(PNG_BYTES, "image/png", question="Only Q1"))
        asyncio.run(solve_image(PNG_BYTES, "image/png", question="Only Q1"))
        asyncio.run(solve_image(PNG_BYTES, "image/png", question="Only Q2"))

    assert mock_generate.call_count == 2


def test_errors_not_cached():
    """Verify a failed Gemini call is retried next time instead of cached."""
    from app.exceptions import AIServiceError

    mock_generate = AsyncMock(side_effect=[AIServiceError(), MOCK_SOLUTION])
    with patch("app.services.ai_service._generate_solution", new=mock_generate):
        try:
            asyncio.run(solve_text("Solve x + 2 = 5"))
        except AIServiceError:
            pass
        result = asyncio.run(solve_text("Solve x + 2 = 5"))

    assert result == MOCK_SOLUTION
    assert mock_generate.call_count == 2
