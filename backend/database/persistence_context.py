from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, Optional
from uuid import UUID


PERSISTENCE_CONTEXT_VERSION = "1.0.0"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ActivePersistenceMission:
    mission_id: UUID
    mission_code: str
    engine_id: UUID
    source_type: str
    started_at: datetime


_lock = RLock()

_active_mission: Optional[
    ActivePersistenceMission
] = None


def set_active_mission(
    *,
    mission_id: UUID,
    mission_code: str,
    engine_id: UUID,
    source_type: str,
    started_at: Optional[datetime] = None,
) -> ActivePersistenceMission:
    """
    Set the mission that should receive new telemetry records.
    """

    global _active_mission

    mission = ActivePersistenceMission(
        mission_id=mission_id,
        mission_code=str(mission_code),
        engine_id=engine_id,
        source_type=str(source_type),
        started_at=started_at or _utc_now(),
    )

    with _lock:
        _active_mission = mission

    return mission


def clear_active_mission() -> None:
    """
    Stop associating future telemetry with a database mission.

    Existing PostgreSQL history is never deleted.
    """

    global _active_mission

    with _lock:
        _active_mission = None


def get_active_mission(
) -> Optional[ActivePersistenceMission]:

    with _lock:

        if _active_mission is None:
            return None

        return ActivePersistenceMission(
            mission_id=_active_mission.mission_id,
            mission_code=_active_mission.mission_code,
            engine_id=_active_mission.engine_id,
            source_type=_active_mission.source_type,
            started_at=_active_mission.started_at,
        )


def get_active_mission_id(
) -> Optional[UUID]:

    with _lock:

        if _active_mission is None:
            return None

        return _active_mission.mission_id


def has_active_mission() -> bool:

    with _lock:
        return _active_mission is not None


def get_persistence_context_status(
) -> Dict[str, Any]:

    with _lock:

        mission = _active_mission

        if mission is None:

            return {
                "service":
                    "persistence_mission_context",

                "version":
                    PERSISTENCE_CONTEXT_VERSION,

                "active":
                    False,

                "mission_id":
                    None,

                "mission_code":
                    None,

                "engine_id":
                    None,

                "source_type":
                    None,

                "started_at":
                    None,
            }

        return {
            "service":
                "persistence_mission_context",

            "version":
                PERSISTENCE_CONTEXT_VERSION,

            "active":
                True,

            "mission_id":
                str(mission.mission_id),

            "mission_code":
                mission.mission_code,

            "engine_id":
                str(mission.engine_id),

            "source_type":
                mission.source_type,

            "started_at":
                mission.started_at.isoformat(),
        }
