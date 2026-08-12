from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any

from .models import MemoryRecord


class MemoryStore:
    """
    Persistent JSON-backed memory store.

    Thread-safe so multiple executor tasks can
    safely write memory.
    """

    def __init__(
        self,
        path: str = "data/memory.json",
    ) -> None:

        self.path = Path(path)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = threading.RLock()

        self._records: list[MemoryRecord] = []

        self._load()

    # =========================================================
    # LOAD
    # =========================================================

    def _load(self) -> None:

        with self._lock:

            if not self.path.exists():

                self._records = []

                self._save()

                return

            try:

                raw = json.loads(
                    self.path.read_text(
                        encoding="utf-8"
                    )
                )

                if not isinstance(
                    raw,
                    list,
                ):
                    raw = []

                self._records = [
                    MemoryRecord.from_dict(
                        item
                    )
                    for item in raw
                ]

            except (
                json.JSONDecodeError,
                OSError,
                KeyError,
                TypeError,
            ):

                self._records = []

    # =========================================================
    # SAVE
    # =========================================================

    def _save(self) -> None:

        data = [
            record.to_dict()
            for record in self._records
        ]

        self.path.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    # =========================================================
    # ADD
    # =========================================================

    def add(
        self,
        memory_type: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:

        record = MemoryRecord(
            id=str(
                uuid.uuid4()
            ),
            memory_type=memory_type,
            content=content,
            metadata=metadata or {},
        )

        with self._lock:

            self._records.append(
                record
            )

            self._save()

        return record

    # =========================================================
    # GET
    # =========================================================

    def all(
        self,
    ) -> list[MemoryRecord]:

        with self._lock:

            return list(
                self._records
            )

    # =========================================================
    # SEARCH
    # =========================================================

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[MemoryRecord]:

        query_words = {
            word.lower()
            for word in query.split()
            if word.strip()
        }

        if not query_words:
            return []

        scored: list[
            tuple[int, MemoryRecord]
        ] = []

        with self._lock:

            for record in self._records:

                text = (
                    f"{record.content} "
                    f"{record.memory_type} "
                    f"{record.metadata}"
                ).lower()

                score = sum(
                    1
                    for word in query_words
                    if word in text
                )

                if score > 0:

                    scored.append(
                        (
                            score,
                            record,
                        )
                    )

        scored.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return [
            record
            for _, record
            in scored[:limit]
        ]

    # =========================================================
    # DELETE
    # =========================================================

    def delete(
        self,
        record_id: str,
    ) -> bool:

        with self._lock:

            original = len(
                self._records
            )

            self._records = [
                record
                for record in self._records
                if record.id != record_id
            ]

            changed = (
                len(self._records)
                != original
            )

            if changed:
                self._save()

            return changed

    # =========================================================
    # CLEAR
    # =========================================================

    def clear(self) -> None:

        with self._lock:

            self._records = []

            self._save()