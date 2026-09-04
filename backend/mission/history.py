from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from backend.database.database import database_session

from backend.database.models import (
    Mission,
    TelemetrySample,
)

from backend.database.repository import (
    count_mission_telemetry,
    get_recent_telemetry,
)


MISSION_HISTORY_VERSION = "1.0.0"


DEFAULT_MISSION_LIMIT = 50

MAX_MISSION_LIMIT = 1000

DEFAULT_TELEMETRY_LIMIT = 1000

MAX_TELEMETRY_LIMIT = 10000


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


def _uuid_string(
    value: Any,
) -> str | None:

    if value is None:
        return None

    return str(value)


def _safe_limit(
    value: int | None,
    *,
    default: int,
    maximum: int,
) -> int:

    if value is None:
        return default

    try:
        parsed = int(value)

    except (
        TypeError,
        ValueError,
    ):
        return default

    return max(
        1,
        min(
            parsed,
            maximum,
        ),
    )


def _as_uuid(
    value: UUID | str,
) -> UUID:

    if isinstance(
        value,
        UUID,
    ):
        return value

    return UUID(
        str(value)
    )


def _safe_dict(
    value: Any,
) -> dict[str, Any]:

    if isinstance(
        value,
        dict,
    ):
        return value

    return {}


def _nested(
    payload: dict[str, Any],
    section: str,
    key: str,
) -> Any:

    section_data = payload.get(
        section
    )

    if not isinstance(
        section_data,
        dict,
    ):
        return None

    return section_data.get(
        key
    )


def serialize_mission(
    mission: Mission,
    *,
    telemetry_count: int | None = None,
) -> dict[str, Any]:

    result = {

        "id":
            _uuid_string(
                mission.id
            ),

        "engine_id":
            _uuid_string(
                mission.engine_id
            ),

        "mission_code":
            mission.mission_code,

        "mission_name":
            mission.mission_name,

        "source_type":
            mission.source_type,

        "status":
            mission.status,

        "profile_name":
            mission.profile_name,

        "started_at":
            _iso(
                mission.started_at
            ),

        "ended_at":
            _iso(
                mission.ended_at
            ),

        "duration_sec":
            mission.duration_sec,

        "notes":
            mission.notes,

        "metadata":
            mission.metadata_json,
    }

    if telemetry_count is not None:

        result[
            "telemetry_count"
        ] = int(
            telemetry_count
        )

    return result


def serialize_telemetry_sample(
    sample: TelemetrySample,
    *,
    prefer_canonical: bool = True,
) -> dict[str, Any]:

    raw_payload = (
        sample.raw_payload
        if isinstance(
            sample.raw_payload,
            dict,
        )
        else None
    )

    result = {

        "id":
            _uuid_string(
                sample.id
            ),

        "mission_id":
            _uuid_string(
                sample.mission_id
            ),

        "sequence":
            sample.sequence,

        "timestamp":
            _iso(
                sample.timestamp
            ),

        "source_type":
            sample.source_type,

        "mission_phase":
            sample.mission_phase,

        "typed": {

            "engine": {

                "rpm":
                    sample.rpm,

                "throttle_pct":
                    sample.throttle_pct,

                "engine_load_pct":
                    sample.engine_load_pct,
            },

            "environment": {

                "altitude_ft":
                    sample.altitude_ft,

                "ambient_temperature_c":
                    sample.ambient_temperature_c,

                "ambient_pressure_kpa":
                    sample.ambient_pressure_kpa,
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

                "flow_lph":
                    sample.fuel_flow_lph,

                "pressure_kpa":
                    sample.fuel_pressure_kpa,

                "injection_timing_deg":
                    sample.injection_timing_deg,
            },

            "vibration": {

                "overall_g":
                    sample.vibration_overall_g,
            },

            "electrical": {

                "battery_voltage_v":
                    sample.battery_voltage_v,

                "alternator_voltage_v":
                    sample.alternator_voltage_v,

                "alternator_current_a":
                    sample.alternator_current_a,
            },
        },

        "raw_payload":
            raw_payload,

        "inserted_at":
            _iso(
                sample.inserted_at
            ),
    }

    if (
        prefer_canonical
        and
        raw_payload is not None
    ):

        result[
            "telemetry"
        ] = raw_payload

        result[
            "telemetry_source"
        ] = "raw_payload"

    else:

        result[
            "telemetry"
        ] = result[
            "typed"
        ]

        result[
            "telemetry_source"
        ] = "typed_columns"

    return result


