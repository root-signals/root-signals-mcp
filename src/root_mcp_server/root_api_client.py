"""RootSignals HTTP client module.

This module provides a simple httpx-based client for the RootSignals API,
replacing the official SDK with a minimal implementation for our specific needs.
"""

import logging
from datetime import datetime
from typing import Any, cast

import httpx

from root_mcp_server.schema import EvaluationResponse, EvaluatorInfo
from root_mcp_server.settings import settings

logger = logging.getLogger("root_mcp_server.root_client")


class RootSignalsAPIError(Exception):
    """Exception raised for RootSignals API errors."""

    def __init__(self, status_code: int, detail: str):
        """Initialize RootSignalsAPIError.

        Args:
            status_code: HTTP status code of the error
            detail: Error message
        """
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"RootSignals API error (HTTP {status_code}): {detail}")


class ResponseValidationError(Exception):
    """Exception raised when API response doesn't match expected schema."""

    def __init__(self, message: str, response_data: Any | None = None):
        """Initialize ResponseValidationError.

        Args:
            message: Error message
            response_data: The response data that failed validation
        """
        self.response_data = response_data
        super().__init__(f"Response validation error: {message}")


class RootSignalsApiClient:
    """HTTP client for the RootSignals API."""

    def __init__(
        self,
        api_key: str = settings.root_signals_api_key.get_secret_value(),
        base_url: str = settings.root_signals_api_url,
    ):
        """Initialize the HTTP client for RootSignals API.

        Args:
            api_key: RootSignals API key
            base_url: Base URL for the RootSignals API
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

        self.headers = {
            "Authorization": f"Api-Key {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"root-signals-mcp/{settings.version}",
        }

        logger.debug(
            f"Initialized RootSignals API client with User-Agent: {self.headers['User-Agent']}"
        )

    async def _make_request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        """Make an HTTP request to the RootSignals API.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            params: URL parameters
            json_data: JSON body data for POST/PUT requests

        Returns:
            Response data as a dictionary or list

        Raises:
            RootSignalsAPIError: If the API returns an error
        """
        url = f"{self.base_url}/{path.lstrip('/')}"

        logger.debug(f"Making {method} request to {url}")
        if settings.debug:
            logger.debug(f"Request headers: {self.headers}")
            if params:
                logger.debug(f"Request params: {params}")
            if json_data:
                logger.debug(f"Request payload: {json_data}")

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                    headers=self.headers,
                    timeout=settings.root_signals_api_timeout,
                )

                logger.debug(f"Response status: {response.status_code}")
                if settings.debug:
                    logger.debug(f"Response headers: {dict(response.headers)}")

                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        error_message = error_data.get("detail", str(error_data))
                    except Exception:
                        error_message = response.text or f"HTTP {response.status_code}"

                    logger.error(f"API error response: {error_message}")
                    raise RootSignalsAPIError(response.status_code, error_message)

                if response.status_code == 204:
                    return {}

                response_data = response.json()
                if settings.debug:
                    logger.debug(f"Response data: {response_data}")
                return response_data

            except httpx.RequestError as e:
                logger.error(f"Request error: {str(e)}")
                raise RootSignalsAPIError(0, f"Connection error: {str(e)}")

    async def list_evaluators(self) -> list[EvaluatorInfo]:
        """List all available evaluators.

        Returns:
            List of evaluator information

        Raises:
            ResponseValidationError: If a required field is missing in any evaluator
        """
        response = await self._make_request("GET", "/v1/evaluators")

        logger.info(f"Raw evaluators response: {response}")

        evaluators_raw: list[dict[str, Any]] = []

        if isinstance(response, dict):
            for key in ["results", "evaluators", "data", "items"]:
                if key in response and isinstance(response[key], list):
                    logger.info(f"Found evaluators in '{key}' field")
                    evaluators_raw = response[key]
                    break
            else:
                raise ResponseValidationError(
                    "Could not find evaluators list in response", response
                )
        elif isinstance(response, list):
            logger.info("Response is a list, using directly")
            evaluators_raw = response
        else:
            raise ResponseValidationError(
                f"Expected response to be a dict or list, got {type(response).__name__}",
                cast(dict[str, Any], response),
            )

        logger.info(f"Found {len(evaluators_raw)} evaluators")

        evaluators = []
        for i, evaluator_data in enumerate(evaluators_raw):
            try:
                logger.debug(f"Processing evaluator {i}: {evaluator_data}")

                for field in [
                    "id",
                    "name",
                    "created_at",
                    "updated_at",
                    "requires_contexts",
                    "requires_expected_output",
                ]:
                    if field not in evaluator_data:
                        raise KeyError(field)

                if "created_at" in evaluator_data:
                    created_at = evaluator_data["created_at"]
                    if isinstance(created_at, datetime):
                        created_at = created_at.isoformat()
                else:
                    raise KeyError("created_at")

                intent = None
                if "objective" in evaluator_data and isinstance(evaluator_data["objective"], dict):
                    objective = evaluator_data["objective"]
                    intent = objective.get("intent")

                if "requires_contexts" not in evaluator_data:
                    raise KeyError("requires_contexts")
                if "requires_expected_output" not in evaluator_data:
                    raise KeyError("requires_expected_output")

                evaluator = EvaluatorInfo(
                    id=evaluator_data["id"],
                    name=evaluator_data["name"],
                    created_at=created_at,
                    intent=intent,
                    requires_contexts=evaluator_data["requires_contexts"],
                    requires_expected_output=evaluator_data["requires_expected_output"],
                )
                evaluators.append(evaluator)
            except KeyError as e:
                missing_field = str(e).strip("'")
                logger.warning(f"Evaluator at index {i} missing required field: '{missing_field}'")
                logger.warning(f"Evaluator data: {evaluator_data}")
                raise ResponseValidationError(
                    f"Evaluator at index {i} missing required field: '{missing_field}'",
                    evaluator_data,
                )

        return evaluators

    async def run_evaluator(
        self,
        evaluator_id: str,
        request: str,
        response: str,
        contexts: list[str] | None = None,
        expected_output: str | None = None,
    ) -> EvaluationResponse:
        """Run an evaluation with the specified evaluator.

        Args:
            evaluator_id: ID of the evaluator to use
            request: User query/request to evaluate
            response: Model's response to evaluate
            contexts: Optional list of context passages for RAG evaluations
            expected_output: Optional expected output for reference-based evaluations

        Returns:
            Evaluation response with score and justification

        Raises:
            ResponseValidationError: If the response is missing required fields
        """
        payload: dict[str, Any] = {
            "request": request,
            "response": response,
        }

        if contexts:
            payload["contexts"] = contexts

        if expected_output:
            payload["expected_output"] = expected_output

        response_data = await self._make_request(
            "POST", f"/v1/evaluators/execute/{evaluator_id}/", json_data=payload
        )

        if not isinstance(response_data, dict):
            raise ResponseValidationError(
                f"Expected response to be a dict, got {type(response_data).__name__}", response_data
            )

        logger.info(f"Raw evaluation response: {response_data}")

        if "result" in response_data and isinstance(response_data["result"], dict):
            result_data = response_data["result"]
        else:
            result_data = response_data

        required_fields = ["evaluator_name", "score"]
        missing_fields = [field for field in required_fields if field not in result_data]

        if missing_fields:
            raise ResponseValidationError(
                f"Missing required fields in evaluation response: {', '.join(missing_fields)}",
                result_data,
            )

        score = result_data["score"]
        if not isinstance(score, int | float):
            raise ResponseValidationError(
                f"Expected 'score' to be a number, got {type(score).__name__}", result_data
            )

        return EvaluationResponse(
            evaluator_name=result_data["evaluator_name"],
            score=score,
            justification=result_data.get("justification"),
            execution_log_id=result_data.get("execution_log_id"),
            cost=result_data.get("cost"),
        )
