from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models import (
    DegradationHistory,
    Engine,
    FaultEvent,
    HealthSnapshot,
    MaintenanceAdvisory,
    Mission,
    RULHistory,
    TelemetrySample,
)


REPOSITORY_VERSION = "1.1.0"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _value(
    mapping: dict[str, Any] | None,
    key: str,
) -> Any:

    if not isinstance(mapping, dict):
        return None

    return mapping.get(key)


def _nested_value(
    mapping: dict[str, Any] | None,
    section: str,
    key: str,
) -> Any:

    if not isinstance(mapping, dict):
        return None

    nested = mapping.get(section)

    if not isinstance(nested, dict):
        return None

    return nested.get(key)


def _first_present(
    mapping: dict[str, Any] | None,
    *keys: str,
) -> Any:

    if not isinstance(mapping, dict):
        return None

    for key in keys:
        if key in mapping:
            return mapping[key]

    return None


def _nested_first_present(
    mapping: dict[str, Any] | None,
    section: str,
    *keys: str,
) -> Any:

    if not isinstance(mapping, dict):
        return None

    nested = mapping.get(section)

    if not isinstance(nested, dict):
        return None

    return _first_present(
        nested,
        *keys,
    )


def _as_datetime(value: Any) -> datetime:

    if isinstance(value, datetime):

        if value.tzinfo is None:
            return value.replace(
                tzinfo=timezone.utc
            )

        return value

    if isinstance(value, str):

        candidate = value.strip()

        if candidate:

            try:

                if candidate.endswith("Z"):
                    candidate = (
                        candidate[:-1]
                        + "+00:00"
                    )

                parsed = datetime.fromisoformat(
                    candidate
                )

                if parsed.tzinfo is None:
                    parsed = parsed.replace(
                        tzinfo=timezone.utc
                    )

                return parsed

            except ValueError:
                pass

    if isinstance(value, (int, float)):

        try:

            return datetime.fromtimestamp(
                float(value),
                tz=timezone.utc,
            )

        except (
            ValueError,
            OSError,
            OverflowError,
        ):
            pass

    return utc_now()


def get_engine_by_code(
    db: Session,
    engine_code: str,
) -> Engine | None:

    statement = select(
        Engine
    ).where(
        Engine.engine_code
        == engine_code
    )

    return db.scalar(
        statement
    )


def get_or_create_engine(
    db: Session,
    *,
    engine_code: str,
    engine_name: str,
    engine_type: str = "AERO_PISTON",
    rated_power_hp: float | None = None,
    description: str | None = None,
) -> Engine:

    engine = get_engine_by_code(
        db,
        engine_code,
    )

    if engine is not None:
        return engine

    engine = Engine(
        engine_code=engine_code,
        engine_name=engine_name,
        engine_type=engine_type,
        rated_power_hp=rated_power_hp,
        description=description,
    )

    db.add(
        engine
    )

    db.flush()

    return engine


def get_mission_by_code(
    db: Session,
    mission_code: str,
) -> Mission | None:

    statement = select(
        Mission
    ).where(
        Mission.mission_code
        == mission_code
    )

    return db.scalar(
        statement
    )


