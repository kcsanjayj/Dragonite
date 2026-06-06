"""
Lightweight memory layer for context continuity across agent executions.
Provides conversation history and pattern tracking.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import deque


class Memory:
    """
    Lightweight memory store for agent context continuity.
    Maintains recent execution history and pattern awareness.
    """

    def __init__(self, max_entries: int = 50):
        """
        Initialize memory store.

        Args:
            max_entries: Maximum number of entries to retain (FIFO)
        """
        self.store: deque = deque(maxlen=max_entries)
        self.max_entries = max_entries

    def add(self, entry_type: str, data: Dict[str, Any]) -> None:
        """
        Add an entry to memory.

        Args:
            entry_type: Type of entry (plan, execution, error, result)
            data: Entry data
        """
        entry = {
            "type": entry_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        self.store.append(entry)

    def get_recent(self, k: int = 5, entry_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recent memory entries.

        Args:
            k: Number of recent entries to retrieve
            entry_type: Filter by entry type (optional)

        Returns:
            List of recent entries
        """
        entries = list(self.store)

        if entry_type:
            entries = [e for e in entries if e["type"] == entry_type]

        return entries[-k:] if k < len(entries) else entries

    def get_patterns(self) -> Dict[str, Any]:
        """
        Extract pattern counts from memory.

        Returns:
            Dictionary of pattern counts including tool failures
        """
        patterns = {
            "total_plans": 0,
            "total_executions": 0,
            "total_errors": 0,
            "tool_usage": {},
            "tool_failures": {},
            "tool_success_rate": {},
            "avoid_tools": []  # Tools with high failure rates
        }

        tool_stats = {}  # {tool_name: {"success": 0, "failure": 0}}

        for entry in self.store:
            if entry["type"] == "plan":
                patterns["total_plans"] += 1
            elif entry["type"] == "execution":
                patterns["total_executions"] += 1
                tool_name = entry["data"].get("tool_name")
                success = entry["data"].get("success", False)

                if tool_name:
                    patterns["tool_usage"][tool_name] = patterns["tool_usage"].get(tool_name, 0) + 1

                    if tool_name not in tool_stats:
                        tool_stats[tool_name] = {"success": 0, "failure": 0}

                    if success:
                        tool_stats[tool_name]["success"] += 1
                    else:
                        tool_stats[tool_name]["failure"] += 1

            elif entry["type"] == "error":
                patterns["total_errors"] += 1
                tool_name = entry["data"].get("tool_name")
                if tool_name:
                    patterns["tool_failures"][tool_name] = patterns["tool_failures"].get(tool_name, 0) + 1

        # Calculate success rates and identify problematic tools
        FAILURE_THRESHOLD = 3
        FAILURE_RATE_THRESHOLD = 0.7  # 70% failure rate

        for tool_name, stats in tool_stats.items():
            total = stats["success"] + stats["failure"]
            if total > 0:
                failure_rate = stats["failure"] / total
                patterns["tool_success_rate"][tool_name] = {
                    "success": stats["success"],
                    "failure": stats["failure"],
                    "failure_rate": failure_rate
                }

                # Mark tools to avoid
                if stats["failure"] >= FAILURE_THRESHOLD and failure_rate >= FAILURE_RATE_THRESHOLD:
                    patterns["avoid_tools"].append(tool_name)

        return patterns

    def get_active_guidance(self) -> str:
        """
        Get active guidance based on memory patterns.
        This actually influences agent behavior, not just context.

        Returns:
            Guidance string for prompts
        """
        patterns = self.get_patterns()
        guidance_lines = []

        # Tool avoidance guidance
        if patterns["avoid_tools"]:
            tools_to_avoid = ", ".join(patterns["avoid_tools"])
            guidance_lines.append(f"CRITICAL: The following tools have high failure rates - AVOID using them: {tools_to_avoid}")
            guidance_lines.append("Use alternative tools or approaches instead.")

        # Tool success rate warnings
        for tool_name, rate_info in patterns["tool_success_rate"].items():
            if rate_info["failure_rate"] > 0.5:
                guidance_lines.append(f"WARNING: Tool '{tool_name}' has {rate_info['failure_rate']:.0%} failure rate. Use cautiously.")

        if not guidance_lines:
            return ""

        return "\n".join(["\nACTIVE LEARNING GUIDANCE:"] + guidance_lines)

    def get_context_summary(self, k: int = 5) -> str:
        """
        Get a text summary of recent context for prompts.

        Args:
            k: Number of recent entries to include

        Returns:
            String summary of recent context
        """
        recent = self.get_recent(k)
        if not recent:
            return "No prior context available."

        lines = ["Recent execution context:"]
        for entry in recent:
            ts = entry["timestamp"][:19]  # Trim to seconds
            if entry["type"] == "plan":
                lines.append(f"  [{ts}] Plan generated: {entry['data'].get('goal', 'N/A')}")
            elif entry["type"] == "execution":
                node_id = entry['data'].get('node_id', 'N/A')
                success = "✓" if entry['data'].get('success') else "✗"
                lines.append(f"  [{ts}] Execution {success} for node {node_id}")
            elif entry["type"] == "error":
                lines.append(f"  [{ts}] Error: {entry['data'].get('error', 'Unknown')}")

        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all memory entries."""
        self.store.clear()


# Global memory instance
memory = Memory()
