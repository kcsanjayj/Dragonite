from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class MemoryRecord:
    """
    One persistent memory entry.
    """

    id: str
    memory_type: str
    content: str

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    created_at: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "memory_type": self.memory_type,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "MemoryRecord":

        return cls(
            id=data["id"],
            memory_type=data["memory_type"],
            content=data["content"],
            metadata=data.get(
                "metadata",
                {},
            ),
            created_at=data.get(
                "created_at",
                datetime.now(
                    timezone.utc
                ).isoformat(),
            ),
        )