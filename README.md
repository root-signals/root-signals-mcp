# RootSignals MCP Server

A Model Context Protocol (MCP) server that exposes RootSignals evaluators as tools for AI assistants.

## Overview

This project implements an MCP server that allows AI assistants to use RootSignals evaluators as tools. 
It provides a bridge between the RootSignals API and MCP client applications, allowing AI assistants 
to evaluate responses against various quality criteria.

## Features

- Exposes RootSignals evaluators as MCP tools
- Supports both standard evaluation and RAG evaluation with contexts
- Implements multiple transport protocols (stdio, WebSocket, SSE)
- Provides asynchronous execution for improved performance
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

2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies using uv:
   ```
   uv pip install -e ".[dev]"
   ```

4. Set up the configuration:
   ```
   cp .env.example .env
   ```
   Then edit the `.env` file to add your RootSignals API key.

## Usage

### Starting the server

To start the server in stdio mode (default for command-line tools):

```
python -m main
```

### Connecting to the server

The server supports multiple transport mechanisms:

1. **stdio** - For local process communication
2. **WebSocket** - For network/Docker deployments
3. **Server-Sent Events (SSE)** - For HTTP-based communication

See the reference documentation in `references/mcp-server-implementation.md` for detailed connection examples.

### Docker

Run the server using Docker:

```
docker build -t rootsignals-mcp .
docker run -p 9090:9090 --env-file .env rootsignals-mcp
```

Or using docker-compose:

```
docker-compose up
```

By default, the Docker container exposes port 9090 for WebSocket/SSE connections.

## Development

### Running tests

Run all tests:

```
uv run python -m pytest
```

Run a specific test file:

```
uv run python -m pytest src/root_mcp_server/tests/test_mcp_server.py -v
```

Run a specific test:

```
uv run python -m pytest src/root_mcp_server/tests/test_mcp_server.py::test_handle_list_evaluators -v
```

### Code formatting and linting

```
uv run ruff format .
uv run ruff check .
uv run mypy .
```

## Documentation

- See `references/mcp-server-implementation.md` for detailed implementation reference
- See `references/rootsignals-sdk-async.md` for RootSignals SDK async usage patterns
- See `specification.md` for the project requirements

## License

MIT License