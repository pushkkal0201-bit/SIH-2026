from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Any, Dict, List, Optional, Sequence

from backend.prognostics.synthetic_degradation_profile import (
    SyntheticDegradationProfile,
)


SYNTHETIC_RUL_VERSION = "1.0.0"

DEFAULT_REFERENCE_HORIZON_HOURS = 1000.0


class SyntheticRULState(str, Enum):
    EARLY_LIFE = "EARLY_LIFE"
    NOMINAL = "NOMINAL"
    DECLINING = "DECLINING"
    LATE_LIFE = "LATE_LIFE"
    HORIZON_REACHED = "HORIZON_REACHED"


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


def _finite_positive(
    value: Any,
) -> Optional[float]:

    result = _finite_non_negative(value)

    if result is None or result <= 0.0:
        return None

    return result


def _clamp01(
    value: float,
) -> float:

    return max(
        0.0,
        min(1.0, value),
    )


def _rul_state(
    remaining_fraction: float,
) -> SyntheticRULState:

    if remaining_fraction <= 0.0:
        return SyntheticRULState.HORIZON_REACHED

    if remaining_fraction <= 0.20:
        return SyntheticRULState.LATE_LIFE

    if remaining_fraction <= 0.50:
        return SyntheticRULState.DECLINING

    if remaining_fraction <= 0.90:
        return SyntheticRULState.NOMINAL

    return SyntheticRULState.EARLY_LIFE


@dataclass(frozen=True)
class SyntheticRULSnapshot:

    engine_hours: float
    reference_horizon_hours: float

    synthetic_degradation_index: float
    synthetic_degradation_percent: float

    projected_remaining_hours: float
    projected_remaining_fraction: float
    projected_remaining_percent: float

    state: SyntheticRULState
    wear_band: str

    synthetic: bool = True
    authoritative_rul: bool = False
    measured_engine_data: bool = False
    official_engine_life_limit: bool = False
    certified_prediction: bool = False

    database_writes: bool = False
    maintenance_calculation: bool = False
    readiness_calculation: bool = False
    flight_authorization: bool = False

    def to_dict(
        self,
    ) -> Dict[str, Any]:

        return {
            "version":
                SYNTHETIC_RUL_VERSION,

            "service":
                "synthetic_rul_progression",

            "engine_hours":
                self.engine_hours,

            "reference_horizon_hours":
                self.reference_horizon_hours,

            "synthetic_degradation": {
                "index":
                    self.synthetic_degradation_index,

                "percent":
                    self.synthetic_degradation_percent,

                "wear_band":
                    self.wear_band,
            },

            "projection": {
                "remaining_hours":
                    self.projected_remaining_hours,

                "remaining_fraction":
                    self.projected_remaining_fraction,

                "remaining_percent":
                    self.projected_remaining_percent,

                "state":
                    self.state.value,
            },

            "semantics": {
                "synthetic":
                    self.synthetic,

                "authoritative_rul":
                    self.authoritative_rul,

                "measured_engine_data":
                    self.measured_engine_data,

                "official_engine_life_limit":
                    self.official_engine_life_limit,

                "certified_prediction":
                    self.certified_prediction,

                "zero":
                    "GENUINE_NUMERIC_ZERO",

                "null":
                    "UNAVAILABLE",
            },

            "isolation": {
                "database_writes":
                    self.database_writes,

                "maintenance_calculation":
                    self.maintenance_calculation,

                "readiness_calculation":
                    self.readiness_calculation,

                "flight_authorization":
                    self.flight_authorization,
            },
        }


class SyntheticRULProgression:

    def __init__(
        self,
        *,
        reference_horizon_hours: float =
            DEFAULT_REFERENCE_HORIZON_HOURS,
    ) -> None:

        horizon = _finite_positive(
            reference_horizon_hours
        )

        if horizon is None:
            raise ValueError(
                "reference_horizon_hours must be "
                "a finite positive number."
            )

        self._reference_horizon_hours = horizon

        self._degradation_profile = (
            SyntheticDegradationProfile(
                reference_life_hours=horizon
            )
        )

        self._evaluation_count = 0

        self._latest: Optional[
            SyntheticRULSnapshot
        ] = None

    @property
    def reference_horizon_hours(
        self,
    ) -> float:

        return self._reference_horizon_hours

    @property
    def evaluation_count(
        self,
    ) -> int:

        return self._evaluation_count

    def evaluate(
        self,
        engine_hours: float,
    ) -> SyntheticRULSnapshot:

        hours = _finite_non_negative(
            engine_hours
        )

        if hours is None:
            raise ValueError(
                "engine_hours must be a finite "
                "non-negative number."
            )

        degradation = (
            self._degradation_profile.evaluate(
                hours
            )
        )

        remaining_fraction = _clamp01(
            1.0
            - degradation.degradation_index
        )

        projected_remaining_hours = (
            self._reference_horizon_hours
            * remaining_fraction
        )

        state = _rul_state(
            remaining_fraction
        )

        snapshot = SyntheticRULSnapshot(
            engine_hours=
                hours,

            reference_horizon_hours=
                self._reference_horizon_hours,

            synthetic_degradation_index=
                degradation.degradation_index,

            synthetic_degradation_percent=
                degradation.degradation_index
                * 100.0,

            projected_remaining_hours=
                projected_remaining_hours,

            projected_remaining_fraction=
                remaining_fraction,

            projected_remaining_percent=
                remaining_fraction
                * 100.0,

            state=
                state,

            wear_band=
                degradation.wear_band.value,
        )

        self._evaluation_count += 1
        self._latest = snapshot

        return snapshot

    def evaluate_progression(
        self,
        engine_hours: Sequence[float],
    ) -> List[Dict[str, Any]]:

        results: List[
            Dict[str, Any]
        ] = []

        for hour in engine_hours:

            results.append(
                self.evaluate(
                    hour
                ).to_dict()
            )

        return results

    def latest(
        self,
    ) -> Optional[SyntheticRULSnapshot]:

        return self._latest

    def status(
        self,
    ) -> Dict[str, Any]:

        return {
            "service":
                "synthetic_rul_progression",

            "version":
                SYNTHETIC_RUL_VERSION,

            "architecture":
                "DEMONSTRATION_ONLY_SYNTHETIC_RUL",

            "reference_horizon_hours":
                self._reference_horizon_hours,

            "evaluation_count":
                self._evaluation_count,

            "latest":
                (
                    self._latest.to_dict()
                    if self._latest
                    is not None
                    else None
                ),

            "semantics": {
                "synthetic":
                    True,

                "authoritative_rul":
                    False,

                "measured_engine_data":
                    False,

                "official_engine_life_limit":
                    False,

                "certified_prediction":
                    False,

                "zero":
                    "GENUINE_NUMERIC_ZERO",

                "null":
                    "UNAVAILABLE",
            },

            "isolation": {
                "database_writes":
                    False,

                "authoritative_rul_execution":
                    False,

                "maintenance_calculation":
                    False,

                "readiness_calculation":
                    False,

                "flight_authorization":
                    False,
            },
        }


_synthetic_rul_progression = (
    SyntheticRULProgression()
)


def get_synthetic_rul_progression(
) -> SyntheticRULProgression:

    return _synthetic_rul_progression


def evaluate_synthetic_rul(
    engine_hours: float,
) -> Dict[str, Any]:

    return (
        _synthetic_rul_progression
        .evaluate(engine_hours)
        .to_dict()
    )


def get_synthetic_rul_status(
) -> Dict[str, Any]:

    return (
        _synthetic_rul_progression
        .status()
    )
