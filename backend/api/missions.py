from __future__ import annotations

import inspect
import math

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import (
    APIRouter,
    HTTPException,
    Path,
)

from pydantic import BaseModel, Field

import backend.mission.simulation_player as simulation_player

from backend.mission.scenario import (
    get_scenario_status,
)

from backend.ingestion.simulation_adapter import (
    SimulationFault,
    clear_simulation_fault,
    clear_simulation_faults,
    get_simulation_fault_status,
    get_simulation_info,
    get_simulation_status,
    set_simulation_fault,
)

from backend.database.mission_persistence import (
    finish_mission_recording,
    get_mission_persistence_status,
    pause_mission_recording,
    restart_mission_recording,
    resume_mission_recording,
    start_mission_recording,
)

MISSIONS_API_VERSION = "1.1.0"

router = APIRouter(
    prefix="/api/missions",
    tags=["missions"],
)

SUPPORTED_SPEEDS = (
    0.5,
    1.0,
    2.0,
    5.0,
)

class SpeedRequest(BaseModel):
    speed: float = Field(
        ...,
        description=(
            "Simulation playback speed. "
            "Supported values: 0.5, 1, 2, 5."
        ),
    )

class SeekRequest(BaseModel):
    elapsed_time_sec: float = Field(
        ...,
        ge=0.0,
        description=(
            "Target simulated mission elapsed time in seconds."
        ),
    )

class TickRequest(BaseModel):
    delta_real_sec: float = Field(
        default=1.0,
        gt=0.0,
        description=(
            "Real-time delta passed to one deterministic "
            "simulation-player tick."
        ),
    )

class FaultRequest(BaseModel):
    fault_type: str = Field(
        ...,
        description=(
            "PRATIRUP demonstrator simulation fault."
        ),
    )

    severity: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description=(
            "Fault severity from 0.0 to 1.0."
        ),
    )

    ramp_sec: float = Field(
        default=0.0,
        ge=0.0,
        description=(
            "Optional time in simulated seconds for the "
            "fault to ramp to requested severity."
        ),
    )

