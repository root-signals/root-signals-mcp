"""RootSignals evaluator service module.

This module handles the integration with RootSignals evaluators.
"""

import logging
from typing import Any

from root import RootSignals
from root.generated.openapi_aclient.models.evaluator_execution_result import (
    EvaluatorExecutionResult,
)

from root_mcp_server.schema import (
    EvaluationRequest,
    EvaluationResponse,
    EvaluatorInfo,
    EvaluatorsListResponse,
    RAGEvaluationRequest,
)
from root_mcp_server.settings import settings

logger = logging.getLogger("root_mcp_server")


class EvaluatorService:
    """Service for interacting with RootSignals evaluators."""

    def __init__(self) -> None:
        """Initialize the evaluator service."""
        self.async_client = RootSignals(
            api_key=settings.root_signals_api_key.get_secret_value(),
            run_async=True,
        )

        self.evaluators_cache: dict[str, Any] | None = None

    async def initialize(self) -> dict[str, Any]:
        """Initialize and cache available evaluators.

        Returns:
            Dict[str, Any]: The evaluators data from RootSignals API.

        Raises:
            RuntimeError: If evaluators cannot be retrieved from the API.
        """
        logger.info("Fetching evaluators from RootSignals API...")

        try:
            evaluators_list = self.async_client.evaluators.alist()

            # Trim down upstream response for better use with llms
            evaluators_data = [
                EvaluatorInfo(
                    id=evaluator.id,
                    name=evaluator.name,
                    updated_at=evaluator.updated_at.isoformat()
                    if evaluator.updated_at
                    else "1970-01-01T00:00:00Z",
                    intent=getattr(evaluator.objective, "intent", None)
                    if hasattr(evaluator, "objective")
                    else None,
                    requires_contexts=evaluator.requires_contexts,
                    requires_expected_output=evaluator.requires_expected_output,
                )
                async for evaluator in evaluators_list
            ]

            total = len(evaluators_data)
            logger.info(f"Retrieved {total} evaluators from RootSignals API")

            self.evaluators_cache = {
                "evaluators": evaluators_data,
                "total": total,
            }

            return self.evaluators_cache

        except Exception as e:
            logger.error(f"Failed to fetch evaluators from API: {e}", exc_info=settings.debug)
            raise RuntimeError(f"Cannot initialize evaluator service: {str(e)}") from e

    async def list_evaluators(self) -> EvaluatorsListResponse:
        """List all available evaluators.

        Returns:
            EvaluatorsListResponse: A response containing all available evaluators.
        """
        if not self.evaluators_cache:
            await self.initialize()

        return EvaluatorsListResponse(
            evaluators=self.evaluators_cache["evaluators"],
            count=len(self.evaluators_cache["evaluators"]),
            total=self.evaluators_cache["total"],
        )

    async def get_evaluator_by_id(self, evaluator_id: str) -> EvaluatorInfo | None:
        """Get evaluator details by ID.

        Args:
            evaluator_id: The ID of the evaluator to retrieve.

        Returns:
            Optional[EvaluatorInfo]: The evaluator details or None if not found.
        """
        if not self.evaluators_cache:
            await self.initialize()

        for evaluator in self.evaluators_cache["evaluators"]:
            if evaluator.id == evaluator_id:
                return evaluator

        return None

    async def run_evaluation(self, request: EvaluationRequest) -> EvaluationResponse:
        """Run a standard evaluation asynchronously.

        This method is used by the SSE server which requires async operation.

        Args:
            evaluator_id: The ID of the evaluator to use.
            request: The evaluation request parameters.

        Returns:
            EvaluationResponse: The evaluation results.
        """
        try:
            evaluators_api = self.async_client.evaluators

            result: EvaluatorExecutionResult = await evaluators_api.arun(
                evaluator_id=request.evaluator_id,
                request=request.request,
                response=request.response,
            )

            return EvaluationResponse(**result.model_dump(exclude_none=True))
        except Exception as e:
            logger.error(f"Error running evaluation: {e}", exc_info=settings.debug)
            raise RuntimeError(f"Failed to run evaluation: {str(e)}") from e

    async def run_rag_evaluation(self, request: RAGEvaluationRequest) -> EvaluationResponse:
        """Run a RAG evaluation with contexts asynchronously.

        This method is used by the SSE server which requires async operation.

        Args:
            evaluator_id: The ID of the evaluator to use.
            request: The RAG evaluation request parameters.

        Returns:
            EvaluationResponse: The evaluation results.
        """
        try:
            evaluators_api = self.async_client.evaluators
            logger.debug(f"Running RAG evaluation with contexts: {request.contexts}")
            result: EvaluatorExecutionResult = await evaluators_api.arun(
                evaluator_id=request.evaluator_id,
                request=request.request,
                response=request.response,
                contexts=request.contexts,
            )

            return EvaluationResponse(**result.model_dump(exclude_none=True))
        except Exception as e:
            logger.error(f"Error running RAG evaluation: {e}", exc_info=settings.debug)
            raise RuntimeError(f"Failed to run RAG evaluation: {str(e)}") from e