def get_mission(
    mission_id: UUID | str,
) -> dict[str, Any] | None:

    mission_uuid = _as_uuid(
        mission_id
    )

    with database_session() as db:

        mission = db.get(
            Mission,
            mission_uuid,
        )

        if mission is None:
            return None

        telemetry_count = (
            count_mission_telemetry(
                db,
                mission_id=
                    mission_uuid,
            )
        )

        return serialize_mission(
            mission,
            telemetry_count=
                telemetry_count,
        )


def list_missions(
    *,
    limit: int = DEFAULT_MISSION_LIMIT,
    status: str | None = None,
    source_type: str | None = None,
) -> dict[str, Any]:

    safe_limit = _safe_limit(
        limit,
        default=
            DEFAULT_MISSION_LIMIT,
        maximum=
            MAX_MISSION_LIMIT,
    )

    with database_session() as db:

        statement = (
            select(
                Mission
            )
            .order_by(
                Mission.started_at.desc(),
                Mission.id.desc(),
            )
        )

        if status is not None:

            statement = (
                statement.where(
                    Mission.status
                    == str(status)
                )
            )

        if source_type is not None:

            statement = (
                statement.where(
                    Mission.source_type
                    == str(source_type)
                )
            )

        statement = (
            statement.limit(
                safe_limit
            )
        )

        missions = list(
            db.scalars(
                statement
            ).all()
        )

        items: list[
            dict[str, Any]
        ] = []

        for mission in missions:

            telemetry_count = (
                count_mission_telemetry(
                    db,
                    mission_id=
                        mission.id,
                )
            )

            items.append(
                serialize_mission(
                    mission,
                    telemetry_count=
                        telemetry_count,
                )
            )

        return {

            "version":
                MISSION_HISTORY_VERSION,

            "count":
                len(items),

            "limit":
                safe_limit,

            "filters": {

                "status":
                    status,

                "source_type":
                    source_type,
            },

            "missions":
                items,
        }


def get_mission_telemetry(
    mission_id: UUID | str,
    *,
    limit: int = DEFAULT_TELEMETRY_LIMIT,
    newest_first: bool = False,
    prefer_canonical: bool = True,
) -> dict[str, Any]:

    mission_uuid = _as_uuid(
        mission_id
    )

    safe_limit = _safe_limit(
        limit,
        default=
            DEFAULT_TELEMETRY_LIMIT,
        maximum=
            MAX_TELEMETRY_LIMIT,
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

                "mission_id":
                    str(
                        mission_uuid
                    ),

                "count":
                    0,

                "frames":
                    [],
            }

        samples = (
            get_recent_telemetry(
                db,
                mission_id=
                    mission_uuid,
                limit=
                    safe_limit,
            )
        )

        if not newest_first:

            samples = list(
                reversed(
                    samples
                )
            )

        frames = [

            serialize_telemetry_sample(
                sample,
                prefer_canonical=
                    prefer_canonical,
            )

            for sample in samples
        ]

        total_count = (
            count_mission_telemetry(
                db,
                mission_id=
                    mission_uuid,
            )
        )

        return {

            "success":
                True,

            "found":
                True,

            "version":
                MISSION_HISTORY_VERSION,

            "mission":
                serialize_mission(
                    mission,
                    telemetry_count=
                        total_count,
                ),

            "total_count":
                total_count,

            "returned_count":
                len(frames),

            "limit":
                safe_limit,

            "order":
                (
                    "NEWEST_FIRST"
                    if newest_first
                    else
                    "OLDEST_FIRST"
                ),

            "canonical_preferred":
                bool(
                    prefer_canonical
                ),

            "frames":
                frames,
        }


def _numeric_values(
    samples: list[TelemetrySample],
    *,
    typed_field: str | None = None,
    canonical_section: str | None = None,
    canonical_key: str | None = None,
) -> list[float]:

    values: list[
        float
    ] = []

    for sample in samples:

        value: Any = None

        raw = (
            sample.raw_payload
            if isinstance(
                sample.raw_payload,
                dict,
            )
            else {}
        )

        if (
            canonical_section is not None
            and
            canonical_key is not None
        ):

            value = _nested(
                raw,
                canonical_section,
                canonical_key,
            )

        if (
            value is None
            and
            typed_field is not None
            and
            hasattr(
                sample,
                typed_field,
            )
        ):

            value = getattr(
                sample,
                typed_field,
            )

        if (
            isinstance(
                value,
                (int, float),
            )
            and
            not isinstance(
                value,
                bool,
            )
        ):

            values.append(
                float(value)
            )

    return values


