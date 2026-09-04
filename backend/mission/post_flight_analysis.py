from __future__ import annotations
from datetime import datetime
from statistics import mean
from typing import Any
from uuid import UUID
from sqlalchemy import select
from backend.database.database import database_session
from backend.database.models import Mission, TelemetrySample

POST_FLIGHT_ANALYSIS_VERSION = "1.0.0"


def _as_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value

    return UUID(str(value))


def _iso(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    return str(value)


def _dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    return {}


def _nested(
    payload: dict[str, Any],
    section: str,
    key: str,
) -> Any:
    section_data = payload.get(section)

    if not isinstance(section_data, dict):
        return None

    return section_data.get(key)


def _number(value: Any) -> float | None:
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
    ):
        return float(value)

    return None


def _first_number(*values: Any) -> float | None:
    for value in values:
        result = _number(value)

        if result is not None:
            return result

    return None


def _stats(
    values: list[float],
) -> dict[str, Any]:
    if not values:
        return {
            "available": False,
            "samples": 0,
            "minimum": None,
            "maximum": None,
            "average": None,
            "first": None,
            "last": None,
            "change": None,
        }

    return {
        "available": True,
        "samples": len(values),
        "minimum": min(values),
        "maximum": max(values),
        "average": mean(values),
        "first": values[0],
        "last": values[-1],
        "change": values[-1] - values[0],
    }


def _percent(
    numerator: int,
    denominator: int,
) -> float:
    if denominator <= 0:
        return 0.0

    return (
        float(numerator)
        / float(denominator)
        * 100.0
    )


def _raw(
    sample: TelemetrySample,
) -> dict[str, Any]:
    return _dict(
        sample.raw_payload
    )


def _rpm(sample: TelemetrySample) -> float | None:
    return _first_number(
        _nested(
            _raw(sample),
            "engine",
            "rpm",
        ),
        sample.rpm,
    )


def _throttle(sample: TelemetrySample) -> float | None:
    return _first_number(
        _nested(
            _raw(sample),
            "engine",
            "throttle_percent",
        ),
        sample.throttle_pct,
    )


def _load(sample: TelemetrySample) -> float | None:
    return _first_number(
        _nested(
            _raw(sample),
            "engine",
            "load_percent",
        ),
        sample.engine_load_pct,
    )


def _power(sample: TelemetrySample) -> float | None:
    return _number(
        _nested(
            _raw(sample),
            "engine",
            "power_kw",
        )
    )


def _torque(sample: TelemetrySample) -> float | None:
    return _number(
        _nested(
            _raw(sample),
            "engine",
            "torque_nm",
        )
    )


def _cht(
    sample: TelemetrySample,
    cylinder: int,
) -> float | None:
    raw_value = _nested(
        _raw(sample),
        "cht",
        f"cylinder{cylinder}_c",
    )

    typed_value = getattr(
        sample,
        f"cht_{cylinder}_c",
        None,
    )

    return _first_number(
        raw_value,
        typed_value,
    )


def _egt(
    sample: TelemetrySample,
    cylinder: int,
) -> float | None:
    raw_value = _nested(
        _raw(sample),
        "egt",
        f"cylinder{cylinder}_c",
    )

    typed_value = getattr(
        sample,
        f"egt_{cylinder}_c",
        None,
    )

    return _first_number(
        raw_value,
        typed_value,
    )


def _oil_pressure(
    sample: TelemetrySample,
) -> float | None:
    return _first_number(
        _nested(
            _raw(sample),
            "oil",
            "pressure_kpa",
        ),
        sample.oil_pressure_kpa,
    )


def _oil_temperature(
    sample: TelemetrySample,
) -> float | None:
    return _first_number(
        _nested(
            _raw(sample),
            "oil",
            "temperature_c",
        ),
        sample.oil_temperature_c,
    )


def _vibration(
    sample: TelemetrySample,
) -> float | None:
    return _first_number(
        _nested(
            _raw(sample),
            "vibration",
            "overall_g",
        ),
        sample.vibration_overall_g,
    )


def _battery_voltage(
    sample: TelemetrySample,
) -> float | None:
    return _first_number(
        _nested(
            _raw(sample),
            "electrical",
            "battery_voltage_v",
        ),
        sample.battery_voltage_v,
    )


def _alternator_voltage(
    sample: TelemetrySample,
) -> float | None:
    return _first_number(
        _nested(
            _raw(sample),
            "electrical",
            "alternator_voltage_v",
        ),
        sample.alternator_voltage_v,
    )


def _altitude_m(
    sample: TelemetrySample,
) -> float | None:
    return _number(
        _nested(
            _raw(sample),
            "environment",
            "altitude_m",
        )
    )


