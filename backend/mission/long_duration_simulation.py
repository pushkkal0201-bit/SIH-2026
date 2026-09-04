from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any, Dict, List, Optional, Sequence

from backend.mission.engine_life_clock import (
    EngineLifeClock,
)

from backend.prognostics.synthetic_degradation_profile import (
    SyntheticDegradationProfile,
)


LONG_DURATION_SIMULATION_VERSION = "1.0.0"

DEFAULT_STEP_HOURS = 0.25

DEFAULT_CHECKPOINTS = (
    0.0,
    10.0,
    100.0,
    250.0,
    500.0,
    800.0,
)


class LongDurationStudyState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


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


@dataclass(frozen=True)
class LongDurationCheckpoint:

    checkpoint_index: int
    engine_hours: float

    life_progress: float
    degradation_index: float
    degradation_percent: float

    wear_band: str

    thermal_wear: float
    lubrication_wear: float
    vibration_growth: float
    efficiency_loss: float
    combustion_wear: float

    synthetic: bool = True

    def to_dict(self) -> Dict[str, Any]:

        return {
            "checkpoint_index":
                self.checkpoint_index,

            "engine_hours":
                self.engine_hours,

            "life_progress":
                self.life_progress,

            "life_progress_percent":
                self.life_progress * 100.0,

            "degradation_index":
                self.degradation_index,

            "degradation_percent":
                self.degradation_percent,

            "wear_band":
                self.wear_band,

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

            "synthetic":
                self.synthetic,
        }


