"""Simple in-memory cache with expiry, shared by the AI and YouTube services."""

import time
from typing import Any, Dict, Hashable, Optional, Tuple


class TTLCache:
    """Store values for a limited time and a limited number of entries.

    Data lives in server memory only, so it is cleared when the server restarts.
    """

    def __init__(self, ttl_seconds: float, max_size: int):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._data: Dict[Hashable, Tuple[float, Any]] = {}

    def get(self, key: Hashable) -> Optional[Any]:
        """Return the cached value, or None if missing or expired."""
        entry = self._data.get(key)
        if entry is None:
            return None

        saved_at, value = entry
        if time.monotonic() - saved_at > self.ttl_seconds:
            del self._data[key]
            return None

        return value

    def set(self, key: Hashable, value: Any) -> None:
        """Save a value, removing the oldest entry when the cache is full."""
        if key not in self._data and len(self._data) >= self.max_size:
            oldest_key = min(self._data, key=lambda k: self._data[k][0])
            del self._data[oldest_key]

        self._data[key] = (time.monotonic(), value)

    def clear(self) -> None:
        """Remove all entries."""
        self._data.clear()

    def __len__(self) -> int:
        return len(self._data)