def _ambient_temperature(
    sample: TelemetrySample,
) -> float | None:
    return _first_number(
        _nested(
            _raw(sample),
            "environment",
            "ambient_temperature_c",
        ),
        sample.ambient_temperature_c,
    )


def _ambient_pressure(
    sample: TelemetrySample,
) -> float | None:
    return _first_number(
        _nested(
            _raw(sample),
            "environment",
            "ambient_pressure_kpa",
        ),
        sample.ambient_pressure_kpa,
    )


def _phase(
    sample: TelemetrySample,
) -> str | None:
    if sample.mission_phase is not None:
        return str(sample.mission_phase)

    mission = _dict(
        _raw(sample).get("mission")
    )

    value = (
        mission.get("phase")
        or mission.get("mission_phase")
    )

    if value is None:
        return None

    return str(value)


def _series(
    samples: list[TelemetrySample],
    getter,
) -> list[float]:
    result: list[float] = []

    for sample in samples:
        value = getter(sample)

        if value is not None:
            result.append(value)

    return result


def _data_completeness(
    samples: list[TelemetrySample],
) -> dict[str, Any]:
    total = len(samples)

    fields = {
        "rpm": _rpm,
        "throttle_percent": _throttle,
        "load_percent": _load,
        "power_kw": _power,
        "torque_nm": _torque,
        "oil_pressure_kpa": _oil_pressure,
        "oil_temperature_c": _oil_temperature,
        "vibration_overall_g": _vibration,
        "battery_voltage_v": _battery_voltage,
        "alternator_voltage_v": _alternator_voltage,
        "altitude_m": _altitude_m,
        "ambient_temperature_c": _ambient_temperature,
        "ambient_pressure_kpa": _ambient_pressure,
    }

    result: dict[str, Any] = {}

    for name, getter in fields.items():
        available = sum(
            1
            for sample in samples
            if getter(sample) is not None
        )

        result[name] = {
            "available_samples": available,
            "total_samples": total,
            "coverage_percent": _percent(
                available,
                total,
            ),
        }

    for cylinder in range(1, 5):
        cht_available = sum(
            1
            for sample in samples
            if _cht(sample, cylinder)
            is not None
        )

        egt_available = sum(
            1
            for sample in samples
            if _egt(sample, cylinder)
            is not None
        )

        result[
            f"cht_cylinder{cylinder}"
        ] = {
            "available_samples":
                cht_available,
            "total_samples":
                total,
            "coverage_percent":
                _percent(
                    cht_available,
                    total,
                ),
        }

        result[
            f"egt_cylinder{cylinder}"
        ] = {
            "available_samples":
                egt_available,
            "total_samples":
                total,
            "coverage_percent":
                _percent(
                    egt_available,
                    total,
                ),
        }

    return result


def _phase_analysis(
    samples: list[TelemetrySample],
) -> list[dict[str, Any]]:
    groups: dict[
        str,
        list[TelemetrySample]
    ] = {}

    phase_order: list[str] = []

    for sample in samples:
        phase = (
            _phase(sample)
            or "UNKNOWN"
        )

        if phase not in groups:
            groups[phase] = []
            phase_order.append(phase)

        groups[phase].append(sample)

    result: list[
        dict[str, Any]
    ] = []

    for phase in phase_order:
        phase_samples = groups[phase]

        rpm = _series(
            phase_samples,
            _rpm,
        )

        throttle = _series(
            phase_samples,
            _throttle,
        )

        load = _series(
            phase_samples,
            _load,
        )

        vibration = _series(
            phase_samples,
            _vibration,
        )

        altitude = _series(
            phase_samples,
            _altitude_m,
        )

        cht_values: list[float] = []
        egt_values: list[float] = []

        for sample in phase_samples:
            for cylinder in range(1, 5):
                cht_value = _cht(
                    sample,
                    cylinder,
                )

                if cht_value is not None:
                    cht_values.append(
                        cht_value
                    )

                egt_value = _egt(
                    sample,
                    cylinder,
                )

                if egt_value is not None:
                    egt_values.append(
                        egt_value
                    )

        start = (
            phase_samples[0].timestamp
            if phase_samples
            else None
        )

        end = (
            phase_samples[-1].timestamp
            if phase_samples
            else None
        )

        duration = None

        if (
            start is not None
            and end is not None
        ):
            duration = (
                end - start
            ).total_seconds()

        result.append({
            "phase": phase,
            "sample_count":
                len(phase_samples),
            "start_timestamp":
                _iso(start),
            "end_timestamp":
                _iso(end),
            "observed_duration_sec":
                duration,
            "rpm":
                _stats(rpm),
            "throttle_percent":
                _stats(throttle),
            "load_percent":
                _stats(load),
            "cht_all_cylinders":
                _stats(cht_values),
            "egt_all_cylinders":
                _stats(egt_values),
            "vibration_overall_g":
                _stats(vibration),
            "altitude_m":
                _stats(altitude),
        })

    return result


