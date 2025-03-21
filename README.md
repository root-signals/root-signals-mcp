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

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/rootsignals/rootsignals-mcp.git
   cd rootsignals-mcp
   ```

2. Set up the configuration:
   ```
   cp .env.example .env
   ```
   Then edit the `.env` file to add your RootSignals API key.

3. `docker compose up` will start the server on `http://localhost:9090`

## Usage


1. From code, e.g. the Python client
   ```python
   from mcp.client.sse import sse_client
   from mcp.client.session import ClientSession

   # Connect to the /sse endpoint (the server endpoint for SSE connections)
   async with sse_client("http://localhost:9090/sse") as transport:
       read_stream, write_stream = transport
       async with ClientSession(read_stream, write_stream) as session:
           await session.initialize()
           # Use session
   ```

2. From all other clients that support sse - add the server to your config
```json
{
    "mcpServers": {
        "root-signals": {
            "url": "http://localhost:9090/sse"
        }
    }
}

```