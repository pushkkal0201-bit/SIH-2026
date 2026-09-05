from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.mission.replay import (
    REPLAY_ENGINE_VERSION,
    historical_replay_engine,
)

from backend.services.websocket_manager import (
    websocket_manager,
)


REPLAY_WEBSOCKET_BRIDGE_VERSION = "1.0.0"


def utc_now_iso() -> str:

    return datetime.now(
        timezone.utc
    ).isoformat()


class ReplayWebSocketBridge:

    def __init__(self):

        self.enabled = False

        self.frames_received = 0

        self.frames_broadcast = 0

        self.total_client_deliveries = 0

        self.last_sequence: int | None = None

        self.last_mission_id: str | None = None

        self.last_broadcast_at: str | None = None

        self.last_error: str | None = None


    async def handle_replay_frame(
        self,
        telemetry: dict[str, Any],
    ) -> None:

        self.frames_received += 1

        if not isinstance(
            telemetry,
            dict,
        ):

            self.last_error = (
                "INVALID_REPLAY_TELEMETRY"
            )

            return


        meta = telemetry.get(
            "meta"
        )

        if not isinstance(
            meta,
            dict,
        ):

            self.last_error = (
                "REPLAY_META_MISSING"
            )

            return


        if (
            meta.get("source")
            != "REPLAY"
            or meta.get("replay")
            is not True
        ):

            self.last_error = (
                "NON_REPLAY_FRAME_REJECTED"
            )

            return


        sequence = meta.get(
            "sequence"
        )

        mission = telemetry.get(
            "mission"
        )

        mission_id = None

        if isinstance(
            mission,
            dict,
        ):

            mission_id = mission.get(
                "id"
            )


        message = {

            "type":
                "replay_telemetry",

            "source":
                "REPLAY",

            "replay":
                True,

            "telemetry":
                telemetry,

            "data":
                telemetry,

            "replay_engine_version":
                REPLAY_ENGINE_VERSION,

            "bridge_version":
                REPLAY_WEBSOCKET_BRIDGE_VERSION,

            "timestamp":
                utc_now_iso(),
        }


        try:

            delivered = (
                await websocket_manager.broadcast(
                    message
                )
            )

        except Exception as exc:

            self.last_error = (
                f"{type(exc).__name__}: {exc}"
            )

            return


        self.frames_broadcast += 1

        self.total_client_deliveries += (
            delivered
        )

        if isinstance(
            sequence,
            int,
        ):

            self.last_sequence = sequence

        elif sequence is not None:

            try:

                self.last_sequence = int(
                    sequence
                )

            except (
                TypeError,
                ValueError,
            ):

                self.last_sequence = None


        if mission_id is not None:

            self.last_mission_id = str(
                mission_id
            )


        self.last_broadcast_at = (
            utc_now_iso()
        )

        self.last_error = None


    def enable(
        self,
    ) -> dict[str, Any]:

        historical_replay_engine.set_callback(
            self.handle_replay_frame
        )

        self.enabled = True

        return self.get_status()


    def reset_statistics(
        self,
    ) -> dict[str, Any]:

        self.frames_received = 0

        self.frames_broadcast = 0

        self.total_client_deliveries = 0

        self.last_sequence = None

        self.last_mission_id = None

        self.last_broadcast_at = None

        self.last_error = None

        return self.get_status()


    def get_status(
        self,
    ) -> dict[str, Any]:

        return {

            "service":
                "replay_websocket_bridge",

            "version":
                REPLAY_WEBSOCKET_BRIDGE_VERSION,

            "status":
                (
                    "READY"
                    if self.enabled
                    else "DISABLED"
                ),

            "enabled":
                self.enabled,

            "replay_engine_version":
                REPLAY_ENGINE_VERSION,

            "architecture":
                "REPLAY_TO_WEBSOCKET_ONLY",

            "message_type":
                "replay_telemetry",

            "frames_received":
                self.frames_received,

            "frames_broadcast":
                self.frames_broadcast,

            "total_client_deliveries":
                self.total_client_deliveries,

            "last_sequence":
                self.last_sequence,

            "last_mission_id":
                self.last_mission_id,

            "last_broadcast_at":
                self.last_broadcast_at,

            "last_error":
                self.last_error,

            "active_websocket_clients":
                websocket_manager.connection_count,

            "read_only":
                True,

            "database_writes":
                False,

            "persistence_enabled":
                False,

            "live_telemetry_ingestion":
                False,

            "model_reprocessing":
                False,

            "diagnostics_reprocessing":
                False,

            "prognostics_reprocessing":
                False,

            "frontend_visualization_only":
                True,

            "timestamp":
                utc_now_iso(),
        }


replay_websocket_bridge = (
    ReplayWebSocketBridge()
)


def enable_replay_websocket_bridge(
) -> dict[str, Any]:

    return replay_websocket_bridge.enable()


def get_replay_websocket_bridge_status(
) -> dict[str, Any]:

    return replay_websocket_bridge.get_status()
