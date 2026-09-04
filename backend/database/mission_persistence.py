from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from backend.database.database import database_session

from backend.database.repository import (
    create_mission,
    get_or_create_engine,
    update_mission_status,
)

from backend.database.persistence_context import (
    clear_active_mission,
    get_active_mission,
    get_persistence_context_status,
    set_active_mission,
)

from backend.database.persistence_service import (
    telemetry_persistence_service,
)

MISSION_PERSISTENCE_VERSION = "1.1.0"

ENGINE_CODE = "PRATIRUP-DEMO-180HP"

ENGINE_NAME = (
    "PRATIRUP 180 HP Aero-Piston "
    "Engineering Demonstrator"
)

ENGINE_TYPE = "AERO_PISTON"

RATED_POWER_HP = 180.0

ENGINE_DESCRIPTION = (
    "PRATIRUP engineering-demonstrator engine baseline. "
    "Inspired by the project 180 HP UAV piston-engine context. "
    "This database record does not represent an operational "
    "DRDO/VRDE engine asset."
)
def _utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


def _new_mission_code() -> str:

    now = _utc_now()

    timestamp = now.strftime(
        "%Y%m%dT%H%M%S%fZ"
    )

    suffix = (
        uuid4()
        .hex[:8]
        .upper()
    )

    return (
        f"PRATIRUP-SIM-"
        f"{timestamp}-"
        f"{suffix}"
    )

async def start_mission_recording(
    *,
    source_type: str = "SIMULATION",
    mission_name: Optional[str] = None,
    profile_name: Optional[str] = None,
) -> Dict[str, Any]:

    existing = get_active_mission()

    if existing is not None:

        return {
            "success": True,
            "created": False,
            "already_active": True,

            "mission_id":
                str(existing.mission_id),

            "mission_code":
                existing.mission_code,

            "engine_id":
                str(existing.engine_id),

            "source_type":
                existing.source_type,

            "started_at":
                existing.started_at.isoformat(),
        }

    started_at = _utc_now()

    mission_code = (
        _new_mission_code()
    )

    with database_session() as db:

        engine = get_or_create_engine(
            db,

            engine_code=
                ENGINE_CODE,

            engine_name=
                ENGINE_NAME,

            engine_type=
                ENGINE_TYPE,

            rated_power_hp=
                RATED_POWER_HP,

            description=
                ENGINE_DESCRIPTION,
        )

        mission = create_mission(
            db,

            engine_id=
                engine.id,

            mission_code=
                mission_code,

            mission_name=(
                mission_name
                or
                "PRATIRUP Simulation Mission"
            ),

            source_type=
                source_type,

            status=
                "RUNNING",

            profile_name=
                profile_name,

            started_at=
                started_at,

            notes=(
                "PRATIRUP Digital Twin "
                "mission recording session."
            ),

            metadata_json={

                "problem_statement_id":
                    "26054",

                "persistence_version":
                    MISSION_PERSISTENCE_VERSION,

                "engineering_demonstrator":
                    True,

                "official_flight_record":
                    False,
            },
        )

        mission_id = mission.id
        engine_id = engine.id

    set_active_mission(
        mission_id=
            mission_id,

        mission_code=
            mission_code,

        engine_id=
            engine_id,

        source_type=
            source_type,

        started_at=
            started_at,
    )

    await (
        telemetry_persistence_service
        .start()
    )

    return {
        "success": True,
        "created": True,
        "already_active": False,

        "mission_id":
            str(mission_id),

        "mission_code":
            mission_code,

        "engine_id":
            str(engine_id),

        "source_type":
            source_type,

        "started_at":
            started_at.isoformat(),
    }

def pause_mission_recording(
) -> Dict[str, Any]:

    active = get_active_mission()

    if active is None:

        return {
            "success": True,
            "active": False,

            "message":
                "No persistence mission is active.",
        }

    return {
        "success": True,
        "active": True,

        "mission_id":
            str(active.mission_id),

        "mission_code":
            active.mission_code,

        "message":
            "Mission recording context preserved.",
    }

def resume_mission_recording(
) -> Dict[str, Any]:

    active = get_active_mission()

    if active is None:

        return {
            "success": False,
            "active": False,

            "message":
                "No persistence mission exists to resume.",
        }

    return {
        "success": True,
        "active": True,

        "mission_id":
            str(active.mission_id),

        "mission_code":
            active.mission_code,

        "message":
            "Existing mission recording resumed.",
    }
async def finish_mission_recording(
    *,
    final_status: str = "COMPLETED",
) -> Dict[str, Any]:


    active = get_active_mission()

    if active is None:

        return {
            "success": True,
            "closed": False,

            "message":
                "No active persistence mission.",
        }
    flushed = await (
        telemetry_persistence_service
        .flush_all()
    )


    persistence_status = (
        telemetry_persistence_service
        .get_status()
    )

    remaining_buffer = int(
        persistence_status.get(
            "buffer_size",
            0,
        )
    )

    persistence_error = (
        persistence_status.get(
            "last_error"
        )
    )

    ended_at = _utc_now()

    duration_sec = max(
        0.0,
        (
            ended_at
            - active.started_at
        ).total_seconds(),
    )

    with database_session() as db:

        from backend.database.models import (
            Mission,
        )

        mission = db.get(
            Mission,
            active.mission_id,
        )

        if mission is None:

            raise RuntimeError(
                "Active persistence mission "
                "was not found in PostgreSQL."
            )

        update_mission_status(
            db,
            mission,

            status=
                final_status,

            ended_at=
                ended_at,

            duration_sec=
                duration_sec,
        )

    result = {
        "success": True,
        "closed": True,

        "mission_id":
            str(active.mission_id),

        "mission_code":
            active.mission_code,

        "final_status":
            final_status,

        "started_at":
            active.started_at.isoformat(),

        "ended_at":
            ended_at.isoformat(),

        "duration_sec":
            duration_sec,


        "flushed_frames":
            flushed,

        "remaining_buffer":
            remaining_buffer,

        "persistence_complete":
            remaining_buffer == 0,

        "persistence_error":
            persistence_error,
    }

    clear_active_mission()

    return result

async def abort_mission_recording(
) -> Dict[str, Any]:

    return await (
        finish_mission_recording(
            final_status=
                "ABORTED"
        )
    )

async def restart_mission_recording(
    *,
    source_type: str = "SIMULATION",
) -> Dict[str, Any]:

    previous = await (
        finish_mission_recording(
            final_status=
                "RESTARTED"
        )
    )

    current = await (
        start_mission_recording(
            source_type=
                source_type
        )
    )

    return {
        "success": True,

        "previous":
            previous,

        "current":
            current,
    }

def get_mission_persistence_status(
) -> Dict[str, Any]:

    return {
        "service":
            "mission_persistence",

        "version":
            MISSION_PERSISTENCE_VERSION,

        "context":
            get_persistence_context_status(),

        "writer":
            (
                telemetry_persistence_service
                .get_status()
            ),
    }
