"""Type definitions for the RootSignals MCP Server.

This module defines Pydantic models and other types used across the server.
"""

from typing import TypeVar

from pydantic import BaseModel, Field, field_validator

K = TypeVar("K")
V = TypeVar("V")


class BaseToolRequest(BaseModel):
    """Base class for all tool request models."""

    model_config = {
        "extra": "forbid",
        "validate_assignment": True,
    }


class ListEvaluatorsRequest(BaseToolRequest):
    """Request model for listing evaluators.

    This is an empty request as list_evaluators doesn't require any parameters.
    """

    pass


#####################################################################
### Implementation specific models                                ###
#####################################################################


class UnknownToolRequest(BaseToolRequest):
    """Request model for handling unknown tools.

    This allows for capturing any parameters passed to unknown tools for debugging.
    """

    model_config = {
        "extra": "allow",  # Allow any fields for debugging purposes
    }


class BaseRootSignalsModel(BaseModel):
    """Base class for all models that interact with the RootSignals API.

    This class sets up handling of schema evolution to:
    1. Ignore new fields that might be added to the API in the future
    2. Still fail if expected fields are removed from the API response
    """

    model_config = {
        "extra": "ignore",
        "strict": True,
        "validate_assignment": True,
    }


#####################################################################
### LLM Facing Models                                             ###
### Make sure to add good descriptions and examples, where needed ###
#####################################################################


class BaseEvaluationRequest(BaseRootSignalsModel):
    """Fields common to all evaluation requests."""

    request: str = Field(..., description="The user query to evaluate")
    response: str = Field(..., description="The AI assistant's response to evaluate")

    @field_validator("request", "response")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:  # noqa: D401 – short
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v


class EvaluationRequestByName(BaseEvaluationRequest):
    """
    Model for evaluation request parameters.

    this is based on the EvaluatorExecutionRequest model from the RootSignals API
    """

    evaluator_name: str = Field(
        ...,
        description="The EXACT name of the evaluator as returned by the `list_evaluators` tool, including spaces and special characters",
        examples=[
            "Compliance-preview",
            "Truthfulness - Global",
            "Safety for Children",
            "Context Precision",
        ],
    )
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


class EvaluationRequest(BaseEvaluationRequest):
    """
    Model for evaluation request parameters.

    this is based on the EvaluatorExecutionRequest model from the RootSignals API
    """

    evaluator_id: str = Field(..., description="The ID of the evaluator to use")


class RAGEvaluationRequest(EvaluationRequest):
    """
    Model for RAG evaluators that require contexts to be sent"""

    contexts: list[str] = Field(
        default=[], description="List of required context strings for evaluation"
    )


class RAGEvaluationByNameRequest(EvaluationRequestByName):
    """
    Model for RAG evaluators that require contexts to be sent"""

    contexts: list[str] = Field(
        default=[], description="List of required context strings for evaluation"
    )


class CodingPolicyAdherenceEvaluationRequest(BaseToolRequest):
    """Request model for coding policy adherence evaluation tool."""

    policy_documents: list[str] = Field(
        ...,
        description="The policy documents which describe the coding policy, such as cursor/rules file contents",
    )
    code: str = Field(..., description="The code to evaluate")


#####################################################################
### Simplified RootSignals Platform API models                    ###
### We trim them down to save tokens                              ###
#####################################################################
class EvaluationResponse(BaseRootSignalsModel):
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


class EvaluatorInfo(BaseRootSignalsModel):
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


class EvaluatorsListResponse(BaseRootSignalsModel):
    """Model for evaluators list response."""

    evaluators: list[EvaluatorInfo] = Field(..., description="List of evaluators")
    count: int = Field(..., description="Number of evaluators returned")
