"""Type definitions for the RootSignals MCP Server.

This module defines Pydantic models and other types used across the server.
"""

import time
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, field_validator

from settings import settings

K = TypeVar("K")
V = TypeVar("V")


class EvaluationRequest(BaseModel):
    """Model for evaluation request parameters."""

    query: str = Field(..., description="The user query to evaluate")
    response: str = Field(..., description="The AI assistant's response to evaluate")

    @field_validator("query")
    @classmethod
    def validate_query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v

    @field_validator("response")
    @classmethod
    def validate_response_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Response cannot be empty")
        return v


class RAGEvaluationRequest(EvaluationRequest):
    """Model for faithfulness evaluation request parameters."""

    contexts: list[str] | None = Field(
        default=None, description="List of required context strings for evaluation"
    )


class EvaluationResponse(BaseModel):
    """Model for evaluation response."""

    score: float = Field(..., description="Evaluation score (0-1)")
    explanation: str | None = Field(None, description="Explanation of the evaluation")
    justification: str | None = Field(None, description="Justification for the score")
    analysis: str | None = Field(None, description="Detailed analysis of the response")
    rating: str | None = Field(None, description="Qualitative rating of the response")
    feedback: str | None = Field(None, description="Feedback on the response")
    details: dict[str, Any] | None = Field(None, description="Additional details")
    reasoning: str | None = Field(None, description="Reasoning behind the evaluation")


class EvaluatorInfo(BaseModel):
    """Model for evaluator information."""

    name: str = Field(..., description="Name of the evaluator")
    id: str = Field(..., description="ID of the evaluator")
    version_id: str = Field(..., description="Version ID of the evaluator")
    models: list[str] = Field(..., description="List of models supported by the evaluator")
    intent: str | None = Field(None, description="Intent of the evaluator")
    requires_context: bool | None = Field(
        False, description="Whether the evaluator requires context"
    )


class EvaluatorsListResponse(BaseModel):
    """Model for evaluators list response."""

    evaluators: list[EvaluatorInfo] = Field(..., description="List of evaluators")
    count: int = Field(..., description="Number of evaluators returned")
    total: int = Field(..., description="Total number of evaluators available")

