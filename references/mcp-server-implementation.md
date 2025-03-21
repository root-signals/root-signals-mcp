# MCP Server Implementation Reference

This document provides a reference for implementing and working with the Model Context Protocol (MCP) server in the RootSignals MCP project.

## Key Components and Files

### Server Implementation

- **`/src/root_mcp_server/server.py`**: Main MCP server implementation
  - Uses `mcp.server.lowlevel.Server` as the base class
  - Implements decorator-based tool registration
  - Handles tool calls and returns results in proper MCP format

- **`/src/root_mcp_server/evaluator.py`**: Service layer for RootSignals evaluators
  - Handles communication with the RootSignals API
  - Implements caching for evaluators
  - Provides methods to run evaluations and format results

- **`/src/root_mcp_server/unified_server.py`**: Entry point for running the server
  - Manages startup, configuration, and cleanup
  - Sets up logging and error handling

- **`/src/root_mcp_server/schema.py`**: Pydantic models for request/response validation
  - Defines the data structures for evaluator info, requests, and responses
  - Implements validation rules for input parameters

### Testing

- **`/src/root_mcp_server/tests/test_mcp_server.py`**: Unit tests for MCP server
  - Tests tool registration, listing, and calling
  - Mocks the evaluator service

- **`/src/root_mcp_server/tests/test_evaluator.py`**: Unit tests for evaluator service
  - Tests listing evaluators and running evaluations
  - Uses mocks to avoid real API calls

- **`/src/root_mcp_server/tests/test_integration.py`**: Integration tests
  - Tests end-to-end functionality with real server process
  - Uses proper MCP client to communicate with the server

- **`/src/root_mcp_server/tests/conftest.py`**: Test configuration
  - Sets up common fixtures and configuration for tests

## MCP Server Patterns

### Server Initialization

```python
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
```

### Tool Registration

The MCP server uses decorators to register handlers for listing and calling tools:

```python
# Register tool handlers with MCP server using decorators
@self.app.list_tools()
async def list_tools() -> List[Tool]:
    return await self.list_tools()
    
@self.app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    return await self.call_tool(name, arguments)
```

### Tool Implementation

Each tool is implemented as a method that handles the specific functionality:

```python
async def _handle_list_evaluators(self, params: dict[str, Any]) -> dict[str, Any]:
    """Handle list_evaluators tool call."""
    response = await self.evaluator_service.list_evaluators()
    return response.model_dump(exclude_none=True)
```

### Response Formatting

Responses must be formatted according to the MCP protocol:

```python
# Convert the result to TextContent
return [TextContent(type="text", text=json.dumps(result))]
```

### Starting the Server

The MCP server can be started with different transport mechanisms depending on your deployment requirements.

#### 1. stdio Transport (Command Line)

Best for:
- Local development
- Command-line tools
- Integration with CLI

```python
from mcp.server.stdio import stdio_server

async def start(self) -> None:
    """Start the MCP server with stdio transport."""
    await self.initialize()
    
    # Use the MCP stdio server
    async with stdio_server() as streams:
        await self.app.run(
            streams[0], 
            streams[1], 
            self.app.create_initialization_options()
        )
```

#### 2. WebSocket Transport (Network)

Best for:
- Remote access
- Docker containers
- Production deployments
- Bidirectional communication

```python
from mcp.server.websocket import websocket_server

async def start_websocket(self, host: str = "0.0.0.0", port: int = 9090) -> None:
    """Start the MCP server with WebSocket transport."""
    await self.initialize()
    
    # Use the MCP WebSocket server
    async with websocket_server(host, port) as streams_generator:
        async for streams in streams_generator:
            # Each new connection gets its own task
            asyncio.create_task(
                self.app.run(
                    streams[0],
                    streams[1],
                    self.app.create_initialization_options()
                )
            )
```

#### 3. SSE Transport (HTTP)

