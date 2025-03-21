# RootSignals SDK Async Reference

## Overview

The RootSignals SDK provides both synchronous and asynchronous APIs. This reference document focuses on the correct asynchronous usage patterns and addresses some limitations in the current SDK.

## Initialization

To use the SDK asynchronously, you must initialize the client with `run_async=True`:

```python
from root import RootSignals

client = RootSignals(
    api_key="your_api_key",
    run_async=True
)
```

## Accessing the Evaluators API

The `evaluators` property on the client returns an instance of the `Evaluators` class:

```python
# Access the evaluators property
evaluators_api = client.evaluators 

# This doesn't make an API call yet, it just returns the Evaluators instance
```

## Getting Available Evaluators

The current SDK design does not appear to provide a direct method to get a list of all available evaluators through the async API. This is a limitation of the SDK.

### Workaround for Getting All Evaluators

Since there's no direct method to list all evaluators, a possible approach is to use a lower-level API call:

```python
async def get_all_evaluators(client):
    # Access the v1_api directly 
    context = client.get_client_context()
    async with context() as api_client:
        api_instance = client.generated.openapi_aclient.api.v1_api.V1Api(api_client)
        # This is an assumption based on the SDK structure - might need to be adjusted
        result = await api_instance.v1_evaluators_list()  
        return result
```

This is speculative and may require adjustments based on the actual SDK implementation.

## Running Evaluations

To run evaluations asynchronously:

```python
# Standard evaluation
result = await client.evaluators.arun(
    evaluator_id="evaluator_id",
    request="user query",  # Note: SDK uses "request" not "query"
    response="assistant response"
)

# RAG evaluation with contexts
result = await client.evaluators.arun(
    evaluator_id="evaluator_id",
    request="user query",  # Note: SDK uses "request" not "query"
    response="assistant response",
    contexts=["context1", "context2"]
)
```

Note the use of `arun()` instead of `run()` for async operation, and the parameter name `request` (not `query`).

## Using Predefined Evaluators

The SDK has predefined evaluator constants that can be accessed as attributes of the `evaluators` property:

```python
# Using a predefined evaluator
clarity_runner = client.evaluators.Clarity  # Returns an async evaluator runner
result = await clarity_runner.arun(
    response="This is the assistant's response",
    request="What is machine learning?"
)
```

## Current Implementation Issue

The current implementation in the RootSignals MCP server incorrectly tries to access the list of all evaluators with:

```python
self.evaluators_cache = await self.client.evaluators
```

This code doesn't retrieve a list of evaluators; it only returns the `Evaluators` class instance. This is likely causing issues because the return value doesn't have the expected structure.

## Suggested Fix for Current Implementation

The implementation should be revised to use the appropriate API calls for listing evaluators. This might require using lower-level API access if the SDK doesn't provide a direct method:

```python
async def initialize(self) -> dict[str, Any]:
    """Initialize and cache available evaluators.

    Returns:
        Dict[str, Any]: The evaluators data from RootSignals API.
    """
    # This is speculative and would need to be confirmed with RootSignals documentation
    context = self.client.get_client_context()
    async with context() as api_client:
        api_instance = self.client.generated.openapi_aclient.api.v1_api.V1Api(api_client)
        self.evaluators_cache = await api_instance.v1_evaluators_list()
        return self.evaluators_cache
```

## Complete Example

```python
import asyncio
from root import RootSignals

async def main():
    client = RootSignals(
        api_key="your_api_key",
        run_async=True
    )
    
    # Get the evaluators API interface
    evaluators_api = client.evaluators
    
    # Run an evaluation using a specific evaluator ID
    result = await evaluators_api.arun(
        evaluator_id="some-evaluator-id",
        response="This is the assistant's response",
        request="What is machine learning?"  # Note: using "request", not "query"
    )
    
    print(f"Evaluation result: {result}")
    
    # Or use a predefined evaluator
    clarity_result = await evaluators_api.Clarity.arun(
        response="This is the assistant's response",
        request="What is machine learning?"  # Note: using "request", not "query"
    )
    
    print(f"Clarity evaluation: {clarity_result}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Important Notes

1. All async methods must be awaited using the `await` keyword
2. The `evaluators` property returns an API interface, not a list of evaluators
3. Use `arun()` instead of `run()` for asynchronous evaluation
4. The client must be initialized with `run_async=True`
5. Mixing sync and async methods will result in errors
6. The SDK parameter is named `request`, not `query`, when providing the user question
7. The SDK does not appear to provide a direct method to list all available evaluators asynchronously

## Next Steps

To properly implement access to all evaluators, consider:

1. Contacting RootSignals for documentation on accessing the full list of evaluators
2. Examining the SDK's source code more thoroughly to identify any undocumented methods
3. Implementing a custom solution using lower-level API access
4. If access to all evaluators isn't needed, use the predefined evaluator constants instead