"""Tool catalogue for the RootSignals MCP server."""

from __future__ import annotations

from mcp.types import Tool

from root_signals_mcp.schema import (
    CodingPolicyAdherenceEvaluationRequest,
    EvaluationRequest,
    EvaluationRequestByName,
    ListEvaluatorsRequest,
    RAGEvaluationByNameRequest,
    RAGEvaluationRequest,
)


def get_tools() -> list[Tool]:
    """Return the list of MCP *tools* supported by RootSignals."""

    return [
        Tool(
            name="list_evaluators",
            description="List all available evaluators from RootSignals",
            inputSchema=ListEvaluatorsRequest.model_json_schema(),
        ),
        Tool(
            name="run_evaluation",
            description="Run a standard evaluation using a RootSignals evaluator by ID",
            inputSchema=EvaluationRequest.model_json_schema(),
        ),
        Tool(
            name="run_rag_evaluation",
            description="Run a RAG evaluation with contexts using a RootSignals evaluator by ID",
            inputSchema=RAGEvaluationRequest.model_json_schema(),
        ),
        Tool(
            name="run_evaluation_by_name",
            description="Run a standard evaluation using a RootSignals evaluator by name",
            inputSchema=EvaluationRequestByName.model_json_schema(),
        ),
        Tool(
            name="run_rag_evaluation_by_name",
            description="Run a RAG evaluation with contexts using a RootSignals evaluator by name",
            inputSchema=RAGEvaluationByNameRequest.model_json_schema(),
        ),
        Tool(
            name="run_coding_policy_adherence",
            description="Evaluate code against repository coding policy documents using a dedicated RootSignals evaluator",
            inputSchema=CodingPolicyAdherenceEvaluationRequest.model_json_schema(),
        ),
    ]


def get_request_model(tool_name: str):
    """Return the Pydantic *request* model class for a given tool.

    This is useful for validating the *arguments* dict passed to
    MCP-`call_tool` before dispatching.
    Returns ``None`` if the name is unknown; caller can then fall back to
    a generic model or raise.
    """

    mapping: dict[str, type] = {
        "list_evaluators": ListEvaluatorsRequest,
        "run_evaluation": EvaluationRequest,
        "run_rag_evaluation": RAGEvaluationRequest,
        "run_evaluation_by_name": EvaluationRequestByName,
        "run_rag_evaluation_by_name": RAGEvaluationByNameRequest,
        "run_coding_policy_adherence": CodingPolicyAdherenceEvaluationRequest,
    }

    return mapping.get(tool_name)
