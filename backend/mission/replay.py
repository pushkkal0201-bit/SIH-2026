from __future__ import annotations

import asyncio

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable
from uuid import UUID

from sqlalchemy import select

from backend.database.database import database_session
from backend.database.models import Mission, TelemetrySample


REPLAY_ENGINE_VERSION = "1.1.0"


SUPPORTED_REPLAY_SPEEDS = (
    0.5,
    1.0,
    2.0,
    5.0,
)

DEFAULT_REPLAY_SPEED = 1.0

MAX_REPLAY_DELAY_SEC = 5.0

MIN_REPLAY_DELAY_SEC = 0.001


class ReplayState(str, Enum):

    EMPTY = "EMPTY"

    LOADED = "LOADED"

    PLAYING = "PLAYING"

    PAUSED = "PAUSED"

    COMPLETED = "COMPLETED"

    STOPPED = "STOPPED"


@dataclass
class ReplayFrame:

    index: int

    sequence: int | None

    timestamp: datetime | None

    mission_phase: str | None

    telemetry: dict[str, Any]


ReplayCallback = Callable[
    [dict[str, Any]],
    Awaitable[None] | None,
]


def _as_uuid(
    value: UUID | str,
) -> UUID:

    if isinstance(value, UUID):

        return value

    return UUID(
        str(value)
    )


def _iso(
    value: Any,
) -> str | None:

    if value is None:

        return None

    if isinstance(
        value,
        datetime,
    ):

        return value.isoformat()

    return str(value)


def _safe_dict(
    value: Any,
) -> dict[str, Any]:

    if isinstance(
        value,
        dict,
    ):

        return deepcopy(
            value
        )

    return {}


def _utc_now() -> str:

    return datetime.now(
        timezone.utc
    ).isoformat()


def _mission_phase(
    sample: TelemetrySample,
    payload: dict[str, Any],
) -> str | None:

    if sample.mission_phase is not None:

        return str(
            sample.mission_phase
        )

    mission = payload.get(
        "mission"
    )

    if isinstance(
        mission,
        dict,
    ):

        phase = (
            mission.get("phase")
            or mission.get(
                "mission_phase"
            )
        )

        if phase is not None:

            return str(
                phase
            )

    meta = payload.get(
        "meta"
    )

    if isinstance(
        meta,
        dict,
    ):

        phase = meta.get(
            "mission_phase"
        )

        if phase is not None:

            return str(
                phase
            )

    return None


def _canonical_payload(
    sample: TelemetrySample,
) -> dict[str, Any]:

    payload = _safe_dict(
        sample.raw_payload
    )

    if payload:

        return payload

    return {

        "meta": {

            "sequence":
                sample.sequence,

            "source":
                sample.source_type,

            "timestamp":
                _iso(
                    sample.timestamp
                ),
        },

        "engine": {

            "rpm":
                sample.rpm,

            "throttle_percent":
                sample.throttle_pct,

            "load_percent":
                sample.engine_load_pct,

            "power_kw":
                None,

            "torque_nm":
                None,
        },

        "cht": {

            "cylinder1_c":
                sample.cht_1_c,

            "cylinder2_c":
                sample.cht_2_c,

            "cylinder3_c":
                sample.cht_3_c,

            "cylinder4_c":
                sample.cht_4_c,
        },

        "egt": {

            "cylinder1_c":
                sample.egt_1_c,

            "cylinder2_c":
                sample.egt_2_c,

            "cylinder3_c":
                sample.egt_3_c,

            "cylinder4_c":
                sample.egt_4_c,
        },

        "oil": {

            "pressure_kpa":
                sample.oil_pressure_kpa,

            "temperature_c":
                sample.oil_temperature_c,
        },

        "fuel": {

            "flow_kg_per_second":
                None,

            "pressure_kpa":
                sample.fuel_pressure_kpa,

            "injection_timing_deg":
                sample.injection_timing_deg,
        },

        "vibration": {

            "overall_g":
                sample.vibration_overall_g,

            "x_g":
                None,

            "y_g":
                None,

            "z_g":
                None,
        },

        "electrical": {

            "battery_voltage_v":
                sample.battery_voltage_v,

            "battery_current_a":
                None,

            "alternator_voltage_v":
                sample.alternator_voltage_v,

            "alternator_current_a":
                sample.alternator_current_a,
        },

        "environment": {

            "altitude_m":
                None,

            "altitude_ft":
                sample.altitude_ft,

            "ambient_temperature_c":
                sample.ambient_temperature_c,

            "ambient_pressure_kpa":
                sample.ambient_pressure_kpa,

            "air_density_kg_m3":
                None,
        },
    }


