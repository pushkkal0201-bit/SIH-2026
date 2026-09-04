from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any, Dict, Optional


ENGINE_LIFE_CLOCK_VERSION = "1.0.0"

DEFAULT_STEP_HOURS = 0.25
DEFAULT_TARGET_HOURS = 800.0


class EngineLifeClockState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"


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


def _clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:

    return max(
        minimum,
        min(maximum, value),
    )


@dataclass(frozen=True)
class EngineLifeSnapshot:
    timestamp: datetime

    version: str

    state: EngineLifeClockState

    accumulated_engine_hours: float
    target_engine_hours: float
    remaining_engine_hours: float

    progress: float
    step_hours: float
    step_count: int

    engine_running: bool

    synthetic: bool = True
    real_engine_hours: bool = False
    database_writes: bool = False
    telemetry_generation: bool = False
    readiness_calculation: bool = False

    def to_dict(self) -> Dict[str, Any]:

        return {
            "timestamp":
                self.timestamp.isoformat(),

            "version":
                self.version,

            "state":
                self.state.value,

            "accumulated_engine_hours":
                self.accumulated_engine_hours,

            "target_engine_hours":
                self.target_engine_hours,

            "remaining_engine_hours":
                self.remaining_engine_hours,

            "progress":
                self.progress,

            "progress_percent":
                self.progress * 100.0,

            "step_hours":
                self.step_hours,

            "step_count":
                self.step_count,

            "engine_running":
                self.engine_running,

            "semantics": {
                "synthetic":
                    self.synthetic,

                "real_engine_hours":
                    self.real_engine_hours,

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

                "readiness_calculation":
                    self.readiness_calculation,
            },
        }


