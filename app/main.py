"""Main application entrypoint for math.gpt."""

import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.config import IS_PRODUCTION
from app.schemas import ErrorResponse
from app.exceptions import InvalidInputError, RateLimitError, AIServiceError, TooManyRequestsError
from app.image_utils import MAX_IMAGE_BYTES
from app.routes.solve import router as solve_router

# Configure basic application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application.
# API docs (/docs, /redoc) are turned off in production.
app = FastAPI(
    title="math.gpt",
    description="Web app for solving math problems using AI and recommending YouTube videos.",
    version="0.2.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)

# Determine base paths
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

# Largest request body we accept: the image limit plus 1 MB for form fields
MAX_REQUEST_BYTES = MAX_IMAGE_BYTES + 1024 * 1024

# Content Security Policy: only load files from trusted places
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self' https://cdn.jsdelivr.net",
        # KaTeX sets inline styles to position math symbols
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
        "font-src 'self' https://cdn.jsdelivr.net",
        # blob: is needed for the image preview, i.ytimg.com for YouTube thumbnails
        "img-src 'self' blob: data: https://i.ytimg.com",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

# Swagger and ReDoc pages use inline scripts, so they skip the CSP (dev only)
DOCS_PATHS = ("/docs", "/redoc")


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Reject very large request bodies before they are read."""
    if request.method == "POST":
        content_length = request.headers.get("content-length")

        if content_length is None or not content_length.isdigit():
            return JSONResponse(
                status_code=411,
                content=ErrorResponse(
                    error_code="LENGTH_REQUIRED",
                    message="Request size is missing. Please try again.",
                ).model_dump(),
            )

        if int(content_length) > MAX_REQUEST_BYTES:
            logger.warning("Rejected request: body too large (%s bytes).", content_length)
            return JSONResponse(
                status_code=413,
                content=ErrorResponse(
                    error_code="REQUEST_TOO_LARGE",
                    message="Upload is too large. Please use an image under 10 MB.",
                ).model_dump(),
            )

    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add browser security headers to every response."""
    response = await call_next(request)

    if not request.url.path.startswith(DOCS_PATHS):
        response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

    # Tell browsers to always use HTTPS (only in production, where HTTPS exists)
    if IS_PRODUCTION:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"

    return response


# Mount static folder for CSS, JS, and other static assets
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include the solve API router
app.include_router(solve_router)


# Global exception handlers returning standardized ErrorResponse
@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError):
    """Handle malformed requests (missing fields, bad options) with HTTP 422."""
    logger.warning("Request validation failed (%d errors).", len(exc.errors()))
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error_code="INVALID_REQUEST",
            message="Invalid request. Please check your question, image, and selected options.",
        ).model_dump(),
    )


@app.exception_handler(InvalidInputError)
async def invalid_input_handler(request: Request, exc: InvalidInputError):
    """Handle invalid user inputs with HTTP 400."""
    logger.warning("InvalidInputError encountered: [%s] %s", exc.error_code, exc.message)
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(error_code=exc.error_code, message=exc.message).model_dump(),
    )


@app.exception_handler(TooManyRequestsError)
async def too_many_requests_handler(request: Request, exc: TooManyRequestsError):
    """Handle users who send too many requests with HTTP 429."""
    logger.warning("TooManyRequestsError encountered: [%s]", exc.error_code)
    return JSONResponse(
        status_code=429,
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


@app.get("/health", summary="Health check", tags=["App"])
def health():
    """Health check endpoint to verify the service is running."""
    return {"status": "ok"}


@app.get("/", summary="Web app page", tags=["App"])
def read_root():
    """Serve the frontend index.html page."""
    return FileResponse(STATIC_DIR / "index.html")
