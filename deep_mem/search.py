"""Core search logic for deep memory retrieval"""

from dataclasses import dataclass, field
from typing import Any

from deep_mem.api import APIClient


@dataclass
class MemoryResult:
    """A memory search result with optional thread references"""
    memory_id: str
    title: str | None
    content: str
    importance: float
    similarity_score: float
    relevance_reason: str | None = None
    source_thread_id: str | None = None
    labels: list[str] = field(default_factory=list)
    created_at: str | None = None


@dataclass
class ThreadResult:
    """A thread search result"""
    thread_id: str
    title: str | None
    summary: str | None
    message_count: int = 0
    created_at: str | None = None


@dataclass
class DeepSearchResult:
    """Combined search result with memories and related threads"""
    query: str
    memories: list[MemoryResult]
    related_threads: list[ThreadResult]
    total_memories_found: int = 0
    total_threads_found: int = 0


class DeepMemorySearcher:
    """Progressive disclosure search: memories -> related threads"""

    def __init__(self, client: APIClient) -> None:
        self.client = client

    def search(
        self,
        query: str,
        memory_limit: int = 10,
        thread_limit: int = 5,
        expand_threads: bool = True,
    ) -> DeepSearchResult:
        """Execute deep memory search with progressive disclosure

        Phase 1: Search memories (brief descriptions)
        Phase 2: Find related threads (detail references)

        Args:
            query: Search query
            memory_limit: Max memories to return
            thread_limit: Max threads per memory
            expand_threads: Whether to search for related threads

        Returns:
            DeepSearchResult with memories and related threads
        """
        # Phase 1: Search memories
        memory_response = self.client.search_memories(
            query=query,
            limit=memory_limit,
            mode="deep",
        )

        memories = self._parse_memories(memory_response)
        # Handle both array and dict response for total count
        if isinstance(memory_response, list):
            total_memories = len(memory_response)
        else:
            total_memories = memory_response.get("total_found", len(memories))

        # Phase 2: Find related threads
        related_threads: list[ThreadResult] = []
        total_threads = 0

        if expand_threads and memories:
            # Strategy 1: Use source_thread_id from memories (metadata reference)
            thread_ids_from_memories = set()
            for mem in memories:
                if mem.source_thread_id:
                    thread_ids_from_memories.add(mem.source_thread_id)

            # Fetch threads by ID if we have references
            for tid in list(thread_ids_from_memories)[:thread_limit]:
                try:
                    thread_data = self.client.get_thread(tid)
                    # get_thread returns {"thread": {...}, "messages": [...]}
                    thread_obj = thread_data.get("thread", thread_data)
                    related_threads.append(self._parse_thread(thread_obj))
                except Exception:
                    pass  # Thread may have been deleted

            # Strategy 2: If no thread references, search by query keywords
            if not related_threads:
                thread_response = self.client.search_threads(
                    query=query,
                    limit=thread_limit,
                    mode="full",
                )
                related_threads = self._parse_threads(thread_response)
                total_threads = thread_response.get("total_found", len(related_threads))

        return DeepSearchResult(
            query=query,
            memories=memories,
            related_threads=related_threads,
            total_memories_found=total_memories,
            total_threads_found=total_threads or len(related_threads),
        )

    def _parse_memories(self, response: dict[str, Any] | list) -> list[MemoryResult]:
        """Parse memory search response into MemoryResult objects"""
        results = []
        # Handle both array response and dict with "results" key
        items = response if isinstance(response, list) else response.get("results", [])
        for item in items:
            # Handle both nested and flat response formats
            memory = item.get("memory", item)
            # Extract labels from metadata if not at top level
            labels = memory.get("labels", [])
            if not labels and "metadata" in memory:
                labels = memory["metadata"].get("labels", [])
            results.append(MemoryResult(
                memory_id=memory.get("id") or memory.get("memory_id", ""),
                title=memory.get("title"),
                content=memory.get("content", ""),
                importance=memory.get("importance", 0.5),
                similarity_score=item.get("similarity_score", 0.0),
                relevance_reason=item.get("relevance_reason"),
                source_thread_id=memory.get("metadata", {}).get("source_id"),
                labels=labels,
                created_at=memory.get("created_at"),
            ))
        return results

    def _parse_threads(self, response: dict[str, Any]) -> list[ThreadResult]:
        """Parse thread search response into ThreadResult objects"""
        results = []
        for thread in response.get("threads", []):
            results.append(self._parse_thread(thread))
        return results

    def _parse_thread(self, thread: dict[str, Any]) -> ThreadResult:
        """Parse a single thread into ThreadResult"""
        # Use thread_id (string format) for API calls, not UUID id
        tid = thread.get("thread_id") or thread.get("id", "")
        return ThreadResult(
            thread_id=tid,
            title=thread.get("title"),
            summary=thread.get("summary"),
            message_count=thread.get("message_count", 0),
            created_at=thread.get("created_at") or thread.get("last_activity"),
        )

    def get_thread_detail(self, thread_id: str) -> dict[str, Any]:
        """Get full thread content for expanded view"""
        return self.client.get_thread(thread_id)
