from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any, Dict, List, Mapping, Optional


SYNTHETIC_MAINTENANCE_VERSION = "1.0.0"


class SyntheticMaintenanceType(str, Enum):
    INSPECTION = "INSPECTION"
    MINOR_SERVICE = "MINOR_SERVICE"
    MAJOR_SERVICE = "MAJOR_SERVICE"
    COMPONENT_REPLACEMENT = "COMPONENT_REPLACEMENT"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _finite_non_negative(
    value: Any,
) -> Optional[float]:

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:
        result = float(value)

    except (TypeError, ValueError):
        return None

    if not isfinite(result):
        return None

    if result < 0.0:
        return None

    return result


def _clamp01(
    value: float,
) -> float:

    return max(
        0.0,
        min(1.0, value),
    )


def _normalized_wear(
    wear: Mapping[str, Any],
) -> Dict[str, float]:

    required = (
        "thermal",
        "lubrication",
        "vibration_growth",
        "efficiency_loss",
        "combustion",
    )

    result: Dict[str, float] = {}

    for key in required:

        value = _finite_non_negative(
            wear.get(key)
        )

        if value is None:
            raise ValueError(
                f"wear['{key}'] must be a finite "
                "non-negative number."
            )

        result[key] = _clamp01(value)

    return result


def _maintenance_restoration(
    maintenance_type: SyntheticMaintenanceType,
) -> Dict[str, float]:

    if maintenance_type == SyntheticMaintenanceType.INSPECTION:

        return {
            "thermal": 0.00,
            "lubrication": 0.00,
            "vibration_growth": 0.00,
            "efficiency_loss": 0.00,
            "combustion": 0.00,
        }

    if maintenance_type == SyntheticMaintenanceType.MINOR_SERVICE:

        return {
            "thermal": 0.08,
            "lubrication": 0.35,
            "vibration_growth": 0.10,
            "efficiency_loss": 0.08,
            "combustion": 0.12,
        }

    if maintenance_type == SyntheticMaintenanceType.MAJOR_SERVICE:

        return {
            "thermal": 0.25,
            "lubrication": 0.60,
            "vibration_growth": 0.35,
            "efficiency_loss": 0.30,
            "combustion": 0.40,
        }

    if (
        maintenance_type
        == SyntheticMaintenanceType.COMPONENT_REPLACEMENT
    ):

        return {
            "thermal": 0.45,
            "lubrication": 0.75,
            "vibration_growth": 0.70,
            "efficiency_loss": 0.55,
            "combustion": 0.60,
        }

    raise ValueError(
        "Unsupported maintenance type."
    )


def _composite_wear(
    wear: Mapping[str, float],
) -> float:

    return _clamp01(
        0.25 * wear["thermal"]
        + 0.22 * wear["lubrication"]
        + 0.18 * wear["vibration_growth"]
        + 0.17 * wear["efficiency_loss"]
        + 0.18 * wear["combustion"]
    )


@dataclass(frozen=True)
class SyntheticMaintenanceEvent:

    event_id: int
    timestamp: str

    engine_hours: float
    maintenance_type: SyntheticMaintenanceType

    wear_before: Dict[str, float]
    wear_after: Dict[str, float]

    degradation_before: float
    degradation_after: float

    restoration: Dict[str, float]

    synthetic: bool = True
    authoritative_maintenance: bool = False

    def to_dict(
        self,
    ) -> Dict[str, Any]:

        reduction = max(
            0.0,
            self.degradation_before
            - self.degradation_after,
        )

        return {
            "event_id":
                self.event_id,

            "timestamp":
                self.timestamp,

            "engine_hours":
                self.engine_hours,

            "maintenance_type":
                self.maintenance_type.value,

            "wear_before":
                dict(self.wear_before),

            "wear_after":
                dict(self.wear_after),

            "degradation_before":
                self.degradation_before,

            "degradation_before_percent":
                self.degradation_before * 100.0,

            "degradation_after":
                self.degradation_after,

            "degradation_after_percent":
                self.degradation_after * 100.0,

            "synthetic_degradation_reduction":
                reduction,

            "synthetic_degradation_reduction_percent":
                reduction * 100.0,

            "restoration":
                dict(self.restoration),

            "semantics": {
                "synthetic":
                    self.synthetic,

                "authoritative_maintenance":
                    self.authoritative_maintenance,

                "zero":
                    "GENUINE_NUMERIC_ZERO",

                "null":
                    "UNAVAILABLE",
            },
        }


