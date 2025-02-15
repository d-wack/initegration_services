"""
Configuration management utilities for all services.

This module provides a base configuration class and utilities for managing
environment variables and service configuration across all microservices.
"""

import os
from typing import Any, Dict, Optional, Union

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    """Base configuration settings for all services.

    Attributes:
        environment (str): The deployment environment (development, staging, production)
        log_level (str): Logging level for the service
        service_name (str): Name of the service
        service_port (int): Port the service runs on
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        env_prefix="",
        use_enum_values=True
    )

    # General settings
    environment: str = Field(
        default="development",
        description="Deployment environment",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level for the service",
    )
    service_name: str = Field(
        description="Name of the service",
    )
    service_port: int = Field(
        description="Port the service runs on",
    )

    # Database settings
    database_type: str = Field(
        default="sqlite",
        description="Type of database to use (sqlite, postgres, mysql)",
    )
    database_url: str = Field(
        description="Database connection URL",
    )

    # Security settings
    jwt_secret_key: Optional[str] = Field(
        default=None,
        description="Secret key for JWT token generation",
    )
    api_key_expiry_days: int = Field(
        default=30,
        description="Number of days until API keys expire",
    )
    cors_allowed_origins: list[str] = Field(
        default=["http://localhost:*"],
        description="List of allowed CORS origins",
    )

    # Rate limiting
    rate_limit_enabled: bool = Field(
        default=True,
        description="Whether rate limiting is enabled",
    )
    rate_limit_requests: int = Field(
        default=100,
        description="Number of requests allowed per period",
    )
    rate_limit_period: int = Field(
        default=60,
        description="Rate limit period in seconds",
    )

    def get_database_settings(self) -> Dict[str, Any]:
        """Get database-specific settings based on the database type.

        Returns:
            Dict[str, Any]: Dictionary of database settings
        """
        if self.database_type == "sqlite":
            return {"url": self.database_url}
        
        # For PostgreSQL and MySQL, parse connection URL for additional settings
        return {
            "url": self.database_url,
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
        }

    def get_service_url(self) -> str:
        """Get the service URL based on the environment.

        Returns:
            str: Service URL
        """
        if self.environment == "development":
            return f"http://localhost:{self.service_port}"
        return os.getenv("SERVICE_URL", f"http://localhost:{self.service_port}")

    def get_cors_settings(self) -> Dict[str, Union[list[str], bool]]:
        """Get CORS settings for the service.

        Returns:
            Dict[str, Union[list[str], bool]]: CORS settings
        """
        return {
            "allow_origins": self.cors_allowed_origins,
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }

    def get_rate_limit_settings(self) -> Dict[str, Any]:
        """Get rate limiting settings for the service.

        Returns:
            Dict[str, Any]: Rate limit settings
        """
        if not self.rate_limit_enabled:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "requests": self.rate_limit_requests,
            "period": self.rate_limit_period,
        } 