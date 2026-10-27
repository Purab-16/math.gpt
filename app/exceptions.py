"""Custom domain exceptions for the math.gpt application."""


class InvalidInputError(Exception):
    """Raised when user input fails validation (empty, too long, non-math question)."""

    def __init__(self, message: str, error_code: str = "INVALID_INPUT"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class AIServiceError(Exception):
    """Raised when the AI model fails to process or return a valid response."""

    def __init__(
        self,
        message: str = "Unable to solve the problem at this moment. Please try again later.",
        error_code: str = "AI_SERVICE_ERROR",
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class TooManyRequestsError(Exception):
    """Raised when one user (IP address) sends too many solve requests."""

    def __init__(
        self,
        message: str = "Too many requests. Please wait a minute and try again.",
        error_code: str = "TOO_MANY_REQUESTS",
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class RateLimitError(AIServiceError):
    """Raised when the Gemini API free-tier rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Google Gemini rate limit reached (5 requests/min). Please wait 30-60 seconds before trying again.",
        error_code: str = "RATE_LIMIT_EXCEEDED",
    ):
        super().__init__(message=message, error_code=error_code)
