from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any, Dict, List, Optional


SCENARIO_VERSION = "1.0.0"


class ScenarioState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"


class MissionPhase(str, Enum):
    ENGINE_START = "ENGINE_START"
    WARMUP = "WARMUP"
    TAKEOFF = "TAKEOFF"
    CLIMB = "CLIMB"
    CRUISE = "CRUISE"
    HIGH_ALTITUDE = "HIGH_ALTITUDE"
    DESCENT = "DESCENT"
    LANDING = "LANDING"
    ENGINE_SHUTDOWN = "ENGINE_SHUTDOWN"


@dataclass(frozen=True)
class PhaseProfile:
    phase: MissionPhase

    duration_sec: float

    start_rpm: float
    end_rpm: float

    start_throttle_percent: float
    end_throttle_percent: float

    start_load_percent: float
    end_load_percent: float

    start_altitude_m: float
    end_altitude_m: float

    start_ambient_temperature_c: float
    end_ambient_temperature_c: float


@dataclass
class ScenarioCommand:
    timestamp: datetime

    scenario_version: str

    mission_id: str

    scenario_state: ScenarioState
    phase: MissionPhase

    elapsed_time_sec: float
    mission_progress: float

    phase_elapsed_sec: float
    phase_progress: float

    simulation_speed: float

    rpm: float
    throttle_percent: float
    load_percent: float

    altitude_m: float
    ambient_temperature_c: float

    def to_dict(self) -> Dict[str, Any]:

        return {
            "timestamp":
                self.timestamp.isoformat(),

            "scenario_version":
                self.scenario_version,

            "mission_id":
                self.mission_id,

            "scenario_state":
                self.scenario_state.value,

            "phase":
                self.phase.value,

            "elapsed_time_sec":
                self.elapsed_time_sec,

            "mission_progress":
                self.mission_progress,

            "mission_progress_percent":
                self.mission_progress * 100.0,

            "phase_elapsed_sec":
                self.phase_elapsed_sec,

            "phase_progress":
                self.phase_progress,

            "phase_progress_percent":
                self.phase_progress * 100.0,

            "simulation_speed":
                self.simulation_speed,

            "targets": {

                "engine": {
                    "rpm":
                        self.rpm,

                    "throttle_percent":
                        self.throttle_percent,

                    "load_percent":
                        self.load_percent,
                },

                "environment": {
                    "altitude_m":
                        self.altitude_m,

                    "ambient_temperature_c":
                        self.ambient_temperature_c,
                },
            },
        }


