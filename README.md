<h1 align="center">
  <img width="600" alt="Root Signals logo" src="https://app.rootsignals.ai/images/root-signals-color.svg" loading="lazy">
</h1>

<p align="center" class="large-text">
  <i><strong>Measurement & Control for LLM Automations</strong></i>
</p>

<p align="center">
  <a href="https://huggingface.co/root-signals">
    <img src="https://img.shields.io/badge/HuggingFace-FF9D00?style=for-the-badge&logo=huggingface&logoColor=white&scale=2" />
  </a>

  <a href="https://discord.gg/QbDAAmW9yz">
    <img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white&scale=2" />
  </a>

  <a href="https://sdk.rootsignals.ai/en/latest/">
    <img src="https://img.shields.io/badge/Documentation-E53935?style=for-the-badge&logo=readthedocs&logoColor=white&scale=2" />
  </a>

  <a href="https://app.rootsignals.ai/demo-user">
    <img src="https://img.shields.io/badge/Temporary_API_Key-15a20b?style=for-the-badge&logo=keycdn&logoColor=white&scale=2" />
  </a>
</p>

# Root Signals MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io/introduction) (*MCP*) server that exposes **Root Signals** evaluators as tools for AI assistants & agents.

## Overview

This project serves as a bridge between Root Signals API and MCP client applications, allowing AI assistants and agents to evaluate responses against various quality criteria.

## Features

- Exposes Root Signals evaluators as MCP tools
- Supports both standard evaluation and RAG evaluation with contexts
- Implements SSE for network deployment
- Compatible with various MCP clients such as [Cursor](https://docs.cursor.com/context/model-context-protocol)

## Tools

The server exposes the following tools:

1. `list_evaluators` - Lists all available evaluators on your Root Signals account
2. `run_evaluation` - Runs a standard evaluation using a specified evaluator ID
3. `run_evaluation_by_name` - Runs a standard evaluation using a specified evaluator name
4. `run_rag_evaluation` - Runs a RAG evaluation with contexts using a specified evaluator ID
5. `run_rag_evaluation_by_name` - Runs a RAG evaluation with contexts using a specified evaluator name

## How to use this server

#### 1. Get Your API Key
[Sign up & create a key](https://app.rootsignals.ai/settings/api-keys) or [generate a temporary key](https://app.rootsignals.ai/demo-user)


#### 2. Run the MCP Server

```bash
docker run -e ROOT_SIGNALS_API_KEY=<your_key> -p 0.0.0.0:9090:9090 --name=rs-mcp -d ghcr.io/root-signals/root-signals-mcp:latest
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

From all other clients that support SSE transport - add the server to your config, for example in Cursor:

```json
{
    "mcpServers": {
        "root-signals": {
            "url": "http://localhost:9090/sse"
        }
    }
}
```

## Usage Examples

### 1. Evaluate and improve Cursor Agent explanations

Let's say you want an explanation for a piece of code. You can simply instruct the agent to evaluate its response and improve it with Root Signals evaluators:

<h1 align="center">
  <img width="750" alt="Use case example image 1" src="https://github.com/user-attachments/assets/bb457e05-038a-4862-aae3-db030aba8a7c" loading="lazy">
</h1>

After the regular LLM answer, the agent can automatically
- discover appropriate evaluators via Root Signals MCP (`Conciseness` and `Relevance` in this case),
- execute them and
- provide a higher quality explanation based on the evaluator feedback:

<h1 align="center">
  <img width="750" alt="Use case example image 1" src="https://github.com/user-attachments/assets/2a83ddc3-9e46-4c2c-bf29-4feabc8c05c7" loading="lazy">
</h1>

It can then automatically evaluate the second attempt again to make sure the improved explanation is indeed higher quality:

<h1 align="center">
  <img width="750" alt="Use case example image 1" src="https://github.com/user-attachments/assets/440d62f6-9443-47c6-9d86-f0cf5a5217b9" loading="lazy">
</h1>

### 2. Using the MCP reference client directly from code

```python
from root_mcp_server.client import RootSignalsMCPClient

async def main():
    mcp_client = RootSignalsMCPClient()
    
    try:
        await mcp_client.connect()
        
        evaluators = await mcp_client.list_evaluators()
        print(f"Found {len(evaluators)} evaluators")
        
        result = await mcp_client.run_evaluation(
            evaluator_id="eval-123456789",
            request="What is the capital of France?",
            response="The capital of France is Paris."
        )
        print(f"Evaluation score: {result['score']}")
        
        result = await mcp_client.run_evaluation_by_name(
            evaluator_name="Clarity",
            request="What is the capital of France?",
            response="The capital of France is Paris."
        )
        print(f"Evaluation by name score: {result['score']}")
        
        result = await mcp_client.run_rag_evaluation(
            evaluator_id="eval-987654321",
            request="What is the capital of France?",
            response="The capital of France is Paris.",
            contexts=["Paris is the capital of France.", "France is a country in Europe."]
        )
        print(f"RAG evaluation score: {result['score']}")
        
        result = await mcp_client.run_rag_evaluation_by_name(
            evaluator_name="Faithfulness",
            request="What is the capital of France?",
            response="The capital of France is Paris.",
            contexts=["Paris is the capital of France.", "France is a country in Europe."]
        )
        print(f"RAG evaluation by name score: {result['score']}")
        
    finally:
        await mcp_client.disconnect()
```

## Limitations

### Network Resilience

- The current implementation does *not* include backoff and retry mechanisms for API calls:  
  - No Exponential backoff for failed requests
  - No Automatic retries for transient errors
  - No Request throttling for rate limit compliance

### Bundled MCP client is for reference only

This repo includes a `root_mcp_server.client.RootSignalsMCPClient` for reference with no support guarantees, unlike the server.
We recommend your own or any of the official [MCP clients](https://modelcontextprotocol.io/clients) for production use.

## How to Contribute

Contributions are welcome as long as they are applicable to all users.

Minimal steps include:
1. `uv sync --extra dev`
2. `pre-commit install`
3. Add your code and your tests to `src/root_mcp_server/tests/`
4. `docker compose up --build`
5. `ROOT_SIGNALS_API_KEY=<something> uv run pytest .` - all should pass
6. `ruff format . && ruff check --fix`