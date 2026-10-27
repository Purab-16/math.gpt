"""Tests for the /solve/image endpoint. Gemini and YouTube are mocked."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.image_utils import MAX_IMAGE_BYTES, detect_image_type
from app.main import app
from app.schemas import GeminiMathSolution

client = TestClient(app)

# Smallest fake files that start with the right magic bytes
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 100
WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 100

MOCK_SOLUTION = GeminiMathSolution(
    problem="Solve 2x = 8",
    steps=["Step 1: Divide by 2: $x = 4$"],
    final_answer="x = 4",
    topic="Linear Equations",
    search_query="linear equations",
)


def test_detect_image_type():
    """Verify image type is detected from file bytes, not the file name."""
    assert detect_image_type(PNG_BYTES) == "image/png"
    assert detect_image_type(JPEG_BYTES) == "image/jpeg"
    assert detect_image_type(WEBP_BYTES) == "image/webp"
    assert detect_image_type(b"hello world") is None
    assert detect_image_type(b"") is None


def test_valid_image_with_hint():
    """Verify a valid image and text hint are both passed to the AI service."""
    with patch("app.routes.solve.solve_image", new=AsyncMock(return_value=MOCK_SOLUTION)) as mock_solve, patch(
        "app.routes.solve.search_math_videos", new=AsyncMock(return_value=[])
    ):
        response = client.post(
            "/solve/image",
            files={"image": ("question.png", PNG_BYTES, "image/png")},
            data={"question": "  Only solve Q3  ", "difficulty": "detailed", "language": "hinglish"},
        )

    assert response.status_code == 200
    assert response.json()["final_answer"] == "x = 4"
    mock_solve.assert_called_once_with(
        image_bytes=PNG_BYTES,
        mime_type="image/png",
        question="Only solve Q3",
        difficulty="detailed",
        language="hinglish",
    )


def test_image_without_hint():
    """Verify an image alone (no text) is accepted."""
    with patch("app.routes.solve.solve_image", new=AsyncMock(return_value=MOCK_SOLUTION)), patch(
        "app.routes.solve.search_math_videos", new=AsyncMock(return_value=[])
    ):
        response = client.post("/solve/image", files={"image": ("q.jpg", JPEG_BYTES, "image/jpeg")})

    assert response.status_code == 200


def test_fake_image_rejected():
    """Verify a text file renamed to .png is rejected without calling Gemini."""
    mock_solve = AsyncMock()
    with patch("app.routes.solve.solve_image", new=mock_solve):
        response = client.post(
            "/solve/image",
            files={"image": ("virus.png", b"this is not an image", "image/png")},
        )

    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_IMAGE"
    mock_solve.assert_not_called()


def test_empty_image_rejected():
    """Verify an empty file is rejected."""
    response = client.post("/solve/image", files={"image": ("empty.png", b"", "image/png")})

    assert response.status_code == 400
    assert response.json()["error_code"] == "INVALID_IMAGE"


def test_image_too_large():
    """Verify an image just over 10 MB is rejected by the route."""
    big_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * MAX_IMAGE_BYTES
    response = client.post("/solve/image", files={"image": ("big.png", big_image, "image/png")})

    assert response.status_code == 400
    assert response.json()["error_code"] == "IMAGE_TOO_LARGE"


def test_request_body_too_large():
    """Verify very large uploads are rejected early by the size middleware."""
    huge_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * (MAX_IMAGE_BYTES + 2 * 1024 * 1024)
    response = client.post("/solve/image", files={"image": ("huge.png", huge_image, "image/png")})

    assert response.status_code == 413
    assert response.json()["error_code"] == "REQUEST_TOO_LARGE"


def test_missing_image():
    """Verify a request without an image returns INVALID_REQUEST."""
    response = client.post("/solve/image", data={"question": "Solve 2x = 8"})

    assert response.status_code == 422
    assert response.json()["error_code"] == "INVALID_REQUEST"


def test_hint_too_long():
    """Verify a text hint over 2000 characters is rejected."""
    response = client.post(
        "/solve/image",
        files={"image": ("q.png", PNG_BYTES, "image/png")},
        data={"question": "x" * 2001},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "INPUT_TOO_LONG"