DEFAULT_MISSION_PROFILE: List[PhaseProfile] = [

    PhaseProfile(
        phase=MissionPhase.ENGINE_START,
        duration_sec=20.0,

        start_rpm=0.0,
        end_rpm=900.0,

        start_throttle_percent=0.0,
        end_throttle_percent=12.0,

        start_load_percent=0.0,
        end_load_percent=10.0,

        start_altitude_m=0.0,
        end_altitude_m=0.0,

        start_ambient_temperature_c=25.0,
        end_ambient_temperature_c=25.0,
    ),

    PhaseProfile(
        phase=MissionPhase.WARMUP,
        duration_sec=40.0,

        start_rpm=900.0,
        end_rpm=1400.0,

        start_throttle_percent=12.0,
        end_throttle_percent=30.0,

        start_load_percent=10.0,
        end_load_percent=25.0,

        start_altitude_m=0.0,
        end_altitude_m=0.0,

        start_ambient_temperature_c=25.0,
        end_ambient_temperature_c=25.0,
    ),

    PhaseProfile(
        phase=MissionPhase.TAKEOFF,
        duration_sec=30.0,

        start_rpm=1400.0,
        end_rpm=2500.0,

        start_throttle_percent=30.0,
        end_throttle_percent=95.0,

        start_load_percent=25.0,
        end_load_percent=95.0,

        start_altitude_m=0.0,
        end_altitude_m=500.0,

        start_ambient_temperature_c=25.0,
        end_ambient_temperature_c=21.8,
    ),

    PhaseProfile(
        phase=MissionPhase.CLIMB,
        duration_sec=120.0,

        start_rpm=2500.0,
        end_rpm=2400.0,

        start_throttle_percent=95.0,
        end_throttle_percent=82.0,

        start_load_percent=95.0,
        end_load_percent=78.0,

        start_altitude_m=500.0,
        end_altitude_m=3350.0,

        start_ambient_temperature_c=21.8,
        end_ambient_temperature_c=3.2,
    ),

    PhaseProfile(
        phase=MissionPhase.CRUISE,
        duration_sec=180.0,

        start_rpm=2400.0,
        end_rpm=2300.0,

        start_throttle_percent=82.0,
        end_throttle_percent=68.0,

        start_load_percent=78.0,
        end_load_percent=62.0,

        start_altitude_m=3350.0,
        end_altitude_m=3350.0,

        start_ambient_temperature_c=3.2,
        end_ambient_temperature_c=3.2,
    ),

    PhaseProfile(
        phase=MissionPhase.HIGH_ALTITUDE,
        duration_sec=180.0,

        start_rpm=2300.0,
        end_rpm=2350.0,

        start_throttle_percent=68.0,
        end_throttle_percent=76.0,

        start_load_percent=62.0,
        end_load_percent=72.0,

        start_altitude_m=3350.0,
        end_altitude_m=5000.0,

        start_ambient_temperature_c=3.2,
        end_ambient_temperature_c=-7.5,
    ),

    PhaseProfile(
        phase=MissionPhase.DESCENT,
        duration_sec=120.0,

        start_rpm=2350.0,
        end_rpm=1800.0,

        start_throttle_percent=76.0,
        end_throttle_percent=35.0,

        start_load_percent=72.0,
        end_load_percent=30.0,

        start_altitude_m=5000.0,
        end_altitude_m=500.0,

        start_ambient_temperature_c=-7.5,
        end_ambient_temperature_c=21.8,
    ),

    PhaseProfile(
        phase=MissionPhase.LANDING,
        duration_sec=50.0,

        start_rpm=1800.0,
        end_rpm=1000.0,

        start_throttle_percent=35.0,
        end_throttle_percent=15.0,

        start_load_percent=30.0,
        end_load_percent=10.0,

        start_altitude_m=500.0,
        end_altitude_m=0.0,

        start_ambient_temperature_c=21.8,
        end_ambient_temperature_c=25.0,
    ),

    PhaseProfile(
        phase=MissionPhase.ENGINE_SHUTDOWN,
        duration_sec=20.0,

        start_rpm=1000.0,
        end_rpm=0.0,

        start_throttle_percent=15.0,
        end_throttle_percent=0.0,

        start_load_percent=10.0,
        end_load_percent=0.0,

        start_altitude_m=0.0,
        end_altitude_m=0.0,

        start_ambient_temperature_c=25.0,
        end_ambient_temperature_c=25.0,
    ),
]


def _utc_now() -> datetime:

    return datetime.now(
        timezone.utc
    )


def _clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:

    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def _lerp(
    start: float,
    end: float,
    progress: float,
) -> float:

    progress = _clamp(
        progress,
        0.0,
        1.0,
    )

    return (
        start
        + (
            end
            - start
        )
        * progress
    )


def _valid_speed(
    value: Any,
) -> Optional[float]:

    if (
        value is None
        or isinstance(
            value,
            bool,
        )
    ):
        return None

    try:

        speed = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return None

    if not isfinite(
        speed
    ):
        return None

    if speed <= 0.0:
        return None

    return speed