Best for:
- Browser clients
- One-way streaming 
- HTTP-only environments

```python
from mcp.server.sse import sse_server

async def start_sse(self, host: str = "0.0.0.0", port: int = 9090) -> None:
    """Start the MCP server with SSE transport."""
    await self.initialize()
    
    # Use the MCP SSE server
    async with sse_server(host, port) as streams_generator:
        async for streams in streams_generator:
            # Each new connection gets its own task
            asyncio.create_task(
                self.app.run(
                    streams[0],
                    streams[1],
                    self.app.create_initialization_options()
                )
            )
```

### Docker/Remote Server Configuration

When running the server in Docker or for remote access:

1. **Host Binding**: Bind to `0.0.0.0` (all interfaces) instead of localhost
   ```python
   start_websocket(host="0.0.0.0", port=9090)
   ```

2. **Port Exposure**: Ensure ports are properly exposed in Docker configuration
   ```yaml
   # docker-compose.yml
   services:
     root-mcp-server:
       # ...
       ports:
         - "9090:9090"  # Expose WebSocket/SSE port
   ```

3. **Environment Variables**: Configure server to read host/port from environment
   ```python
   host = os.environ.get("HOST", "0.0.0.0")
   port = int(os.environ.get("PORT", "9090"))
   start_websocket(host=host, port=port)
   ```

4. **Transport Selection**: Implement logic to select transport based on configuration
   ```python
   transport = os.environ.get("TRANSPORT", "stdio")
   if transport == "websocket":
       await start_websocket(host, port)
   elif transport == "sse":
       await start_sse(host, port)
   else:
       await start_stdio()
   ```

## MCP Client Implementation

The MCP SDK supports multiple transport mechanisms for clients to connect to servers running in different environments.

### Transport Options

1. **stdio** - For local subprocess communication (server runs as a child process)
2. **WebSocket** - For remote communication over network (server runs on a remote machine/container)
3. **Server-Sent Events (SSE)** - For one-way streaming from server to client over HTTP

### Client Setup by Transport Type

#### 1. stdio (Local Process Communication)

Best for:
- Local development
- Testing
- Command-line tools

```python
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

# Define parameters for the server process
server_params = StdioServerParameters(
    command="python",
    args=["main.py"],
    env=env,
)

# Create client context manager
async with stdio_client(server_params) as stdio_transport:
    read_stream, write_stream = stdio_transport
    
    # Create and initialize the client session
    async with ClientSession(read_stream, write_stream) as session:
        # Initialize the session (establish connection with server)
        await session.initialize()
        
        # Use the session...
```

#### 2. WebSocket (Remote Communication)

Best for:
- Containerized environments (Docker)
- Remote servers
- Production deployments
- Bidirectional communication

```python
from mcp.client.websocket import websocket_client
from mcp.client.session import ClientSession

# Connect to the WebSocket endpoint
async with websocket_client("ws://server-host:port/ws") as ws_transport:
    read_stream, write_stream = ws_transport
    
    # Create and initialize the client session
    async with ClientSession(read_stream, write_stream) as session:
        # Initialize the session
        await session.initialize()
        
        # Use the session...
```

#### 3. Server-Sent Events (SSE)

Best for:
- One-way server-to-client streaming
- Browser clients
- Environments with HTTP-only connectivity

```python
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

# Connect to the SSE endpoint
async with sse_client("http://server-host:port/sse") as sse_transport:
    read_stream, write_stream = sse_transport
    
    # Create and initialize the client session
    async with ClientSession(read_stream, write_stream) as session:
        # Initialize the session
        await session.initialize()
        
        # Use the session...
```

### Docker/Remote Connection Considerations

When running the MCP server in Docker or on a remote machine:

1. **Port Exposure**: Ensure that the WebSocket or SSE ports are exposed in your Docker configuration:
   ```yaml
   # docker-compose.yml
   services:
     root-mcp-server:
       # ...
       ports:
         - "9090:9090"  # WebSocket/SSE port
   ```