def create_mission(
    db: Session,
    *,
    engine_id: UUID,
    mission_code: str,
    mission_name: str | None = None,
    source_type: str = "SIMULATION",
    status: str = "CREATED",
    profile_name: str | None = None,
    started_at: datetime | None = None,
    notes: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> Mission:

    existing = get_mission_by_code(
        db,
        mission_code,
    )

    if existing is not None:
        return existing

    mission = Mission(
        engine_id=engine_id,
        mission_code=mission_code,
        mission_name=mission_name,
        source_type=source_type,
        status=status,
        profile_name=profile_name,
        started_at=started_at,
        notes=notes,
        metadata_json=metadata_json,
    )

    db.add(
        mission
    )

    db.flush()

    return mission


def update_mission_status(
    db: Session,
    mission: Mission,
    *,
    status: str,
    ended_at: datetime | None = None,
    duration_sec: float | None = None,
) -> Mission:

    mission.status = status

    if ended_at is not None:
        mission.ended_at = ended_at

    if duration_sec is not None:
        mission.duration_sec = duration_sec

    db.flush()

    return mission


def telemetry_sample_from_canonical(
    *,
    mission_id: UUID,
    telemetry: dict[str, Any],
) -> TelemetrySample:

    meta = telemetry.get(
        "meta"
    )

    if not isinstance(
        meta,
        dict,
    ):
        meta = {}

    timestamp_value = _first_present(
        meta,
        "timestamp",
        "timestamp_utc",
    )

    if timestamp_value is None:

        timestamp_value = _first_present(
            telemetry,
            "timestamp",
            "timestamp_utc",
        )

    sequence = _first_present(
        meta,
        "sequence",
        "seq",
    )

    source_type = _first_present(
        meta,
        "source",
        "source_type",
    )

    if source_type is None:
        source_type = "unknown"

    mission_phase = _first_present(
        meta,
        "mission_phase",
        "phase",
    )

    if mission_phase is None:

        mission = telemetry.get(
            "mission"
        )

        if isinstance(
            mission,
            dict,
        ):

            mission_phase = _first_present(
                mission,
                "phase",
                "mission_phase",
            )

    fuel_flow_lph = _nested_first_present(
        telemetry,
        "fuel",
        "flow_lph",
        "fuel_flow_lph",
    )

    return TelemetrySample(

        mission_id=mission_id,

        sequence=sequence,

        timestamp=_as_datetime(
            timestamp_value
        ),

        source_type=str(
            source_type
        ),

        mission_phase=mission_phase,

        rpm=_nested_first_present(
            telemetry,
            "engine",
            "rpm",
        ),

        throttle_pct=_nested_first_present(
            telemetry,
            "engine",
            "throttle_percent",
            "throttle_pct",
            "throttle",
        ),

        engine_load_pct=_nested_first_present(
            telemetry,
            "engine",
            "load_percent",
            "load_pct",
            "engine_load_pct",
            "load",
        ),

        altitude_ft=_nested_first_present(
            telemetry,
            "environment",
            "altitude_ft",
            "altitude",
        ),

        ambient_temperature_c=
            _nested_first_present(
                telemetry,
                "environment",
                "ambient_temperature_c",
                "temperature_c",
                "ambient_temp_c",
            ),

        ambient_pressure_kpa=
            _nested_first_present(
                telemetry,
                "environment",
                "ambient_pressure_kpa",
                "pressure_kpa",
            ),

        cht_1_c=_nested_first_present(
            telemetry,
            "cht",
            "cylinder1_c",
            "cylinder_1_c",
            "cyl_1_c",
            "c1",
        ),

        cht_2_c=_nested_first_present(
            telemetry,
            "cht",
            "cylinder2_c",
            "cylinder_2_c",
            "cyl_2_c",
            "c2",
        ),

        cht_3_c=_nested_first_present(
            telemetry,
            "cht",
            "cylinder3_c",
            "cylinder_3_c",
            "cyl_3_c",
            "c3",
        ),

        cht_4_c=_nested_first_present(
            telemetry,
            "cht",
            "cylinder4_c",
            "cylinder_4_c",
            "cyl_4_c",
            "c4",
        ),

        egt_1_c=_nested_first_present(
            telemetry,
            "egt",
            "cylinder1_c",
            "cylinder_1_c",
            "cyl_1_c",
            "c1",
        ),

        egt_2_c=_nested_first_present(
            telemetry,
            "egt",
            "cylinder2_c",
            "cylinder_2_c",
            "cyl_2_c",
            "c2",
        ),

        egt_3_c=_nested_first_present(
            telemetry,
            "egt",
            "cylinder3_c",
            "cylinder_3_c",
            "cyl_3_c",
            "c3",
        ),

        egt_4_c=_nested_first_present(
            telemetry,
            "egt",
            "cylinder4_c",
            "cylinder_4_c",
            "cyl_4_c",
            "c4",
        ),

        oil_pressure_kpa=
            _nested_first_present(
                telemetry,
                "oil",
                "pressure_kpa",
                "oil_pressure_kpa",
            ),

        oil_temperature_c=
            _nested_first_present(
                telemetry,
                "oil",
                "temperature_c",
                "oil_temperature_c",
                "temp_c",
            ),

        fuel_flow_lph=
            fuel_flow_lph,

        fuel_pressure_kpa=
            _nested_first_present(
                telemetry,
                "fuel",
                "pressure_kpa",
                "fuel_pressure_kpa",
            ),

        injection_timing_deg=
            _nested_first_present(
                telemetry,
                "fuel",
                "injection_timing_deg",
                "injectionTimingDeg",
            ),

        vibration_overall_g=
            _nested_first_present(
                telemetry,
                "vibration",
                "overall_g",
                "overallG",
            ),

        battery_voltage_v=
            _nested_first_present(
                telemetry,
                "electrical",
                "battery_voltage_v",
                "battery_v",
            ),

        alternator_voltage_v=
            _nested_first_present(
                telemetry,
                "electrical",
                "alternator_voltage_v",
                "alternator_v",
            ),

        alternator_current_a=
            _nested_first_present(
                telemetry,
                "electrical",
                "alternator_current_a",
                "alternator_current",
            ),

        raw_payload=telemetry,
    )


def add_telemetry_sample(
    db: Session,
    *,
    mission_id: UUID,
    telemetry: dict[str, Any],
) -> TelemetrySample:

    sample = telemetry_sample_from_canonical(
        mission_id=mission_id,
        telemetry=telemetry,
    )

    db.add(
        sample
    )

    return sample


def add_telemetry_batch(
    db: Session,
    *,
    mission_id: UUID,
    telemetry_frames: Iterable[
        dict[str, Any]
    ],
) -> int:

    samples = [

        telemetry_sample_from_canonical(
            mission_id=mission_id,
            telemetry=frame,
        )

        for frame in telemetry_frames
    ]

    if not samples:
        return 0

    db.add_all(
        samples
    )

    return len(
        samples
    )


def add_fault_event(
    db: Session,
    *,
    mission_id: UUID,
    fault_type: str,
    timestamp: datetime | None = None,
    source: str = "DIAGNOSTIC",
    severity: float | None = None,
    confidence: float | None = None,
    active: bool = True,
    description: str | None = None,
    evidence_json: dict[str, Any] | None = None,
    cleared_at: datetime | None = None,
) -> FaultEvent:

    event = FaultEvent(
        mission_id=mission_id,
        timestamp=timestamp or utc_now(),
        fault_type=fault_type,
        source=source,
        severity=severity,
        confidence=confidence,
        active=active,
        description=description,
        evidence_json=evidence_json,
        cleared_at=cleared_at,
    )

    db.add(
        event
    )

    return event


def add_health_snapshot(
    db: Session,
    *,
    mission_id: UUID,
    timestamp: datetime | None = None,
    overall_health_index: float | None = None,
    health_status: str | None = None,
    anomaly_score: float | None = None,
    readiness_status: str | None = None,
    model_version: str | None = None,
    details_json: dict[str, Any] | None = None,
) -> HealthSnapshot:

    snapshot = HealthSnapshot(
        mission_id=mission_id,
        timestamp=timestamp or utc_now(),
        overall_health_index=overall_health_index,
        health_status=health_status,
        anomaly_score=anomaly_score,
        readiness_status=readiness_status,
        model_version=model_version,
        details_json=details_json,
    )

    db.add(
        snapshot
    )

    return snapshot


def add_degradation_record(
    db: Session,
    *,
    mission_id: UUID,
    subsystem: str,
    timestamp: datetime | None = None,
    degradation_index: float | None = None,
    trend: float | None = None,
    status: str | None = None,
    model_version: str | None = None,
    details_json: dict[str, Any] | None = None,
) -> DegradationHistory:

    record = DegradationHistory(
        mission_id=mission_id,
        timestamp=timestamp or utc_now(),
        subsystem=subsystem,
        degradation_index=degradation_index,
        trend=trend,
        status=status,
        model_version=model_version,
        details_json=details_json,
    )

    db.add(
        record
    )

    return record


def add_rul_record(
    db: Session,
    *,
    mission_id: UUID,
    timestamp: datetime | None = None,
    subsystem: str = "ENGINE",
    rul_hours: float | None = None,
    confidence: float | None = None,
    degradation_index: float | None = None,
    model_version: str | None = None,
    details_json: dict[str, Any] | None = None,
) -> RULHistory:

    record = RULHistory(
        mission_id=mission_id,
        timestamp=timestamp or utc_now(),
        subsystem=subsystem,
        rul_hours=rul_hours,
        confidence=confidence,
        degradation_index=degradation_index,
        model_version=model_version,
        details_json=details_json,
    )

    db.add(
        record
    )

    return record


def add_maintenance_advisory(
    db: Session,
    *,
    mission_id: UUID,
    recommendation: str,
    timestamp: datetime | None = None,
    subsystem: str | None = None,
    priority: str | None = None,
    reason: str | None = None,
    status: str = "OPEN",
    model_version: str | None = None,
    details_json: dict[str, Any] | None = None,
) -> MaintenanceAdvisory:

    advisory = MaintenanceAdvisory(
        mission_id=mission_id,
        timestamp=timestamp or utc_now(),
        subsystem=subsystem,
        priority=priority,
        recommendation=recommendation,
        reason=reason,
        status=status,
        model_version=model_version,
        details_json=details_json,
    )

    db.add(
        advisory
    )

    return advisory


def get_recent_telemetry(
    db: Session,
    *,
    mission_id: UUID,
    limit: int = 100,
) -> list[TelemetrySample]:

    safe_limit = max(
        1,
        min(
            int(limit),
            10_000,
        ),
    )

    statement = (
        select(
            TelemetrySample
        )
        .where(
            TelemetrySample.mission_id
            == mission_id
        )
        .order_by(
            TelemetrySample.timestamp.desc(),
            TelemetrySample.id.desc(),
        )
        .limit(
            safe_limit
        )
    )

    return list(
        db.scalars(
            statement
        ).all()
    )


def count_mission_telemetry(
    db: Session,
    *,
    mission_id: UUID,
) -> int:

    from sqlalchemy import func

    statement = (
        select(
            func.count(
                TelemetrySample.id
            )
        )
        .where(
            TelemetrySample.mission_id
            == mission_id
        )
    )

    result = db.scalar(
        statement
    )

    return int(
        result or 0
    )