def _utc_now() -> str:

    return (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

def _finite_number(
    value: Any,
) -> Optional[float]:

    if value is None:
        return None

    if isinstance(
        value,
        bool,
    ):
        return None

    try:
        number = float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None

    if not math.isfinite(number):
        return None

    return number

async def _call_player_function(
    function_name: str,
    *args: Any,
    **kwargs: Any,
) -> Any:

    function = getattr(
        simulation_player,
        function_name,
        None,
    )

    if function is None:
        raise RuntimeError(
            "Simulation Player does not expose "
            f"'{function_name}'."
        )

    result = function(
        *args,
        **kwargs,
    )

    if inspect.isawaitable(result):
        result = await result

    return result

def _player_status() -> Dict[str, Any]:

    function = getattr(
        simulation_player,
        "get_simulation_player_status",
        None,
    )

    if function is None:
        return {
            "available": False,
            "error": (
                "get_simulation_player_status "
                "is unavailable."
            ),
        }

    try:
        result = function()

        if isinstance(
            result,
            dict,
        ):
            return result

        return {
            "available": True,
            "value": result,
        }

    except Exception as exc:

        return {
            "available": False,
            "error": str(exc),
        }

def _player_info() -> Dict[str, Any]:

    function = getattr(
        simulation_player,
        "get_simulation_player_info",
        None,
    )

    if function is None:
        return {
            "available": False,
            "error": (
                "get_simulation_player_info "
                "is unavailable."
            ),
        }

    try:
        result = function()

        if isinstance(
            result,
            dict,
        ):
            return result

        return {
            "available": True,
            "value": result,
        }

    except Exception as exc:

        return {
            "available": False,
            "error": str(exc),
        }

def _scenario_status_safe() -> Dict[str, Any]:

    try:
        result = get_scenario_status()

        if isinstance(
            result,
            dict,
        ):
            return result

        return {
            "available": True,
            "value": result,
        }

    except Exception as exc:

        return {
            "available": False,
            "error": str(exc),
        }

def _adapter_status_safe() -> Dict[str, Any]:

    try:
        return get_simulation_status()

    except Exception as exc:

        return {
            "available": False,
            "error": str(exc),
        }

def _fault_status_safe() -> Dict[str, Any]:

    try:
        return (
            get_simulation_fault_status()
        )

    except Exception as exc:

        return {
            "enabled": False,
            "active_fault_count": 0,
            "active_faults": [],
            "error": str(exc),
        }

def _persistence_status_safe() -> Dict[str, Any]:

    try:
        result = get_mission_persistence_status()
        return result if isinstance(result, dict) else {"available": True, "value": result}
    except Exception as exc:
        return {"available": False, "error": str(exc)}

async def _start_persistence_safe() -> Dict[str, Any]:

    try:
        result = await start_mission_recording(
            source_type="SIMULATION",
            mission_name="PRATIRUP Simulation Mission",
        )
        return {"available": True, "success": True, "result": result}
    except Exception as exc:
        return {"available": False, "success": False, "error": str(exc)}

def _pause_persistence_safe() -> Dict[str, Any]:

    try:
        result = pause_mission_recording()
        return {"available": True, "success": True, "result": result}
    except Exception as exc:
        return {"available": False, "success": False, "error": str(exc)}

def _resume_persistence_safe() -> Dict[str, Any]:

    try:
        result = resume_mission_recording()
        success = result.get("success", True) if isinstance(result, dict) else True
        return {"available": True, "success": bool(success), "result": result}
    except Exception as exc:
        return {"available": False, "success": False, "error": str(exc)}

async def _finish_persistence_safe(*, final_status: str) -> Dict[str, Any]:

    try:
        result = await finish_mission_recording(final_status=final_status)
        return {"available": True, "success": True, "result": result}
    except Exception as exc:
        return {"available": False, "success": False, "error": str(exc)}

async def _restart_persistence_safe() -> Dict[str, Any]:

    try:
        result = await restart_mission_recording(source_type="SIMULATION")
        return {"available": True, "success": True, "result": result}
    except Exception as exc:
        return {"available": False, "success": False, "error": str(exc)}

def _combined_status() -> Dict[str, Any]:

    player = _player_status()

    return {
        "service": "missions_api",
        "version": MISSIONS_API_VERSION,
        "status": "READY",
        "simulation_player": player,
        "scenario": _scenario_status_safe(),
        "simulation_adapter": _adapter_status_safe(),
        "fault_injection": _fault_status_safe(),
        "persistence": _persistence_status_safe(),
        "timestamp": _utc_now(),
    }

def _normalize_fault_type(
    fault_type: str,
) -> str:

    value = str(
        fault_type
    ).strip().upper()

    try:
        return (
            SimulationFault(
                value
            ).value
        )

    except ValueError as exc:

        supported = [
            fault.value
            for fault
            in SimulationFault
        ]

        raise HTTPException(
            status_code=400,
            detail={
                "error":
                    "UNSUPPORTED_FAULT",

                "fault_type":
                    value,

                "supported_faults":
                    supported,
            },
        ) from exc

def _validate_speed(
    value: Any,
) -> float:

    speed = _finite_number(
        value
    )

    if speed is None:

        raise HTTPException(
            status_code=400,
            detail=(
                "Simulation speed must be "
                "a finite numeric value."
            ),
        )

    if speed not in SUPPORTED_SPEEDS:

        raise HTTPException(
            status_code=400,
            detail={
                "error":
                    "UNSUPPORTED_SPEED",

                "requested":
                    speed,

                "supported_speeds":
                    list(
                        SUPPORTED_SPEEDS
                    ),
            },
        )

    return speed

@router.get("")
async def missions_root(
) -> Dict[str, Any]:

    return {
        "service":
            "PRATIRUP Mission Control API",

        "version":
            MISSIONS_API_VERSION,

        "status":
            "READY",

        "base_path":
            "/api/missions",

        "timestamp":
            _utc_now(),
    }

@router.get("/status")
async def mission_status(
) -> Dict[str, Any]:

    return _combined_status()

@router.get("/info")
async def mission_info(
) -> Dict[str, Any]:

    return {
        "service":
            "missions_api",

        "version":
            MISSIONS_API_VERSION,

        "purpose":
            (
                "PRATIRUP mission simulation "
                "and fault-injection control API"
            ),

        "architecture": {
            "control_layer_only":
                True,

            "simulation_source_only":
                True,

            "modifies_can_fadec":
                False,

            "runs_physics_directly":
                False,

            "runs_diagnostics_directly":
                False,

            "runs_prognostics_directly":
                False,

            "uses_telemetry_pipeline":
                True,
        },

        "controls": [
            "play",
            "pause",
            "resume",
            "stop",
            "restart",
            "reset",
            "speed",
            "seek",
            "tick",
            "inject_fault",
            "clear_fault",
            "clear_faults",
        ],

        "supported_speeds":
            list(
                SUPPORTED_SPEEDS
            ),

        "player":
            _player_info(),

        "simulation_adapter":
            get_simulation_info(),

        "supported_faults": [
            fault.value
            for fault
            in SimulationFault
        ],

        "fault_semantics": {
            "severity_range":
                [
                    0.0,
                    1.0,
                ],

            "supports_ramp":
                True,

            "modifies_telemetry_only":
                True,

            "forces_diagnostics":
                False,

            "official_drdo_vrde_fault_model":
                False,
        },

        "data_semantics": {
            "zero_is_valid":
                True,

            "none_means_unavailable":
                True,
        },

        "timestamp":
            _utc_now(),
    }

@router.post("/play")
async def play_mission() -> Dict[str, Any]:

    try:
        result = await _call_player_function("play_simulation")
        persistence = await _start_persistence_safe()
        return {"success": True, "action": "play", "result": result, "persistence": persistence, "status": _combined_status(), "timestamp": _utc_now()}
    except Exception as exc:
        raise HTTPException(status_code=409, detail={"action": "play", "error": str(exc)}) from exc

@router.post("/pause")
async def pause_mission() -> Dict[str, Any]:

    try:
        result = await _call_player_function("pause_simulation")
        persistence = _pause_persistence_safe()
        return {"success": True, "action": "pause", "result": result, "persistence": persistence, "status": _combined_status(), "timestamp": _utc_now()}
    except Exception as exc:
        raise HTTPException(status_code=409, detail={"action": "pause", "error": str(exc)}) from exc

@router.post("/resume")
async def resume_mission() -> Dict[str, Any]:

    try:
        result = await _call_player_function("resume_simulation")
        persistence = _resume_persistence_safe()
        return {"success": True, "action": "resume", "result": result, "persistence": persistence, "status": _combined_status(), "timestamp": _utc_now()}
    except Exception as exc:
        raise HTTPException(status_code=409, detail={"action": "resume", "error": str(exc)}) from exc

@router.post("/stop")
async def stop_mission() -> Dict[str, Any]:

    try:
        result = await _call_player_function("stop_simulation")
        persistence = await _finish_persistence_safe(final_status="COMPLETED")
        return {"success": True, "action": "stop", "result": result, "persistence": persistence, "status": _combined_status(), "timestamp": _utc_now()}
    except Exception as exc:
        raise HTTPException(status_code=409, detail={"action": "stop", "error": str(exc)}) from exc

@router.post("/reset")
async def reset_mission() -> Dict[str, Any]:

    try:
        result = await _call_player_function("reset_simulation_player")
        persistence = await _finish_persistence_safe(final_status="RESET")
        return {"success": True, "action": "reset", "result": result, "persistence": persistence, "status": _combined_status(), "timestamp": _utc_now()}
    except Exception as exc:
        raise HTTPException(status_code=409, detail={"action": "reset", "error": str(exc)}) from exc

@router.post("/restart")
async def restart_mission() -> Dict[str, Any]:

    try:
        native_restart = getattr(simulation_player, "restart_simulation", None)
        if native_restart is not None:
            result = native_restart()
            if inspect.isawaitable(result):
                result = await result
        else:
            await _call_player_function("reset_simulation_player")
            result = await _call_player_function("play_simulation")
        persistence = await _restart_persistence_safe()
        return {"success": True, "action": "restart", "result": result, "persistence": persistence, "status": _combined_status(), "timestamp": _utc_now()}
    except Exception as exc:
        raise HTTPException(status_code=409, detail={"action": "restart", "error": str(exc)}) from exc

@router.post("/speed")
async def set_mission_speed(
    request: SpeedRequest,
) -> Dict[str, Any]:

    speed = _validate_speed(
        request.speed
    )

    try:

        result = await _call_player_function(
            "set_simulation_speed",
            speed,
        )

        return {
            "success":
                True,

            "action":
                "speed",

            "speed":
                speed,

            "result":
                result,

            "status":
                _combined_status(),

            "timestamp":
                _utc_now(),
        }

    except Exception as exc:

        raise HTTPException(
            status_code=409,
            detail={
                "action":
                    "speed",

                "error":
                    str(exc),
            },
        ) from exc

@router.post("/seek")
async def seek_mission(
    request: SeekRequest,
) -> Dict[str, Any]:

    elapsed = _finite_number(
        request.elapsed_time_sec
    )

    if (
        elapsed is None
        or elapsed < 0.0
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "elapsed_time_sec must be "
                "finite and non-negative."
            ),
        )

    try:

        native_seek = getattr(
            simulation_player,
            "seek_simulation",
            None,
        )

        if native_seek is not None:

            result = native_seek(
                elapsed
            )

            if inspect.isawaitable(
                result
            ):
                result = await result

        else:
            from backend.mission.scenario import (
                seek_scenario,
            )

            result = seek_scenario(
                elapsed
            )

        return {
            "success":
                True,

            "action":
                "seek",

            "elapsed_time_sec":
                elapsed,

            "result":
                result,

            "status":
                _combined_status(),

            "timestamp":
                _utc_now(),
        }

    except Exception as exc:

        raise HTTPException(
            status_code=409,
            detail={
                "action":
                    "seek",

                "error":
                    str(exc),
            },
        ) from exc

