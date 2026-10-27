"""Integration tests for the /solve endpoint using mocks for Gemini API calls."""

from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import GeminiMathSolution, VideoItem
from app.exceptions import InvalidInputError, AIServiceError

client = TestClient(app)

# Sample video returned by the mocked YouTube service
MOCK_VIDEO = VideoItem(
    title="Linear Equations Explained",
    url="https://www.youtube.com/watch?v=abc123",
    thumbnail="https://i.ytimg.com/vi/abc123/mqdefault.jpg",
)


def test_valid_input():
    """Verify that a valid math question returns a 200 OK SolveResponse."""
    mock_solution = GeminiMathSolution(
        problem="Solve 2x + 4 = 10",
        steps=[
            "Step 1: Subtract 4 from both sides: $2x = 6$",
            "Step 2: Divide by 2: $x = 3$",
        ],
        final_answer="x = 3",
        topic="Linear Equations",
        search_query="how to solve linear equations",
    )

    with patch("app.routes.solve.solve_text", new=AsyncMock(return_value=mock_solution)), patch(
        "app.routes.solve.search_math_videos", new=AsyncMock(return_value=[MOCK_VIDEO])
    ) as mock_videos:
        response = client.post(
            "/solve",
            json={
                "question": "Solve 2x + 4 = 10",
                "difficulty": "simple",
                "language": "english",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["final_answer"] == "x = 3"
        assert data["topic"] == "Linear Equations"
        assert len(data["steps"]) == 2
        assert data["videos"][0]["url"] == MOCK_VIDEO.url
        mock_videos.assert_called_once_with("how to solve linear equations", language="english")


def test_solve_without_videos():
    """Verify that the solution is still returned when no videos are found."""
    mock_solution = GeminiMathSolution(
        problem="Solve x + 1 = 2",
        steps=["Step 1: Subtract 1: $x = 1$"],
        final_answer="x = 1",
        topic="Linear Equations",
        search_query="linear equations",
    )

    with patch("app.routes.solve.solve_text", new=AsyncMock(return_value=mock_solution)), patch(
        "app.routes.solve.search_math_videos", new=AsyncMock(return_value=[])
    ):
        response = client.post("/solve", json={"question": "Solve x + 1 = 2"})

        assert response.status_code == 200
        data = response.json()
        assert data["final_answer"] == "x = 1"
        assert data["videos"] == []


def test_empty_input():
    """Verify that empty or whitespace-only questions return a 400 ErrorResponse."""
    response = client.post(
        "/solve",
        json={
            "question": "    ",
            "difficulty": "simple",
            "language": "english",
        },
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "EMPTY_INPUT"
    assert "empty" in data["message"].lower()


def test_long_input():
    """Verify that inputs exceeding 2000 characters return a 400 ErrorResponse."""
    long_question = "x + " * 600  # Exceeds 2000 chars

    response = client.post(
        "/solve",
        json={
            "question": long_question,
            "difficulty": "simple",
            "language": "english",
        },
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INPUT_TOO_LONG"
    assert "too long" in data["message"].lower()


def test_non_math_input():
    """Verify that non-math questions rejected by the model return a 400 ErrorResponse."""
    with patch(
        "app.routes.solve.solve_text",
        new=AsyncMock(
            side_effect=InvalidInputError(
                message="This is a geography question, not a math question.",
                error_code="NON_MATH_INPUT",
            )
        ),
    ):
        response = client.post(
            "/solve",
            json={
                "question": "What is the capital of Japan?",
                "difficulty": "simple",
                "language": "english",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "NON_MATH_INPUT"
        assert "not a math question" in data["message"].lower()


def test_ai_failure():
    """Verify that AI service exceptions return a clean generic 500 ErrorResponse."""
    with patch(
        "app.routes.solve.solve_text",
        new=AsyncMock(
            side_effect=AIServiceError(
                message="Internal model failure occurred.",
                error_code="AI_SERVICE_ERROR",
            )
        ),
    ):
        response = client.post(
            "/solve",
            json={
                "question": "Solve x^2 - 4 = 0",
                "difficulty": "detailed",
                "language": "english",
            },
        )

        assert response.status_code == 500
        data = response.json()
        assert data["error_code"] == "AI_SERVICE_ERROR"
        # Verify sensitive internal stack traces or keys are NOT exposed
        assert "Internal model failure" in data["message"] or "Unable to solve" in data["message"]


def test_invalid_options():
    """Verify that unknown difficulty or language values return a 422 ErrorResponse."""
    response = client.post(
        "/solve",
        json={
            "question": "Solve 2x = 4",
            "difficulty": "expert",
            "language": "french",
        },
    )

    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "INVALID_REQUEST"


def test_hinglish_detailed_input():
    """Verify that difficulty='detailed' and language='hinglish' parameters are accepted."""
    mock_solution = GeminiMathSolution(
        problem="Solve 3x = 9",
        steps=["Step 1: Dono sides ko 3 se divide karein: $x = 3$"],
        final_answer="x = 3",
        topic="Linear Equations",
        search_query="basic algebra in hindi",
    )

    with patch("app.routes.solve.solve_text", new=AsyncMock(return_value=mock_solution)) as mock_solve, patch(
        "app.routes.solve.search_math_videos", new=AsyncMock(return_value=[])
    ) as mock_videos:
        response = client.post(
            "/solve",
            json={
                "question": "Solve 3x = 9",
                "difficulty": "detailed",
                "language": "hinglish",
            },
        )

        assert response.status_code == 200
        # Ensure parameters were passed to service
        mock_solve.assert_called_once_with(
            question="Solve 3x = 9",
            difficulty="detailed",
            language="hinglish",
        )
        mock_videos.assert_called_once_with("basic algebra in hindi", language="hinglish")
