from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.database import Base


DATABASE_MODELS_VERSION = "1.0.0"


def utc_now() -> datetime:

    return datetime.now(timezone.utc)
class Engine(Base):
 __tablename__ = "engines"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    engine_code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    engine_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    engine_type: Mapped[str] = mapped_column(
        String(100),
        default="AERO_PISTON",
        nullable=False,
    )

    rated_power_hp: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    missions: Mapped[list["Mission"]] = relationship(
        back_populates="engine",
        cascade="all, delete-orphan",
    )

class Mission(Base):

    __tablename__ = "missions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    engine_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("engines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    mission_code: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        nullable=False,
        index=True,
    )

    mission_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="SIMULATION",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="CREATED",
    )

    profile_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    duration_sec: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    engine: Mapped["Engine"] = relationship(
        back_populates="missions",
    )

    telemetry_samples: Mapped[list["TelemetrySample"]] = relationship(
        back_populates="mission",
        cascade="all, delete-orphan",
    )

    fault_events: Mapped[list["FaultEvent"]] = relationship(
        back_populates="mission",
        cascade="all, delete-orphan",
    )

    health_snapshots: Mapped[list["HealthSnapshot"]] = relationship(
        back_populates="mission",
        cascade="all, delete-orphan",
    )

    degradation_history: Mapped[list["DegradationHistory"]] = relationship(
        back_populates="mission",
        cascade="all, delete-orphan",
    )

    rul_history: Mapped[list["RULHistory"]] = relationship(
        back_populates="mission",
        cascade="all, delete-orphan",
    )

    maintenance_advisories: Mapped[list["MaintenanceAdvisory"]] = relationship(
        back_populates="mission",
        cascade="all, delete-orphan",
    )

class TelemetrySample(Base):
    __tablename__ = "telemetry_samples"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    mission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=False,
    )

    sequence: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    mission_phase: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    rpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    throttle_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    engine_load_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    altitude_ft: Mapped[float | None] = mapped_column(Float, nullable=True)

    ambient_temperature_c: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    ambient_pressure_kpa: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    cht_1_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    cht_2_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    cht_3_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    cht_4_c: Mapped[float | None] = mapped_column(Float, nullable=True)

    egt_1_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    egt_2_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    egt_3_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    egt_4_c: Mapped[float | None] = mapped_column(Float, nullable=True)

    oil_pressure_kpa: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    oil_temperature_c: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    fuel_flow_lph: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    fuel_pressure_kpa: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    injection_timing_deg: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    vibration_overall_g: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    battery_voltage_v: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    alternator_voltage_v: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    alternator_current_a: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    inserted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    mission: Mapped["Mission"] = relationship(
        back_populates="telemetry_samples",
    )

    __table_args__ = (
        Index(
            "ix_telemetry_mission_timestamp",
            "mission_id",
            "timestamp",
        ),
        Index(
            "ix_telemetry_mission_sequence",
            "mission_id",
            "sequence",
        ),
        Index(
            "ix_telemetry_phase_timestamp",
            "mission_phase",
            "timestamp",
        ),
    )

class FaultEvent(Base):

    __tablename__ = "fault_events"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    mission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=False,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    fault_type: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="DIAGNOSTIC",
    )

    severity: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    evidence_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    cleared_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    mission: Mapped["Mission"] = relationship(
        back_populates="fault_events",
    )

    __table_args__ = (
        Index(
            "ix_fault_mission_timestamp",
            "mission_id",
            "timestamp",
        ),
    )

class HealthSnapshot(Base):

    __tablename__ = "health_snapshots"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    mission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=False,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    overall_health_index: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    health_status: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    anomaly_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    readiness_status: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    model_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    details_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    mission: Mapped["Mission"] = relationship(
        back_populates="health_snapshots",
    )

    __table_args__ = (
        Index(
            "ix_health_mission_timestamp",
            "mission_id",
            "timestamp",
        ),
    )

class DegradationHistory(Base):

    __tablename__ = "degradation_history"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    mission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=False,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    subsystem: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    degradation_index: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    trend: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    status: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    model_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    details_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    mission: Mapped["Mission"] = relationship(
        back_populates="degradation_history",
    )

    __table_args__ = (
        Index(
            "ix_degradation_mission_timestamp",
            "mission_id",
            "timestamp",
        ),
        Index(
            "ix_degradation_subsystem_timestamp",
            "subsystem",
            "timestamp",
        ),
    )

class RULHistory(Base):

    __tablename__ = "rul_history"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    mission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=False,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    subsystem: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="ENGINE",
    )

    rul_hours: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    degradation_index: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    model_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    details_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    mission: Mapped["Mission"] = relationship(
        back_populates="rul_history",
    )

    __table_args__ = (
        Index(
            "ix_rul_mission_timestamp",
            "mission_id",
            "timestamp",
        ),
    )

class MaintenanceAdvisory(Base):

    __tablename__ = "maintenance_advisories"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    mission_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=False,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    subsystem: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    priority: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    recommendation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="OPEN",
        nullable=False,
    )

    model_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    details_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    mission: Mapped["Mission"] = relationship(
        back_populates="maintenance_advisories",
    )

    __table_args__ = (
        Index(
            "ix_maintenance_mission_timestamp",
            "mission_id",
            "timestamp",
        ),
    )

class ModelVersion(Base):

    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    model_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    model_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    version: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ux_model_name_version",
            "model_name",
            "version",
            unique=True,
        ),
    )
