"""Settings module for the RootSignals MCP Server.

This module provides a settings model for the unified server using pydantic-settings.
"""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for the RootSignals MCP Server.

    This class handles loading and validating configuration from environment variables.
    """

    # RootSignals API key
    root_signals_api_key: SecretStr = Field(
        default=...,  # Required field
        description="RootSignals API key for authentication",
        alias="ROOT_SIGNALS_API_KEY",
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Host to bind to", alias="HOST")
    port: int = Field(default=9091, description="Port to listen on", alias="PORT")
    log_level: Literal["debug", "info", "warning", "error", "critical"] = Field(
        default="info", description="Logging level", alias="LOG_LEVEL"
    )
    debug: bool = Field(default=False, description="Enable debug mode", alias="DEBUG")

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
    settings = Settings()  # Will use env_file from model_config
except Exception as e:
    import sys

    sys.stderr.write(f"Error loading settings: {str(e)}\n")
    sys.stderr.write("Check that your .env file exists with proper ROOT_SIGNALS_API_KEY\n")
    raise
