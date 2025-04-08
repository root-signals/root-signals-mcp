"""RootSignals evaluator service module.

This module handles the integration with RootSignals evaluators.
"""

import logging

from root_mcp_server.root_api_client import (
    ResponseValidationError,
    RootSignalsApiClient,
    RootSignalsAPIError,
)
from root_mcp_server.schema import (
    EvaluationRequest,
    EvaluationResponse,
    EvaluatorInfo,
    EvaluatorsListResponse,
    RAGEvaluationRequest,
)
from root_mcp_server.settings import settings

logger = logging.getLogger("root_mcp_server.evaluator")


class EvaluatorService:
    """Service for interacting with RootSignals evaluators."""

    def __init__(self) -> None:
        """Initialize the evaluator service."""
        self.async_client = RootSignalsApiClient(
            api_key=settings.root_signals_api_key.get_secret_value(),
            base_url=settings.root_signals_api_url,
        )

    async def fetch_evaluators(self) -> list[EvaluatorInfo]:
        """Fetch available evaluators from the API.

        Returns:
            List[EvaluatorInfo]: List of evaluator information.

        Raises:
            RuntimeError: If evaluators cannot be retrieved from the API.
        """
        logger.info("Fetching evaluators from RootSignals API...")

        try:
            evaluators_data = await self.async_client.list_evaluators()

            total = len(evaluators_data)
            logger.info(f"Retrieved {total} evaluators from RootSignals API")

            return evaluators_data

        except RootSignalsAPIError as e:
            logger.error(f"Failed to fetch evaluators from API: {e}", exc_info=settings.debug)
            raise RuntimeError(f"Cannot fetch evaluators: {str(e)}") from e
        except ResponseValidationError as e:
            logger.error(f"Response validation error: {e}", exc_info=settings.debug)
            if e.response_data:
                logger.debug(f"Response data: {e.response_data}")
            raise RuntimeError(f"Invalid evaluators response: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error fetching evaluators: {e}", exc_info=settings.debug)
            raise RuntimeError(f"Cannot fetch evaluators: {str(e)}") from e

    async def list_evaluators(self) -> EvaluatorsListResponse:
        """List all available evaluators.

        Returns:
            EvaluatorsListResponse: A response containing all available evaluators.
        """
        evaluators = await self.fetch_evaluators()

        return EvaluatorsListResponse(
            evaluators=evaluators,
            count=len(evaluators),
            total=len(evaluators),
        )

    async def get_evaluator_by_id(self, evaluator_id: str) -> EvaluatorInfo | None:
        """Get evaluator details by ID.

        Args:
            evaluator_id: The ID of the evaluator to retrieve.

        Returns:
            Optional[EvaluatorInfo]: The evaluator details or None if not found.
        """
        evaluators = await self.fetch_evaluators()

        for evaluator in evaluators:
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
            result = await self.async_client.run_evaluator(
                evaluator_id=request.evaluator_id,
                request=request.request,
                response=request.response,
            )

            return result
        except RootSignalsAPIError as e:
            logger.error(f"API error running evaluation: {e}", exc_info=settings.debug)
            raise RuntimeError(f"Failed to run evaluation: {str(e)}") from e
        except ResponseValidationError as e:
            logger.error(f"Response validation error: {e}", exc_info=settings.debug)
            if e.response_data:
                logger.debug(f"Response data: {e.response_data}")
            raise RuntimeError(f"Invalid evaluation response: {str(e)}") from e
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
            logger.debug(f"Running RAG evaluation with contexts: {request.contexts}")
            result = await self.async_client.run_evaluator(
                evaluator_id=request.evaluator_id,
                request=request.request,
                response=request.response,
                contexts=request.contexts,
            )

            return result
        except RootSignalsAPIError as e:
            logger.error(f"API error running RAG evaluation: {e}", exc_info=settings.debug)
            raise RuntimeError(f"Failed to run RAG evaluation: {str(e)}") from e
        except ResponseValidationError as e:
            logger.error(f"Response validation error: {e}", exc_info=settings.debug)
            if e.response_data:
                logger.debug(f"Response data: {e.response_data}")
            raise RuntimeError(f"Invalid RAG evaluation response: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error running RAG evaluation: {e}", exc_info=settings.debug)
            raise RuntimeError(f"Failed to run RAG evaluation: {str(e)}") from e
