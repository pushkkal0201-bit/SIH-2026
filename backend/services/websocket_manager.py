from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket


def utc_now_iso() -> str:

    return datetime.now(
        timezone.utc
    ).isoformat()


class WebSocketManager:

    def __init__(self):

        self.active_connections: list[
            WebSocket
        ] = []

        self.total_connections = 0

        self.total_disconnections = 0

        self.total_broadcasts = 0

        self.total_messages_sent = 0

        self.started_at = (
            datetime.now(
                timezone.utc
            )
        )

        self._lock = asyncio.Lock()


    async def connect(
        self,
        websocket: WebSocket
    ) -> None:

        await websocket.accept()


        async with self._lock:

            if (
                websocket not in
                self.active_connections
            ):

                self.active_connections.append(
                    websocket
                )

                self.total_connections += 1


        print(
            "[PRATIRUP WebSocket] "
            f"Client connected. "
            f"Active clients: "
            f"{self.connection_count}"
        )


    def disconnect(
        self,
        websocket: WebSocket
    ) -> bool:

        if (
            websocket not in
            self.active_connections
        ):

            return False


        try:

            self.active_connections.remove(
                websocket
            )

        except ValueError:

            return False


        self.total_disconnections += 1


        print(
            "[PRATIRUP WebSocket] "
            f"Client removed. "
            f"Active clients: "
            f"{self.connection_count}"
        )


        return True


    async def send_personal(
        self,
        websocket: WebSocket,
        message: dict[str, Any]
    ) -> bool:

        try:

            await websocket.send_json(
                message
            )

            self.total_messages_sent += 1

            return True


        except Exception as exc:

            print(
                "[PRATIRUP WebSocket] "
                "Personal message failed:",
                exc
            )


            self.disconnect(
                websocket
            )


            return False


    async def broadcast(
        self,
        message: dict[str, Any]
    ) -> int:

        if (
            not self.active_connections
        ):

            return 0


        connections = list(
            self.active_connections
        )


        delivered = 0

        dead_connections: list[
            WebSocket
        ] = []


        for websocket in connections:

            try:

                await websocket.send_json(
                    message
                )

                delivered += 1

                self.total_messages_sent += 1


            except Exception as exc:

                print(
                    "[PRATIRUP WebSocket] "
                    "Broadcast delivery failed:",
                    exc
                )

                dead_connections.append(
                    websocket
                )


        for websocket in dead_connections:

            self.disconnect(
                websocket
            )


        self.total_broadcasts += 1


        return delivered


    async def broadcast_telemetry(
        self,
        telemetry: dict[str, Any]
    ) -> int:

        return await self.broadcast(
            {
                "type":
                    "telemetry",

                "data":
                    telemetry,

                "timestamp":
                    utc_now_iso(),
            }
        )


    async def broadcast_system_status(
        self,
        services: dict[str, Any]
    ) -> int:

        return await self.broadcast(
            {
                "type":
                    "system_status",

                "services":
                    services,

                "timestamp":
                    utc_now_iso(),
            }
        )


    async def broadcast_can_status(
        self,
        status: str,
        **extra: Any
    ) -> int:

        return await self.broadcast(
            {
                "type":
                    "can_status",

                "status":
                    status,

                "timestamp":
                    utc_now_iso(),

                **extra,
            }
        )


    async def broadcast_prediction(
        self,
        prediction: dict[str, Any]
    ) -> int:

        return await self.broadcast(
            {
                "type":
                    "prediction",

                "data":
                    prediction,

                "timestamp":
                    utc_now_iso(),
            }
        )


    async def broadcast_anomaly(
        self,
        result: dict[str, Any]
    ) -> int:

        return await self.broadcast(
            {
                "type":
                    "anomaly",

                "data":
                    result,

                "timestamp":
                    utc_now_iso(),
            }
        )


    async def broadcast_rul(
        self,
        result: dict[str, Any]
    ) -> int:

        return await self.broadcast(
            {
                "type":
                    "rul",

                "data":
                    result,

                "timestamp":
                    utc_now_iso(),
            }
        )


    async def broadcast_maintenance(
        self,
        advisory: dict[str, Any]
    ) -> int:

        return await self.broadcast(
            {
                "type":
                    "maintenance",

                "data":
                    advisory,

                "timestamp":
                    utc_now_iso(),
            }
        )


    async def heartbeat(
        self
    ) -> int:

        return await self.broadcast(
            {
                "type":
                    "heartbeat",

                "status":
                    "ONLINE",

                "timestamp":
                    utc_now_iso(),
            }
        )


    async def disconnect_all(
        self
    ) -> None:

        connections = list(
            self.active_connections
        )


        for websocket in connections:

            try:

                await websocket.close(
                    code=1001,
                    reason=(
                        "PRATIRUP backend "
                        "shutting down."
                    )
                )

            except Exception:

                pass


        disconnected_count = len(
            self.active_connections
        )


        self.active_connections.clear()

        self.total_disconnections += (
            disconnected_count
        )


        print(
            "[PRATIRUP WebSocket] "
            "All clients disconnected."
        )


    @property
    def connection_count(
        self
    ) -> int:

        return len(
            self.active_connections
        )


    @property
    def has_connections(
        self
    ) -> bool:

        return (
            self.connection_count > 0
        )


    def get_statistics(
        self
    ) -> dict[str, Any]:

        return {

            "service":
                "websocket",

            "status":
                "READY",

            "active_connections":
                self.connection_count,

            "total_connections":
                self.total_connections,

            "total_disconnections":
                self.total_disconnections,

            "total_broadcasts":
                self.total_broadcasts,

            "total_messages_sent":
                self.total_messages_sent,

            "started_at":
                self.started_at.isoformat(),

            "timestamp":
                utc_now_iso(),
        }


websocket_manager = WebSocketManager()
