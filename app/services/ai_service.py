"""AI Service module for solving math questions using Google Gemini API."""

import json
import logging
import re
from typing import Optional
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from pydantic import ValidationError

from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.schemas import GeminiMathSolution
from app.exceptions import InvalidInputError, RateLimitError, AIServiceError

# Initialize module logger
logger = logging.getLogger(__name__)


def build_system_prompt(difficulty: str = "simple", language: str = "english") -> str:
    """Build a customized system instruction incorporating difficulty and language preferences.

    Args:
        difficulty: Level of detail ('simple' or 'detailed').
        language: Response language ('english' or 'hinglish').

    Returns:
        str: Formatted system instruction for the Gemini model.
    """
    prompt_parts = [
        "You are a friendly and helpful math tutor.",
        "Use LaTeX notation for all mathematical formulas, equations, and variables (e.g., $2x + 5 = 15$).",
        "If the user input is not a math question, do not attempt to guess or answer it. "
        "Instead, set the 'error' field with a clear explanation that the input is not a math question, "
        "and leave other fields empty.",
    ]

    # Difficulty instruction
    if difficulty.strip().lower() == "detailed":
        prompt_parts.append(
            "Detail level: DETAILED. Provide an in-depth step-by-step explanation, "
            "explaining the mathematical reasoning and rules behind each transformation."
        )
    else:
        prompt_parts.append(
            "Detail level: SIMPLE. Provide clear, direct, and concise steps without excessive explanation."
        )

    # Language instruction
    if language.strip().lower() == "hinglish":
        prompt_parts.append(
            "Language: HINGLISH. Explain the solution steps in Hinglish (a natural, conversational blend "
            "of Hindi and English in Latin script, e.g., 'Pehle dono sides se 5 subtract karein')."
        )
    else:
        prompt_parts.append("Language: ENGLISH. Explain the solution steps in clear, plain English.")

    return "\n".join(prompt_parts)


async def solve_text(
    question: str,
    difficulty: str = "simple",
    language: str = "english",
) -> GeminiMathSolution:
    """Solve a text-based math question using the Gemini API.

    Args:
        question: The math problem text provided by the user.
        difficulty: 'simple' or 'detailed' explanation mode.
        language: 'english' or 'hinglish'.

    Returns:
        GeminiMathSolution: Pydantic model with problem, steps, final_answer, topic,
                           search_query, and optional error.

    Raises:
        InvalidInputError: If the model determines the input is not a math question.
        RateLimitError: If Google Gemini rate limit (429) is hit.
        AIServiceError: If configuration is missing or model fails after retry.
    """
    if not GEMINI_API_KEY:
        logger.error("Gemini API key is not configured.")
        raise AIServiceError("Gemini API key is missing. Please configure it in server settings.")

    if not GEMINI_MODEL:
        logger.error("Gemini model name is not configured.")
        raise AIServiceError("Gemini model is missing. Please configure it in server settings.")

    # Initialize Gemini client
    client = genai.Client(api_key=GEMINI_API_KEY)

    system_prompt = build_system_prompt(difficulty=difficulty, language=language)

    # Configure structured JSON output with response schema
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=GeminiMathSolution,
        system_instruction=system_prompt,
        temperature=0.1,
    )

    max_attempts = 2
    last_error: Optional[Exception] = None

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(
                "Calling Gemini API (attempt %d of %d, difficulty: %s, language: %s)",
                attempt,
                max_attempts,
                difficulty,
                language,
            )

            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=question,
                config=config,
            )

            raw_text = response.text
            if not raw_text:
                raise AIServiceError("Empty response received from the AI model.")

            # Clean markdown code block fences if present
            clean_text = raw_text.strip()
            if clean_text.startswith("```"):
                clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
                clean_text = re.sub(r"\s*```$", "", clean_text)

            # Parse JSON
            data = json.loads(clean_text)

            # Validate against Pydantic schema
            solution = GeminiMathSolution.model_validate(data)

            # Check if model detected a non-math question
            if solution.error and solution.error.strip():
                logger.info("Model classified question as non-math.")
                raise InvalidInputError(
                    message=solution.error.strip(),
                    error_code="NON_MATH_INPUT",
                )

            logger.info("Successfully solved math problem on attempt %d.", attempt)
            return solution

        except ClientError as err:
            err_str = str(err)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                logger.warning("Gemini API free-tier rate limit exceeded (429).")
                raise RateLimitError() from err
            logger.error("Client error from Gemini API: %s", type(err).__name__)
            last_error = err

        except (json.JSONDecodeError, ValidationError) as err:
            logger.warning(
                "JSON/Schema validation failed on attempt %d of %d: %s",
                attempt,
                max_attempts,
                type(err).__name__,
            )
            last_error = err

        except InvalidInputError:
            # Re-raise user validation error immediately without retry
            raise

        except Exception as err:
            logger.error("Error occurred while contacting Gemini API: %s", type(err).__name__)
            last_error = err

    logger.error("Exhausted all %d attempts to obtain a valid solution.", max_attempts)
    raise AIServiceError("Failed to obtain a valid math solution after retry.") from last_error
