"""Route handlers for math problem solving endpoints."""

import logging
from fastapi import APIRouter
from app.schemas import SolveRequest, SolveResponse
from app.exceptions import InvalidInputError
from app.services.ai_service import solve_text

# Module logger
logger = logging.getLogger(__name__)

router = APIRouter()

# Input length limit
MAX_PROBLEM_LENGTH = 2000


@router.post("/solve", response_model=SolveResponse)
async def solve(request: SolveRequest):
    """Receive a math question and return a step-by-step solution.

    Day 3 accepts text requests structured via SolveRequest with configurable
    difficulty ('simple' or 'detailed') and language ('english' or 'hinglish').
    """
    raw_question = request.question

    # Validate empty input
    if not raw_question or not raw_question.strip():
        logger.warning("Rejected request: Empty math question.")
        raise InvalidInputError("Math question cannot be empty. Please enter a problem to solve.", error_code="EMPTY_INPUT")

    cleaned_question = raw_question.strip()

    # Validate input length limit
    if len(cleaned_question) > MAX_PROBLEM_LENGTH:
        logger.warning(
            "Rejected request: Question length (%d) exceeded limit (%d).",
            len(cleaned_question),
            MAX_PROBLEM_LENGTH,
        )
        raise InvalidInputError(
            f"Math question is too long. Please keep your question under {MAX_PROBLEM_LENGTH} characters.",
            error_code="INPUT_TOO_LONG",
        )

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

    return SolveResponse(
        problem=solution.problem or cleaned_question,
        steps=solution.steps,
        final_answer=solution.final_answer,
        topic=solution.topic or "Mathematics",
        search_query=solution.search_query or "math tutorial",
        videos=[],  # Video recommendations will be populated in Day 4
    )
