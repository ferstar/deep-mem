"""API client for Nowledge Mem server"""

from typing import Any
import httpx

SUCCESS_CODES = frozenset({200, 201, 202, 204})


class APIError(Exception):
    """Raised when API request fails"""
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class APIClient:
    """HTTP client for Nowledge Mem API"""

    def __init__(self, base_url: str, auth_token: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                headers={
                    "Authorization": f"Bearer {self.auth_token}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "APIClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.close()
        return False

    def search_memories(
        self,
        query: str,
        limit: int = 10,
        mode: str = "deep",
        filter_labels: str | None = None,
    ) -> dict[str, Any]:
        """Search memories with semantic search

        Args:
            query: Search query text
            limit: Maximum results (1-100)
            mode: Search mode - 'deep' or 'fast'
            filter_labels: Comma-separated labels to filter

        Returns:
            Search results with memories and metadata
        """
        client = self._get_client()
        payload = {
            "query": query,
            "limit": limit,
            "mode": mode,
        }
        if filter_labels:
            payload["filter_labels"] = filter_labels

        response = client.post(f"{self.base_url}/memories/search", json=payload)

        if response.status_code not in SUCCESS_CODES:
            raise APIError(
                f"Memory search failed: {response.status_code} - {response.text[:200]}",
                status_code=response.status_code,
            )
        return response.json()

    def get_memory(self, memory_id: str) -> dict[str, Any]:
        """Get a specific memory by ID"""
        client = self._get_client()
        response = client.get(f"{self.base_url}/memories/{memory_id}")

        if response.status_code not in SUCCESS_CODES:
            raise APIError(
                f"Get memory failed: {response.status_code}",
                status_code=response.status_code,
            )
        return response.json()

    def search_threads(
        self,
        query: str,
        limit: int = 20,
        mode: str = "full",
    ) -> dict[str, Any]:
        """Search threads with message matching

        Args:
            query: Search query text
            limit: Maximum results (1-500)
            mode: Search mode - 'suggestions' or 'full'

        Returns:
            Search results with threads and metadata
        """
        client = self._get_client()
        params = {
            "query": query,
            "limit": limit,
            "mode": mode,
        }

        response = client.get(f"{self.base_url}/threads/search", params=params)

        if response.status_code not in SUCCESS_CODES:
            raise APIError(
                f"Thread search failed: {response.status_code} - {response.text[:200]}",
                status_code=response.status_code,
            )
        return response.json()

    def get_thread(self, thread_id: str) -> dict[str, Any]:
        """Get a specific thread with all messages"""
        client = self._get_client()
        response = client.get(f"{self.base_url}/threads/{thread_id}")

        if response.status_code not in SUCCESS_CODES:
            raise APIError(
                f"Get thread failed: {response.status_code}",
                status_code=response.status_code,
            )
        return response.json()

    def get_thread_summaries(self, limit: int = 50) -> dict[str, Any]:
        """Get thread summaries/titles"""
        client = self._get_client()
        response = client.get(
            f"{self.base_url}/threads/summaries",
            params={"limit": limit},
        )

        if response.status_code not in SUCCESS_CODES:
            raise APIError(
                f"Get summaries failed: {response.status_code}",
                status_code=response.status_code,
            )
        return response.json()
