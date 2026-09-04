from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
)

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from backend.api.system import (
    router as system_router,
)

from backend.api.telemetry import (
    router as telemetry_router,
)

from backend.api.missions import (
    router as missions_router,
)

from backend.api.history import (
    router as history_router,
)

from backend.api.replay import (
    router as replay_router,
)

from backend.services.websocket_manager import (
    websocket_manager,
)

from backend.services.replay_websocket_bridge import (
    enable_replay_websocket_bridge,
    get_replay_websocket_bridge_status,
)

APP_NAME = (
    "PRATIRUP Digital Twin Backend"
)

APP_VERSION = "0.3.1"

PROBLEM_STATEMENT_ID = "26054"


def utc_now_iso() -> str:

    return datetime.now(
        timezone.utc
    ).isoformat()


def get_application_services() -> dict:

    replay_bridge = (
        get_replay_websocket_bridge_status()
    )

    return {

        "system":
            "READY",

        "telemetry":
            "READY",

        "missions":
            "READY",

        "simulation":
            "READY",

        "history":
            "READY",

        "post_flight_analysis":
            "READY",

        "replay":
            "READY",

        "replay_websocket_bridge":
            replay_bridge.get(
                "status",
                "UNKNOWN",
            ),

        "websocket":
            "READY",

        "can_fadec":
            "NOT_CONNECTED",

        "database":
            "NOT_CONFIGURED",

        "ai":
            "PROTOTYPE",
    }


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):

    print()
    print(
        f"[PRATIRUP] Backend "
        f"{APP_VERSION} starting..."
    )

    print(
        "[PRATIRUP] Initial mode: "
        "SIMULATION / DEVELOPMENT"
    )

    print(
        "[PRATIRUP] System API: READY"
    )

    print(
        "[PRATIRUP] Telemetry API: READY"
    )

    print(
        "[PRATIRUP] Mission Simulation API: READY"
    )

    print(
        "[PRATIRUP] Mission History API: READY"
    )

    print(
        "[PRATIRUP] Post-Flight Analysis: READY"
    )

    print(
        "[PRATIRUP] Historical Replay API: READY"
    )

    print(
        "[PRATIRUP] Historical Replay mode: "
        "READ ONLY"
    )

    replay_bridge_status = (
        enable_replay_websocket_bridge()
    )

    print(
        "[PRATIRUP] Replay WebSocket Bridge: "
        f"{replay_bridge_status['status']}"
    )

    print(
        "[PRATIRUP] Replay WebSocket Architecture: "
        f"{replay_bridge_status['architecture']}"
    )

    print(
        "[PRATIRUP] Replay WebSocket Message Type: "
        f"{replay_bridge_status['message_type']}"
    )

    print(
        "[PRATIRUP] Real CAN / FADEC "
        "connection is not active yet."
    )

    print(
        "[PRATIRUP] Backend startup complete."
    )

    print()

    yield

    print()
    print(
        "[PRATIRUP] Backend shutting down..."
    )

    await (
        websocket_manager.disconnect_all()
    )

    print(
        "[PRATIRUP] WebSocket clients disconnected."
    )

    print(
        "[PRATIRUP] Backend shutdown complete."
    )


app = FastAPI(

    title=
        APP_NAME,

    version=
        APP_VERSION,

    description=(
        "Backend services for the PRATIRUP "
        "MALE UAV aero-piston engine "
        "Digital Twin platform."
    ),

    lifespan=
        lifespan,
)

ALLOWED_ORIGINS = [

    "http://localhost:5500",

    "http://127.0.0.1:5500",

    "http://localhost:5501",

    "http://127.0.0.1:5501",

    "http://localhost:3000",

    "http://127.0.0.1:3000",
]

app.add_middleware(

    CORSMiddleware,

    allow_origins=
        ALLOWED_ORIGINS,

    allow_credentials=
        True,

    allow_methods=[
        "*"
    ],

    allow_headers=[
        "*"
    ],
)

app.include_router(
    system_router
)

app.include_router(
    telemetry_router
)

app.include_router(
    missions_router
)

app.include_router(
    history_router
)

app.include_router(
    replay_router
)


@app.get("/")
async def root():

    replay_bridge = (
        get_replay_websocket_bridge_status()
    )

    return {

        "application":
            APP_NAME,

        "version":
            APP_VERSION,

        "problem_statement_id":
            PROBLEM_STATEMENT_ID,

        "status":
            "running",

        "mode":
            "development",

        "services":
            get_application_services(),

        "historical_replay": {

            "status":
                "READY",

            "mode":
                "READ_ONLY",

            "websocket_bridge":
                replay_bridge.get(
                    "status",
                    "UNKNOWN",
                ),

            "websocket_message_type":
                replay_bridge.get(
                    "message_type",
                    "replay_telemetry",
                ),

            "frontend_visualization_only":
                True,

            "database_writes":
                False,

            "live_telemetry_ingestion":
                False,

            "model_reprocessing":
                False,
        },

        "timestamp":
            utc_now_iso(),
    }


