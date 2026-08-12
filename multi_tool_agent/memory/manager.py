from __future__ import annotations

from typing import Any

from .models import MemoryRecord
from .store import MemoryStore


class MemoryManager:
    """
    High-level memory interface for the autonomous agent.

    Handles:
        - request memory
        - task-result memory
        - repair memory
        - final-answer memory
        - contextual retrieval
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
    # STORE REQUEST
    # =========================================================

    def remember_request(
        self,
        request: str,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:

        return self.store.add(
            memory_type="request",
            content=request,
            metadata=metadata,
        )

    # =========================================================
    # STORE TASK RESULT
    # =========================================================

    def remember_task(
        self,
        task_id: str,
        task: str,
        result: Any,
    ) -> MemoryRecord:

        return self.store.add(
            memory_type="task_result",
            content=str(result),
            metadata={
                "task_id": task_id,
                "task": task,
            },
        )

    # =========================================================
    # STORE REPAIR
    # =========================================================

    def remember_repair(
        self,
        task_id: str,
        instructions: Any,
    ) -> MemoryRecord:

        return self.store.add(
            memory_type="repair",
            content=str(
                instructions
            ),
            metadata={
                "task_id": task_id,
            },
        )

    # =========================================================
    # STORE FINAL ANSWER
    # =========================================================

    def remember_final(
        self,
        request: str,
        answer: str,
    ) -> MemoryRecord:

        return self.store.add(
            memory_type="final_answer",
            content=answer,
            metadata={
                "request": request,
            },
        )

    # =========================================================
    # RETRIEVE
    # =========================================================

    def retrieve(
        self,
        query: str,
        limit: int = 5,
    ) -> list[MemoryRecord]:

        return self.store.search(
            query=query,
            limit=limit,
        )

    # =========================================================
    # CONTEXT
    # =========================================================

    def build_context(
        self,
        query: str,
        limit: int = 5,
    ) -> str:

        records = self.retrieve(
            query,
            limit,
        )

        if not records:

            return (
                "No relevant previous "
                "memory was found."
            )

        lines = [
            "Relevant previous memory:"
        ]

        for record in records:

            lines.append(
                f"- [{record.memory_type}] "
                f"{record.content}"
            )

        return "\n".join(
            lines
        )

    # =========================================================
    # STATUS
    # =========================================================

    def status(self) -> dict:

        records = self.store.all()

        by_type: dict[str, int] = {}

        for record in records:

            by_type[
                record.memory_type
            ] = (
                by_type.get(
                    record.memory_type,
                    0,
                )
                + 1
            )

        return {
            "total_records": len(
                records
            ),
            "by_type": by_type,
            "storage": str(
                self.store.path
            ),
        }