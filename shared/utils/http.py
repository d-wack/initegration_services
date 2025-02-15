"""
HTTP client utilities for all services.

This module provides a standardized HTTP client with retry logic,
logging, and error handling that can be used across all microservices.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, Union
from urllib.parse import urljoin

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from shared.utils.logging import get_logger

logger = get_logger(__name__)


class HTTPClientError(Exception):
    """Base exception for HTTP client errors.

    Attributes:
        message: Error message
        status_code: HTTP status code
        response_body: Response body from the server
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[Any] = None,
    ) -> None:
        """Initialize HTTP client error.

        Args:
            message: Error message
            status_code: HTTP status code
            response_body: Response body from the server
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body


class HTTPClient:
    """HTTP client with retry logic and logging.

    This class provides a wrapper around httpx with additional
    functionality for retries, logging, and error handling.

    Attributes:
        base_url: Base URL for all requests
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        auth_header: Authorization header value
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        auth_header: Optional[str] = None,
    ) -> None:
        """Initialize HTTP client.

        Args:
            base_url: Base URL for all requests
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            auth_header: Authorization header value
        """
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.max_retries = max_retries
        self.auth_header = auth_header
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )

    async def __aenter__(self) -> "HTTPClient":
        """Async context manager entry.

        Returns:
            HTTPClient: Self
        """
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    def _get_headers(
        self, additional_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Get request headers.

        Args:
            additional_headers: Additional headers to include

        Returns:
            Dict[str, str]: Combined headers
        """
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.auth_header:
            headers["Authorization"] = self.auth_header
        if additional_headers:
            headers.update(additional_headers)
        return headers

    def _build_url(self, path: str) -> str:
        """Build full URL from path.

        Args:
            path: URL path

        Returns:
            str: Full URL
        """
        return urljoin(self.base_url, path.lstrip("/"))

    @retry(
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.TransportError)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make an HTTP request with retry logic.

        Args:
            method: HTTP method
            path: URL path
            **kwargs: Additional arguments for the request

        Returns:
            httpx.Response: HTTP response

        Raises:
            HTTPClientError: If the request fails
        """
        url = self._build_url(path)
        headers = self._get_headers(kwargs.pop("headers", None))
        start_time = datetime.utcnow()

        try:
            response = await self.client.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs,
            )
            response.raise_for_status()
            return response

        except httpx.TimeoutException as e:
            logger.error(
                "Request timeout",
                url=url,
                method=method,
                error=str(e),
            )
            raise HTTPClientError(
                f"Request timeout: {str(e)}",
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error response",
                url=url,
                method=method,
                status_code=e.response.status_code,
                response_body=e.response.text,
            )
            raise HTTPClientError(
                f"HTTP {e.response.status_code}",
                status_code=e.response.status_code,
                response_body=e.response.text,
            )

        except Exception as e:
            logger.exception(
                "Request failed",
                url=url,
                method=method,
                error=str(e),
            )
            raise HTTPClientError(f"Request failed: {str(e)}")

        finally:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                "HTTP request completed",
                url=url,
                method=method,
                duration=duration,
            )

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make a GET request.

        Args:
            path: URL path
            params: Query parameters
            **kwargs: Additional arguments for the request

        Returns:
            httpx.Response: HTTP response
        """
        return await self.request("GET", path, params=params, **kwargs)

    async def post(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make a POST request.

        Args:
            path: URL path
            json: JSON body data
            **kwargs: Additional arguments for the request

        Returns:
            httpx.Response: HTTP response
        """
        return await self.request("POST", path, json=json, **kwargs)

    async def put(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make a PUT request.

        Args:
            path: URL path
            json: JSON body data
            **kwargs: Additional arguments for the request

        Returns:
            httpx.Response: HTTP response
        """
        return await self.request("PUT", path, json=json, **kwargs)

    async def patch(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make a PATCH request.

        Args:
            path: URL path
            json: JSON body data
            **kwargs: Additional arguments for the request

        Returns:
            httpx.Response: HTTP response
        """
        return await self.request("PATCH", path, json=json, **kwargs)

    async def delete(
        self,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make a DELETE request.

        Args:
            path: URL path
            **kwargs: Additional arguments for the request

        Returns:
            httpx.Response: HTTP response
        """
        return await self.request("DELETE", path, **kwargs)


async def create_http_client(
    base_url: str,
    auth_token: Optional[str] = None,
    **kwargs: Any,
) -> HTTPClient:
    """Create an HTTP client instance.

    Args:
        base_url: Base URL for all requests
        auth_token: Optional authentication token
        **kwargs: Additional arguments for HTTPClient

    Returns:
        HTTPClient: Configured HTTP client instance
    """
    auth_header = f"Bearer {auth_token}" if auth_token else None
    return HTTPClient(
        base_url=base_url,
        auth_header=auth_header,
        **kwargs,
    ) 