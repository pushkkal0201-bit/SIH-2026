from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from backend.mission.replay import (
    REPLAY_ENGINE_VERSION,
    get_replay_service_status,
    historical_replay_engine,
)

REPLAY_API_VERSION = "1.0.0"

router = APIRouter(
    prefix="/api/replay",
    tags=["Historical Replay"],
)

def _validate_uuid(value: str) -> str:

    try:
        UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_MISSION_ID",
                "message": "mission_id must be a valid UUID.",
            },
        ) from exc

    return str(value)

def _raise_replay_failure(
    result: dict[str, Any],
    *,
    default_status_code: int = 400,
) -> None:

    if result.get("success", True):
        return

    error = result.get("error") or "REPLAY_OPERATION_FAILED"

    message = (
        result.get("message")
        or result.get("detail")
        or "Replay operation failed."
    )

    status_code = default_status_code

    if error in {
        "MISSION_NOT_FOUND",
        "REPLAY_MISSION_NOT_FOUND",
    }:
        status_code = 404

    elif error in {
        "REPLAY_NOT_LOADED",
        "NO_REPLAY_LOADED",
        "NO_MISSION_LOADED",
    }:
        status_code = 409

    elif error in {
        "INVALID_REPLAY_STATE",
        "REPLAY_ALREADY_PLAYING",
        "REPLAY_NOT_PLAYING",
        "REPLAY_NOT_PAUSED",
    }:
        status_code = 409

    elif error in {
        "INVALID_REPLAY_INDEX",
        "INVALID_REPLAY_PERCENT",
        "UNSUPPORTED_REPLAY_SPEED",
        "INVALID_REPLAY_SPEED",
    }:
        status_code = 400

    elif error in {
        "DATABASE_ERROR",
        "REPLAY_DATABASE_ERROR",
        "REPLAY_LOAD_FAILED",
    }:
        status_code = 503

    raise HTTPException(
        status_code=status_code,
        detail={
            "error": error,
            "message": message,
            "result": result,
        },
    )

def _success_response(
    operation: str,
    result: Any,
) -> dict[str, Any]:

    return {
        "success": True,
        "operation": operation,
        "api_version": REPLAY_API_VERSION,
        "replay_engine_version": REPLAY_ENGINE_VERSION,
        "result": result,
    }

@router.get("")
async def replay_root() -> dict[str, Any]:

    service = get_replay_service_status()

    return {
        "service": "PRATIRUP Historical Replay API",
        "api_version": REPLAY_API_VERSION,
        "replay_engine_version": REPLAY_ENGINE_VERSION,
        "architecture": "READ_ONLY_HISTORICAL_REPLAY",
        "read_only": service.get("read_only", True),
        "database_writes": service.get(
            "database_writes",
            False,
        ),
        "persistence_enabled": service.get(
            "persistence_enabled",
            False,
        ),
        "live_telemetry_ingestion": service.get(
            "live_telemetry_ingestion",
            False,
        ),
        "model_reprocessing": service.get(
            "model_reprocessing",
            False,
        ),
        "endpoints": {
            "status": "GET /api/replay/status",
            "frame": "GET /api/replay/frame",
            "load": "POST /api/replay/load/{mission_id}",
            "play": "POST /api/replay/play",
            "pause": "POST /api/replay/pause",
            "resume": "POST /api/replay/resume",
            "stop": "POST /api/replay/stop",
            "reset": "POST /api/replay/reset",
            "seek": "POST /api/replay/seek?index=...",
            "seek_percent": (
                "POST /api/replay/seek-percent?percent=..."
            ),
            "speed": "POST /api/replay/speed?speed=...",
        },
    }

@router.get("/status")
async def replay_status() -> dict[str, Any]:

    status = historical_replay_engine.get_status()
    service = get_replay_service_status()

    return {
        "success": True,
        "api_version": REPLAY_API_VERSION,
        "replay_engine_version": REPLAY_ENGINE_VERSION,
        "architecture": "READ_ONLY_HISTORICAL_REPLAY",
        "replay": status,
        "isolation": {
            "read_only": service.get(
                "read_only",
                True,
            ),
            "database_writes": service.get(
                "database_writes",
                False,
            ),
            "persistence_enabled": service.get(
                "persistence_enabled",
                False,
            ),
            "live_telemetry_ingestion": service.get(
                "live_telemetry_ingestion",
                False,
            ),
            "model_reprocessing": service.get(
                "model_reprocessing",
                False,
            ),
        },
    }

