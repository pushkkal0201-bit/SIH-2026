from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Any, Dict, Optional


SYNTHETIC_DEGRADATION_VERSION = "1.0.0"

DEFAULT_REFERENCE_LIFE_HOURS = 1000.0


class SyntheticWearBand(str, Enum):
    NEW = "NEW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"


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


def _clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:

    return max(
        minimum,
        min(maximum, value),
    )


def _smooth_progress(
    progress: float,
    exponent: float,
) -> float:

    p = _clamp(progress)

    return _clamp(
        p ** exponent
    )


def _wear_band(
    degradation_index: float,
    engine_hours: float,
) -> SyntheticWearBand:

    if engine_hours <= 0.0:
        return SyntheticWearBand.NEW

    if degradation_index < 0.20:
        return SyntheticWearBand.LOW

    if degradation_index < 0.45:
        return SyntheticWearBand.MODERATE

    if degradation_index < 0.70:
        return SyntheticWearBand.ELEVATED

    return SyntheticWearBand.HIGH


@dataclass(frozen=True)
class SyntheticDegradationSnapshot:

    engine_hours: float
    reference_life_hours: float

    normalized_life_progress: float

    thermal_wear: float
    lubrication_wear: float
    vibration_growth: float
    efficiency_loss: float
    combustion_wear: float

    degradation_index: float
    wear_band: SyntheticWearBand

    synthetic: bool = True
    measured_engine_data: bool = False
    official_engine_life_limit: bool = False

    database_writes: bool = False
    telemetry_generation: bool = False
    fault_state_calculation: bool = False
    rul_calculation: bool = False
    maintenance_calculation: bool = False
    readiness_calculation: bool = False
    flight_authorization: bool = False

    def to_dict(self) -> Dict[str, Any]:

        return {
            "version":
                SYNTHETIC_DEGRADATION_VERSION,

            "service":
                "synthetic_degradation_profile",

            "engine_hours":
                self.engine_hours,

            "reference_life_hours":
                self.reference_life_hours,

            "normalized_life_progress":
                self.normalized_life_progress,

            "normalized_life_progress_percent":
                self.normalized_life_progress * 100.0,

            "wear": {
                "thermal":
                    self.thermal_wear,

                "lubrication":
                    self.lubrication_wear,

                "vibration_growth":
                    self.vibration_growth,

                "efficiency_loss":
                    self.efficiency_loss,

                "combustion":
                    self.combustion_wear,
            },

            "degradation_index":
                self.degradation_index,

            "degradation_percent":
                self.degradation_index * 100.0,

            "wear_band":
                self.wear_band.value,

            "semantics": {
                "synthetic":
                    self.synthetic,

                "measured_engine_data":
                    self.measured_engine_data,

                "official_engine_life_limit":
                    self.official_engine_life_limit,

                "zero":
                    "GENUINE_NUMERIC_ZERO",

                "null":
                    "UNAVAILABLE",
            },

            "isolation": {
                "database_writes":
                    self.database_writes,

                "telemetry_generation":
                    self.telemetry_generation,

                "fault_state_calculation":
                    self.fault_state_calculation,

                "rul_calculation":
                    self.rul_calculation,

                "maintenance_calculation":
                    self.maintenance_calculation,

                "readiness_calculation":
                    self.readiness_calculation,

                "flight_authorization":
                    self.flight_authorization,
            },
        }


class SyntheticDegradationProfile:

    def __init__(
        self,
        *,
        reference_life_hours: float =
            DEFAULT_REFERENCE_LIFE_HOURS,
    ) -> None:

        reference = _finite_positive(
            reference_life_hours
        )

        if reference is None:
            raise ValueError(
                "reference_life_hours must be a finite positive number."
            )

        self._reference_life_hours = reference

        self._evaluation_count = 0

        self._latest: Optional[
            SyntheticDegradationSnapshot
        ] = None

    @property
    def reference_life_hours(self) -> float:
        return self._reference_life_hours

    @property
    def evaluation_count(self) -> int:
        return self._evaluation_count

    def evaluate(
        self,
        engine_hours: float,
    ) -> SyntheticDegradationSnapshot:

        hours = _finite_non_negative(
            engine_hours
        )

        if hours is None:
            raise ValueError(
                "engine_hours must be a finite non-negative number."
            )

        progress = _clamp(
            hours / self._reference_life_hours
        )


        thermal_wear = _smooth_progress(
            progress,
            1.35,
        )

        lubrication_wear = _smooth_progress(
            progress,
            1.55,
        )

        vibration_growth = _smooth_progress(
            progress,
            1.80,
        )

        efficiency_loss = _smooth_progress(
            progress,
            1.45,
        )

        combustion_wear = _smooth_progress(
            progress,
            1.65,
        )


        degradation_index = _clamp(
            0.25 * thermal_wear
            + 0.22 * lubrication_wear
            + 0.18 * vibration_growth
            + 0.17 * efficiency_loss
            + 0.18 * combustion_wear
        )

        band = _wear_band(
            degradation_index,
            hours,
        )

        snapshot = SyntheticDegradationSnapshot(
            engine_hours=hours,

            reference_life_hours=
                self._reference_life_hours,

            normalized_life_progress=
                progress,

            thermal_wear=
                thermal_wear,

            lubrication_wear=
                lubrication_wear,

            vibration_growth=
                vibration_growth,

            efficiency_loss=
                efficiency_loss,

            combustion_wear=
                combustion_wear,

            degradation_index=
                degradation_index,

            wear_band=
                band,
        )

        self._evaluation_count += 1
        self._latest = snapshot

        return snapshot

    def latest(
        self,
    ) -> Optional[SyntheticDegradationSnapshot]:

        return self._latest

    def status(
        self,
    ) -> Dict[str, Any]:

        return {
            "service":
                "synthetic_degradation_profile",

            "version":
                SYNTHETIC_DEGRADATION_VERSION,

            "architecture":
                "SYNTHETIC_LONG_TERM_WEAR_ONLY",

            "reference_life_hours":
                self._reference_life_hours,

            "evaluation_count":
                self._evaluation_count,

            "latest":
                (
                    self._latest.to_dict()
                    if self._latest is not None
                    else None
                ),

            "semantics": {
                "synthetic":
                    True,

                "measured_engine_data":
                    False,

                "official_engine_life_limit":
                    False,

                "zero":
                    "GENUINE_NUMERIC_ZERO",

                "null":
                    "UNAVAILABLE",
            },

            "isolation": {
                "database_writes":
                    False,

                "telemetry_generation":
                    False,

                "fault_state_calculation":
                    False,

                "rul_calculation":
                    False,

                "maintenance_calculation":
                    False,

                "readiness_calculation":
                    False,

                "flight_authorization":
                    False,
            },
        }


_synthetic_degradation_profile = (
    SyntheticDegradationProfile()
)


def get_synthetic_degradation_profile(
) -> SyntheticDegradationProfile:

    return _synthetic_degradation_profile


def evaluate_synthetic_degradation(
    engine_hours: float,
) -> Dict[str, Any]:

    return (
        _synthetic_degradation_profile
        .evaluate(engine_hours)
        .to_dict()
    )


def get_synthetic_degradation_status(
) -> Dict[str, Any]:

    return (
        _synthetic_degradation_profile
        .status()
    )