@router.post("/tick")
async def tick_mission(
    request: TickRequest,
) -> Dict[str, Any]:

    delta = _finite_number(
        request.delta_real_sec
    )

    if (
        delta is None
        or delta <= 0.0
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "delta_real_sec must be "
                "finite and greater than zero."
            ),
        )

    try:

        result = await _call_player_function(
            "tick_simulation",
            delta_real_sec=delta,
        )

        return {
            "success":
                True,

            "action":
                "tick",

            "delta_real_sec":
                delta,

            "result":
                result,

            "status":
                _combined_status(),

            "timestamp":
                _utc_now(),
        }

    except Exception as exc:

        raise HTTPException(
            status_code=409,
            detail={
                "action":
                    "tick",

                "error":
                    str(exc),
            },
        ) from exc

@router.get("/faults")
async def mission_faults(
) -> Dict[str, Any]:

    return {
        "service":
            "simulation_fault_injection",

        "version":
            "1.2.0",

        "supported_faults": [
            fault.value
            for fault
            in SimulationFault
        ],

        "status":
            _fault_status_safe(),

        "notes": [
            (
                "Fault models modify simulated telemetry only."
            ),
            (
                "Downstream diagnostics independently determine "
                "whether a simulated condition represents a fault."
            ),
            (
                "These are PRATIRUP engineering-demonstrator "
                "models, not official DRDO/VRDE failure models."
            ),
        ],

        "timestamp":
            _utc_now(),
    }

