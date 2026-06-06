"""
State persistence for crash recovery.
Provides JSON-based snapshot and recovery functionality.
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class StatePersistence:
    """
    Handles saving and loading system state for crash recovery.
    """

    def __init__(self, snapshot_dir: str = "logs/snapshots", max_snapshots: int = 10):
        """
        Initialize persistence manager.

        Args:
            snapshot_dir: Directory to store snapshots
            max_snapshots: Maximum number of snapshots to retain (default: 10)
        """
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.max_snapshots = max_snapshots

    def save_state(
        self,
        state: Any,
        execution_id: str,
        user_input: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save current state to JSON file.

        Args:
            state: RuntimeState object to save
            execution_id: Unique execution identifier
            user_input: Original user input
            metadata: Additional metadata to store

        Returns:
            Path to saved snapshot file
        """
        from ..core.state import RuntimeState

        timestamp = datetime.utcnow().isoformat()
        filename = f"snapshot_{execution_id}_{timestamp.replace(':', '-')}.json"
        filepath = self.snapshot_dir / filename

        # Build snapshot data
        if isinstance(state, RuntimeState):
            snapshot_data = {
                "execution_id": execution_id,
                "timestamp": timestamp,
                "user_input": user_input,
                "system_state": state.system_state.value if hasattr(state.system_state, 'value') else str(state.system_state),
                "execution_context": state.execution_context,
                "metrics": state.metrics,
                "errors": state.errors,
                "replan_attempts": state.metrics.get("replan_attempts", 0),
                "execution_results": [
                    {
                        "node_id": r.node_id,
                        "success": r.success,
                        "error": r.error,
                        "result": str(r.result)[:500] if r.result else None  # Truncate
                    }
                    for r in state.execution_results
                ],
                "metadata": metadata or {}
            }
        else:
            snapshot_data = {
                "execution_id": execution_id,
                "timestamp": timestamp,
                "user_input": user_input,
                "state": str(state),
                "metadata": metadata or {}
            }

        # Write to file
        with open(filepath, 'w') as f:
            json.dump(snapshot_data, f, indent=2, default=str)

        # Enforce retention limit
        self._enforce_retention_limit()

        return str(filepath)

    def _enforce_retention_limit(self) -> int:
        """
        Remove oldest snapshots if exceeding max_snapshots limit.

        Returns:
            Number of snapshots removed
        """
        snapshots = self.list_snapshots()
        if len(snapshots) <= self.max_snapshots:
            return 0

        # Remove oldest snapshots (sorted newest first, so slice from max_snapshots index)
        to_remove = snapshots[self.max_snapshots:]
        removed = 0
        for old_snapshot in to_remove:
            try:
                Path(old_snapshot).unlink()
                removed += 1
            except OSError:
                pass  # Ignore errors during cleanup
        return removed

    def load_state(self, filepath: str) -> Optional[Dict[str, Any]]:
        """
        Load state from JSON file.

        Args:
            filepath: Path to snapshot file

        Returns:
            Loaded state data or None if not found
        """
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except json.JSONDecodeError:
            return None

    def list_snapshots(self, execution_id: Optional[str] = None) -> list:
        """
        List available snapshots.

        Args:
            execution_id: If specified, filter by execution ID

        Returns:
            List of snapshot file paths
        """
        if not self.snapshot_dir.exists():
            return []

        snapshots = list(self.snapshot_dir.glob("snapshot_*.json"))

        if execution_id:
            snapshots = [s for s in snapshots if execution_id in s.name]

        # Sort by modification time (newest first)
        snapshots.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        return [str(s) for s in snapshots]

    def get_latest_snapshot(self, execution_id: Optional[str] = None) -> Optional[str]:
        """
        Get the most recent snapshot.

        Args:
            execution_id: If specified, filter by execution ID

        Returns:
            Path to latest snapshot or None
        """
        snapshots = self.list_snapshots(execution_id)
        return snapshots[0] if snapshots else None

    def recover_execution(self, filepath: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to recover from a snapshot.

        Args:
            filepath: Path to snapshot file

        Returns:
            Recovered state data or None
        """
        state_data = self.load_state(filepath)

        if state_data is None:
            return None

        # Log recovery attempt
        print(f"Recovering execution {state_data.get('execution_id')} from {filepath}")
        print(f"Snapshot taken at: {state_data.get('timestamp')}")
        print(f"System state: {state_data.get('system_state')}")
        print(f"Completed nodes: {state_data.get('metrics', {}).get('completed_nodes', 0)}")

        return state_data

    def cleanup_old_snapshots(self, max_age_hours: int = 24) -> int:
        """
        Remove old snapshot files.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of files removed
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        removed = 0

        for snapshot_file in self.snapshot_dir.glob("snapshot_*.json"):
            mtime = datetime.fromtimestamp(snapshot_file.stat().st_mtime)
            if mtime < cutoff:
                snapshot_file.unlink()
                removed += 1

        return removed


# Global persistence instance
persistence = StatePersistence()
