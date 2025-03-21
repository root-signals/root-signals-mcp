"""MCP server implementation for RootSignals evaluators.

This module provides a Model Context Protocol server that exposes
RootSignals evaluators as tools.
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List

from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from pydantic import ValidationError

from root_mcp_server.evaluator import EvaluatorService
from root_mcp_server.settings import settings
from root_mcp_server.schema import EvaluationRequest, RAGEvaluationRequest


logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("root_mcp_server")


class MCPServer:
    """Model Context Protocol server for RootSignals evaluators."""

    def __init__(self) -> None:
        """Initialize the MCP server."""
        self.evaluator_service = EvaluatorService()
        self.app = Server("RootSignals Evaluators")
        
        # Register tool handlers with MCP server using decorators
        @self.app.list_tools()
        async def list_tools() -> List[Tool]:
            return await self.list_tools()
            
        @self.app.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            return await self.call_tool(name, arguments)
        
        # Store the function handlers internally
        self.function_map = {
            "list_evaluators": self._handle_list_evaluators,
            "run_evaluation": self._handle_run_evaluation,
            "run_rag_evaluation": self._handle_run_rag_evaluation,
        }

    async def initialize(self) -> None:
        """Initialize the server and required services."""
        logger.info("Initializing MCP server...")
        await self.evaluator_service.initialize()
        logger.info("MCP server initialized successfully")
    
    async def list_tools(self) -> List[Tool]:
        """List available tools for the MCP server.
        
        This function is called by the MCP protocol to get the list of available tools.
        
        Returns:
            List[Tool]: A list of tool definitions.
        """
        return [
            Tool(
                name="list_evaluators",
                description="List all available evaluators from RootSignals",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                }
            ),
            Tool(
                name="run_evaluation",
                description="Run a standard evaluation using a RootSignals evaluator",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "evaluator_id": {
                            "type": "string", 
                            "description": "ID of the evaluator to use"
                        },
                        "query": {
                            "type": "string",
                            "description": "The user query to evaluate"
                        },
                        "response": {
                            "type": "string",
                            "description": "The AI assistant's response to evaluate"
                        },
                    },
                    "required": ["evaluator_id", "query", "response"],
                }
            ),
            Tool(
                name="run_rag_evaluation",
                description="Run a RAG evaluation with contexts using a RootSignals evaluator",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "evaluator_id": {
                            "type": "string", 
                            "description": "ID of the evaluator to use"
                        },
                        "query": {
                            "type": "string",
                            "description": "The user query to evaluate"
                        },
                        "response": {
                            "type": "string",
                            "description": "The AI assistant's response to evaluate"
                        },
                        "contexts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of context strings for RAG evaluation"
                        },
                    },
                    "required": ["evaluator_id", "query", "response"],
                }
            )
        ]
        
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Call a tool by name with the given arguments.
        
        This function is called by the MCP protocol to execute a tool.
        
        Args:
            name: The name of the tool to call
            arguments: The arguments to pass to the tool
            
        Returns:
            List[TextContent]: The result of the tool execution formatted as text content
        """
        logger.debug(f"Tool call: {name}, arguments: {arguments}")
        
        # Find the handler for this tool
        handler = self.function_map.get(name)
        if not handler:
            logger.warning(f"Unknown tool: {name}")
            error_result = {"error": f"Unknown tool: {name}"}
            return [TextContent(type="text", text=json.dumps(error_result))]
            
        # Execute the handler
        try:
            result = await handler(arguments)
            # Convert the result to TextContent
            return [TextContent(type="text", text=json.dumps(result))]
        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}", exc_info=settings.debug)
            error_result = {"error": f"Error calling tool {name}: {e}"}
            return [TextContent(type="text", text=json.dumps(error_result))]

    async def _handle_list_evaluators(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle list_evaluators tool call.

        Args:
            params: The tool parameters (empty for this tool).
            
        Returns:
            Dict[str, Any]: The evaluators list response.
        """
        logger.debug("Handling list_evaluators request")
        response = await self.evaluator_service.list_evaluators()
        return response.model_dump(exclude_none=True)

    async def _handle_run_evaluation(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle run_evaluation tool call.
        
        Args:
            params: The tool parameters containing evaluator_id, query, and response.
            
        Returns:
            Dict[str, Any]: The evaluation response.
        """
        logger.debug(f"Handling run_evaluation request: {params}")
        
        try:
            evaluator_id = params.pop("evaluator_id", None)
            if not evaluator_id:
                return {"error": "evaluator_id is required"}
            
            # Validate request using Pydantic
            request = EvaluationRequest(**params)
            
            # Check if evaluator exists
            evaluator = await self.evaluator_service.get_evaluator_by_id(evaluator_id)
            if not evaluator:
                return {"error": f"Evaluator with ID '{evaluator_id}' not found"}
            
            # Run evaluation
            response = await self.evaluator_service.run_evaluation(evaluator_id, request)
            return response.model_dump(exclude_none=True)
        
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return {"error": f"Validation error: {e}"}
        except Exception as e:
            logger.error(f"Error running evaluation: {e}", exc_info=True)
            return {"error": f"Error running evaluation: {e}"}

    async def _handle_run_rag_evaluation(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle run_rag_evaluation tool call.
        
        Args:
            params: The tool parameters containing evaluator_id, query, response, and contexts.
            
        Returns:
            Dict[str, Any]: The evaluation response.
        """
        logger.debug(f"Handling run_rag_evaluation request: {params}")
        
        try:
            evaluator_id = params.pop("evaluator_id", None)
            if not evaluator_id:
                return {"error": "evaluator_id is required"}
            
            # Validate request using Pydantic
            request = RAGEvaluationRequest(**params)
            
            # Check if evaluator exists
            evaluator = await self.evaluator_service.get_evaluator_by_id(evaluator_id)
            if not evaluator:
                return {"error": f"Evaluator with ID '{evaluator_id}' not found"}
            
            # Check if evaluator requires context
            requires_context = evaluator.get("requires_context", False)
            if requires_context and not request.contexts:
                return {"error": "This evaluator requires context, but none was provided"}
            
            # Run evaluation
            response = await self.evaluator_service.run_rag_evaluation(evaluator_id, request)
            return response.model_dump(exclude_none=True)
        
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return {"error": f"Validation error: {e}"}
        except Exception as e:
            logger.error(f"Error running RAG evaluation: {e}", exc_info=True)
            return {"error": f"Error running RAG evaluation: {e}"}

    async def start(self) -> None:
        """Start the MCP server."""
        logger.info("Starting MCP server...")
        await self.initialize()
        
        logger.info("MCP server initialized, starting stdio transport...")
        
        # Use the MCP stdio server
        async with stdio_server() as streams:
            await self.app.run(
                streams[0], 
                streams[1], 
                self.app.create_initialization_options()
            )