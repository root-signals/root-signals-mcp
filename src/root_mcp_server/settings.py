"""Settings module for the RootSignals MCP Server.

This module provides a settings model for the unified server using pydantic-settings.
"""

import sys
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for the RootSignals MCP Server.

    This class handles loading and validating configuration from environment variables.
    """

    # Version
    version: str = Field(default="0.1.0", description="Server version")

    # RootSignals API key
    root_signals_api_key: SecretStr = Field(
        default=...,  # Required field
        description="RootSignals API key for authentication",
        alias="ROOT_SIGNALS_API_KEY",
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Host to bind to", alias="HOST")
    port: int = Field(default=9090, description="Port to listen on", alias="PORT")
    log_level: Literal["debug", "info", "warning", "error", "critical"] = Field(
        default="info", description="Logging level", alias="LOG_LEVEL"
    )
    debug: bool = Field(default=False, description="Enable debug mode", alias="DEBUG")

    # Transport settings
    transport: Literal["stdio", "sse", "websocket"] = Field(
        default="sse",
        description="Transport mechanism to use (stdio, sse, websocket)",
        alias="TRANSPORT",
    )

    env: str = Field(
        default="development",
        description="Environment identifier (development, staging, production)",
        alias="ENV",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        validate_default=True,
    )


# Create a global settings instance
try:
    # Load settings from environment or .env file
    settings = Settings()
except Exception as e:
    sys.stderr.write(f"Error loading settings: {str(e)}\n")
    sys.stderr.write("Check that your .env file exists with proper ROOT_SIGNALS_API_KEY\n")
    raise