def _prepare_replay_payload(
    *,
    frame: ReplayFrame,
    mission_id: UUID,
    mission_code: str | None,
    replay_speed: float,
) -> dict[str, Any]:

    payload = deepcopy(
        frame.telemetry
    )

    meta = payload.get(
        "meta"
    )

    if not isinstance(
        meta,
        dict,
    ):

        meta = {}

        payload["meta"] = meta

    original_source = meta.get(
        "source"
    )

    if original_source is None:

        original_source = "UNKNOWN"

    meta["source"] = "REPLAY"

    meta["original_source"] = (
        original_source
    )

    meta["replay"] = True

    meta["replay_engine_version"] = (
        REPLAY_ENGINE_VERSION
    )

    meta["replay_frame_index"] = (
        frame.index
    )

    meta["replay_speed"] = (
        replay_speed
    )

    meta["historical_timestamp"] = (
        _iso(
            frame.timestamp
        )
    )

    meta["replay_emitted_at"] = (
        _utc_now()
    )

    if frame.sequence is not None:

        meta["sequence"] = (
            frame.sequence
        )

    mission = payload.get(
        "mission"
    )

    if not isinstance(
        mission,
        dict,
    ):

        mission = {}

        payload["mission"] = (
            mission
        )

    mission["id"] = str(
        mission_id
    )

    if mission_code is not None:

        mission["mission_code"] = (
            mission_code
        )

    mission["phase"] = (
        frame.mission_phase
    )

    mission["replay"] = True

    return payload


