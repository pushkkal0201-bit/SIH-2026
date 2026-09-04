from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(
    prefix="/api/system",
    tags=["System"],
)

SYSTEM_NAME = "PRATIRUP"

SYSTEM_VERSION = "0.1.0"

PROBLEM_STATEMENT_ID = "26054"

ORGANIZATION = "DRDO"

CATEGORY = "Software"

THEME = "Robotics and Drones"

SERVICE_STATE = {

    "backend":
        "ONLINE",

    "telemetry":
        "READY",

    "websocket":
        "READY",

    "database":
        "NOT_CONFIGURED",

    "ai":
        "NOT_CONFIGURED",

    "can":
        "NOT_CONNECTED",

    "fadec":
        "NOT_CONNECTED",

    "digital_twin":
        "FRONTEND_PROTOTYPE",

    "physics":
        "FRONTEND_PROTOTYPE",

    "diagnostics":
        "FRONTEND_PROTOTYPE",

    "prognostics":
        "FRONTEND_PROTOTYPE",

    "mission_intelligence":
        "FRONTEND_PROTOTYPE",

}


def utc_timestamp():

    return datetime.now(
        timezone.utc
    ).isoformat()


@router.get("")
async def get_system_status():

    return {

        "system":
            SYSTEM_NAME,

        "version":
            SYSTEM_VERSION,

        "problem_statement_id":
            PROBLEM_STATEMENT_ID,

        "status":
            "ONLINE",

        "mode":
            "DEVELOPMENT",

        "services": {

            "backend":
                SERVICE_STATE[
                    "backend"
                ],

            "telemetry":
                SERVICE_STATE[
                    "telemetry"
                ],

            "websocket":
                SERVICE_STATE[
                    "websocket"
                ],

            "database":
                SERVICE_STATE[
                    "database"
                ],

            "ai":
                SERVICE_STATE[
                    "ai"
                ],

            "can":
                SERVICE_STATE[
                    "can"
                ],

            "fadec":
                SERVICE_STATE[
                    "fadec"
                ],

            "digital_twin":
                SERVICE_STATE[
                    "digital_twin"
                ],

            "physics":
                SERVICE_STATE[
                    "physics"
                ],

            "diagnostics":
                SERVICE_STATE[
                    "diagnostics"
                ],

            "prognostics":
                SERVICE_STATE[
                    "prognostics"
                ],

            "mission_intelligence":
                SERVICE_STATE[
                    "mission_intelligence"
                ],

        },

        "timestamp":
            utc_timestamp(),

    }


@router.get("/services")
async def get_service_status():

    return {

        "system":
            SYSTEM_NAME,

        "services":
            SERVICE_STATE.copy(),

        "timestamp":
            utc_timestamp(),

    }


@router.get("/info")
async def get_system_information():

    return {

        "name":
            SYSTEM_NAME,

        "full_name":
            "PRATIRUP Digital Twin Framework",

        "description":
            (
                "Digital Twin framework for real-time "
                "health monitoring, diagnostics, "
                "prognostics and mission intelligence "
                "for an aero-piston engine used in "
                "MALE UAV applications."
            ),

        "problem_statement_id":
            PROBLEM_STATEMENT_ID,

        "organization":
            ORGANIZATION,

        "category":
            CATEGORY,

        "theme":
            THEME,

        "version":
            SYSTEM_VERSION,

        "backend_framework":
            "FastAPI",

        "current_mode":
            "DEVELOPMENT",

        "data_source":
            "SIMULATION",

        "real_engine_connection":
            False,

        "timestamp":
            utc_timestamp(),

    }


def set_service_status(
    service_name: str,
    status: str
) -> bool:

    if (
        service_name not in
        SERVICE_STATE
    ):

        return False

    SERVICE_STATE[
        service_name
    ] = str(
        status
    ).upper()

    return True


def get_service_status_value(
    service_name: str
):

    return SERVICE_STATE.get(
        service_name,
        "UNKNOWN"
    )


def get_all_service_states():

    return SERVICE_STATE.copy()
