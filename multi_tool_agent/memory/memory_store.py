from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class MemoryItem:
    id: str
    user_id: str
    content: str
    metadata: dict[str, Any]
    created_at: str
    updated_at: str


class MemoryStore:
    """
    Persistent file-backed memory for the autonomous agent.

    Public API:
        save()
        get_recent()
        search()
        delete()
        clear_user()
        stats()

    Also keeps compatibility with the internal
    _save() method used by older versions.
    """

    def __init__(
        self,
        storage_path: str = "data/memory.json",
    ) -> None:

        self.storage_path = Path(
            storage_path
        )

        self.storage_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = threading.RLock()

        self._ensure_store()

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def _ensure_store(self) -> None:

        if not self.storage_path.exists():

            self._save(
                {
                    "memories": []
                }
            )

    # =========================================================
    # READ
    # =========================================================

    def _load(self) -> dict[str, Any]:

        with self._lock:

            try:

                with self.storage_path.open(
                    "r",
                    encoding="utf-8",
                ) as file:

                    data = json.load(file)

            except (
                FileNotFoundError,
                json.JSONDecodeError,
            ):

                return {
                    "memories": []
                }

            if not isinstance(
                data,
                dict,
            ):

                return {
                    "memories": []
                }

            if not isinstance(
                data.get("memories"),
                list,
            ):

                data["memories"] = []

            return data

    # =========================================================
    # WRITE
    # =========================================================

    def _save(
        self,
        data: dict[str, Any],
    ) -> None:

        with self._lock:

            self.storage_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            temp_path = (
                self.storage_path.with_suffix(
                    ".tmp"
                )
            )

            with temp_path.open(
                "w",
                encoding="utf-8",
            ) as file:

                json.dump(
                    data,
                    file,
                    indent=2,
                    ensure_ascii=False,
                )

            temp_path.replace(
                self.storage_path
            )

    # =========================================================
    # PUBLIC SAVE
    # =========================================================

    def save(
        self,
        user_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:

        if not user_id:

            raise ValueError(
                "user_id is required."
            )

        if not content:

            raise ValueError(
                "content is required."
            )

        now = datetime.now(
            timezone.utc
        ).isoformat()

        item = MemoryItem(
            id=str(
                uuid.uuid4()
            ),
            user_id=user_id,
            content=content,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )

        with self._lock:

            data = self._load()

            data["memories"].append(
                asdict(item)
            )

            self._save(data)

        return item.id

    # =========================================================
    # RECENT MEMORIES
    # =========================================================

    def get_recent(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:

        if limit <= 0:

            return []

        data = self._load()

        memories = [
            memory
            for memory in data["memories"]
            if memory.get("user_id")
            == user_id
        ]

        memories.sort(
            key=lambda item:
                item.get(
                    "created_at",
                    "",
                ),
            reverse=True,
        )

        return memories[:limit]

    # =========================================================
    # SEARCH
    # =========================================================

    def search(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:

        if not query:

            return []

        terms = {
            term.lower()
            for term in query.split()
            if term.strip()
        }

        if not terms:

            return []

        data = self._load()

        matches = []

        for memory in data["memories"]:

            if (
                memory.get("user_id")
                != user_id
            ):

                continue

            content = str(
                memory.get(
                    "content",
                    "",
                )
            ).lower()

            score = sum(
                1
                for term in terms
                if term in content
            )

            if score > 0:

                matches.append(
                    (
                        score,
                        memory,
                    )
                )

        matches.sort(
            key=lambda item: (
                item[0],
                item[1].get(
                    "created_at",
                    "",
                ),
            ),
            reverse=True,
        )

        return [
            memory
            for _, memory
            in matches[:limit]
        ]

    # =========================================================
    # DELETE ONE
    # =========================================================

    def delete(
        self,
        user_id: str,
        memory_id: str,
    ) -> bool:

        with self._lock:

            data = self._load()

            original = len(
                data["memories"]
            )

            data["memories"] = [
                memory
                for memory
                in data["memories"]
                if not (
                    memory.get("id")
                    == memory_id
                    and memory.get("user_id")
                    == user_id
                )
            ]

            changed = (
                len(data["memories"])
                != original
            )

            if changed:

                self._save(data)

            return changed

    # =========================================================
    # DELETE USER
    # =========================================================

    def clear_user(
        self,
        user_id: str,
    ) -> int:

        with self._lock:

            data = self._load()

            before = len(
                data["memories"]
            )

            data["memories"] = [
                memory
                for memory
                in data["memories"]
                if memory.get("user_id")
                != user_id
            ]

            deleted = (
                before
                - len(data["memories"])
            )

            if deleted:

                self._save(data)

            return deleted

    # =========================================================
    # STATS
    # =========================================================

    def stats(self) -> dict[str, Any]:

        data = self._load()

        memories = data[
            "memories"
        ]

        users = {
            memory.get("user_id")
            for memory in memories
            if memory.get("user_id")
        }

        return {
            "storage": str(
                self.storage_path
            ),
            "total_memories": len(
                memories
            ),
            "users": len(users),
        }