class HistoricalReplayEngine:

    def __init__(
        self,
    ) -> None:

        self._lock = (
            asyncio.Lock()
        )

        self._state = (
            ReplayState.EMPTY
        )

        self._mission_id: (
            UUID | None
        ) = None

        self._mission_code: (
            str | None
        ) = None

        self._mission_status: (
            str | None
        ) = None

        self._frames: list[
            ReplayFrame
        ] = []

        self._cursor = 0

        self._speed = (
            DEFAULT_REPLAY_SPEED
        )

        self._callback: (
            ReplayCallback | None
        ) = None

        self._task: (
            asyncio.Task | None
        ) = None

        self._emitted_frames = 0

        self._last_emitted_index: (
            int | None
        ) = None

        self._last_error: (
            str | None
        ) = None


    def set_callback(
        self,
        callback: ReplayCallback | None,
    ) -> None:

        self._callback = callback


    async def load(
        self,
        mission_id: UUID | str,
    ) -> dict[str, Any]:

        mission_uuid = _as_uuid(
            mission_id
        )

        await self.stop(
            clear=True
        )

        with database_session() as db:

            mission = db.get(
                Mission,
                mission_uuid,
            )

            if mission is None:

                return {

                    "success":
                        False,

                    "found":
                        False,

                    "error":
                        "MISSION_NOT_FOUND",

                    "mission_id":
                        str(
                            mission_uuid
                        ),
                }

            statement = (

                select(
                    TelemetrySample
                )

                .where(
                    TelemetrySample.mission_id
                    == mission_uuid
                )

                .order_by(
                    TelemetrySample.timestamp.asc(),
                    TelemetrySample.id.asc(),
                )
            )

            samples = list(
                db.scalars(
                    statement
                ).all()
            )

            frames: list[
                ReplayFrame
            ] = []

            for index, sample in enumerate(
                samples
            ):

                payload = (
                    _canonical_payload(
                        sample
                    )
                )

                frames.append(

                    ReplayFrame(

                        index=
                            index,

                        sequence=
                            sample.sequence,

                        timestamp=
                            sample.timestamp,

                        mission_phase=
                            _mission_phase(
                                sample,
                                payload,
                            ),

                        telemetry=
                            payload,
                    )
                )

            mission_code = getattr(
                mission,
                "mission_code",
                None,
            )

            mission_status = getattr(
                mission,
                "status",
                None,
            )

        async with self._lock:

            self._mission_id = (
                mission_uuid
            )

            self._mission_code = (
                mission_code
            )

            self._mission_status = (
                mission_status
            )

            self._frames = frames

            self._cursor = 0

            self._speed = (
                DEFAULT_REPLAY_SPEED
            )

            self._emitted_frames = 0

            self._last_emitted_index = (
                None
            )

            self._last_error = None

            if frames:

                self._state = (
                    ReplayState.LOADED
                )

            else:

                self._state = (
                    ReplayState.EMPTY
                )

        return {

            "success":
                True,

            "found":
                True,

            "mission_id":
                str(
                    mission_uuid
                ),

            "mission_code":
                mission_code,

            "mission_status":
                mission_status,

            "frame_count":
                len(
                    frames
                ),

            "state":
                self._state.value,

            "speed":
                self._speed,
        }


    async def play(
        self,
    ) -> dict[str, Any]:

        async with self._lock:

            if not self._frames:

                return self._failure(
                    "NO_REPLAY_LOADED"
                )

            if self._state == (
                ReplayState.PLAYING
            ):

                return self.get_status()

            if (
                self._state
                == ReplayState.COMPLETED
            ):

                self._cursor = 0

            if (
                self._state
                == ReplayState.STOPPED
                and self._cursor
                >= len(self._frames)
            ):

                self._cursor = 0

            self._state = (
                ReplayState.PLAYING
            )

            self._ensure_task()

        return self.get_status()


    async def pause(
        self,
    ) -> dict[str, Any]:

        async with self._lock:

            if self._state != (
                ReplayState.PLAYING
            ):

                return self._failure(
                    "REPLAY_NOT_PLAYING"
                )

            self._state = (
                ReplayState.PAUSED
            )

        return self.get_status()


    async def resume(
        self,
    ) -> dict[str, Any]:

        async with self._lock:

            if self._state != (
                ReplayState.PAUSED
            ):

                return self._failure(
                    "REPLAY_NOT_PAUSED"
                )

            if self._cursor >= len(
                self._frames
            ):

                self._state = (
                    ReplayState.COMPLETED
                )

                return self.get_status()

            self._state = (
                ReplayState.PLAYING
            )

            self._ensure_task()

        return self.get_status()


    async def set_speed(
        self,
        speed: float,
    ) -> dict[str, Any]:

        try:

            requested_speed = float(
                speed
            )

        except (
            TypeError,
            ValueError,
        ):

            return {

                "success":
                    False,

                "error":
                    "INVALID_REPLAY_SPEED",

                "requested_speed":
                    speed,

                "supported_speeds":
                    list(
                        SUPPORTED_REPLAY_SPEEDS
                    ),
            }

        if requested_speed not in (
            SUPPORTED_REPLAY_SPEEDS
        ):

            return {

                "success":
                    False,

                "error":
                    "UNSUPPORTED_REPLAY_SPEED",

                "requested_speed":
                    requested_speed,

                "supported_speeds":
                    list(
                        SUPPORTED_REPLAY_SPEEDS
                    ),
            }

        async with self._lock:

            self._speed = (
                requested_speed
            )

        return self.get_status()


    async def seek(
        self,
        frame_index: int,
    ) -> dict[str, Any]:

        try:

            requested_index = int(
                frame_index
            )

        except (
            TypeError,
            ValueError,
        ):

            return {

                "success":
                    False,

                "error":
                    "INVALID_REPLAY_INDEX",

                "requested_index":
                    frame_index,
            }

        async with self._lock:

            if not self._frames:

                return self._failure(
                    "NO_REPLAY_LOADED"
                )

            if (
                requested_index < 0
                or requested_index
                >= len(
                    self._frames
                )
            ):

                return {

                    "success":
                        False,

                    "error":
                        "INVALID_REPLAY_INDEX",

                    "requested_index":
                        requested_index,

                    "minimum_index":
                        0,

                    "maximum_index":
                        len(
                            self._frames
                        ) - 1,
                }

            self._cursor = (
                requested_index
            )

            if self._state == (
                ReplayState.COMPLETED
            ):

                self._state = (
                    ReplayState.PAUSED
                )

        return self.get_status()


    async def seek_percent(
        self,
        percent: float,
    ) -> dict[str, Any]:

        try:

            requested_percent = float(
                percent
            )

        except (
            TypeError,
            ValueError,
        ):

            return {

                "success":
                    False,

                "error":
                    "INVALID_REPLAY_PERCENT",

                "requested_percent":
                    percent,

                "minimum_percent":
                    0.0,

                "maximum_percent":
                    100.0,
            }

        async with self._lock:

            frame_count = len(
                self._frames
            )

        if frame_count == 0:

            return self._failure(
                "NO_REPLAY_LOADED"
            )

        if (
            requested_percent < 0.0
            or requested_percent > 100.0
        ):

            return {

                "success":
                    False,

                "error":
                    "INVALID_REPLAY_PERCENT",

                "requested_percent":
                    requested_percent,

                "minimum_percent":
                    0.0,

                "maximum_percent":
                    100.0,
            }

        if frame_count == 1:

            index = 0

        else:

            index = round(
                (
                    requested_percent
                    / 100.0
                )
                * (
                    frame_count - 1
                )
            )

        return await self.seek(
            index
        )


    async def reset(
        self,
    ) -> dict[str, Any]:

        await self.stop(
            clear=False
        )

        async with self._lock:

            if not self._frames:

                self._state = (
                    ReplayState.EMPTY
                )

                return self.get_status()

            self._cursor = 0

            self._state = (
                ReplayState.LOADED
            )

            self._emitted_frames = 0

            self._last_emitted_index = (
                None
            )

            self._last_error = None

        return self.get_status()


    async def stop(
        self,
        *,
        clear: bool = False,
    ) -> dict[str, Any]:

        task: asyncio.Task | None

        async with self._lock:

            task = self._task

            self._task = None

            if clear:

                self._frames = []

                self._mission_id = None

                self._mission_code = None

                self._mission_status = None

                self._cursor = 0

                self._state = (
                    ReplayState.EMPTY
                )

                self._emitted_frames = 0

                self._last_emitted_index = (
                    None
                )

                self._last_error = None

            elif self._frames:

                self._state = (
                    ReplayState.STOPPED
                )

            else:

                self._state = (
                    ReplayState.EMPTY
                )

        current_task = (
            asyncio.current_task()
        )

        if (
            task is not None
            and task is not current_task
            and not task.done()
        ):

            task.cancel()

            try:

                await task

            except asyncio.CancelledError:

                pass

        return self.get_status()


    def get_current_frame(
        self,
    ) -> dict[str, Any] | None:

        if not self._frames:

            return None

        index = min(
            max(
                self._cursor,
                0,
            ),
            len(
                self._frames
            ) - 1,
        )

        frame = self._frames[
            index
        ]

        mission_id = (
            self._mission_id
        )

        if mission_id is None:

            return None

        return _prepare_replay_payload(

            frame=
                frame,

            mission_id=
                mission_id,

            mission_code=
                self._mission_code,

            replay_speed=
                self._speed,
        )


    def get_status(
        self,
    ) -> dict[str, Any]:

        frame_count = len(
            self._frames
        )

        if frame_count > 0:

            maximum_index = (
                frame_count - 1
            )

            display_index = min(
                self._cursor,
                maximum_index,
            )

            if maximum_index > 0:

                progress_percent = (
                    display_index
                    / maximum_index
                    * 100.0
                )

            else:

                progress_percent = (
                    100.0
                )

            frame = self._frames[
                display_index
            ]

            current_sequence = (
                frame.sequence
            )

            current_phase = (
                frame.mission_phase
            )

            current_timestamp = (
                _iso(
                    frame.timestamp
                )
            )

        else:

            maximum_index = None

            display_index = None

            progress_percent = 0.0

            current_sequence = None

            current_phase = None

            current_timestamp = None

        return {

            "success":
                True,

            "service":
                "historical_replay",

            "version":
                REPLAY_ENGINE_VERSION,

            "state":
                self._state.value,

            "mission_id":
                (
                    str(
                        self._mission_id
                    )
                    if self._mission_id
                    else None
                ),

            "mission_code":
                self._mission_code,

            "mission_status":
                self._mission_status,

            "frame_count":
                frame_count,

            "cursor":
                self._cursor,

            "current_index":
                display_index,

            "maximum_index":
                maximum_index,

            "current_sequence":
                current_sequence,

            "current_phase":
                current_phase,

            "current_historical_timestamp":
                current_timestamp,

            "progress_percent":
                progress_percent,

            "speed":
                self._speed,

            "supported_speeds":
                list(
                    SUPPORTED_REPLAY_SPEEDS
                ),

            "emitted_frames":
                self._emitted_frames,

            "last_emitted_index":
                self._last_emitted_index,

            "last_error":
                self._last_error,

            "read_only":
                True,

            "database_writes":
                False,

            "persistence_enabled":
                False,

            "live_telemetry_ingestion":
                False,

            "model_reprocessing":
                False,
        }


    def _failure(
        self,
        error: str,
    ) -> dict[str, Any]:

        status = (
            self.get_status()
        )

        status["success"] = False

        status["error"] = (
            error
        )

        return status


    def _ensure_task(
        self,
    ) -> None:

        if (
            self._task is None
            or self._task.done()
        ):

            self._task = (
                asyncio.create_task(
                    self._run(),
                    name=
                        "pratirup-historical-replay",
                )
            )


    def _frame_delay(
        self,
        current_index: int,
        speed: float,
    ) -> float:

        if (
            current_index < 0
            or current_index
            >= len(
                self._frames
            ) - 1
        ):

            return (
                MIN_REPLAY_DELAY_SEC
            )

        current = self._frames[
            current_index
        ]

        following = self._frames[
            current_index + 1
        ]

        if (
            current.timestamp is None
            or following.timestamp is None
        ):

            recorded_delay = 1.0

        else:

            recorded_delay = (
                following.timestamp
                - current.timestamp
            ).total_seconds()

        if recorded_delay <= 0:

            recorded_delay = (
                MIN_REPLAY_DELAY_SEC
            )

        recorded_delay = min(
            recorded_delay,
            MAX_REPLAY_DELAY_SEC,
        )

        return max(
            recorded_delay / speed,
            MIN_REPLAY_DELAY_SEC,
        )


    async def _emit(
        self,
        frame: ReplayFrame,
        speed: float,
    ) -> None:

        mission_id = (
            self._mission_id
        )

        if mission_id is None:

            raise RuntimeError(
                "Replay mission identity is unavailable."
            )

        payload = (
            _prepare_replay_payload(

                frame=
                    frame,

                mission_id=
                    mission_id,

                mission_code=
                    self._mission_code,

                replay_speed=
                    speed,
            )
        )

        callback = (
            self._callback
        )

        if callback is not None:

            result = callback(
                payload
            )

            if asyncio.iscoroutine(
                result
            ):

                await result

        self._emitted_frames += 1

        self._last_emitted_index = (
            frame.index
        )


    async def _run(
        self,
    ) -> None:

        try:

            while True:

                async with self._lock:

                    if self._state != (
                        ReplayState.PLAYING
                    ):

                        return

                    if (
                        self._cursor
                        >= len(
                            self._frames
                        )
                    ):

                        self._state = (
                            ReplayState.COMPLETED
                        )

                        return

                    index = (
                        self._cursor
                    )

                    frame = (
                        self._frames[
                            index
                        ]
                    )

                    speed = (
                        self._speed
                    )

                    delay = (
                        self._frame_delay(
                            index,
                            speed,
                        )
                    )

                await self._emit(
                    frame,
                    speed,
                )

                async with self._lock:

                    if self._cursor == index:

                        self._cursor += 1

                    if (
                        self._cursor
                        >= len(
                            self._frames
                        )
                    ):

                        self._state = (
                            ReplayState.COMPLETED
                        )

                        return

                    if self._state != (
                        ReplayState.PLAYING
                    ):

                        return

                await asyncio.sleep(
                    delay
                )

        except asyncio.CancelledError:

            raise

        except Exception as exc:

            async with self._lock:

                self._last_error = (
                    f"{type(exc).__name__}: {exc}"
                )

                self._state = (
                    ReplayState.STOPPED
                )

        finally:

            current_task = (
                asyncio.current_task()
            )

            if self._task is current_task:

                self._task = None


historical_replay_engine = (
    HistoricalReplayEngine()
)


def get_replay_service_status(
) -> dict[str, Any]:

    status = (
        historical_replay_engine
        .get_status()
    )

    status["architecture"] = (
        "READ_ONLY_HISTORICAL_REPLAY"
    )

    status["database_writes"] = (
        False
    )

    status["live_telemetry_ingestion"] = (
        False
    )

    status["persistence_enabled"] = (
        False
    )

    status["model_reprocessing"] = (
        False
    )

    return status