class EngineLifeClock:

    def __init__(
        self,
        *,
        target_engine_hours: float = DEFAULT_TARGET_HOURS,
        step_hours: float = DEFAULT_STEP_HOURS,
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

        self._target_engine_hours = target
        self._step_hours = step

        self._accumulated_engine_hours = 0.0
        self._step_count = 0

        self._state = EngineLifeClockState.IDLE
        self._engine_running = False

        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None
        self._stopped_at: Optional[datetime] = None

    @property
    def state(self) -> EngineLifeClockState:
        return self._state

    @property
    def target_engine_hours(self) -> float:
        return self._target_engine_hours

    @property
    def accumulated_engine_hours(self) -> float:
        return self._accumulated_engine_hours

    @property
    def remaining_engine_hours(self) -> float:
        return max(
            0.0,
            self._target_engine_hours
            - self._accumulated_engine_hours,
        )

    @property
    def step_hours(self) -> float:
        return self._step_hours

    @property
    def step_count(self) -> int:
        return self._step_count

    @property
    def engine_running(self) -> bool:
        return self._engine_running

    @property
    def progress(self) -> float:

        if self._target_engine_hours <= 0.0:
            return 0.0

        return _clamp(
            self._accumulated_engine_hours
            / self._target_engine_hours,
            0.0,
            1.0,
        )

    def set_engine_running(
        self,
        running: bool,
    ) -> EngineLifeSnapshot:

        if not isinstance(running, bool):
            raise ValueError(
                "running must be boolean."
            )

        self._engine_running = running

        return self.snapshot()

    def start(
        self,
        *,
        engine_running: bool = True,
    ) -> EngineLifeSnapshot:

        if not isinstance(engine_running, bool):
            raise ValueError(
                "engine_running must be boolean."
            )

        if (
            self._state
            in {
                EngineLifeClockState.COMPLETED,
                EngineLifeClockState.STOPPED,
            }
        ):
            self._accumulated_engine_hours = 0.0
            self._step_count = 0
            self._completed_at = None
            self._stopped_at = None

        self._state = EngineLifeClockState.RUNNING
        self._engine_running = engine_running

        if self._started_at is None:
            self._started_at = _utc_now()

        return self.snapshot()

    def pause(self) -> EngineLifeSnapshot:

        if self._state == EngineLifeClockState.RUNNING:
            self._state = EngineLifeClockState.PAUSED

        return self.snapshot()

    def resume(self) -> EngineLifeSnapshot:

        if self._state == EngineLifeClockState.PAUSED:
            self._state = EngineLifeClockState.RUNNING

        return self.snapshot()

    def stop(self) -> EngineLifeSnapshot:

        self._state = EngineLifeClockState.STOPPED
        self._engine_running = False
        self._stopped_at = _utc_now()

        return self.snapshot()

    def reset(self) -> EngineLifeSnapshot:

        self._state = EngineLifeClockState.IDLE

        self._accumulated_engine_hours = 0.0
        self._step_count = 0

        self._engine_running = False

        self._started_at = None
        self._completed_at = None
        self._stopped_at = None

        return self.snapshot()

    def restart(
        self,
        *,
        engine_running: bool = True,
    ) -> EngineLifeSnapshot:

        if not isinstance(engine_running, bool):
            raise ValueError(
                "engine_running must be boolean."
            )

        self._accumulated_engine_hours = 0.0
        self._step_count = 0

        self._state = EngineLifeClockState.RUNNING
        self._engine_running = engine_running

        self._started_at = _utc_now()
        self._completed_at = None
        self._stopped_at = None

        return self.snapshot()

    def set_target(
        self,
        target_engine_hours: float,
    ) -> EngineLifeSnapshot:

        target = _finite_positive(
            target_engine_hours
        )

        if target is None:
            raise ValueError(
                "target_engine_hours must be a finite positive number."
            )

        self._target_engine_hours = target

        if (
            self._accumulated_engine_hours
            >= self._target_engine_hours
        ):
            self._accumulated_engine_hours = (
                self._target_engine_hours
            )

            self._state = EngineLifeClockState.COMPLETED
            self._completed_at = _utc_now()

        return self.snapshot()

    def set_step(
        self,
        step_hours: float,
    ) -> EngineLifeSnapshot:

        step = _finite_positive(
            step_hours
        )

        if step is None:
            raise ValueError(
                "step_hours must be a finite positive number."
            )

        self._step_hours = step

        return self.snapshot()

    def seek(
        self,
        engine_hours: float,
    ) -> EngineLifeSnapshot:

        value = _finite_non_negative(
            engine_hours
        )

        if value is None:
            raise ValueError(
                "engine_hours must be a finite non-negative number."
            )

        self._accumulated_engine_hours = _clamp(
            value,
            0.0,
            self._target_engine_hours,
        )

        if (
            self._accumulated_engine_hours
            >= self._target_engine_hours
        ):
            self._state = EngineLifeClockState.COMPLETED
            self._completed_at = _utc_now()

        elif self._state == EngineLifeClockState.COMPLETED:
            self._state = EngineLifeClockState.PAUSED
            self._completed_at = None

        return self.snapshot()

    def advance(
        self,
        engine_hours: Optional[float] = None,
    ) -> EngineLifeSnapshot:

        if engine_hours is None:
            delta = self._step_hours

        else:
            delta = _finite_non_negative(
                engine_hours
            )

            if delta is None:
                raise ValueError(
                    "engine_hours must be finite and non-negative."
                )

        if self._state != EngineLifeClockState.RUNNING:
            return self.snapshot()

        if not self._engine_running:
            return self.snapshot()

        if delta == 0.0:
            return self.snapshot()

        previous = self._accumulated_engine_hours

        self._accumulated_engine_hours = min(
            self._target_engine_hours,
            previous + delta,
        )

        if self._accumulated_engine_hours > previous:
            self._step_count += 1

        if (
            self._accumulated_engine_hours
            >= self._target_engine_hours
        ):
            self._accumulated_engine_hours = (
                self._target_engine_hours
            )

            self._state = EngineLifeClockState.COMPLETED
            self._completed_at = _utc_now()

        return self.snapshot()

    def snapshot(self) -> EngineLifeSnapshot:

        return EngineLifeSnapshot(
            timestamp=_utc_now(),

            version=ENGINE_LIFE_CLOCK_VERSION,

            state=self._state,

            accumulated_engine_hours=
                self._accumulated_engine_hours,

            target_engine_hours=
                self._target_engine_hours,

            remaining_engine_hours=
                self.remaining_engine_hours,

            progress=self.progress,

            step_hours=self._step_hours,

            step_count=self._step_count,

            engine_running=self._engine_running,
        )

    def status(self) -> Dict[str, Any]:

        snapshot = self.snapshot().to_dict()

        snapshot["service"] = (
            "synthetic_engine_life_clock"
        )

        snapshot["architecture"] = (
            "INDEPENDENT_SYNTHETIC_ENGINE_TIME"
        )

        snapshot["started_at"] = (
            self._started_at.isoformat()
            if self._started_at is not None
            else None
        )

        snapshot["completed_at"] = (
            self._completed_at.isoformat()
            if self._completed_at is not None
            else None
        )

        snapshot["stopped_at"] = (
            self._stopped_at.isoformat()
            if self._stopped_at is not None
            else None
        )

        return snapshot


_engine_life_clock = EngineLifeClock()


def get_engine_life_clock() -> EngineLifeClock:
    return _engine_life_clock


def get_engine_life_status() -> Dict[str, Any]:
    return _engine_life_clock.status()


def start_engine_life_clock(
    *,
    engine_running: bool = True,
) -> Dict[str, Any]:

    return (
        _engine_life_clock
        .start(
            engine_running=engine_running
        )
        .to_dict()
    )


def pause_engine_life_clock() -> Dict[str, Any]:

    return (
        _engine_life_clock
        .pause()
        .to_dict()
    )


def resume_engine_life_clock() -> Dict[str, Any]:

    return (
        _engine_life_clock
        .resume()
        .to_dict()
    )


def stop_engine_life_clock() -> Dict[str, Any]:

    return (
        _engine_life_clock
        .stop()
        .to_dict()
    )


def reset_engine_life_clock() -> Dict[str, Any]:

    return (
        _engine_life_clock
        .reset()
        .to_dict()
    )


def restart_engine_life_clock(
    *,
    engine_running: bool = True,
) -> Dict[str, Any]:

    return (
        _engine_life_clock
        .restart(
            engine_running=engine_running
        )
        .to_dict()
    )


def set_engine_life_running(
    running: bool,
) -> Dict[str, Any]:

    return (
        _engine_life_clock
        .set_engine_running(running)
        .to_dict()
    )


def set_engine_life_target(
    target_engine_hours: float,
) -> Dict[str, Any]:

    return (
        _engine_life_clock
        .set_target(target_engine_hours)
        .to_dict()
    )


def set_engine_life_step(
    step_hours: float,
) -> Dict[str, Any]:

    return (
        _engine_life_clock
        .set_step(step_hours)
        .to_dict()
    )


def seek_engine_life(
    engine_hours: float,
) -> Dict[str, Any]:

    return (
        _engine_life_clock
        .seek(engine_hours)
        .to_dict()
    )


def advance_engine_life(
    engine_hours: Optional[float] = None,
) -> Dict[str, Any]:

    return (
        _engine_life_clock
        .advance(engine_hours)
        .to_dict()
    )
