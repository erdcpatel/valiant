"""
WebSocket manager for streaming live workflow execution events.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List, Any
import json
import asyncio

router = APIRouter(prefix="/ws", tags=["WebSocket"])


class ConnectionManager:
    def __init__(self):
        # Maps run_id -> List of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Stores recent events for late joiners
        self.event_buffer: Dict[str, List[Dict[str, Any]]] = {}

    async def connect(self, run_id: str, websocket: WebSocket):
        await websocket.accept()
        if run_id not in self.active_connections:
            self.active_connections[run_id] = []
        self.active_connections[run_id].append(websocket)

        # Replay any buffered events
        if run_id in self.event_buffer:
            for ev in self.event_buffer[run_id]:
                await websocket.send_text(json.dumps(ev))

    def disconnect(self, run_id: str, websocket: WebSocket):
        if run_id in self.active_connections:
            if websocket in self.active_connections[run_id]:
                self.active_connections[run_id].remove(websocket)
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]

    async def broadcast(self, run_id: str, event_data: Dict[str, Any]):
        if run_id not in self.event_buffer:
            self.event_buffer[run_id] = []
        self.event_buffer[run_id].append(event_data)

        # Keep buffer bounded
        if len(self.event_buffer[run_id]) > 200:
            self.event_buffer[run_id] = self.event_buffer[run_id][-200:]

        if run_id in self.active_connections:
            dead_sockets = []
            for connection in self.active_connections[run_id]:
                try:
                    await connection.send_text(json.dumps(event_data))
                except Exception:
                    dead_sockets.append(connection)
            for s in dead_sockets:
                self.disconnect(run_id, s)


ws_manager = ConnectionManager()


@router.websocket("/runs/{run_id}")
async def websocket_run_endpoint(websocket: WebSocket, run_id: str):
    """Subscribe to real-time events for a specific workflow run."""
    await ws_manager.connect(run_id, websocket)
    try:
        while True:
            # Keep socket alive and receive client pings/messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(run_id, websocket)
    except Exception:
        ws_manager.disconnect(run_id, websocket)