def _cylinder_analysis(
    samples: list[TelemetrySample],
) -> dict[str, Any]:
    cht_result: dict[
        str,
        Any
    ] = {}

    egt_result: dict[
        str,
        Any
    ] = {}

    for cylinder in range(1, 5):
        cht_values = [
            value
            for sample in samples
            if (
                value := _cht(
                    sample,
                    cylinder,
                )
            ) is not None
        ]

        egt_values = [
            value
            for sample in samples
            if (
                value := _egt(
                    sample,
                    cylinder,
                )
            ) is not None
        ]

        cht_result[
            f"cylinder{cylinder}"
        ] = _stats(
            cht_values
        )

        egt_result[
            f"cylinder{cylinder}"
        ] = _stats(
            egt_values
        )

    cht_spreads: list[float] = []
    egt_spreads: list[float] = []

    max_cht_spread_event = None
    max_egt_spread_event = None

    for sample in samples:
        cht_values = [
            _cht(sample, cylinder)
            for cylinder in range(1, 5)
        ]

        cht_available = [
            value
            for value in cht_values
            if value is not None
        ]

        if len(cht_available) >= 2:
            spread = (
                max(cht_available)
                - min(cht_available)
            )

            cht_spreads.append(
                spread
            )

            if (
                max_cht_spread_event is None
                or spread
                >
                max_cht_spread_event[
                    "spread_c"
                ]
            ):
                max_cht_spread_event = {
                    "sequence":
                        sample.sequence,
                    "timestamp":
                        _iso(
                            sample.timestamp
                        ),
                    "phase":
                        _phase(sample),
                    "spread_c":
                        spread,
                    "values_c":
                        cht_values,
                }

        egt_values = [
            _egt(sample, cylinder)
            for cylinder in range(1, 5)
        ]

        egt_available = [
            value
            for value in egt_values
            if value is not None
        ]

        if len(egt_available) >= 2:
            spread = (
                max(egt_available)
                - min(egt_available)
            )

            egt_spreads.append(
                spread
            )

            if (
                max_egt_spread_event is None
                or spread
                >
                max_egt_spread_event[
                    "spread_c"
                ]
            ):
                max_egt_spread_event = {
                    "sequence":
                        sample.sequence,
                    "timestamp":
                        _iso(
                            sample.timestamp
                        ),
                    "phase":
                        _phase(sample),
                    "spread_c":
                        spread,
                    "values_c":
                        egt_values,
                }

    return {
        "cht": {
            "cylinders":
                cht_result,
            "spread":
                _stats(
                    cht_spreads
                ),
            "maximum_spread_event":
                max_cht_spread_event,
        },
        "egt": {
            "cylinders":
                egt_result,
            "spread":
                _stats(
                    egt_spreads
                ),
            "maximum_spread_event":
                max_egt_spread_event,
        },
    }


def _peak_event(
    samples: list[TelemetrySample],
    getter,
    *,
    mode: str = "MAX",
) -> dict[str, Any] | None:
    selected_sample = None
    selected_value = None

    for sample in samples:
        value = getter(sample)

        if value is None:
            continue

        if selected_value is None:
            selected_value = value
            selected_sample = sample
            continue

        if (
            mode == "MAX"
            and value > selected_value
        ):
            selected_value = value
            selected_sample = sample

        elif (
            mode == "MIN"
            and value < selected_value
        ):
            selected_value = value
            selected_sample = sample

    if selected_sample is None:
        return None

    return {
        "sequence":
            selected_sample.sequence,
        "timestamp":
            _iso(
                selected_sample.timestamp
            ),
        "phase":
            _phase(
                selected_sample
            ),
        "value":
            selected_value,
    }