@router.get("/frame")
async def replay_current_frame() -> dict[str, Any]:

    frame = historical_replay_engine.get_current_frame()

    if frame is None:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "NO_REPLAY_FRAME_AVAILABLE",
                "message": (
                    "No historical replay frame is currently available. "
                    "Load a mission first."
                ),
            },
        )

    return _success_response(
        "CURRENT_FRAME",
        frame,
    )

@router.post("/load/{mission_id}")
async def replay_load(
    mission_id: str,
) -> dict[str, Any]:

    validated_id = _validate_uuid(mission_id)

    try:
        result = await historical_replay_engine.load(
            validated_id
        )

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "REPLAY_LOAD_FAILED",
                "message": str(exc),
            },
        ) from exc

    _raise_replay_failure(
        result,
        default_status_code=404,
    )

    return _success_response(
        "LOAD",
        result,
    )

@router.post("/play")
async def replay_play() -> dict[str, Any]:

    try:
        result = await historical_replay_engine.play()

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "REPLAY_PLAY_FAILED",
                "message": str(exc),
            },
        ) from exc

    _raise_replay_failure(result)

    return _success_response(
        "PLAY",
        result,
    )

@router.post("/pause")
async def replay_pause() -> dict[str, Any]:

    try:
        result = await historical_replay_engine.pause()

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "REPLAY_PAUSE_FAILED",
                "message": str(exc),
            },
        ) from exc

    _raise_replay_failure(result)

    return _success_response(
        "PAUSE",
        result,
    )

@router.post("/resume")
async def replay_resume() -> dict[str, Any]:

    try:
        result = await historical_replay_engine.resume()

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "REPLAY_RESUME_FAILED",
                "message": str(exc),
            },
        ) from exc

    _raise_replay_failure(result)

    return _success_response(
        "RESUME",
        result,
    )

@router.post("/stop")
async def replay_stop() -> dict[str, Any]:

    try:
        result = await historical_replay_engine.stop()

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "REPLAY_STOP_FAILED",
                "message": str(exc),
            },
        ) from exc

    _raise_replay_failure(result)

    return _success_response(
        "STOP",
        result,
    )

@router.post("/reset")
async def replay_reset() -> dict[str, Any]:

    try:
        result = await historical_replay_engine.reset()

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "REPLAY_RESET_FAILED",
                "message": str(exc),
            },
        ) from exc

    _raise_replay_failure(result)

    return _success_response(
        "RESET",
        result,
    )

@router.post("/seek")
async def replay_seek(
    index: int = Query(
        ...,
        ge=0,
        description=(
            "Zero-based historical replay frame index."
        ),
    ),
) -> dict[str, Any]:

    try:
        result = await historical_replay_engine.seek(
            index
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "REPLAY_SEEK_FAILED",
                "message": str(exc),
            },
        ) from exc

    _raise_replay_failure(result)

    return _success_response(
        "SEEK",
        result,
    )

@router.post("/seek-percent")
async def replay_seek_percent(
    percent: float = Query(
        ...,
        ge=0.0,
        le=100.0,
        description=(
            "Historical mission position from 0 to 100 percent."
        ),
    ),
) -> dict[str, Any]:

    try:
        result = (
            await historical_replay_engine.seek_percent(
                percent
            )
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "REPLAY_PERCENT_SEEK_FAILED",
                "message": str(exc),
            },
        ) from exc

    _raise_replay_failure(result)

    return _success_response(
        "SEEK_PERCENT",
        result,
    )

@router.post("/speed")
async def replay_speed(
    speed: float = Query(
        ...,
        gt=0.0,
        description=(
            "Replay speed. Supported demonstrator speeds are "
            "0.5, 1.0, 2.0 and 5.0."
        ),
    ),
) -> dict[str, Any]:

    try:
        result = await historical_replay_engine.set_speed(
            speed
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "REPLAY_SPEED_FAILED",
                "message": str(exc),
            },
        ) from exc

    _raise_replay_failure(result)

    return _success_response(
        "SPEED",
        result,
    )
