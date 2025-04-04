"""Type definitions for the RootSignals MCP Server.

This module defines Pydantic models and other types used across the server.
"""

from typing import TypeVar

from pydantic import BaseModel, Field, field_validator

K = TypeVar("K")
V = TypeVar("V")


class BaseToolRequest(BaseModel):
    """Base class for all tool request models."""

    class Config:
        """Configure behavior for all request models."""

        extra = "forbid"


class ListEvaluatorsRequest(BaseToolRequest):
    """Request model for listing evaluators.

    This is an empty request as list_evaluators doesn't require any parameters.
    """

    pass


class RunEvaluationToolRequest(BaseToolRequest):
    """Request model for run_evaluation tool."""

    evaluator_id: str = Field(..., description="The ID of the evaluator to use")
    request: str = Field(..., description="The user query to evaluate")
    response: str = Field(..., description="The AI assistant's response to evaluate")

    @field_validator("request")
    @classmethod
    def validate_request_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Request cannot be empty")
        return v

    @field_validator("response")
    @classmethod
    def validate_response_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Response cannot be empty")
        return v


class RunRAGEvaluationToolRequest(RunEvaluationToolRequest):
    """Request model for run_rag_evaluation tool."""

    contexts: list[str] = Field(
        default=[], description="List of required context strings for evaluation"
    )


class UnknownToolRequest(BaseToolRequest):
    """Request model for handling unknown tools.

    This allows for capturing any parameters passed to unknown tools for debugging.
    """

    class Config:
        """Allow any fields to capture all parameters."""

        extra = "allow"


###############################################
## Simplified RootSignals Platform API models #
###############################################
class EvaluationRequest(BaseModel):
    """
    Model for evaluation request parameters.

    this is based on the EvaluatorExecutionRequest model from the RootSignals API
    but the optional fields require domain knowledge, so we'll reduce the ones we need and
    be strict about it instead.
    """

    evaluator_id: str = Field(..., description="The ID of the evaluator to use")
    request: str = Field(..., description="The user query to evaluate")
    response: str = Field(..., description="The AI assistant's response to evaluate")

    @field_validator("request")
    @classmethod
    def validate_request_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Request cannot be empty")
        return v

    @field_validator("response")
    @classmethod
    def validate_response_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Response cannot be empty")
        return v


class RAGEvaluationRequest(EvaluationRequest):
    """
    Model for faithfulness evaluation request parameters."""

    contexts: list[str] = Field(
        default=[], description="List of required context strings for evaluation"
    )


class EvaluationResponse(BaseModel):
    """
    Model for evaluation response.

    Trimmed down version of
    root.generated.openapi_aclient.models.evaluator_execution_result.EvaluatorExecutionResult
    """

    evaluator_name: str = Field(..., description="Name of the evaluator")
    score: float = Field(..., description="Evaluation score (0-1)")
    justification: str | None = Field(None, description="Justification for the score")
    execution_log_id: str | None = Field(None, description="Execution log ID for use in monitoring")
    cost: float | int | None = Field(None, description="Cost of the evaluation")


class EvaluatorInfo(BaseModel):
    """
    Model for evaluator information.

    Trimmed down version of root.generated.openapi_aclient.models.evaluator.Evaluator
    """

    name: str = Field(..., description="Name of the evaluator")
    id: str = Field(..., description="ID of the evaluator")
    created_at: str = Field(..., description="Creation timestamp of the evaluator")
    intent: str | None = Field(None, description="Intent of the evaluator")
    requires_contexts: bool | None = Field(
        False, description="Whether the evaluator requires context"
    )
    requires_expected_output: bool | None = Field(
        False, description="Whether the evaluator requires gold standard output"
    )


class EvaluatorsListResponse(BaseModel):
    """Model for evaluators list response."""

    evaluators: list[EvaluatorInfo] = Field(..., description="List of evaluators")
    count: int = Field(..., description="Number of evaluators returned")
    total: int = Field(..., description="Total number of evaluators available")
