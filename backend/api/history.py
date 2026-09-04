from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from backend.mission.history import (
    MAX_MISSION_LIMIT,
    MAX_TELEMETRY_LIMIT,
    MISSION_HISTORY_VERSION,
    get_history_status,
    get_mission,
    get_mission_summary,
    get_mission_telemetry,
    get_mission_timeline,
    list_missions,
)

from backend.mission.post_flight_analysis import (
    POST_FLIGHT_ANALYSIS_VERSION,
    analyze_mission,
    get_post_flight_analysis_status,
)

HISTORY_API_VERSION = "1.1.0"

router = APIRouter(
    prefix="/api/history",
    tags=[
        "Mission History",
    ],
)

def _validate_mission_id(
    mission_id: str,
) -> str:

    try:

        return str(
            UUID(
                mission_id
            )
        )

    except (
        ValueError,
        TypeError,
        AttributeError,
    ) as exc:

        raise HTTPException(
            status_code=400,
            detail={
                "error":
                    "INVALID_MISSION_ID",

                "message":
                    "mission_id must be a valid UUID.",

                "mission_id":
                    mission_id,
            },
        ) from exc

def _service_failure(
    *,
    operation: str,
    exc: Exception,
) -> HTTPException:

    return HTTPException(
        status_code=503,
        detail={
            "error":
                "HISTORY_SERVICE_UNAVAILABLE",

            "operation":
                operation,

            "message":
                str(exc),

            "history_api_version":
                HISTORY_API_VERSION,
        },
    )

def _analysis_failure(
    *,
    operation: str,
    exc: Exception,
) -> HTTPException:

    return HTTPException(
        status_code=503,
        detail={
            "error":
                "POST_FLIGHT_ANALYSIS_UNAVAILABLE",

            "operation":
                operation,

            "message":
                str(exc),

            "history_api_version":
                HISTORY_API_VERSION,

            "post_flight_analysis_version":
                POST_FLIGHT_ANALYSIS_VERSION,
        },
    )

def _mission_not_found(
    mission_id: str,
) -> HTTPException:

    return HTTPException(
        status_code=404,
        detail={
            "error":
                "MISSION_NOT_FOUND",

            "mission_id":
                mission_id,

            "message":
                "No historical mission exists with this ID.",
        },
    )

@router.get("")
async def history_root() -> dict[str, Any]:

    return {

        "service":
            "PRATIRUP Mission History API",

        "api_version":
            HISTORY_API_VERSION,

        "history_service_version":
            MISSION_HISTORY_VERSION,

        "post_flight_analysis_version":
            POST_FLIGHT_ANALYSIS_VERSION,

        "status":
            "READY",

        "read_only":
            True,

        "capabilities": [

            "mission_listing",

            "mission_lookup",

            "historical_telemetry",

            "mission_summary",

            "mission_timeline",

            "post_flight_analysis",
        ],

        "post_flight_analysis":
            "READY",

        "historical_replay":
            "NOT_ACTIVE_YET",
    }

@router.get("/status")
async def history_status() -> dict[str, Any]:

    try:

        status = get_history_status()

        return {

            "success":
                True,

            "api_version":
                HISTORY_API_VERSION,

            "history":
                status,
        }

    except Exception as exc:

        raise _service_failure(
            operation=
                "history_status",

            exc=
                exc,
        )

@router.get("/analysis/status")
async def post_flight_analysis_status() -> dict[str, Any]:

    try:

        status = (
            get_post_flight_analysis_status()
        )

        return {

            "success":
                True,

            "api_version":
                HISTORY_API_VERSION,

            "analysis":
                status,
        }

    except Exception as exc:

        raise _analysis_failure(
            operation=
                "post_flight_analysis_status",

            exc=
                exc,
        )

@router.get("/missions")
async def history_missions(
    limit: int = Query(
        default=50,
        ge=1,
        le=MAX_MISSION_LIMIT,
    ),
    status: str | None = Query(
        default=None,
    ),
    source_type: str | None = Query(
        default=None,
    ),
) -> dict[str, Any]:

    try:

        result = list_missions(
            limit=
                limit,

            status=
                status,

            source_type=
                source_type,
        )

        return {

            "success":
                True,

            "api_version":
                HISTORY_API_VERSION,

            **result,
        }

    except Exception as exc:

        raise _service_failure(
            operation=
                "list_missions",

            exc=
                exc,
        )