def _significant_events(
    samples: list[TelemetrySample],
) -> list[dict[str, Any]]:
    events: list[
        dict[str, Any]
    ] = []

    if not samples:
        return events

    events.append({
        "type":
            "MISSION_DATA_START",
        "sequence":
            samples[0].sequence,
        "timestamp":
            _iso(
                samples[0].timestamp
            ),
        "phase":
            _phase(
                samples[0]
            ),
        "description":
            "First persisted telemetry sample.",
    })

    previous_phase = _phase(
        samples[0]
    )

    for sample in samples[1:]:
        phase = _phase(sample)

        if (
            phase is not None
            and phase != previous_phase
        ):
            events.append({
                "type":
                    "PHASE_TRANSITION",
                "sequence":
                    sample.sequence,
                "timestamp":
                    _iso(
                        sample.timestamp
                    ),
                "from_phase":
                    previous_phase,
                "to_phase":
                    phase,
                "description":
                    "Observed mission phase transition.",
            })

            previous_phase = phase

    peak_rpm = _peak_event(
        samples,
        _rpm,
        mode="MAX",
    )

    if peak_rpm:
        events.append({
            "type":
                "PEAK_RPM",
            **peak_rpm,
            "description":
                "Highest observed RPM in persisted mission data.",
        })

    peak_vibration = _peak_event(
        samples,
        _vibration,
        mode="MAX",
    )

    if peak_vibration:
        events.append({
            "type":
                "PEAK_VIBRATION",
            **peak_vibration,
            "description":
                "Highest observed overall vibration.",
        })

    peak_oil_temp = _peak_event(
        samples,
        _oil_temperature,
        mode="MAX",
    )

    if peak_oil_temp:
        events.append({
            "type":
                "PEAK_OIL_TEMPERATURE",
            **peak_oil_temp,
            "description":
                "Highest observed oil temperature.",
        })

    minimum_oil_pressure = (
        _peak_event(
            samples,
            _oil_pressure,
            mode="MIN",
        )
    )

    if minimum_oil_pressure:
        events.append({
            "type":
                "MINIMUM_OIL_PRESSURE",
            **minimum_oil_pressure,
            "description":
                "Lowest observed oil pressure. "
                "This is descriptive only; engine operating "
                "state must be considered before interpretation.",
        })

    peak_altitude = _peak_event(
        samples,
        _altitude_m,
        mode="MAX",
    )

    if peak_altitude:
        events.append({
            "type":
                "PEAK_ALTITUDE",
            **peak_altitude,
            "description":
                "Highest observed mission altitude.",
        })

    events.append({
        "type":
            "MISSION_DATA_END",
        "sequence":
            samples[-1].sequence,
        "timestamp":
            _iso(
                samples[-1].timestamp
            ),
        "phase":
            _phase(
                samples[-1]
            ),
        "description":
            "Final persisted telemetry sample.",
    })

    return events


def _observations(
    samples: list[TelemetrySample],
    *,
    phases: list[dict[str, Any]],
    completeness: dict[str, Any],
) -> list[dict[str, Any]]:
    observations: list[
        dict[str, Any]
    ] = []

    if not samples:
        return [{
            "level":
                "INFO",
            "code":
                "NO_TELEMETRY",
            "message":
                "No persisted telemetry is available for analysis.",
        }]

    phase_names = [
        item["phase"]
        for item in phases
    ]

    observations.append({
        "level":
            "INFO",
        "code":
            "MISSION_PHASE_COVERAGE",
        "message":
            (
                "Persisted telemetry contains "
                f"{len(phase_names)} observed mission phase(s): "
                + ", ".join(phase_names)
                + "."
            ),
    })

    if "ENGINE_SHUTDOWN" not in phase_names:
        observations.append({
            "level":
                "INFO",
            "code":
                "PARTIAL_MISSION_PROFILE",
            "message":
                (
                    "Persisted telemetry does not contain the "
                    "ENGINE_SHUTDOWN phase. Post-flight results "
                    "therefore describe the recorded portion of "
                    "the mission rather than a complete default "
                    "mission profile."
                ),
        })

    incomplete_fields = []

    for field, info in completeness.items():
        coverage = info[
            "coverage_percent"
        ]

        if coverage < 100.0:
            incomplete_fields.append({
                "field":
                    field,
                "coverage_percent":
                    coverage,
            })

    if incomplete_fields:
        observations.append({
            "level":
                "INFO",
            "code":
                "INCOMPLETE_PARAMETERS",
            "message":
                (
                    "Some telemetry parameters are unavailable "
                    "for part or all of this historical mission. "
                    "Missing values remain null and are not "
                    "replaced with synthetic zero values."
                ),
            "fields":
                incomplete_fields,
        })

    observations.append({
        "level":
            "INFO",
        "code":
            "DESCRIPTIVE_ANALYSIS_ONLY",
        "message":
            (
                "This report contains descriptive engineering "
                "statistics. Values are not compared against "
                "official DRDO/VRDE certified operating limits."
            ),
    })

    observations.append({
        "level":
            "INFO",
        "code":
            "NO_MODEL_REPROCESSING",
        "message":
            (
                "Historical telemetry was not rerun through "
                "current diagnostic, anomaly, degradation or "
                "RUL models."
            ),
    })

    return observations


