from __future__ import annotations

from typing import Any

from multi_tool_agent.memory.memory_store import MemoryStore


class MemoryContext:
    """
    Adapter between the autonomous engine and MemoryStore.

    Responsibilities:
        - retrieve relevant memories
        - format memories for planning
        - save completed interactions
        - retrieve recent memories
    """

    def __init__(
        self,
        store: MemoryStore | None = None,
    ) -> None:

        self.store = (
            store
            or MemoryStore()
        )

    # =========================================================
    # RETRIEVE
    # =========================================================

    def retrieve(
        self,
        user_id: str,
        request: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:

        if not user_id:
            return []

        if not request:
            return []

        return self.store.search(
            user_id=user_id,
            query=request,
            limit=limit,
        )

    # =========================================================
    # BUILD CONTEXT
    # =========================================================

    @staticmethod
    def build_context(
        memories: list[dict[str, Any]],
    ) -> str:

        if not memories:
            return ""

        lines = [
            "RELEVANT PREVIOUS MEMORY:",
            "",
        ]

        for index, memory in enumerate(
            memories,
            start=1,
        ):

            content = memory.get(
                "content",
                "",
            )

            if not content:
                continue

            lines.append(
                f"{index}. {content}"
            )

        return "\n".join(
            lines
        ).strip()

    # =========================================================
    # SAVE INTERACTION
    # =========================================================

    def save_interaction(
        self,
        user_id: str,
        request: str,
        answer: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:

        content = (
            f"User request: {request}\n"
            f"Agent answer: {answer}"
        )

        memory_metadata = {
            "type": "interaction",
            **(metadata or {}),
        }

        return self.store.save(
            user_id=user_id,
            content=content,
            metadata=memory_metadata,
        )

    # =========================================================
    # RECENT
    # =========================================================

    def recent(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:

        return self.store.get_recent(
            user_id=user_id,
            limit=limit,
        )