from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List, Literal, Dict, Any

from pydantic import BaseModel, Field, ConfigDict, AliasChoices


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TelemetryMeta(BaseModel):

    model_config = ConfigDict(
        extra="allow"
    )

    timestamp: datetime = Field(
        default_factory=utc_now
    )

    source: Literal[
        "simulation",
        "can_fadec",
        "replay",
        "test_rig",
        "unknown"
    ] = "unknown"

    sequence: Optional[int] = None

    transport: Optional[str] = None

    received_at: Optional[datetime] = None


class EngineState(BaseModel):

    rpm: float = Field(
        default=0,
        ge=0
    )

    throttle_percent: float = Field(
        default=0,
        ge=0,
        le=100
    )

    load_percent: float = Field(
        default=0,
        ge=0,
        le=100
    )

    power_kw: Optional[float] = Field(
        default=None,
        ge=0
    )

    torque_nm: Optional[float] = None


class CylinderTemperatures(BaseModel):

    cylinder1_c: Optional[float] = None

    cylinder2_c: Optional[float] = None

    cylinder3_c: Optional[float] = None

    cylinder4_c: Optional[float] = None


class OilState(BaseModel):

    pressure_kpa: Optional[float] = None

    temperature_c: Optional[float] = None


class FuelState(BaseModel):

    flow_kg_per_second: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices(
            "flow_kg_per_second",
            "flow_kg_s",
        ),
    )

    pressure_kpa: Optional[float] = None

    injection_timing_deg: Optional[float] = None


class VibrationState(BaseModel):

    overall_g: Optional[float] = None

    x_g: Optional[float] = None

    y_g: Optional[float] = None

    z_g: Optional[float] = None


class ElectricalState(BaseModel):

    battery_voltage_v: Optional[float] = None

    battery_current_a: Optional[float] = None

    alternator_voltage_v: Optional[float] = None

    alternator_current_a: Optional[float] = None


class EnvironmentState(BaseModel):

    altitude_m: float = 0

    altitude_ft: Optional[float] = None

    ambient_temperature_c: float = 15

    ambient_pressure_kpa: Optional[float] = None

    air_density_kg_m3: Optional[float] = None


class TelemetryFrame(BaseModel):

    model_config = ConfigDict(
        extra="allow"
    )

    meta: TelemetryMeta = Field(
        default_factory=TelemetryMeta
    )

    engine: EngineState = Field(
        default_factory=EngineState
    )

    cht: CylinderTemperatures = Field(
        default_factory=CylinderTemperatures
    )

    egt: CylinderTemperatures = Field(
        default_factory=CylinderTemperatures
    )

    oil: OilState = Field(
        default_factory=OilState
    )

    fuel: FuelState = Field(
        default_factory=FuelState
    )

    vibration: VibrationState = Field(
        default_factory=VibrationState
    )

    electrical: ElectricalState = Field(
        default_factory=ElectricalState
    )

    environment: EnvironmentState = Field(
        default_factory=EnvironmentState
    )


class TelemetryResponse(BaseModel):

    accepted: bool

    message: str

    telemetry: Optional[
        TelemetryFrame
    ] = None


class MissionConfiguration(BaseModel):

    mission_id: Optional[str] = None

    profile: Literal[
        "IDLE",
        "TAKEOFF",
        "CLIMB",
        "CRUISE",
        "ENDURANCE",
        "HIGH_ALTITUDE",
        "HOT_WEATHER",
        "RAPID_THROTTLE",
        "DESCENT",
        "LANDING",
        "TEST"
    ] = "ENDURANCE"

    duration_hours: float = Field(
        default=4,
        gt=0
    )

    altitude_ft: float = Field(
        default=10000,
        ge=0
    )

    ambient_temperature_c: float = 25

    expected_load_percent: float = Field(
        default=65,
        ge=0,
        le=100
    )


class FaultEvidence(BaseModel):

    id: str

    name: str

    subsystem: str

    score: float = Field(
        ge=0,
        le=1
    )

    probability: float = Field(
        ge=0,
        le=100
    )

    severity: str

    active: bool

    evidence: List[str] = Field(
        default_factory=list
    )


class AnomalyResult(BaseModel):

    anomaly_score: float = Field(
        ge=0,
        le=100
    )

    status: str

    component_scores: Dict[
        str,
        float
    ] = Field(
        default_factory=dict
    )


class RULResult(BaseModel):

    overall_rul_hours: Optional[float] = None

    confidence: float = Field(
        default=0,
        ge=0,
        le=100
    )

    status: str = "UNKNOWN"

    critical_subsystem: Optional[str] = None

    validated_rul: bool = False


class MaintenanceAdvisory(BaseModel):

    priority: str

    maintenance_risk: float = Field(
        ge=0,
        le=100
    )

    affected_subsystem: Optional[str] = None

    affected_component: Optional[str] = None

    probable_fault: Optional[str] = None

    inspection: Optional[str] = None

    recommended_action: Optional[str] = None

    service_window: Optional[str] = None

    mission_restriction: Optional[str] = None

    advisory: Optional[str] = None

    prototype_advisory: bool = True


class MissionReadinessResult(BaseModel):

    readiness: Literal[
        "GO",
        "CAUTION",
        "NO-GO",
        "UNKNOWN"
    ] = "UNKNOWN"

    mission_risk: float = Field(
        default=0,
        ge=0,
        le=100
    )

    propulsion_health_risk: float = Field(
        default=0,
        ge=0,
        le=100
    )

    environmental_risk: float = Field(
        default=0,
        ge=0,
        le=100
    )

    reasons: List[str] = Field(
        default_factory=list
    )

    recommendation: Optional[str] = None

    flight_authorization: bool = False


class ServiceStatus(BaseModel):

    database: str = "NOT_CONFIGURED"

    ai: str = "NOT_CONFIGURED"

    telemetry: str = "READY"

    can: str = "NOT_CONNECTED"

    websocket: str = "READY"


class BackendHealthResponse(BaseModel):

    status: str = "ok"

    backend: str = "ONLINE"

    version: str

    database: str = "NOT_CONFIGURED"

    ai: str = "NOT_CONFIGURED"

    telemetry: str = "READY"

    can: str = "NOT_CONNECTED"

    services: ServiceStatus

    timestamp: datetime = Field(
        default_factory=utc_now
    )


class APIMessage(BaseModel):

    success: bool = True

    message: str

    data: Optional[
        Dict[str, Any]
    ] = None
