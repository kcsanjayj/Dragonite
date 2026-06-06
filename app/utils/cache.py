"""
Result caching layer for tool execution.
Reduces redundant API calls and speeds up repeated operations.
"""

import json
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class ResultCache:
    """
    Simple in-memory cache for tool execution results.
    Uses deterministic cache keys based on tool name and parameters.
    """

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize result cache.

        Args:
            ttl_seconds: Time-to-live for cache entries (default 5 minutes)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds

    def _make_key(self, tool_name: str, params: Dict[str, Any]) -> str:
        """
        Create deterministic cache key from tool and params.

        Args:
            tool_name: Name of the tool
            params: Tool parameters

        Returns:
            Cache key string
        """
        # Sort keys for deterministic serialization
        params_str = json.dumps(params, sort_keys=True, separators=(',', ':'))
        key_str = f"{tool_name}:{params_str}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, tool_name: str, params: Dict[str, Any]) -> Optional[Any]:
        """
        Get cached result if available and not expired.

        Args:
            tool_name: Name of the tool
            params: Tool parameters

        Returns:
            Cached result or None
        """
        key = self._make_key(tool_name, params)
        entry = self._cache.get(key)

        if not entry:
            return None

        # Check expiration
        if datetime.utcnow() > entry["expires_at"]:
            del self._cache[key]
            return None

        return entry["result"]

    def set(self, tool_name: str, params: Dict[str, Any], result: Any, is_valid: bool = True) -> None:
        """
        Cache a result with validation metadata.

        Args:
            tool_name: Name of the tool
            params: Tool parameters
            result: Result to cache
            is_valid: Whether the result passed validation (default True)
        """
        key = self._make_key(tool_name, params)
        self._cache[key] = {
            "result": result,
            "expires_at": datetime.utcnow() + timedelta(seconds=self._ttl),
            "tool": tool_name,
            "is_valid": is_valid,
            "cached_at": datetime.utcnow().isoformat()
        }

    def set_with_validation(self, tool_name: str, params: Dict[str, Any], result: Any,
                             validation_passed: bool, validation_message: str = "") -> bool:
        """
        Cache a result only if validation passed.

        Args:
            tool_name: Name of the tool
            params: Tool parameters
            result: Result to cache
            validation_passed: Whether validation passed
            validation_message: Validation message for metadata

        Returns:
            True if cached, False if validation failed and not cached
        """
        if not validation_passed:
            # Don't cache invalid results
            return False

        key = self._make_key(tool_name, params)
        self._cache[key] = {
            "result": result,
            "expires_at": datetime.utcnow() + timedelta(seconds=self._ttl),
            "tool": tool_name,
            "is_valid": True,
            "cached_at": datetime.utcnow().isoformat(),
            "validation_message": validation_message
        }
        return True

    def invalidate(self, tool_name: Optional[str] = None) -> int:
        """
        Invalidate cache entries.

        Args:
            tool_name: If specified, only invalidate entries for this tool

        Returns:
            Number of entries invalidated
        """
        if tool_name is None:
            count = len(self._cache)
            self._cache.clear()
            return count

        keys_to_delete = [k for k, v in self._cache.items() if v["tool"] == tool_name]
        for k in keys_to_delete:
            del self._cache[k]
        return len(keys_to_delete)

    def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        now = datetime.utcnow()
        expired = sum(1 for v in self._cache.values() if v["expires_at"] < now)
        return {
            "total_entries": len(self._cache),
            "expired_entries": expired,
            "valid_entries": len(self._cache) - expired
        }


# Global cache instance
result_cache = ResultCache()