class MissionScenarioController:

    def __init__(
        self,
        mission_id: str = "PRATIRUP-DEMO-001",
        profile: Optional[
            List[PhaseProfile]
        ] = None,
    ) -> None:

        self.mission_id = (
            mission_id
        )

        self.profile = (
            list(
                profile
                or DEFAULT_MISSION_PROFILE
            )
        )

        if not self.profile:

            raise ValueError(
                "Mission profile cannot be empty."
            )

        self.state = (
            ScenarioState.IDLE
        )

        self.simulation_speed = 1.0

        self.elapsed_time_sec = 0.0

        self._last_command: Optional[
            ScenarioCommand
        ] = None

    @property
    def total_duration_sec(
        self,
    ) -> float:

        return sum(
            phase.duration_sec
            for phase in self.profile
        )

    @property
    def progress(
        self,
    ) -> float:

        total = (
            self.total_duration_sec
        )

        if total <= 0.0:
            return 0.0

        return _clamp(
            self.elapsed_time_sec
            / total,
            0.0,
            1.0,
        )

    def start(
        self,
    ) -> ScenarioCommand:

        if self.state in {
            ScenarioState.COMPLETED,
            ScenarioState.STOPPED,
        }:

            self.elapsed_time_sec = 0.0

        self.state = (
            ScenarioState.RUNNING
        )

        return self.current_command()

    def pause(
        self,
    ) -> ScenarioCommand:

        if (
            self.state
            == ScenarioState.RUNNING
        ):

            self.state = (
                ScenarioState.PAUSED
            )

        return self.current_command()

    def resume(
        self,
    ) -> ScenarioCommand:

        if (
            self.state
            == ScenarioState.PAUSED
        ):

            self.state = (
                ScenarioState.RUNNING
            )

        return self.current_command()

    def stop(
        self,
    ) -> ScenarioCommand:

        self.state = (
            ScenarioState.STOPPED
        )

        return self.current_command()

    def reset(
        self,
    ) -> ScenarioCommand:

        self.state = (
            ScenarioState.IDLE
        )

        self.elapsed_time_sec = 0.0

        self.simulation_speed = 1.0

        return self.current_command()

    def restart(
        self,
    ) -> ScenarioCommand:

        self.elapsed_time_sec = 0.0

        self.state = (
            ScenarioState.RUNNING
        )

        return self.current_command()

    def set_speed(
        self,
        speed: float,
    ) -> ScenarioCommand:

        validated = (
            _valid_speed(
                speed
            )
        )

        if validated is None:

            raise ValueError(
                "Simulation speed must be a finite value greater than zero."
            )

        self.simulation_speed = (
            validated
        )

        return self.current_command()

    def seek(
        self,
        elapsed_time_sec: float,
    ) -> ScenarioCommand:

        if isinstance(
            elapsed_time_sec,
            bool,
        ):

            raise ValueError(
                "Mission elapsed time must be numeric."
            )

        try:

            value = float(
                elapsed_time_sec
            )

        except (
            TypeError,
            ValueError,
        ):

            raise ValueError(
                "Mission elapsed time must be numeric."
            )

        if not isfinite(
            value
        ):

            raise ValueError(
                "Mission elapsed time must be finite."
            )

        self.elapsed_time_sec = (
            _clamp(
                value,
                0.0,
                self.total_duration_sec,
            )
        )

        if (
            self.elapsed_time_sec
            >= self.total_duration_sec
        ):

            self.state = (
                ScenarioState.COMPLETED
            )

        return self.current_command()

    def update(
        self,
        delta_real_sec: float,
    ) -> ScenarioCommand:

        if isinstance(
            delta_real_sec,
            bool,
        ):

            raise ValueError(
                "Simulation delta must be numeric."
            )

        try:

            delta = float(
                delta_real_sec
            )

        except (
            TypeError,
            ValueError,
        ):

            raise ValueError(
                "Simulation delta must be numeric."
            )

        if (
            not isfinite(
                delta
            )
            or delta < 0.0
        ):

            raise ValueError(
                "Simulation delta must be a finite non-negative value."
            )

        if (
            self.state
            != ScenarioState.RUNNING
        ):

            return (
                self.current_command()
            )

        simulated_delta = (
            delta
            * self.simulation_speed
        )

        self.elapsed_time_sec += (
            simulated_delta
        )

        if (
            self.elapsed_time_sec
            >= self.total_duration_sec
        ):

            self.elapsed_time_sec = (
                self.total_duration_sec
            )

            self.state = (
                ScenarioState.COMPLETED
            )

        return self.current_command()

    def _resolve_phase(
        self,
    ) -> tuple[
        PhaseProfile,
        float,
        float,
    ]:

        elapsed = (
            self.elapsed_time_sec
        )

        accumulated = 0.0

        for profile in self.profile:

            phase_end = (
                accumulated
                + profile.duration_sec
            )

            if elapsed <= phase_end:

                phase_elapsed = (
                    elapsed
                    - accumulated
                )

                phase_elapsed = (
                    _clamp(
                        phase_elapsed,
                        0.0,
                        profile.duration_sec,
                    )
                )

                if (
                    profile.duration_sec
                    > 0.0
                ):

                    phase_progress = (
                        phase_elapsed
                        / profile.duration_sec
                    )

                else:

                    phase_progress = 1.0

                return (
                    profile,
                    phase_elapsed,
                    _clamp(
                        phase_progress,
                        0.0,
                        1.0,
                    ),
                )

            accumulated = (
                phase_end
            )

        final_profile = (
            self.profile[-1]
        )

        return (
            final_profile,
            final_profile.duration_sec,
            1.0,
        )

    def current_command(
        self,
    ) -> ScenarioCommand:

        (
            profile,
            phase_elapsed,
            phase_progress,
        ) = self._resolve_phase()

        command = (
            ScenarioCommand(
                timestamp=
                    _utc_now(),

                scenario_version=
                    SCENARIO_VERSION,

                mission_id=
                    self.mission_id,

                scenario_state=
                    self.state,

                phase=
                    profile.phase,

                elapsed_time_sec=
                    self.elapsed_time_sec,

                mission_progress=
                    self.progress,

                phase_elapsed_sec=
                    phase_elapsed,

                phase_progress=
                    phase_progress,

                simulation_speed=
                    self.simulation_speed,

                rpm=
                    _lerp(
                        profile.start_rpm,
                        profile.end_rpm,
                        phase_progress,
                    ),

                throttle_percent=
                    _lerp(
                        profile.start_throttle_percent,
                        profile.end_throttle_percent,
                        phase_progress,
                    ),

                load_percent=
                    _lerp(
                        profile.start_load_percent,
                        profile.end_load_percent,
                        phase_progress,
                    ),

                altitude_m=
                    _lerp(
                        profile.start_altitude_m,
                        profile.end_altitude_m,
                        phase_progress,
                    ),

                ambient_temperature_c=
                    _lerp(
                        profile.start_ambient_temperature_c,
                        profile.end_ambient_temperature_c,
                        phase_progress,
                    ),
            )
        )

        self._last_command = (
            command
        )

        return command

    def status(
        self,
    ) -> Dict[str, Any]:

        command = (
            self.current_command()
        )

        return {

            "service":
                "mission_scenario",

            "version":
                SCENARIO_VERSION,

            "mission_id":
                self.mission_id,

            "state":
                self.state.value,

            "simulation_speed":
                self.simulation_speed,

            "elapsed_time_sec":
                self.elapsed_time_sec,

            "total_duration_sec":
                self.total_duration_sec,

            "progress":
                self.progress,

            "progress_percent":
                self.progress * 100.0,

            "phase":
                command.phase.value,

            "command":
                command.to_dict(),
        }


