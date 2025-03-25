# RootSignals MCP Server

A Model Context Protocol (MCP) server that exposes RootSignals evaluators as tools for AI assistants.

## Overview

This project implements an MCP server that allows AI assistants to use RootSignals evaluators as tools. 
It provides a bridge between the RootSignals API and MCP client applications, allowing AI assistants 
to evaluate responses against various quality criteria.

## Features

- Exposes RootSignals evaluators as MCP tools
- Supports both standard evaluation and RAG evaluation with contexts
- Implements sse
- Compatible with various MCP clients
- Docker-ready for containerized deployment

## Tools

The server exposes the following tools:

1. `list_evaluators` - Lists all available evaluators from RootSignals
2. `run_evaluation` - Runs a standard evaluation using a specified evaluator
3. `run_rag_evaluation` - Runs a RAG evaluation with contexts using a specified evaluator

## Usage

Start the docker container  

```bash
docker run -e ROOT_SIGNALS_API_KEY=<your_key> -p 0.0.0.0:9090:9090 -name=rs-mcp -d ghcr.io/root-signals/root-signals-mcp:latest
```

You should see some logs
```bash
docker logs rs-mcp
2025-03-25 12:03:24,167 - root_mcp_server.sse - INFO - Starting RootSignals MCP Server v0.1.0
2025-03-25 12:03:24,167 - root_mcp_server.sse - INFO - Environment: development
2025-03-25 12:03:24,167 - root_mcp_server.sse - INFO - Transport: stdio
2025-03-25 12:03:24,167 - root_mcp_server.sse - INFO - Host: 0.0.0.0, Port: 9090
2025-03-25 12:03:24,168 - root_mcp_server.sse - INFO - Initializing MCP server...
2025-03-25 12:03:24,168 - root_mcp_server - INFO - Fetching evaluators from RootSignals API...
2025-03-25 12:03:25,627 - root_mcp_server - INFO - Retrieved 100 evaluators from RootSignals API
2025-03-25 12:03:25,627 - root_mcp_server.sse - INFO - MCP server initialized successfully
2025-03-25 12:03:25,628 - root_mcp_server.sse - INFO - SSE server listening on http://0.0.0.0:9090/sse
```

From all other clients that support sse transport - add the server to your config
```json
{
    "mcpServers": {
        "root-signals": {
            "url": "http://localhost:9090/sse"
        }
    }
}
```

## How to contribute

Contributions are welcome