class SyntheticMaintenanceSimulator:

    def __init__(
        self,
    ) -> None:

        self._events: List[
            SyntheticMaintenanceEvent
        ] = []

        self._event_count = 0

    @property
    def event_count(
        self,
    ) -> int:

        return self._event_count

    @property
    def events(
        self,
    ) -> List[SyntheticMaintenanceEvent]:

        return list(self._events)

    def apply(
        self,
        *,
        engine_hours: float,
        wear: Mapping[str, Any],
        maintenance_type: SyntheticMaintenanceType,
    ) -> SyntheticMaintenanceEvent:

        hours = _finite_non_negative(
            engine_hours
        )

        if hours is None:
            raise ValueError(
                "engine_hours must be a finite "
                "non-negative number."
            )

        if not isinstance(
            maintenance_type,
            SyntheticMaintenanceType,
        ):
            try:
                maintenance_type = (
                    SyntheticMaintenanceType(
                        maintenance_type
                    )
                )
            except (TypeError, ValueError):
                raise ValueError(
                    "Invalid maintenance_type."
                )

        before = _normalized_wear(
            wear
        )

        restoration = (
            _maintenance_restoration(
                maintenance_type
            )
        )

        after: Dict[str, float] = {}

        for key, before_value in before.items():

            restoration_fraction = (
                restoration[key]
            )

            after[key] = _clamp01(
                before_value
                * (
                    1.0
                    - restoration_fraction
                )
            )

        degradation_before = (
            _composite_wear(
                before
            )
        )

        degradation_after = (
            _composite_wear(
                after
            )
        )

        self._event_count += 1

        event = SyntheticMaintenanceEvent(
            event_id=
                self._event_count,

            timestamp=
                _utc_now_iso(),

            engine_hours=
                hours,

            maintenance_type=
                maintenance_type,

            wear_before=
                before,

            wear_after=
                after,

            degradation_before=
                degradation_before,

            degradation_after=
                degradation_after,

            restoration=
                restoration,
        )

        self._events.append(
            event
        )

        return event

    def clear(
        self,
    ) -> None:

        self._events.clear()
        self._event_count = 0

    def status(
        self,
    ) -> Dict[str, Any]:

        latest = (
            self._events[-1]
            if self._events
            else None
        )

        return {
            "service":
                "synthetic_maintenance_events",

            "version":
                SYNTHETIC_MAINTENANCE_VERSION,

            "architecture":
                "DEMONSTRATION_ONLY_SYNTHETIC_MAINTENANCE",

            "event_count":
                self._event_count,

            "latest":
                (
                    latest.to_dict()
                    if latest is not None
                    else None
                ),

            "events": [
                event.to_dict()
                for event in self._events
            ],

            "semantics": {
                "synthetic":
                    True,

                "authoritative_maintenance":
                    False,

                "official_maintenance_schedule":
                    False,

                "official_engine_life_limit":
                    False,

                "measured_engine_data":
                    False,

                "zero":
                    "GENUINE_NUMERIC_ZERO",

                "null":
                    "UNAVAILABLE",
            },

            "isolation": {
                "database_writes":
                    False,

                "authoritative_degradation":
                    False,

                "authoritative_rul":
                    False,

                "authoritative_maintenance":
                    False,

                "readiness_calculation":
                    False,

                "flight_authorization":
                    False,
            },
        }


_synthetic_maintenance_simulator = (
    SyntheticMaintenanceSimulator()
)


def get_synthetic_maintenance_simulator(
) -> SyntheticMaintenanceSimulator:

    return _synthetic_maintenance_simulator


def apply_synthetic_maintenance(
    *,
    engine_hours: float,
    wear: Mapping[str, Any],
    maintenance_type: SyntheticMaintenanceType,
) -> Dict[str, Any]:

    return (
        _synthetic_maintenance_simulator
        .apply(
            engine_hours=engine_hours,
            wear=wear,
            maintenance_type=maintenance_type,
        )
        .to_dict()
    )


def get_synthetic_maintenance_status(
) -> Dict[str, Any]:

    return (
        _synthetic_maintenance_simulator
        .status()
    )
