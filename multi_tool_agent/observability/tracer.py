from __future__ import annotations

import json
import threading
import uuid

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class TraceEvent:
    event: str
    run_id: str
    data: dict[str, Any] = field(
        default_factory=dict
    )
    timestamp: str = field(
        default_factory=lambda:
        datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "data": self.data,
        }


class Tracer:
    """
    Persistent structured tracing for the autonomous agent.
    """

    def __init__(
        self,
        path: str = "data/traces.jsonl",
    ) -> None:

        self.path = Path(path)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._lock = threading.RLock()

    # =========================================================
    # RUN
    # =========================================================

    def start_run(
        self,
        request: str,
    ) -> str:

        run_id = str(
            uuid.uuid4()
        )

        self.record(
            "run_started",
            run_id,
            {
                "request": request,
            },
        )

        return run_id

    def end_run(
        self,
        run_id: str,
        success: bool,
        data: dict[str, Any] | None = None,
    ) -> None:

        payload = {
            "success": success,
        }

        if data:
            payload.update(data)

        self.record(
            "run_completed",
            run_id,
            payload,
        )

    # =========================================================
    # RECORD
    # =========================================================

    def record(
        self,
        event: str,
        run_id: str,
        data: dict[str, Any] | None = None,
    ) -> TraceEvent:

        trace_event = TraceEvent(
            event=event,
            run_id=run_id,
            data=data or {},
        )

        line = json.dumps(
            trace_event.to_dict(),
            ensure_ascii=False,
        )

        with self._lock:

            with self.path.open(
                "a",
                encoding="utf-8",
            ) as file:

                file.write(
                    line + "\n"
                )

        return trace_event

    # =========================================================
    # READ
    # =========================================================

    def read_run(
        self,
        run_id: str,
    ) -> list[dict[str, Any]]:

        if not self.path.exists():
            return []

        events = []

        with self._lock:

            with self.path.open(
                "r",
                encoding="utf-8",
            ) as file:

                for line in file:

                    line = line.strip()

                    if not line:
                        continue

                    try:
                        event = json.loads(
                            line
                        )

                        if (
                            event.get(
                                "run_id"
                            )
                            == run_id
                        ):
                            events.append(
                                event
                            )

                    except json.JSONDecodeError:
                        continue

        return events

    # =========================================================
    # STATUS
    # =========================================================

    def status(self) -> dict[str, Any]:

        total_events = 0

        if self.path.exists():

            with self._lock:

                with self.path.open(
                    "r",
                    encoding="utf-8",
                ) as file:

                    total_events = sum(
                        1
                        for line in file
                        if line.strip()
                    )

        return {
            "trace_file": str(
                self.path
            ),
            "total_events": total_events,
        }