@router.get(
    "/missions/{mission_id}"
)
async def history_mission(
    mission_id: str,
) -> dict[str, Any]:

    normalized_id = (
        _validate_mission_id(
            mission_id
        )
    )

    try:

        mission = get_mission(
            normalized_id
        )

        if mission is None:

            raise _mission_not_found(
                normalized_id
            )

        return {

            "success":
                True,

            "api_version":
                HISTORY_API_VERSION,

            "mission":
                mission,
        }

    except HTTPException:
        raise

    except Exception as exc:

        raise _service_failure(
            operation=
                "get_mission",

            exc=
                exc,
        )

@router.get(
    "/missions/{mission_id}/telemetry"
)
async def history_mission_telemetry(
    mission_id: str,
    limit: int = Query(
        default=1000,
        ge=1,
        le=MAX_TELEMETRY_LIMIT,
    ),
    newest_first: bool = Query(
        default=False,
    ),
    prefer_canonical: bool = Query(
        default=True,
    ),
) -> dict[str, Any]:

    normalized_id = (
        _validate_mission_id(
            mission_id
        )
    )

    try:

        result = (
            get_mission_telemetry(
                normalized_id,

                limit=
                    limit,

                newest_first=
                    newest_first,

                prefer_canonical=
                    prefer_canonical,
            )
        )

        if not result.get(
            "found",
            False,
        ):

            raise _mission_not_found(
                normalized_id
            )

        return {

            "api_version":
                HISTORY_API_VERSION,

            **result,
        }

    except HTTPException:
        raise

    except Exception as exc:

        raise _service_failure(
            operation=
                "get_mission_telemetry",

            exc=
                exc,
        )

@router.get(
    "/missions/{mission_id}/summary"
)
async def history_mission_summary(
    mission_id: str,
) -> dict[str, Any]:

    normalized_id = (
        _validate_mission_id(
            mission_id
        )
    )

    try:

        result = (
            get_mission_summary(
                normalized_id
            )
        )

        if not result.get(
            "found",
            False,
        ):

            raise _mission_not_found(
                normalized_id
            )

        return {

            "api_version":
                HISTORY_API_VERSION,

            **result,
        }

    except HTTPException:
        raise

    except Exception as exc:

        raise _service_failure(
            operation=
                "get_mission_summary",

            exc=
                exc,
        )

@router.get(
    "/missions/{mission_id}/timeline"
)
async def history_mission_timeline(
    mission_id: str,
    limit: int = Query(
        default=1000,
        ge=1,
        le=MAX_TELEMETRY_LIMIT,
    ),
) -> dict[str, Any]:

    normalized_id = (
        _validate_mission_id(
            mission_id
        )
    )

    try:

        result = (
            get_mission_timeline(
                normalized_id,

                limit=
                    limit,
            )
        )

        if not result.get(
            "found",
            False,
        ):

            raise _mission_not_found(
                normalized_id
            )

        return {

            "api_version":
                HISTORY_API_VERSION,

            **result,
        }

    except HTTPException:
        raise

    except Exception as exc:

        raise _service_failure(
            operation=
                "get_mission_timeline",

            exc=
                exc,
        )

@router.get(
    "/missions/{mission_id}/analysis"
)
async def history_mission_analysis(
    mission_id: str,
) -> dict[str, Any]:

    normalized_id = (
        _validate_mission_id(
            mission_id
        )
    )

    try:

        result = (
            analyze_mission(
                normalized_id
            )
        )

        if not result.get(
            "found",
            False,
        ):

            raise _mission_not_found(
                normalized_id
            )

        return {

            "api_version":
                HISTORY_API_VERSION,

            **result,
        }

    except HTTPException:
        raise

    except Exception as exc:

        raise _analysis_failure(
            operation=
                "analyze_mission",

            exc=
                exc,
        )
