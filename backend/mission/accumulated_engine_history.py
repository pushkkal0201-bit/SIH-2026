from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from math import isfinite
from typing import Any, Dict, List, Optional
from uuid import uuid4


VERSION = "1.0.0"


class MissionHistoryState(str, Enum):
    IDLE = "IDLE"
    MISSION_ACTIVE = "MISSION_ACTIVE"
    MISSION_COMPLETED = "MISSION_COMPLETED"


@dataclass(frozen=True)
class MissionEngineHistoryRecord:
    record_id: str
    mission_id: str
    sequence_number: int

    start_engine_hours: float
    mission_runtime_hours: float
    end_engine_hours: float

    synthetic: bool = True
    measured_engine_hours: bool = False
    database_persisted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AccumulatedEngineHistory:

    def __init__(
        self,
        initial_engine_hours: float = 0.0,
    ) -> None:

        self._validate_nonnegative_finite(
            initial_engine_hours,
            "initial_engine_hours",
        )

        self._initial_engine_hours = float(
            initial_engine_hours
        )

        self._accumulated_engine_hours = float(
            initial_engine_hours
        )

        self._records: List[
            MissionEngineHistoryRecord
        ] = []

        self._state = MissionHistoryState.IDLE

        self._active_mission_id: Optional[str] = None
        self._active_start_hours: Optional[float] = None


    @staticmethod
    def _validate_nonnegative_finite(
        value: Any,
        field_name: str,
    ) -> None:

        if isinstance(value, bool):
            raise ValueError(
                f"{field_name} must be a finite non-negative number."
            )

        if not isinstance(
            value,
            (int, float),
        ):
            raise ValueError(
                f"{field_name} must be a finite non-negative number."
            )

        numeric = float(value)

        if not isfinite(numeric):
            raise ValueError(
                f"{field_name} must be finite."
            )

        if numeric < 0:
            raise ValueError(
                f"{field_name} cannot be negative."
            )


    @property
    def version(self) -> str:
        return VERSION

    @property
    def state(self) -> MissionHistoryState:
        return self._state

    @property
    def accumulated_engine_hours(self) -> float:
        return self._accumulated_engine_hours

    @property
    def mission_count(self) -> int:
        return len(self._records)

    @property
    def active_mission_id(self) -> Optional[str]:
        return self._active_mission_id

    @property
    def records(self) -> List[
        MissionEngineHistoryRecord
    ]:
        return list(self._records)


    def start_mission(
        self,
        mission_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        if (
            self._state
            == MissionHistoryState.MISSION_ACTIVE
        ):
            raise RuntimeError(
                "A mission is already active."
            )

        resolved_mission_id = (
            mission_id.strip()
            if isinstance(mission_id, str)
            and mission_id.strip()
            else str(uuid4())
        )

        self._active_mission_id = (
            resolved_mission_id
        )

        self._active_start_hours = (
            self._accumulated_engine_hours
        )

        self._state = (
            MissionHistoryState.MISSION_ACTIVE
        )

        return {
            "mission_id": self._active_mission_id,
            "start_engine_hours": (
                self._active_start_hours
            ),
            "accumulated_engine_hours": (
                self._accumulated_engine_hours
            ),
            "synthetic": True,
            "database_writes": False,
        }


    def complete_mission(
        self,
        mission_runtime_hours: float,
    ) -> MissionEngineHistoryRecord:

        if (
            self._state
            != MissionHistoryState.MISSION_ACTIVE
        ):
            raise RuntimeError(
                "No active mission exists."
            )

        self._validate_nonnegative_finite(
            mission_runtime_hours,
            "mission_runtime_hours",
        )

        runtime = float(
            mission_runtime_hours
        )

        if self._active_start_hours is None:
            raise RuntimeError(
                "Active mission start hours are unavailable."
            )

        if self._active_mission_id is None:
            raise RuntimeError(
                "Active mission ID is unavailable."
            )

        start_hours = float(
            self._active_start_hours
        )

        end_hours = (
            start_hours + runtime
        )

        record = MissionEngineHistoryRecord(
            record_id=str(uuid4()),
            mission_id=self._active_mission_id,
            sequence_number=len(self._records) + 1,
            start_engine_hours=start_hours,
            mission_runtime_hours=runtime,
            end_engine_hours=end_hours,
            synthetic=True,
            measured_engine_hours=False,
            database_persisted=False,
        )

        self._records.append(
            record
        )

        self._accumulated_engine_hours = (
            end_hours
        )

        self._active_mission_id = None
        self._active_start_hours = None

        self._state = (
            MissionHistoryState.MISSION_COMPLETED
        )

        return record


    def record_zero_runtime_mission(
        self,
        mission_id: Optional[str] = None,
    ) -> MissionEngineHistoryRecord:

        self.start_mission(
            mission_id=mission_id
        )

        return self.complete_mission(
            mission_runtime_hours=0.0
        )


    def register_maintenance_context(
        self,
        maintenance_type: str,
    ) -> Dict[str, Any]:

        resolved_type = (
            maintenance_type.strip()
            if isinstance(
                maintenance_type,
                str,
            )
            and maintenance_type.strip()
            else "UNKNOWN"
        )

        return {
            "maintenance_type": resolved_type,
            "engine_hours_before": (
                self._accumulated_engine_hours
            ),
            "engine_hours_after": (
                self._accumulated_engine_hours
            ),
            "engine_hours_reset": False,
            "synthetic": True,
            "authoritative_maintenance": False,
            "database_writes": False,
        }


    def get_history(
        self,
    ) -> List[Dict[str, Any]]:

        return [
            record.to_dict()
            for record in self._records
        ]


    def get_status(
        self,
    ) -> Dict[str, Any]:

        return {
            "service": (
                "accumulated_engine_history"
            ),
            "version": VERSION,
            "state": self._state.value,
            "initial_engine_hours": (
                self._initial_engine_hours
            ),
            "accumulated_engine_hours": (
                self._accumulated_engine_hours
            ),
            "mission_count": len(
                self._records
            ),
            "active_mission_id": (
                self._active_mission_id
            ),
            "synthetic": True,
            "measured_engine_hours": False,
            "database_writes": False,
            "canonical_telemetry_mutation": False,
            "digital_twin_execution": False,
            "authoritative_degradation": False,
            "authoritative_rul": False,
            "authoritative_maintenance": False,
            "readiness_calculation": False,
            "flight_authorization": False,
            "semantics": {
                "zero": (
                    "GENUINE_NUMERIC_ZERO"
                ),
                "none": (
                    "UNAVAILABLE"
                ),
                "mission_time_resets": True,
                "accumulated_engine_hours_reset": False,
                "maintenance_resets_engine_hours": False,
            },
        }


    def reset_study(
        self,
        initial_engine_hours: Optional[
            float
        ] = None,
    ) -> Dict[str, Any]:

        if (
            self._state
            == MissionHistoryState.MISSION_ACTIVE
        ):
            raise RuntimeError(
                "Cannot reset while a mission is active."
            )

        if initial_engine_hours is None:

            resolved_initial = (
                self._initial_engine_hours
            )

        else:

            self._validate_nonnegative_finite(
                initial_engine_hours,
                "initial_engine_hours",
            )

            resolved_initial = float(
                initial_engine_hours
            )

        self._initial_engine_hours = (
            resolved_initial
        )

        self._accumulated_engine_hours = (
            resolved_initial
        )

        self._records.clear()

        self._state = (
            MissionHistoryState.IDLE
        )

        self._active_mission_id = None
        self._active_start_hours = None

        return self.get_status()


_accumulated_engine_history: Optional[
    AccumulatedEngineHistory
] = None


def get_accumulated_engine_history(
) -> AccumulatedEngineHistory:

    global _accumulated_engine_history

    if _accumulated_engine_history is None:

        _accumulated_engine_history = (
            AccumulatedEngineHistory()
        )

    return _accumulated_engine_history


def get_accumulated_engine_history_status(
) -> Dict[str, Any]:

    return (
        get_accumulated_engine_history()
        .get_status()
    )