_default_controller = (
    MissionScenarioController()
)


def get_scenario_controller(
) -> MissionScenarioController:

    return _default_controller


def start_scenario(
) -> Dict[str, Any]:

    return (
        _default_controller
        .start()
        .to_dict()
    )


def pause_scenario(
) -> Dict[str, Any]:

    return (
        _default_controller
        .pause()
        .to_dict()
    )


def resume_scenario(
) -> Dict[str, Any]:

    return (
        _default_controller
        .resume()
        .to_dict()
    )


def stop_scenario(
) -> Dict[str, Any]:

    return (
        _default_controller
        .stop()
        .to_dict()
    )


def reset_scenario(
) -> Dict[str, Any]:

    return (
        _default_controller
        .reset()
        .to_dict()
    )


def restart_scenario(
) -> Dict[str, Any]:

    return (
        _default_controller
        .restart()
        .to_dict()
    )


def set_scenario_speed(
    speed: float,
) -> Dict[str, Any]:

    return (
        _default_controller
        .set_speed(
            speed
        )
        .to_dict()
    )


def seek_scenario(
    elapsed_time_sec: float,
) -> Dict[str, Any]:

    return (
        _default_controller
        .seek(
            elapsed_time_sec
        )
        .to_dict()
    )


def update_scenario(
    delta_real_sec: float,
) -> Dict[str, Any]:

    return (
        _default_controller
        .update(
            delta_real_sec
        )
        .to_dict()
    )


def get_scenario_status(
) -> Dict[str, Any]:

    return (
        _default_controller
        .status()
    )


def get_scenario_info(
) -> Dict[str, Any]:

    return {

        "service":
            "mission_scenario",

        "version":
            SCENARIO_VERSION,

        "purpose":
            "PRATIRUP mission simulation operating-target generator",

        "states": [
            state.value
            for state
            in ScenarioState
        ],

        "mission_phases": [
            phase.value
            for phase
            in MissionPhase
        ],

        "controls": [
            "start",
            "pause",
            "resume",
            "stop",
            "reset",
            "restart",
            "set_speed",
            "seek",
            "update",
        ],

        "total_duration_sec":
            _default_controller.total_duration_sec,

        "simulation_source_only":
            True,

        "modifies_can_fadec":
            False,

        "generates_final_sensor_telemetry":
            False,

        "runs_digital_twin":
            False,

        "runs_diagnostics":
            False,

        "directly_controls_threejs":
            False,

        "zero_is_valid":
            True,

        "none_means_unavailable":
            True,

        "official_drdo_vrde_mission_profile":
            False,

        "certified_flight_profile":
            False,
    }