@app.get("/health")
async def health():

    replay_bridge = (
        get_replay_websocket_bridge_status()
    )

    return {

        "status":
            "ok",

        "backend":
            "ONLINE",

        "version":
            APP_VERSION,

        "problem_statement_id":
            PROBLEM_STATEMENT_ID,

        "database":
            "NOT_CONFIGURED",

        "ai":
            "PROTOTYPE",

        "telemetry":
            "READY",

        "missions":
            "READY",

        "simulation":
            "READY",

        "history":
            "READY",

        "replay":
            "READY",

        "can":
            "NOT_CONNECTED",

        "services":
            get_application_services(),

        "replay_websocket_bridge": {

            "status":
                replay_bridge.get(
                    "status",
                    "UNKNOWN",
                ),

            "enabled":
                replay_bridge.get(
                    "enabled",
                    False,
                ),

            "architecture":
                replay_bridge.get(
                    "architecture",
                ),

            "message_type":
                replay_bridge.get(
                    "message_type",
                ),

            "frames_received":
                replay_bridge.get(
                    "frames_received",
                    0,
                ),

            "frames_broadcast":
                replay_bridge.get(
                    "frames_broadcast",
                    0,
                ),

            "total_client_deliveries":
                replay_bridge.get(
                    "total_client_deliveries",
                    0,
                ),

            "active_websocket_clients":
                replay_bridge.get(
                    "active_websocket_clients",
                    0,
                ),

            "last_sequence":
                replay_bridge.get(
                    "last_sequence",
                ),

            "last_mission_id":
                replay_bridge.get(
                    "last_mission_id",
                ),

            "last_error":
                replay_bridge.get(
                    "last_error",
                ),

            "database_writes":
                False,

            "persistence_enabled":
                False,

            "live_telemetry_ingestion":
                False,

            "model_reprocessing":
                False,
        },

        "timestamp":
            utc_now_iso(),
    }


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
):

    await websocket_manager.connect(
        websocket
    )

    try:

        replay_bridge = (
            get_replay_websocket_bridge_status()
        )

        await websocket_manager.send_personal(

            websocket,

            {

                "type":
                    "system_status",

                "status":
                    "ONLINE",

                "backend":
                    "PRATIRUP",

                "version":
                    APP_VERSION,

                "problem_statement_id":
                    PROBLEM_STATEMENT_ID,

                "services":
                    get_application_services(),

                "replay": {

                    "status":
                        "READY",

                    "mode":
                        "READ_ONLY",

                    "websocket_bridge":
                        replay_bridge.get(
                            "status",
                            "UNKNOWN",
                        ),

                    "message_type":
                        "replay_telemetry",

                    "database_writes":
                        False,

                    "live_telemetry_ingestion":
                        False,

                    "model_reprocessing":
                        False,
                },

                "timestamp":
                    utc_now_iso(),
            }
        )

        while True:

            message = (
                await websocket.receive_json()
            )

            await process_client_message(
                websocket,
                message,
            )

    except WebSocketDisconnect:

        websocket_manager.disconnect(
            websocket
        )

        print(
            "[PRATIRUP] WebSocket "
            "client disconnected."
        )

    except Exception as exc:

        websocket_manager.disconnect(
            websocket
        )

        print(
            "[PRATIRUP] WebSocket error:",
            exc,
        )


async def process_client_message(
    websocket: WebSocket,
    message: dict,
):

    message_type = (

        message.get(
            "type"
        )

        if isinstance(
            message,
            dict,
        )

        else None
    )

    if message_type == "client_hello":

        await websocket_manager.send_personal(

            websocket,

            {

                "type":
                    "heartbeat",

                "backend":
                    "PRATIRUP",

                "status":
                    "ONLINE",

                "version":
                    APP_VERSION,

                "timestamp":
                    utc_now_iso(),
            }
        )

        return

    if message_type == "ping":

        await websocket_manager.send_personal(

            websocket,

            {

                "type":
                    "heartbeat",

                "status":
                    "ONLINE",

                "timestamp":
                    utc_now_iso(),
            }
        )

        return

    if message_type == "get_system_status":

        replay_bridge = (
            get_replay_websocket_bridge_status()
        )

        await websocket_manager.send_personal(

            websocket,

            {

                "type":
                    "system_status",

                "backend":
                    "PRATIRUP",

                "version":
                    APP_VERSION,

                "services":
                    get_application_services(),

                "replay": {

                    "status":
                        "READY",

                    "mode":
                        "READ_ONLY",

                    "bridge_status":
                        replay_bridge.get(
                            "status",
                            "UNKNOWN",
                        ),

                    "message_type":
                        "replay_telemetry",

                    "frames_received":
                        replay_bridge.get(
                            "frames_received",
                            0,
                        ),

                    "frames_broadcast":
                        replay_bridge.get(
                            "frames_broadcast",
                            0,
                        ),

                    "database_writes":
                        False,

                    "live_telemetry_ingestion":
                        False,

                    "model_reprocessing":
                        False,
                },

                "timestamp":
                    utc_now_iso(),
            }
        )

        return

    if message_type == "get_replay_status":

        replay_bridge = (
            get_replay_websocket_bridge_status()
        )

        await websocket_manager.send_personal(

            websocket,

            {

                "type":
                    "replay_status",

                "status":
                    replay_bridge,

                "timestamp":
                    utc_now_iso(),
            }
        )

        return

    await websocket_manager.send_personal(

        websocket,

        {

            "type":
                "server_message",

            "message":
                "Message received.",

            "received_type":
                message_type or "UNKNOWN",

            "timestamp":
                utc_now_iso(),
        }
    )


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "backend.main:app",

        host=
            "127.0.0.1",

        port=
            8000,

        reload=
            False,
    )