def _statistics(
    values: list[float],
) -> dict[str, Any]:

    if not values:

        return {

            "available":
                False,

            "samples":
                0,

            "minimum":
                None,

            "maximum":
                None,

            "average":
                None,

            "first":
                None,

            "last":
                None,
        }

    return {

        "available":
            True,

        "samples":
            len(values),

        "minimum":
            min(values),

        "maximum":
            max(values),

        "average":
            (
                sum(values)
                / len(values)
            ),

        "first":
            values[0],

        "last":
            values[-1],
    }


def get_mission_summary(
    mission_id: UUID | str,
) -> dict[str, Any]:

    mission_uuid = _as_uuid(
        mission_id
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

        count = len(
            samples
        )

        rpm = _numeric_values(
            samples,
            typed_field="rpm",
            canonical_section="engine",
            canonical_key="rpm",
        )

        throttle = _numeric_values(
            samples,
            typed_field="throttle_pct",
            canonical_section="engine",
            canonical_key="throttle_percent",
        )

        load = _numeric_values(
            samples,
            typed_field="engine_load_pct",
            canonical_section="engine",
            canonical_key="load_percent",
        )

        power = _numeric_values(
            samples,
            canonical_section="engine",
            canonical_key="power_kw",
        )

        torque = _numeric_values(
            samples,
            canonical_section="engine",
            canonical_key="torque_nm",
        )

        cht1 = _numeric_values(
            samples,
            typed_field="cht_1_c",
            canonical_section="cht",
            canonical_key="cylinder1_c",
        )

        cht2 = _numeric_values(
            samples,
            typed_field="cht_2_c",
            canonical_section="cht",
            canonical_key="cylinder2_c",
        )

        cht3 = _numeric_values(
            samples,
            typed_field="cht_3_c",
            canonical_section="cht",
            canonical_key="cylinder3_c",
        )

        cht4 = _numeric_values(
            samples,
            typed_field="cht_4_c",
            canonical_section="cht",
            canonical_key="cylinder4_c",
        )

        egt1 = _numeric_values(
            samples,
            typed_field="egt_1_c",
            canonical_section="egt",
            canonical_key="cylinder1_c",
        )

        egt2 = _numeric_values(
            samples,
            typed_field="egt_2_c",
            canonical_section="egt",
            canonical_key="cylinder2_c",
        )

        egt3 = _numeric_values(
            samples,
            typed_field="egt_3_c",
            canonical_section="egt",
            canonical_key="cylinder3_c",
        )

        egt4 = _numeric_values(
            samples,
            typed_field="egt_4_c",
            canonical_section="egt",
            canonical_key="cylinder4_c",
        )

        oil_pressure = (
            _numeric_values(
                samples,
                typed_field=
                    "oil_pressure_kpa",
                canonical_section=
                    "oil",
                canonical_key=
                    "pressure_kpa",
            )
        )

        oil_temperature = (
            _numeric_values(
                samples,
                typed_field=
                    "oil_temperature_c",
                canonical_section=
                    "oil",
                canonical_key=
                    "temperature_c",
            )
        )

        fuel_pressure = (
            _numeric_values(
                samples,
                typed_field=
                    "fuel_pressure_kpa",
                canonical_section=
                    "fuel",
                canonical_key=
                    "pressure_kpa",
            )
        )

        fuel_mass_flow = (
            _numeric_values(
                samples,
                canonical_section=
                    "fuel",
                canonical_key=
                    "flow_kg_per_second",
            )
        )

        injection_timing = (
            _numeric_values(
                samples,
                typed_field=
                    "injection_timing_deg",
                canonical_section=
                    "fuel",
                canonical_key=
                    "injection_timing_deg",
            )
        )

        vibration = (
            _numeric_values(
                samples,
                typed_field=
                    "vibration_overall_g",
                canonical_section=
                    "vibration",
                canonical_key=
                    "overall_g",
            )
        )

        battery_voltage = (
            _numeric_values(
                samples,
                typed_field=
                    "battery_voltage_v",
                canonical_section=
                    "electrical",
                canonical_key=
                    "battery_voltage_v",
            )
        )

        alternator_voltage = (
            _numeric_values(
                samples,
                typed_field=
                    "alternator_voltage_v",
                canonical_section=
                    "electrical",
                canonical_key=
                    "alternator_voltage_v",
            )
        )

        altitude_m = (
            _numeric_values(
                samples,
                canonical_section=
                    "environment",
                canonical_key=
                    "altitude_m",
            )
        )

        altitude_ft = (
            _numeric_values(
                samples,
                typed_field=
                    "altitude_ft",
                canonical_section=
                    "environment",
                canonical_key=
                    "altitude_ft",
            )
        )

        ambient_temperature = (
            _numeric_values(
                samples,
                typed_field=
                    "ambient_temperature_c",
                canonical_section=
                    "environment",
                canonical_key=
                    "ambient_temperature_c",
            )
        )

        ambient_pressure = (
            _numeric_values(
                samples,
                typed_field=
                    "ambient_pressure_kpa",
                canonical_section=
                    "environment",
                canonical_key=
                    "ambient_pressure_kpa",
            )
        )

        phases: list[str] = []

        for sample in samples:

            phase = (
                sample.mission_phase
            )

            if phase is None:

                raw = (
                    sample.raw_payload
                    if isinstance(
                        sample.raw_payload,
                        dict,
                    )
                    else {}
                )

                mission_data = (
                    _safe_dict(
                        raw.get(
                            "mission"
                        )
                    )
                )

                phase = (
                    mission_data.get(
                        "phase"
                    )
                    or
                    mission_data.get(
                        "mission_phase"
                    )
                )

            if (
                phase is not None
                and
                str(phase) not in phases
            ):

                phases.append(
                    str(phase)
                )

        first_timestamp = (
            samples[0].timestamp
            if samples
            else None
        )

        last_timestamp = (
            samples[-1].timestamp
            if samples
            else None
        )

        observed_duration_sec = None

        if (
            first_timestamp is not None
            and
            last_timestamp is not None
        ):

            observed_duration_sec = (
                last_timestamp
                - first_timestamp
            ).total_seconds()

        return {

            "success":
                True,

            "found":
                True,

            "version":
                MISSION_HISTORY_VERSION,

            "mission":
                serialize_mission(
                    mission,
                    telemetry_count=
                        count,
                ),

            "telemetry": {

                "sample_count":
                    count,

                "first_timestamp":
                    _iso(
                        first_timestamp
                    ),

                "last_timestamp":
                    _iso(
                        last_timestamp
                    ),

                "observed_duration_sec":
                    observed_duration_sec,

                "phases":
                    phases,
            },

            "engine": {

                "rpm":
                    _statistics(
                        rpm
                    ),

                "throttle_percent":
                    _statistics(
                        throttle
                    ),

                "load_percent":
                    _statistics(
                        load
                    ),

                "power_kw":
                    _statistics(
                        power
                    ),

                "torque_nm":
                    _statistics(
                        torque
                    ),
            },

            "cht": {

                "cylinder1_c":
                    _statistics(
                        cht1
                    ),

                "cylinder2_c":
                    _statistics(
                        cht2
                    ),

                "cylinder3_c":
                    _statistics(
                        cht3
                    ),

                "cylinder4_c":
                    _statistics(
                        cht4
                    ),
            },

            "egt": {

                "cylinder1_c":
                    _statistics(
                        egt1
                    ),

                "cylinder2_c":
                    _statistics(
                        egt2
                    ),

                "cylinder3_c":
                    _statistics(
                        egt3
                    ),

                "cylinder4_c":
                    _statistics(
                        egt4
                    ),
            },

            "oil": {

                "pressure_kpa":
                    _statistics(
                        oil_pressure
                    ),

                "temperature_c":
                    _statistics(
                        oil_temperature
                    ),
            },

            "fuel": {

                "pressure_kpa":
                    _statistics(
                        fuel_pressure
                    ),

                "flow_kg_per_second":
                    _statistics(
                        fuel_mass_flow
                    ),

                "injection_timing_deg":
                    _statistics(
                        injection_timing
                    ),
            },

            "vibration": {

                "overall_g":
                    _statistics(
                        vibration
                    ),
            },

            "electrical": {

                "battery_voltage_v":
                    _statistics(
                        battery_voltage
                    ),

                "alternator_voltage_v":
                    _statistics(
                        alternator_voltage
                    ),
            },

            "environment": {

                "altitude_m":
                    _statistics(
                        altitude_m
                    ),

                "altitude_ft":
                    _statistics(
                        altitude_ft
                    ),

                "ambient_temperature_c":
                    _statistics(
                        ambient_temperature
                    ),

                "ambient_pressure_kpa":
                    _statistics(
                        ambient_pressure
                    ),
            },
        }


def get_mission_timeline(
    mission_id: UUID | str,
    *,
    limit: int = DEFAULT_TELEMETRY_LIMIT,
) -> dict[str, Any]:

    mission_uuid = _as_uuid(
        mission_id
    )

    safe_limit = _safe_limit(
        limit,
        default=
            DEFAULT_TELEMETRY_LIMIT,
        maximum=
            MAX_TELEMETRY_LIMIT,
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

                "mission_id":
                    str(
                        mission_uuid
                    ),

                "points":
                    [],
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
            .limit(
                safe_limit
            )
        )

        samples = list(
            db.scalars(
                statement
            ).all()
        )

        points: list[
            dict[str, Any]
        ] = []

        first_timestamp = (
            samples[0].timestamp
            if samples
            else None
        )

        for sample in samples:

            raw = (
                sample.raw_payload
                if isinstance(
                    sample.raw_payload,
                    dict,
                )
                else {}
            )

            engine = _safe_dict(
                raw.get(
                    "engine"
                )
            )

            oil = _safe_dict(
                raw.get(
                    "oil"
                )
            )

            vibration = _safe_dict(
                raw.get(
                    "vibration"
                )
            )

            environment = (
                _safe_dict(
                    raw.get(
                        "environment"
                    )
                )
            )

            mission_data = (
                _safe_dict(
                    raw.get(
                        "mission"
                    )
                )
            )

            phase = (
                sample.mission_phase
            )

            if phase is None:

                phase = (
                    mission_data.get(
                        "phase"
                    )
                    or
                    mission_data.get(
                        "mission_phase"
                    )
                )

            elapsed_sec = None

            if (
                first_timestamp is not None
                and
                sample.timestamp is not None
            ):

                elapsed_sec = (
                    sample.timestamp
                    - first_timestamp
                ).total_seconds()

            rpm = engine.get(
                "rpm"
            )

            if rpm is None:
                rpm = sample.rpm

            throttle = engine.get(
                "throttle_percent"
            )

            if throttle is None:
                throttle = (
                    sample.throttle_pct
                )

            load = engine.get(
                "load_percent"
            )

            if load is None:
                load = (
                    sample.engine_load_pct
                )

            oil_pressure = oil.get(
                "pressure_kpa"
            )

            if oil_pressure is None:
                oil_pressure = (
                    sample.oil_pressure_kpa
                )

            vibration_g = (
                vibration.get(
                    "overall_g"
                )
            )

            if vibration_g is None:
                vibration_g = (
                    sample.vibration_overall_g
                )

            altitude_m = (
                environment.get(
                    "altitude_m"
                )
            )

            altitude_ft = (
                environment.get(
                    "altitude_ft"
                )
            )

            if altitude_ft is None:
                altitude_ft = (
                    sample.altitude_ft
                )

            points.append({

                "sequence":
                    sample.sequence,

                "timestamp":
                    _iso(
                        sample.timestamp
                    ),

                "elapsed_sec":
                    elapsed_sec,

                "phase":
                    phase,

                "rpm":
                    rpm,

                "throttle_percent":
                    throttle,

                "load_percent":
                    load,

                "oil_pressure_kpa":
                    oil_pressure,

                "vibration_overall_g":
                    vibration_g,

                "altitude_m":
                    altitude_m,

                "altitude_ft":
                    altitude_ft,
            })

        total_count = (
            count_mission_telemetry(
                db,
                mission_id=
                    mission_uuid,
            )
        )

        return {

            "success":
                True,

            "found":
                True,

            "version":
                MISSION_HISTORY_VERSION,

            "mission_id":
                str(
                    mission_uuid
                ),

            "mission_code":
                mission.mission_code,

            "total_count":
                total_count,

            "returned_count":
                len(points),

            "limit":
                safe_limit,

            "order":
                "OLDEST_FIRST",

            "points":
                points,
        }


def get_history_status(
) -> dict[str, Any]:

    with database_session() as db:

        mission_count = db.scalar(
            select(
                func.count(
                    Mission.id
                )
            )
        )

        telemetry_count = db.scalar(
            select(
                func.count(
                    TelemetrySample.id
                )
            )
        )

        completed_count = db.scalar(
            select(
                func.count(
                    Mission.id
                )
            ).where(
                Mission.status
                == "COMPLETED"
            )
        )

        return {

            "service":
                "mission_history",

            "version":
                MISSION_HISTORY_VERSION,

            "status":
                "READY",

            "read_only":
                True,

            "mission_count":
                int(
                    mission_count
                    or 0
                ),

            "completed_missions":
                int(
                    completed_count
                    or 0
                ),

            "telemetry_samples":
                int(
                    telemetry_count
                    or 0
                ),
        }
