"""Tests for security headers, rate limiting, and request size checks."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.rate_limit import MAX_REQUESTS_PER_WINDOW, RateLimiter
from app.schemas import GeminiMathSolution

client = TestClient(app)

MOCK_SOLUTION = GeminiMathSolution(
    problem="Solve 2x = 4",
    steps=["Step 1: Divide by 2: $x = 2$"],
    final_answer="x = 2",
    topic="Linear Equations",
    search_query="linear equations",
)


def test_security_headers_present():
    """Verify the home page sends browser security headers."""
    response = client.get("/")

    assert response.status_code == 200
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_rate_limit_blocks_extra_requests():
    """Verify one IP is blocked after too many solve requests."""
    with patch("app.routes.solve.solve_text", new=AsyncMock(return_value=MOCK_SOLUTION)), patch(
        "app.routes.solve.search_math_videos", new=AsyncMock(return_value=[])
    ):
        for _ in range(MAX_REQUESTS_PER_WINDOW):
            response = client.post("/solve", json={"question": "Solve 2x = 4"})
            assert response.status_code == 200

        response = client.post("/solve", json={"question": "Solve 2x = 4"})

    assert response.status_code == 429
    assert response.json()["error_code"] == "TOO_MANY_REQUESTS"


def test_rate_limiter_window_resets():
    """Verify requests are allowed again after the time window passes."""
    limiter = RateLimiter(max_requests=2, window_seconds=60)

    with patch("app.rate_limit.time.monotonic", return_value=100.0):
        assert limiter.is_allowed("1.2.3.4")
        assert limiter.is_allowed("1.2.3.4")
        assert not limiter.is_allowed("1.2.3.4")
        # A different IP has its own limit
        assert limiter.is_allowed("5.6.7.8")

    with patch("app.rate_limit.time.monotonic", return_value=161.0):
        assert limiter.is_allowed("1.2.3.4")


def test_post_without_content_length():
    """Verify POST requests without a size header are rejected."""
    response = client.post(
        "/solve",
        content=iter([b'{"question": "Solve 2x = 4"}']),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 411
    assert response.json()["error_code"] == "LENGTH_REQUIRED"
