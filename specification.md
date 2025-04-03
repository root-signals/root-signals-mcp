# Synopsis

Implementation of a Model Context Protocol server that exposes Root-Signals evaluators as tools for use with MCP clients

# Requirements and Acceptance Criteria
- Implement a stdio compatible MCP server
- Python sdks are used for root-signals and MCP client / servers
- Pydantic BaseModel and settings should be used for all configuration variables and Request / Response types. Examples are given in root_types.py and settings.py
- Pytest testcase should pass for one of regular evaluators and RAG evaluators using a real MCP client and no mocks
- Deployment should include a docker and docker-compose.yml
- No caching nor retries for calls

# Implementation guidelines
- a valid .env file with API key is provided, not other secrets are required
- uv and ruff should be used
- the implementation is async compatible
- all project requirements are only added to pyproject.toml, example with minimal requirements is given.
- type hints are strictly required
- reference documentation for 3rd party sdks is available in the `references` subdir
- Dockerfile and docker-compose.yml are given with examples for running uv and adding .env
- pytest should be used for tests
