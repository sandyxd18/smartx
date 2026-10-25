"""In-process pub/sub for run events (log lines, status changes), consumed by SSE."""

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

Event = dict[str, Any]


class EventHub:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[Event]]] = defaultdict(set)

    def publish(self, run_id: str, event: Event) -> None:
        for inbox in self._subscribers.get(run_id, ()):
            inbox.put_nowait(event)

    @asynccontextmanager
    async def subscribe(self, run_id: str) -> AsyncIterator[asyncio.Queue[Event]]:
        inbox: asyncio.Queue[Event] = asyncio.Queue()
        self._subscribers[run_id].add(inbox)
        try:
            yield inbox
        finally:
            self._subscribers[run_id].discard(inbox)
            if not self._subscribers[run_id]:
                del self._subscribers[run_id]
