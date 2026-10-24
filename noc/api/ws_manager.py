from __future__ import annotations

import asyncio
import json
from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self.connections.discard(websocket)

    async def broadcast(self, event: dict) -> None:
        message = json.dumps(event, default=str)
        async with self._lock:
            peers = list(self.connections)
        if not peers:
            return
        results = await asyncio.gather(*(peer.send_text(message) for peer in peers), return_exceptions=True)
        stale = [peer for peer, result in zip(peers, results) if isinstance(result, Exception)]
        if stale:
            async with self._lock:
                self.connections.difference_update(stale)