2. **Network Configuration**: Ensure network routes are properly configured
   - For Docker containers, use the service name as hostname in Docker Compose networks
   - For external access, map to host ports

3. **Connection URLs**: Use the appropriate URL format
   - Docker internal: `ws://service-name:port/ws` or `http://service-name:port/sse`
   - External: `ws://host-ip:port/ws` or `http://host-ip:port/sse`

### Calling Tools

Once the client session is established, the API is the same regardless of transport:

```python
# Call a tool
response = await session.call_tool("list_evaluators", {})

# Extract content from the response
text_content = next((item for item in response.content if item.type == "text"), None)
result = json.loads(text_content.text)
```

## Testing Patterns

### Mocking the Server

```python
@pytest.fixture
def mock_mcp_server():
    """Mock the MCP Server class."""
    with patch("root_mcp_server.server.Server") as mock_server_class:
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server
        
        # Mock the list_tools and call_tool methods to return decorators
        mock_server.list_tools.return_value = lambda func: func
        mock_server.call_tool.return_value = lambda func: func
        
        yield mock_server
```

### Mocking the Evaluator Service

```python
@pytest.fixture
def mock_evaluator_service():
    """Mock the evaluator service."""
    with patch("root_mcp_server.server.EvaluatorService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service

        # Create a proper mock for list_evaluators
        mock_evaluators_response = MagicMock()
        mock_evaluators_response.model_dump.return_value = {
            "evaluators": [
                {
                    "id": "test-evaluator-1",
                    "name": "Test Evaluator 1",
                    "version_id": "v1",
                    "models": ["gpt-4"],
                    "intent": "test",
                    "requires_context": False,
                }
            ],
            "count": 1,
            "total": 1,
        }
        
        mock_service.list_evaluators.return_value = mock_evaluators_response
        
        yield mock_service
```

### Integration Testing with MCP Client

```python
@pytest_asyncio.fixture(scope="function")
async def mcp_client() -> AsyncGenerator[ClientSession, None]:
    """Create and initialize an MCP client for testing."""
    # Set up environment
    env = os.environ.copy()
    
    # Define parameters for the server process
    server_params = StdioServerParameters(
        command="python",
        args=["main.py"],
        env=env,
    )
    
    # Create client context manager
    async with stdio_client(server_params) as stdio_transport:
        read_stream, write_stream = stdio_transport
        
        # Create and initialize the client session
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the session
            await session.initialize()
            
            # Yield the session to the test
            yield session
```

## pytest Configuration

To properly configure pytest for async tests:

```ini
# pytest.ini
[pytest]
asyncio_mode = strict
asyncio_default_fixture_loop_scope = function
```

## Common Issues and Solutions

1. **Problem**: Importing `MCPClient` directly from `mcp.client`
   **Solution**: Use `ClientSession` from `mcp.client.session` instead

2. **Problem**: Not properly awaiting async properties or methods
   **Solution**: Always use `await` with async properties and methods

3. **Problem**: Not properly handling MCP response format
   **Solution**: Return responses as `[TextContent(type="text", text=json.dumps(result))]`

4. **Problem**: Async fixture scope warnings
   **Solution**: Set `asyncio_default_fixture_loop_scope = function` in pytest.ini

5. **Problem**: Decorator-based tool registration
   **Solution**: Use `@self.app.list_tools()` pattern instead of direct method calls

## Reference SDK Documentation

For details on the underlying MCP SDK:
- `/references/mcp-python-sdk/src/mcp/server/lowlevel/server.py`: Base MCP server implementation
- `/references/mcp-python-sdk/src/mcp/client/session.py`: Client session implementation
- `/references/mcp-python-sdk/src/mcp/client/stdio.py`: Client stdio transport
- `/references/rootsignals-sdk-async.md`: Async usage patterns for RootSignals SDK