def analyze_mission(
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
                "success": False,
                "found": False,
                "mission_id":
                    str(mission_uuid),
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

        observed_duration = None

        if (
            first_timestamp is not None
            and last_timestamp is not None
        ):
            observed_duration = (
                last_timestamp
                - first_timestamp
            ).total_seconds()

        rpm = _series(
            samples,
            _rpm,
        )

        throttle = _series(
            samples,
            _throttle,
        )

        load = _series(
            samples,
            _load,
        )

        power = _series(
            samples,
            _power,
        )

        torque = _series(
            samples,
            _torque,
        )

        oil_pressure = _series(
            samples,
            _oil_pressure,
        )

        oil_temperature = _series(
            samples,
            _oil_temperature,
        )

        vibration = _series(
            samples,
            _vibration,
        )

        battery = _series(
            samples,
            _battery_voltage,
        )

        alternator = _series(
            samples,
            _alternator_voltage,
        )

        altitude = _series(
            samples,
            _altitude_m,
        )

        ambient_temp = _series(
            samples,
            _ambient_temperature,
        )

        ambient_pressure = _series(
            samples,
            _ambient_pressure,
        )

        completeness = (
            _data_completeness(
                samples
            )
        )

        phases = (
            _phase_analysis(
                samples
            )
        )

        cylinders = (
            _cylinder_analysis(
                samples
            )
        )

        events = (
            _significant_events(
                samples
            )
        )

        observations = (
            _observations(
                samples,
                phases=phases,
                completeness=
                    completeness,
            )
        )

        return {
            "success":
                True,

            "found":
                True,

            "service":
                "post_flight_analysis",

            "version":
                POST_FLIGHT_ANALYSIS_VERSION,

            "analysis_mode":
                "DESCRIPTIVE_HISTORICAL",

            "model_reprocessing":
                False,

            "official_engine_limits":
                False,

            "mission": {
                "id":
                    str(mission.id),

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

                "recorded_duration_sec":
                    mission.duration_sec,

                "telemetry_first_timestamp":
                    _iso(
                        first_timestamp
                    ),

                "telemetry_last_timestamp":
                    _iso(
                        last_timestamp
                    ),

                "observed_telemetry_duration_sec":
                    observed_duration,

                "telemetry_samples":
                    len(samples),
            },

            "data_completeness":
                completeness,

            "phase_analysis":
                phases,

            "engine_performance": {
                "rpm":
                    _stats(rpm),

                "throttle_percent":
                    _stats(throttle),

                "load_percent":
                    _stats(load),

                "power_kw":
                    _stats(power),

                "torque_nm":
                    _stats(torque),

                "peak_rpm_event":
                    _peak_event(
                        samples,
                        _rpm,
                        mode="MAX",
                    ),
            },

            "thermal_analysis":
                cylinders,

            "lubrication": {
                "oil_pressure_kpa":
                    _stats(
                        oil_pressure
                    ),

                "oil_temperature_c":
                    _stats(
                        oil_temperature
                    ),

                "minimum_pressure_event":
                    _peak_event(
                        samples,
                        _oil_pressure,
                        mode="MIN",
                    ),

                "maximum_temperature_event":
                    _peak_event(
                        samples,
                        _oil_temperature,
                        mode="MAX",
                    ),
            },

            "vibration": {
                "overall_g":
                    _stats(
                        vibration
                    ),

                "peak_event":
                    _peak_event(
                        samples,
                        _vibration,
                        mode="MAX",
                    ),
            },

            "electrical": {
                "battery_voltage_v":
                    _stats(
                        battery
                    ),

                "alternator_voltage_v":
                    _stats(
                        alternator
                    ),
            },

            "environment": {
                "altitude_m":
                    _stats(
                        altitude
                    ),

                "ambient_temperature_c":
                    _stats(
                        ambient_temp
                    ),

                "ambient_pressure_kpa":
                    _stats(
                        ambient_pressure
                    ),

                "peak_altitude_event":
                    _peak_event(
                        samples,
                        _altitude_m,
                        mode="MAX",
                    ),
            },

            "significant_events":
                events,

            "engineering_observations":
                observations,
        }


def get_post_flight_analysis_status(
) -> dict[str, Any]:
    return {
        "service":
            "post_flight_analysis",
        "version":
            POST_FLIGHT_ANALYSIS_VERSION,
        "status":
            "READY",
        "read_only":
            True,
        "analysis_mode":
            "DESCRIPTIVE_HISTORICAL",
        "model_reprocessing":
            False,
        "official_engine_limits":
            False,
    }
