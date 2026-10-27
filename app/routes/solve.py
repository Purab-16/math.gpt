"""Route handlers for math problem solving endpoints."""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile
from app.schemas import GeminiMathSolution, SolveRequest, SolveResponse
from app.exceptions import InvalidInputError
from app.image_utils import read_image
from app.rate_limit import check_rate_limit
from app.services.ai_service import solve_image, solve_text
from app.services.youtube_service import search_math_videos

# Module logger
logger = logging.getLogger(__name__)

router = APIRouter()

# Input length limit
MAX_PROBLEM_LENGTH = 2000


def validate_question_length(question: str) -> None:
    """Raise InvalidInputError if the question text is longer than the limit."""
    if len(question) > MAX_PROBLEM_LENGTH:
        logger.warning(
            "Rejected request: Question length (%d) exceeded limit (%d).",
            len(question),
            MAX_PROBLEM_LENGTH,
        )
        raise InvalidInputError(
            f"Math question is too long. Please keep your question under {MAX_PROBLEM_LENGTH} characters.",
            error_code="INPUT_TOO_LONG",
        )


async def build_response(solution: GeminiMathSolution, fallback_problem: str, language: str) -> SolveResponse:
    """Add YouTube videos to a Gemini solution and build the API response."""
    search_query = solution.search_query or "math tutorial"

    # Find related videos. Never fails: returns [] if YouTube is unavailable.
    videos = await search_math_videos(search_query, language=language)

    return SolveResponse(
        problem=solution.problem or fallback_problem,
        steps=solution.steps,
        final_answer=solution.final_answer,
        topic=solution.topic or "Mathematics",
        search_query=search_query,
        videos=videos,
    )


@router.post(
    "/solve",
    response_model=SolveResponse,
    dependencies=[Depends(check_rate_limit)],
    summary="Solve a text question",
    tags=["Solve"],
)
async def solve(request: SolveRequest):
    """Receive a math question and return a step-by-step solution.

    Accepts text requests structured via SolveRequest with configurable
    difficulty ('simple' or 'detailed') and language ('english' or 'hinglish').
    Also returns related YouTube videos (Hindi + English for Hinglish mode).
    """
    raw_question = request.question

    # Validate empty input
    if not raw_question or not raw_question.strip():
        logger.warning("Rejected request: Empty math question.")
        raise InvalidInputError("Math question cannot be empty. Please enter a problem to solve.", error_code="EMPTY_INPUT")

    cleaned_question = raw_question.strip()
    validate_question_length(cleaned_question)

    logger.info(
        "Processing solve request (length: %d, difficulty: %s, language: %s)",
        len(cleaned_question),
        request.difficulty,
        request.language,
    )

    # Call AI service with difficulty and language parameters
    solution = await solve_text(
        question=cleaned_question,
        difficulty=request.difficulty,
        language=request.language,
    )

    return await build_response(solution, cleaned_question, request.language)


@router.post(
    "/solve/image",
    response_model=SolveResponse,
    dependencies=[Depends(check_rate_limit)],
    summary="Solve a question from a photo",
    tags=["Solve"],
)
async def solve_image_route(
    image: UploadFile = File(..., description="PNG, JPEG, or WEBP image of the math problem (max 10 MB)"),
    question: str = Form(default="", description="Optional text hint, e.g. 'Only solve Q3'"),
    difficulty: Literal["simple", "detailed"] = Form(default="simple"),
    language: Literal["english", "hinglish"] = Form(default="english"),
):
    """Receive an image of a math problem (plus optional text) and return a solution.

    The image is only kept in memory. It is never saved to disk or logged.
    """
    cleaned_question = question.strip()
    validate_question_length(cleaned_question)

    image_bytes, mime_type = await read_image(image)

    logger.info(
        "Processing image solve request (image size: %d, hint length: %d, difficulty: %s, language: %s)",
        len(image_bytes),
        len(cleaned_question),
        difficulty,
        language,
    )

    solution = await solve_image(
        image_bytes=image_bytes,
        mime_type=mime_type,
        question=cleaned_question,
        difficulty=difficulty,
        language=language,
    )

    return await build_response(solution, cleaned_question or "Math problem from image", language)
