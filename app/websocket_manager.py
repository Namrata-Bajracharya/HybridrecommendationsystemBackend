from fastapi import WebSocket
from typing import List, Optional
import json
import asyncio


class ConnectionManager:
    def __init__(self):
        self._connections: dict[int, List[WebSocket]] = {}
        self._admin_connections: List[WebSocket] = []
        self._anon_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, user_id: Optional[int] = None, is_admin: bool = False):
        await websocket.accept()
        if user_id is not None:
            self._connections.setdefault(user_id, []).append(websocket)
            if is_admin:
                self._admin_connections.append(websocket)
        else:
            self._anon_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        for user_id, conns in self._connections.items():
            if websocket in conns:
                conns.remove(websocket)
                if not conns:
                    del self._connections[user_id]
                break
        if websocket in self._admin_connections:
            self._admin_connections.remove(websocket)
        if websocket in self._anon_connections:
            self._anon_connections.remove(websocket)

    async def send_json(self, websocket: WebSocket, data: dict):
        try:
            await websocket.send_json(data)
        except Exception:
            self.disconnect(websocket)

    async def send_to_user(self, user_id: int, data: dict):
        message = json.dumps(data)
        for ws in self._connections.get(user_id, []):
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(ws)

    async def send_to_admins(self, data: dict):
        message = json.dumps(data)
        for ws in self._admin_connections[:]:
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(ws)

    async def broadcast(self, data: dict):
        message = json.dumps(data)
        tasks = []
        for conns in self._connections.values():
            for ws in conns:
                tasks.append(self._safe_send(ws, message))
        for ws in self._admin_connections:
            tasks.append(self._safe_send(ws, message))
        for ws in self._anon_connections:
            tasks.append(self._safe_send(ws, message))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_send(self, ws: WebSocket, message: str):
        try:
            await ws.send_text(message)
        except Exception:
            self.disconnect(ws)


manager = ConnectionManager()
