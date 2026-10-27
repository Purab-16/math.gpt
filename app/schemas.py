"""Pydantic schemas for data validation and API response formatting."""

from typing import List, Optional
from pydantic import BaseModel, Field


class SolveRequest(BaseModel):
    """Schema representing the math solving request input."""

    question: str = Field(..., description="The math problem text to solve")
    difficulty: str = Field(default="simple", description="Explanation detail level: 'simple' or 'detailed'")
    language: str = Field(default="english", description="Explanation language: 'english' or 'hinglish'")


class ErrorResponse(BaseModel):
    """Schema representing a standardized error response."""

    error_code: str = Field(..., description="Machine-readable error identifier")
    message: str = Field(..., description="Human-readable error description")


class VideoItem(BaseModel):
    """Schema representing an educational video recommendation."""

    title: str
    url: str
    thumbnail: str


class SolveResponse(BaseModel):
    """Schema representing a complete math solution response."""

    problem: str
    steps: List[str]
    final_answer: str
    topic: str
    search_query: str
    videos: List[VideoItem]


class GeminiMathSolution(BaseModel):
    """Schema representing structured JSON output from Gemini."""

    problem: str = ""
    steps: List[str] = []
    final_answer: str = ""
    topic: str = ""
    search_query: str = ""
    error: Optional[str] = None