class LongDurationSimulation:

    def __init__(
        self,
        *,
        target_engine_hours: float,
        step_hours: float = DEFAULT_STEP_HOURS,
        reference_life_hours: float = 1000.0,
        checkpoints: Optional[
            Sequence[float]
        ] = None,
    ) -> None:

        target = _finite_positive(
            target_engine_hours
        )

        if target is None:
            raise ValueError(
                "target_engine_hours must be a finite positive number."
            )

        step = _finite_positive(
            step_hours
        )

        if step is None:
            raise ValueError(
                "step_hours must be a finite positive number."
            )

        reference = _finite_positive(
            reference_life_hours
        )

        if reference is None:
            raise ValueError(
                "reference_life_hours must be a finite positive number."
            )

        self._target_engine_hours = target
        self._step_hours = step
        self._reference_life_hours = reference

        self._clock = EngineLifeClock(
            target_engine_hours=target,
            step_hours=step,
        )

        self._profile = (
            SyntheticDegradationProfile(
                reference_life_hours=reference
            )
        )

        self._requested_checkpoints = (
            self._normalize_checkpoints(
                checkpoints
            )
        )

        self._state = (
            LongDurationStudyState.IDLE
        )

        self._results: List[
            LongDurationCheckpoint
        ] = []

        self._started_at: Optional[
            datetime
        ] = None

        self._completed_at: Optional[
            datetime
        ] = None

        self._last_error: Optional[str] = None

        self._run_count = 0

    def _normalize_checkpoints(
        self,
        checkpoints: Optional[
            Sequence[float]
        ],
    ) -> List[float]:

        if checkpoints is None:
            source = list(
                DEFAULT_CHECKPOINTS
            )

        else:
            source = list(checkpoints)

        values: List[float] = [0.0]

        for raw in source:

            value = _finite_non_negative(
                raw
            )

            if value is None:
                raise ValueError(
                    "checkpoints must contain only "
                    "finite non-negative numbers."
                )

            if value <= self._target_engine_hours:
                values.append(value)

        values.append(
            self._target_engine_hours
        )

        return sorted(
            set(values)
        )

    @property
    def state(
        self,
    ) -> LongDurationStudyState:

        return self._state

    @property
    def target_engine_hours(
        self,
    ) -> float:

        return self._target_engine_hours

    @property
    def step_hours(
        self,
    ) -> float:

        return self._step_hours

    @property
    def results(
        self,
    ) -> List[LongDurationCheckpoint]:

        return list(self._results)

    def _create_checkpoint(
        self,
        engine_hours: float,
    ) -> LongDurationCheckpoint:

        degradation = (
            self._profile.evaluate(
                engine_hours
            )
        )

        return LongDurationCheckpoint(
            checkpoint_index=
                len(self._results),

            engine_hours=
                engine_hours,

            life_progress=
                (
                    engine_hours
                    / self._target_engine_hours
                ),

            degradation_index=
                degradation.degradation_index,

            degradation_percent=
                degradation.degradation_index
                * 100.0,

            wear_band=
                degradation.wear_band.value,

            thermal_wear=
                degradation.thermal_wear,

            lubrication_wear=
                degradation.lubrication_wear,

            vibration_growth=
                degradation.vibration_growth,

            efficiency_loss=
                degradation.efficiency_loss,

            combustion_wear=
                degradation.combustion_wear,
        )

    def run(
        self,
    ) -> Dict[str, Any]:

        self._state = (
            LongDurationStudyState.RUNNING
        )

        self._started_at = _utc_now()
        self._completed_at = None
        self._last_error = None

        self._results = []

        self._clock.restart(
            engine_running=True
        )

        self._run_count += 1

        try:

            checkpoint_index = 0

            while (
                checkpoint_index
                < len(
                    self._requested_checkpoints
                )
            ):

                checkpoint_hour = (
                    self._requested_checkpoints[
                        checkpoint_index
                    ]
                )

                current_hours = (
                    self._clock
                    .accumulated_engine_hours
                )

                if (
                    current_hours
                    < checkpoint_hour
                ):

                    delta = min(
                        self._step_hours,
                        checkpoint_hour
                        - current_hours,
                    )

                    self._clock.advance(
                        delta
                    )

                    continue

                self._results.append(
                    self._create_checkpoint(
                        checkpoint_hour
                    )
                )

                checkpoint_index += 1

            if (
                self._clock
                .accumulated_engine_hours
                < self._target_engine_hours
            ):

                while (
                    self._clock
                    .accumulated_engine_hours
                    < self._target_engine_hours
                ):

                    remaining = (
                        self._target_engine_hours
                        - self._clock
                        .accumulated_engine_hours
                    )

                    self._clock.advance(
                        min(
                            self._step_hours,
                            remaining,
                        )
                    )

            self._state = (
                LongDurationStudyState.COMPLETED
            )

            self._completed_at = _utc_now()

            return self.summary()

        except Exception as exc:

            self._state = (
                LongDurationStudyState.ERROR
            )

            self._last_error = str(exc)

            raise

    def summary(
        self,
    ) -> Dict[str, Any]:

        latest = (
            self._results[-1]
            if self._results
            else None
        )

        return {
            "service":
                "long_duration_simulation",

            "version":
                LONG_DURATION_SIMULATION_VERSION,

            "architecture":
                "OFFLINE_SYNTHETIC_ENGINE_LIFE_STUDY",

            "state":
                self._state.value,

            "run_count":
                self._run_count,

            "configuration": {
                "target_engine_hours":
                    self._target_engine_hours,

                "step_hours":
                    self._step_hours,

                "reference_life_hours":
                    self._reference_life_hours,

                "requested_checkpoints":
                    list(
                        self._requested_checkpoints
                    ),
            },

            "execution": {
                "accumulated_engine_hours":
                    self._clock
                    .accumulated_engine_hours,

                "clock_step_count":
                    self._clock.step_count,

                "checkpoint_count":
                    len(self._results),

                "started_at":
                    (
                        self._started_at
                        .isoformat()
                        if self._started_at
                        is not None
                        else None
                    ),

                "completed_at":
                    (
                        self._completed_at
                        .isoformat()
                        if self._completed_at
                        is not None
                        else None
                    ),

                "last_error":
                    self._last_error,
            },

            "latest": (
                latest.to_dict()
                if latest is not None
                else None
            ),

            "checkpoints": [
                item.to_dict()
                for item
                in self._results
            ],

            "semantics": {
                "synthetic":
                    True,

                "real_engine_hours":
                    False,

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

                "fault_injection":
                    False,

                "digital_twin_execution":
                    False,

                "authoritative_degradation":
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


def run_long_duration_study(
    *,
    target_engine_hours: float,
    step_hours: float =
        DEFAULT_STEP_HOURS,
    reference_life_hours: float =
        1000.0,
    checkpoints: Optional[
        Sequence[float]
    ] = None,
) -> Dict[str, Any]:

    simulation = LongDurationSimulation(
        target_engine_hours=
            target_engine_hours,

        step_hours=
            step_hours,

        reference_life_hours=
            reference_life_hours,

        checkpoints=
            checkpoints,
    )

    return simulation.run()