@router.post("/faults")
async def inject_mission_fault(
    request: FaultRequest,
) -> Dict[str, Any]:

    fault_type = _normalize_fault_type(
        request.fault_type
    )

    severity = _finite_number(
        request.severity
    )

    ramp_sec = _finite_number(
        request.ramp_sec
    )

    if severity is None:

        raise HTTPException(
            status_code=400,
            detail=(
                "Fault severity must be finite."
            ),
        )

    if not (
        0.0
        <= severity
        <= 1.0
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Fault severity must be "
                "between 0.0 and 1.0."
            ),
        )

    if (
        ramp_sec is None
        or ramp_sec < 0.0
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "ramp_sec must be finite "
                "and non-negative."
            ),
        )

    try:

        result = set_simulation_fault(
            fault_type,
            severity=severity,
            ramp_sec=ramp_sec,
        )

        return {
            "success":
                True,

            "action":
                "inject_fault",

            "fault_type":
                fault_type,

            "severity":
                severity,

            "ramp_sec":
                ramp_sec,

            "fault_status":
                result,

            "timestamp":
                _utc_now(),
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail={
                "action":
                    "inject_fault",

                "error":
                    str(exc),
            },
        ) from exc

@router.delete("/faults")
async def clear_all_mission_faults(
) -> Dict[str, Any]:

    try:

        result = (
            clear_simulation_faults()
        )

        return {
            "success":
                True,

            "action":
                "clear_all_faults",

            "fault_status":
                result,

            "timestamp":
                _utc_now(),
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail={
                "action":
                    "clear_all_faults",

                "error":
                    str(exc),
            },
        ) from exc

@router.delete(
    "/faults/{fault_type}"
)
async def clear_one_mission_fault(
    fault_type: str = Path(
        ...,
        description=(
            "Simulation fault type to clear."
        ),
    ),
) -> Dict[str, Any]:

    normalized = (
        _normalize_fault_type(
            fault_type
        )
    )

    try:

        result = (
            clear_simulation_fault(
                normalized
            )
        )

        return {
            "success":
                True,

            "action":
                "clear_fault",

            "fault_type":
                normalized,

            "fault_status":
                result,

            "timestamp":
                _utc_now(),
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail={
                "action":
                    "clear_fault",

                "fault_type":
                    normalized,

                "error":
                    str(exc),
            },
        ) from exc

@router.get("/health")
async def mission_api_health(
) -> Dict[str, Any]:

    player_status = (
        _player_status()
    )

    adapter_status = (
        _adapter_status_safe()
    )

    player_ok = (
        player_status.get(
            "available",
            True,
        )
        is not False
    )

    adapter_ok = (
        adapter_status.get(
            "last_error"
        )
        in (
            None,
            "",
        )
    )

    return {
        "service":
            "missions_api",

        "version":
            MISSIONS_API_VERSION,

        "healthy":
            bool(
                player_ok
                and adapter_ok
            ),

        "player_available":
            player_ok,

        "adapter_available":
            True,

        "simulation_source_only":
            True,

        "can_fadec_modified":
            False,

        "timestamp":
            _utc_now(),
    }
