"""Main application entrypoint for Math Solver."""

import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.schemas import ErrorResponse
from app.exceptions import InvalidInputError, RateLimitError, AIServiceError
from app.routes.solve import router as solve_router

# Configure basic application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="Math Solver",
    description="Web app for solving math problems using AI and recommending YouTube videos.",
    version="0.1.0",
)

# Determine base paths
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

# Mount static folder for CSS, JS, and other static assets
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include the solve API router
app.include_router(solve_router)


# Global exception handlers returning standardized ErrorResponse
@app.exception_handler(InvalidInputError)
async def invalid_input_handler(request: Request, exc: InvalidInputError):
    """Handle invalid user inputs with HTTP 400."""
    logger.warning("InvalidInputError encountered: [%s] %s", exc.error_code, exc.message)
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(error_code=exc.error_code, message=exc.message).model_dump(),
    )


@app.exception_handler(RateLimitError)
async def rate_limit_handler(request: Request, exc: RateLimitError):
    """Handle API rate limit exceeded with HTTP 429."""
    logger.warning("RateLimitError encountered: [%s]", exc.error_code)
    return JSONResponse(
        status_code=429,
        content=ErrorResponse(error_code=exc.error_code, message=exc.message).model_dump(),
    )


@app.exception_handler(AIServiceError)
async def ai_service_error_handler(request: Request, exc: AIServiceError):
    """Handle AI backend failures with HTTP 500 without leaking keys or stack traces."""
    logger.error("AIServiceError encountered: [%s]", exc.error_code)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error_code=exc.error_code, message=exc.message).model_dump(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected server errors securely without leaking internal details."""
    logger.error("Unhandled server exception: %s", type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred. Please try again later.",
        ).model_dump(),
    )


@app.get("/health")
def health():
    """Health check endpoint to verify the service is running."""
    return {"status": "ok"}


@app.get("/")
def read_root():
    """Serve the frontend index.html page."""
    return FileResponse(STATIC_DIR / "index.html")
