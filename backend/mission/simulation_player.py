from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any, Dict, Optional

from backend.mission.scenario import (
    get_scenario_status,
    pause_scenario,
    reset_scenario,
    restart_scenario,
    resume_scenario,
    seek_scenario,
    set_scenario_speed,
    start_scenario,
    stop_scenario,
    update_scenario,
)

from backend.ingestion.simulation_adapter import (
    get_simulation_status,
    process_simulation_command,
    reset_simulation_adapter,
)


SIMULATION_PLAYER_VERSION = "1.0.0"

DEFAULT_TICK_INTERVAL_SEC = 1.0

SUPPORTED_SPEEDS = (
    0.5,
    1.0,
    2.0,
    5.0,
)


class PlayerState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utc_now().isoformat()


def _valid_number(
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

    return result


class SimulationPlayer:

    def __init__(
        self,
        *,
        tick_interval_sec: float = DEFAULT_TICK_INTERVAL_SEC,
    ) -> None:

        tick = _valid_number(
            tick_interval_sec
        )

        if tick is None or tick <= 0.0:
            raise ValueError(
                "tick_interval_sec must be a finite positive number."
            )

        self._tick_interval_sec = tick

        self._state = PlayerState.IDLE

        self._task: Optional[
            asyncio.Task
        ] = None

        self._lock = asyncio.Lock()

        self._ticks = 0

        self._successful_ticks = 0

        self._failed_ticks = 0

        self._play_count = 0

        self._pause_count = 0

        self._resume_count = 0

        self._stop_count = 0

        self._restart_count = 0

        self._seek_count = 0

        self._speed_change_count = 0

        self._latest_command: Optional[
            Dict[str, Any]
        ] = None

        self._latest_result: Optional[
            Dict[str, Any]
        ] = None

        self._last_error: Optional[str] = None

        self._started_at: Optional[str] = None

        self._stopped_at: Optional[str] = None

        self._completed_at: Optional[str] = None


    def _sync_state_from_scenario(
        self,
    ) -> None:

        scenario = get_scenario_status()

        scenario_state = scenario.get(
            "state"
        )

        if scenario_state == "RUNNING":
            self._state = PlayerState.RUNNING

        elif scenario_state == "PAUSED":
            self._state = PlayerState.PAUSED

        elif scenario_state == "STOPPED":
            self._state = PlayerState.STOPPED

        elif scenario_state == "COMPLETED":
            self._state = PlayerState.COMPLETED

        elif scenario_state == "IDLE":
            self._state = PlayerState.IDLE


    async def tick(
        self,
        *,
        delta_real_sec: Optional[float] = None,
    ) -> Dict[str, Any]:

        if delta_real_sec is None:
            delta = self._tick_interval_sec

        else:
            delta = _valid_number(
                delta_real_sec
            )

            if delta is None or delta < 0.0:
                raise ValueError(
                    "delta_real_sec must be finite and non-negative."
                )

        async with self._lock:

            scenario_before = (
                get_scenario_status()
            )

            scenario_state = (
                scenario_before.get(
                    "state"
                )
            )

            if scenario_state == "PAUSED":

                self._state = (
                    PlayerState.PAUSED
                )

                return {
                    "success": True,
                    "executed": False,
                    "reason": "SCENARIO_PAUSED",
                    "player_state": self._state.value,
                    "scenario": scenario_before,
                }

            if scenario_state == "COMPLETED":

                self._state = (
                    PlayerState.COMPLETED
                )

                if self._completed_at is None:
                    self._completed_at = _iso_now()

                return {
                    "success": True,
                    "executed": False,
                    "reason": "SCENARIO_COMPLETED",
                    "player_state": self._state.value,
                    "scenario": scenario_before,
                }

            if scenario_state == "STOPPED":

                self._state = (
                    PlayerState.STOPPED
                )

                return {
                    "success": True,
                    "executed": False,
                    "reason": "SCENARIO_STOPPED",
                    "player_state": self._state.value,
                    "scenario": scenario_before,
                }

            if scenario_state == "IDLE":

                return {
                    "success": False,
                    "executed": False,
                    "reason": "SCENARIO_NOT_STARTED",
                    "player_state": self._state.value,
                    "scenario": scenario_before,
                }

            self._ticks += 1

            try:

                command = update_scenario(
                    delta
                )

                self._latest_command = command

                scenario_after = (
                    get_scenario_status()
                )

                simulated_delta = (
                    scenario_after.get(
                        "elapsed_time_sec",
                        0.0,
                    )
                    - scenario_before.get(
                        "elapsed_time_sec",
                        0.0,
                    )
                )

                simulated_delta = max(
                    0.0,
                    float(simulated_delta),
                )

                result = (
                    await process_simulation_command(
                        command,
                        delta_sec=simulated_delta,
                    )
                )

                self._latest_result = result

                if result.get("success"):

                    self._successful_ticks += 1

                    self._last_error = None

                else:

                    self._failed_ticks += 1

                    self._last_error = (
                        result.get("error")
                        or "Simulation adapter ingestion failed."
                    )

                self._sync_state_from_scenario()

                if self._state == PlayerState.COMPLETED:

                    if self._completed_at is None:
                        self._completed_at = _iso_now()

                return {
                    "success": bool(
                        result.get("success")
                    ),
                    "executed": True,
                    "player_state": self._state.value,
                    "tick": self._ticks,
                    "real_delta_sec": delta,
                    "simulated_delta_sec": simulated_delta,
                    "scenario": scenario_after,
                    "command": command,
                    "simulation": result,
                }

            except Exception as exc:

                self._failed_ticks += 1

                self._last_error = str(exc)

                self._state = (
                    PlayerState.ERROR
                )

                return {
                    "success": False,
                    "executed": True,
                    "player_state": self._state.value,
                    "tick": self._ticks,
                    "error": str(exc),
                }


    async def _run_loop(
        self,
    ) -> None:

        try:

            while True:

                if self._state != PlayerState.RUNNING:
                    break

                result = await self.tick(
                    delta_real_sec=self._tick_interval_sec
                )

                if not result.get("success"):

                    if result.get("executed"):
                        self._state = PlayerState.ERROR
                        break

                self._sync_state_from_scenario()

                if self._state in (
                    PlayerState.COMPLETED,
                    PlayerState.STOPPED,
                    PlayerState.ERROR,
                ):
                    break

                await asyncio.sleep(
                    self._tick_interval_sec
                )

        except asyncio.CancelledError:
            raise

        except Exception as exc:

            self._last_error = str(exc)

            self._state = (
                PlayerState.ERROR
            )

        finally:

            current_task = asyncio.current_task()

            if self._task is current_task:
                self._task = None


    async def play(
        self,
    ) -> Dict[str, Any]:

        if self._state == PlayerState.RUNNING:

            return self.status()

        scenario = get_scenario_status()

        scenario_state = scenario.get(
            "state"
        )

        if scenario_state == "PAUSED":

            resume_scenario()

            self._resume_count += 1

        elif scenario_state in (
            "COMPLETED",
            "STOPPED",
        ):

            restart_scenario()

            reset_simulation_adapter()

        elif scenario_state == "IDLE":

            start_scenario()

        self._state = (
            PlayerState.RUNNING
        )

        self._play_count += 1

        self._started_at = (
            self._started_at
            or _iso_now()
        )

        self._stopped_at = None

        self._completed_at = None

        self._last_error = None

        if (
            self._task is None
            or self._task.done()
        ):

            self._task = (
                asyncio.create_task(
                    self._run_loop()
                )
            )

        return self.status()


    async def pause(
        self,
    ) -> Dict[str, Any]:

        if get_scenario_status().get(
            "state"
        ) == "RUNNING":

            pause_scenario()

            self._pause_count += 1

        self._state = (
            PlayerState.PAUSED
        )

        await self._cancel_task()

        return self.status()


    async def resume(
        self,
    ) -> Dict[str, Any]:

        scenario_state = (
            get_scenario_status()
            .get("state")
        )

        if scenario_state == "PAUSED":

            resume_scenario()

        elif scenario_state == "IDLE":

            start_scenario()

        elif scenario_state in (
            "STOPPED",
            "COMPLETED",
        ):

            restart_scenario()

            reset_simulation_adapter()

        self._resume_count += 1

        self._state = (
            PlayerState.RUNNING
        )

        self._last_error = None

        if (
            self._task is None
            or self._task.done()
        ):

            self._task = (
                asyncio.create_task(
                    self._run_loop()
                )
            )

        return self.status()


    async def stop(
        self,
    ) -> Dict[str, Any]:

        stop_scenario()

        self._state = (
            PlayerState.STOPPED
        )

        self._stop_count += 1

        self._stopped_at = (
            _iso_now()
        )

        await self._cancel_task()

        return self.status()


    async def reset(
        self,
    ) -> Dict[str, Any]:

        await self._cancel_task()

        reset_scenario()

        reset_simulation_adapter()

        self._state = (
            PlayerState.IDLE
        )

        self._ticks = 0

        self._successful_ticks = 0

        self._failed_ticks = 0

        self._play_count = 0

        self._pause_count = 0

        self._resume_count = 0

        self._stop_count = 0

        self._restart_count = 0

        self._seek_count = 0

        self._speed_change_count = 0

        self._latest_command = None

        self._latest_result = None

        self._last_error = None

        self._started_at = None

        self._stopped_at = None

        self._completed_at = None

        return self.status()


    async def restart(
        self,
        *,
        auto_play: bool = True,
    ) -> Dict[str, Any]:

        await self._cancel_task()

        restart_scenario()

        reset_simulation_adapter()

        self._restart_count += 1

        self._ticks = 0

        self._successful_ticks = 0

        self._failed_ticks = 0

        self._latest_command = None

        self._latest_result = None

        self._last_error = None

        self._started_at = (
            _iso_now()
            if auto_play
            else None
        )

        self._stopped_at = None

        self._completed_at = None

        if auto_play:

            self._state = (
                PlayerState.RUNNING
            )

            if (
                self._task is None
                or self._task.done()
            ):

                self._task = (
                    asyncio.create_task(
                        self._run_loop()
                    )
                )

        else:

            pause_scenario()

            self._state = (
                PlayerState.PAUSED
            )

        return self.status()


    def set_speed(
        self,
        speed: float,
    ) -> Dict[str, Any]:

        value = _valid_number(
            speed
        )

        if value is None:

            raise ValueError(
                "Simulation speed must be numeric."
            )

        if value not in SUPPORTED_SPEEDS:

            raise ValueError(
                "Unsupported simulation speed. "
                f"Supported speeds: {SUPPORTED_SPEEDS}"
            )

        set_scenario_speed(
            value
        )

        self._speed_change_count += 1

        return self.status()


    async def seek(
        self,
        elapsed_time_sec: float,
    ) -> Dict[str, Any]:

        value = _valid_number(
            elapsed_time_sec
        )

        if value is None:

            raise ValueError(
                "Seek time must be numeric."
            )

        if value < 0.0:

            raise ValueError(
                "Seek time cannot be negative."
            )

        command = seek_scenario(
            value
        )

        self._seek_count += 1

        self._latest_command = command

        self._sync_state_from_scenario()

        return {
            "player":
                self.status(),

            "command":
                command,
        }


    async def _cancel_task(
        self,
    ) -> None:

        task = self._task

        if task is None:
            return

        if task.done():

            self._task = None

            return

        if task is asyncio.current_task():
            return

        task.cancel()

        try:
            await task

        except asyncio.CancelledError:
            pass

        finally:
            self._task = None


    def status(
        self,
    ) -> Dict[str, Any]:

        scenario = (
            get_scenario_status()
        )

        simulation = (
            get_simulation_status()
        )

        task_active = (
            self._task is not None
            and not self._task.done()
        )

        return {
            "service":
                "simulation_player",

            "version":
                SIMULATION_PLAYER_VERSION,

            "state":
                self._state.value,

            "tick_interval_sec":
                self._tick_interval_sec,

            "supported_speeds":
                list(
                    SUPPORTED_SPEEDS
                ),

            "speed":
                scenario.get(
                    "speed"
                ),

            "phase":
                scenario.get(
                    "phase"
                ),

            "elapsed_time_sec":
                scenario.get(
                    "elapsed_time_sec"
                ),

            "total_duration_sec":
                scenario.get(
                    "total_duration_sec"
                ),

            "progress":
                scenario.get(
                    "progress"
                ),

            "task_active":
                task_active,

            "ticks":
                self._ticks,

            "successful_ticks":
                self._successful_ticks,

            "failed_ticks":
                self._failed_ticks,

            "play_count":
                self._play_count,

            "pause_count":
                self._pause_count,

            "resume_count":
                self._resume_count,

            "stop_count":
                self._stop_count,

            "restart_count":
                self._restart_count,

            "seek_count":
                self._seek_count,

            "speed_change_count":
                self._speed_change_count,

            "latest_command_available":
                self._latest_command
                is not None,

            "latest_result_available":
                self._latest_result
                is not None,

            "last_error":
                self._last_error,

            "started_at":
                self._started_at,

            "stopped_at":
                self._stopped_at,

            "completed_at":
                self._completed_at,

            "scenario":
                scenario,

            "simulation_adapter":
                simulation,
        }


    def latest_result(
        self,
    ) -> Optional[Dict[str, Any]]:

        return self._latest_result


_default_player = (
    SimulationPlayer()
)


def get_simulation_player(
) -> SimulationPlayer:

    return _default_player


async def play_simulation(
) -> Dict[str, Any]:

    return await (
        _default_player.play()
    )


async def pause_simulation(
) -> Dict[str, Any]:

    return await (
        _default_player.pause()
    )


async def resume_simulation(
) -> Dict[str, Any]:

    return await (
        _default_player.resume()
    )


async def stop_simulation(
) -> Dict[str, Any]:

    return await (
        _default_player.stop()
    )


async def reset_simulation_player(
) -> Dict[str, Any]:

    return await (
        _default_player.reset()
    )


async def restart_simulation(
    *,
    auto_play: bool = True,
) -> Dict[str, Any]:

    return await (
        _default_player.restart(
            auto_play=auto_play
        )
    )


def set_simulation_speed(
    speed: float,
) -> Dict[str, Any]:

    return (
        _default_player.set_speed(
            speed
        )
    )


async def seek_simulation(
    elapsed_time_sec: float,
) -> Dict[str, Any]:

    return await (
        _default_player.seek(
            elapsed_time_sec
        )
    )


async def tick_simulation(
    *,
    delta_real_sec: Optional[float] = None,
) -> Dict[str, Any]:

    return await (
        _default_player.tick(
            delta_real_sec=delta_real_sec
        )
    )


def get_simulation_player_status(
) -> Dict[str, Any]:

    return (
        _default_player.status()
    )


def get_latest_simulation_result(
) -> Optional[Dict[str, Any]]:

    return (
        _default_player.latest_result()
    )


def get_simulation_player_info(
) -> Dict[str, Any]:

    return {
        "service":
            "simulation_player",

        "version":
            SIMULATION_PLAYER_VERSION,

        "purpose":
            "Continuous PRATIRUP mission simulation runtime",

        "controls": [
            "play",
            "pause",
            "resume",
            "stop",
            "reset",
            "restart",
            "speed",
            "seek",
            "tick",
        ],

        "supported_speeds":
            list(
                SUPPORTED_SPEEDS
            ),

        "default_tick_interval_sec":
            DEFAULT_TICK_INTERVAL_SEC,

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

        "scenario_version_expected":
            "1.0.0",

        "simulation_adapter_version_expected":
            "1.2.0",

        "telemetry_pipeline_version_expected":
            "2.8.0",

        "zero_is_valid":
            True,

        "none_means_unavailable":
            True,
    }
