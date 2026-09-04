from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any, Dict, List, Optional


READINESS_VERSION = "1.0.0"


MIN_SENSOR_COVERAGE = 0.30
GOOD_SENSOR_COVERAGE = 0.70

MIN_READINESS_CONFIDENCE = 0.30

CAUTION_DEGRADATION_SCORE = 0.35
NOT_READY_DEGRADATION_SCORE = 0.75

CRITICAL_SAMPLE_PROJECTION = 1.0
LIMITED_SAMPLE_PROJECTION = 5.0


class ReadinessState(str, Enum):
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    READY = "READY"
    READY_WITH_CAUTION = "READY_WITH_CAUTION"
    NOT_READY = "NOT_READY"


class ReadinessSeverity(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ReadinessConfidenceLevel(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class ReadinessFactor:
    code: str
    source: str
    severity: ReadinessSeverity
    description: str
    blocking: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "source": self.source,
            "severity": self.severity.value,
            "description": self.description,
            "blocking": self.blocking,
        }


@dataclass
class MissionReadinessReport:
    timestamp: datetime
    version: str

    state: ReadinessState
    severity: ReadinessSeverity

    confidence: float
    confidence_level: ReadinessConfidenceLevel

    readiness_score: Optional[float]
    readiness_score_percent: Optional[float]

    factors: List[ReadinessFactor]
    factor_count: int
    blocking_factor_count: int

    sensor_coverage: Optional[float]

    maintenance_state: Optional[str]
    rul_state: Optional[str]
    degradation_state: Optional[str]
    fault_state: Optional[str]

    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,

            "state": self.state.value,
            "severity": self.severity.value,

            "confidence": self.confidence,
            "confidence_percent": self.confidence * 100.0,
            "confidence_level": self.confidence_level.value,

            "readiness_score": self.readiness_score,
            "readiness_score_percent": self.readiness_score_percent,

            "factors": [
                factor.to_dict()
                for factor in self.factors
            ],

            "factor_count": self.factor_count,
            "blocking_factor_count": self.blocking_factor_count,

            "sensor_coverage": self.sensor_coverage,
            "sensor_coverage_percent": (
                self.sensor_coverage * 100.0
                if self.sensor_coverage is not None
                else None
            ),

            "maintenance_state": self.maintenance_state,
            "rul_state": self.rul_state,
            "degradation_state": self.degradation_state,
            "fault_state": self.fault_state,

            "warnings": list(self.warnings),
        }


_latest_report: Optional[MissionReadinessReport] = None

_assessment_count = 0
_failed_assessment_count = 0


def _utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


def _normalize_timestamp(
    value: Optional[datetime],
) -> datetime:

    if value is None:
        return _utc_now()

    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc
        )

    return value.astimezone(
        timezone.utc
    )


def _numeric(
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
        number = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return None

    if not isfinite(
        number
    ):
        return None

    return number


def _clamp01(
    value: Any,
) -> float:

    number = _numeric(
        value
    )

    if number is None:
        return 0.0

    return max(
        0.0,
        min(
            1.0,
            number,
        ),
    )


def _optional_clamp01(
    value: Any,
) -> Optional[float]:

    number = _numeric(
        value
    )

    if number is None:
        return None

    return max(
        0.0,
        min(
            1.0,
            number,
        ),
    )


def _confidence_level(
    value: float,
) -> ReadinessConfidenceLevel:

    if value <= 0.0:
        return (
            ReadinessConfidenceLevel.NONE
        )

    if value < 0.50:
        return (
            ReadinessConfidenceLevel.LOW
        )

    if value < 0.75:
        return (
            ReadinessConfidenceLevel.MEDIUM
        )

    return (
        ReadinessConfidenceLevel.HIGH
    )


def _severity_rank(
    severity: ReadinessSeverity,
) -> int:

    mapping = {
        ReadinessSeverity.NONE: 0,
        ReadinessSeverity.LOW: 1,
        ReadinessSeverity.MEDIUM: 2,
        ReadinessSeverity.HIGH: 3,
        ReadinessSeverity.CRITICAL: 4,
    }

    return mapping[
        severity
    ]


def _highest_severity(
    factors: List[ReadinessFactor],
) -> ReadinessSeverity:

    if not factors:
        return (
            ReadinessSeverity.NONE
        )

    return max(
        (
            factor.severity
            for factor in factors
        ),
        key=_severity_rank,
    )


def _sensor_coverage(
    report: Optional[Dict[str, Any]],
) -> Optional[float]:

    if not isinstance(
        report,
        dict,
    ):
        return None

    return _optional_clamp01(
        report.get(
            "coverage"
        )
    )


def _sensor_confidence(
    report: Optional[Dict[str, Any]],
) -> float:

    if not isinstance(
        report,
        dict,
    ):
        return 0.0

    return _clamp01(
        report.get(
            "overall_quality"
        )
    )


def _sensor_factors(
    report: Optional[Dict[str, Any]],
) -> List[ReadinessFactor]:

    factors: List[
        ReadinessFactor
    ] = []

    coverage = _sensor_coverage(
        report
    )

    if coverage is None:

        factors.append(
            ReadinessFactor(
                code=
                    "SENSOR_COVERAGE_UNAVAILABLE",

                source=
                    "sensor_validation",

                severity=
                    ReadinessSeverity.MEDIUM,

                description=(
                    "Sensor coverage information is unavailable, "
                    "so mission readiness cannot be assessed confidently."
                ),

                blocking=
                    False,
            )
        )

        return factors

    if coverage < MIN_SENSOR_COVERAGE:

        factors.append(
            ReadinessFactor(
                code=
                    "SENSOR_COVERAGE_INSUFFICIENT",

                source=
                    "sensor_validation",

                severity=
                    ReadinessSeverity.MEDIUM,

                description=(
                    "Available sensor coverage is too limited "
                    "for a confident mission-readiness assessment."
                ),

                blocking=
                    False,
            )
        )

    elif coverage < GOOD_SENSOR_COVERAGE:

        factors.append(
            ReadinessFactor(
                code=
                    "SENSOR_COVERAGE_LIMITED",

                source=
                    "sensor_validation",

                severity=
                    ReadinessSeverity.LOW,

                description=(
                    "Mission-readiness confidence is reduced "
                    "because telemetry coverage is limited."
                ),

                blocking=
                    False,
            )
        )

    return factors


def _fault_confidence(
    report: Optional[Dict[str, Any]],
) -> float:

    if not isinstance(
        report,
        dict,
    ):
        return 0.0

    return _clamp01(
        report.get(
            "overall_confidence"
        )
    )


def _fault_factors(
    report: Optional[Dict[str, Any]],
) -> List[ReadinessFactor]:

    if not isinstance(
        report,
        dict,
    ):
        return []

    factors: List[
        ReadinessFactor
    ] = []

    faults = report.get(
        "active_faults"
    )

    if not isinstance(
        faults,
        list,
    ):
        return factors

    for fault in faults:

        if not isinstance(
            fault,
            dict,
        ):
            continue

        state = str(
            fault.get(
                "state"
            )
            or ""
        ).upper()

        if state not in {
            "SUSPECTED",
            "DETECTED",
        }:
            continue

        severity_text = str(
            fault.get(
                "severity"
            )
            or ""
        ).upper()

        code = str(
            fault.get(
                "code"
            )
            or fault.get(
                "fault_code"
            )
            or "FAULT"
        )

        if severity_text == "CRITICAL":

            severity = (
                ReadinessSeverity.CRITICAL
            )

            blocking = True

        elif severity_text == "HIGH":

            severity = (
                ReadinessSeverity.HIGH
            )

            blocking = (
                state == "DETECTED"
            )

        elif severity_text == "MEDIUM":

            severity = (
                ReadinessSeverity.MEDIUM
            )

            blocking = False

        else:

            severity = (
                ReadinessSeverity.LOW
            )

            blocking = False

        factors.append(
            ReadinessFactor(
                code=
                    f"FAULT_{code}",

                source=
                    "fault_detection",

                severity=
                    severity,

                description=(
                    f"Fault Detection reported "
                    f"{state} evidence for {code}."
                ),

                blocking=
                    blocking,
            )
        )

    return factors


def _degradation_confidence(
    report: Optional[Dict[str, Any]],
) -> float:

    if not isinstance(
        report,
        dict,
    ):
        return 0.0

    return _clamp01(
        report.get(
            "overall_confidence"
        )
    )


def _degradation_factors(
    report: Optional[Dict[str, Any]],
) -> List[ReadinessFactor]:

    if not isinstance(
        report,
        dict,
    ):
        return []

    factors: List[
        ReadinessFactor
    ] = []

    state = str(
        report.get(
            "overall_state"
        )
        or ""
    ).upper()

    score = _numeric(
        report.get(
            "overall_score"
        )
    )

    if state == "SEVERE_DEGRADATION":

        factors.append(
            ReadinessFactor(
                code=
                    "SEVERE_DEGRADATION",

                source=
                    "degradation",

                severity=
                    ReadinessSeverity.CRITICAL,

                description=
                    "Severe progressive degradation is present.",

                blocking=
                    True,
            )
        )

        return factors

    if state == "DEGRADING":

        if (
            score is not None
            and score
            >= NOT_READY_DEGRADATION_SCORE
        ):

            severity = (
                ReadinessSeverity.HIGH
            )

            blocking = True

        else:

            severity = (
                ReadinessSeverity.MEDIUM
            )

            blocking = False

        factors.append(
            ReadinessFactor(
                code=
                    "CONFIRMED_DEGRADATION",

                source=
                    "degradation",

                severity=
                    severity,

                description=
                    "A progressive degradation trend has been confirmed.",

                blocking=
                    blocking,
            )
        )

    elif state == "EARLY_DEGRADATION":

        factors.append(
            ReadinessFactor(
                code=
                    "EARLY_DEGRADATION",

                source=
                    "degradation",

                severity=
                    ReadinessSeverity.LOW,

                description=
                    "Early degradation evidence is present.",

                blocking=
                    False,
            )
        )

    elif (
        score is not None
        and score
        >= CAUTION_DEGRADATION_SCORE
    ):

        factors.append(
            ReadinessFactor(
                code=
                    "ELEVATED_DEGRADATION_SCORE",

                source=
                    "degradation",

                severity=
                    ReadinessSeverity.LOW,

                description=(
                    "Degradation score is elevated but a worsening "
                    "trend is not fully confirmed."
                ),

                blocking=
                    False,
            )
        )

    return factors


def _rul_confidence(
    report: Optional[Dict[str, Any]],
) -> float:

    if not isinstance(
        report,
        dict,
    ):
        return 0.0

    return _clamp01(
        report.get(
            "confidence"
        )
    )


def _rul_factors(
    report: Optional[Dict[str, Any]],
) -> List[ReadinessFactor]:

    if not isinstance(
        report,
        dict,
    ):
        return []

    factors: List[
        ReadinessFactor
    ] = []

    state = str(
        report.get(
            "state"
        )
        or ""
    ).upper()

    projected = _numeric(
        report.get(
            "projected_samples_remaining"
        )
    )

    hours = _numeric(
        report.get(
            "estimated_rul_hours"
        )
    )

    if state == "CRITICAL":

        factors.append(
            ReadinessFactor(
                code=
                    "RUL_CRITICAL",

                source=
                    "rul",

                severity=
                    ReadinessSeverity.CRITICAL,

                description=
                    "RUL assessment is in a critical demonstrator state.",

                blocking=
                    True,
            )
        )

        return factors

    if (
        projected is not None
        and projected
        <= CRITICAL_SAMPLE_PROJECTION
    ):

        factors.append(
            ReadinessFactor(
                code=
                    "RUL_SAMPLE_PROJECTION_CRITICAL",

                source=
                    "rul",

                severity=
                    ReadinessSeverity.CRITICAL,

                description=(
                    "Sample-domain degradation projection is "
                    "near its demonstrator end condition. "
                    "This is not an operating-hour estimate."
                ),

                blocking=
                    True,
            )
        )

    elif (
        projected is not None
        and projected
        <= LIMITED_SAMPLE_PROJECTION
    ):

        factors.append(
            ReadinessFactor(
                code=
                    "RUL_SAMPLE_PROJECTION_LIMITED",

                source=
                    "rul",

                severity=
                    ReadinessSeverity.HIGH,

                description=(
                    "Sample-domain degradation projection is short. "
                    "This is not an operating-hour estimate."
                ),

                blocking=
                    False,
            )
        )

    elif state == "LIMITED_LIFE":

        factors.append(
            ReadinessFactor(
                code=
                    "RUL_LIMITED_LIFE",

                source=
                    "rul",

                severity=
                    ReadinessSeverity.HIGH,

                description=
                    "RUL assessment indicates limited remaining life evidence.",

                blocking=
                    False,
            )
        )

    if hours is not None:

        factors.append(
            ReadinessFactor(
                code=
                    "RUL_PHYSICAL_HOURS_AVAILABLE",

                source=
                    "rul",

                severity=
                    ReadinessSeverity.LOW,

                description=(
                    f"A physical-time RUL estimate of "
                    f"{hours:.2f} hours is available."
                ),

                blocking=
                    False,
            )
        )

    return factors


def _maintenance_confidence(
    report: Optional[Dict[str, Any]],
) -> float:

    if not isinstance(
        report,
        dict,
    ):
        return 0.0

    return _clamp01(
        report.get(
            "confidence"
        )
    )


def _maintenance_factors(
    report: Optional[Dict[str, Any]],
) -> List[ReadinessFactor]:

    if not isinstance(
        report,
        dict,
    ):
        return []

    state = str(
        report.get(
            "state"
        )
        or ""
    ).upper()

    if state == "IMMEDIATE_ATTENTION":

        return [
            ReadinessFactor(
                code=
                    "MAINTENANCE_IMMEDIATE_ATTENTION",

                source=
                    "maintenance",

                severity=
                    ReadinessSeverity.CRITICAL,

                description=(
                    "Maintenance engine recommends immediate "
                    "engineering attention."
                ),

                blocking=
                    True,
            )
        ]

    if state == "MAINTENANCE_REQUIRED":

        return [
            ReadinessFactor(
                code=
                    "MAINTENANCE_REQUIRED",

                source=
                    "maintenance",

                severity=
                    ReadinessSeverity.HIGH,

                description=
                    "Maintenance engine reports maintenance is required.",

                blocking=
                    True,
            )
        ]

    if state == "INSPECT":

        return [
            ReadinessFactor(
                code=
                    "MAINTENANCE_INSPECTION",

                source=
                    "maintenance",

                severity=
                    ReadinessSeverity.MEDIUM,

                description=
                    "Focused engineering inspection is recommended.",

                blocking=
                    False,
            )
        ]

    return []


def _overall_confidence(
    *,
    sensor_validation: Optional[Dict[str, Any]],
    fault_detection: Optional[Dict[str, Any]],
    degradation: Optional[Dict[str, Any]],
    rul: Optional[Dict[str, Any]],
    maintenance: Optional[Dict[str, Any]],
) -> float:

    values = [
        _sensor_confidence(
            sensor_validation
        ),

        _fault_confidence(
            fault_detection
        ),

        _degradation_confidence(
            degradation
        ),

        _rul_confidence(
            rul
        ),

        _maintenance_confidence(
            maintenance
        ),
    ]

    available = [
        value
        for value in values
        if value > 0.0
    ]

    if not available:
        return 0.0

    return _clamp01(
        sum(
            available
        )
        / len(
            available
        )
    )


def _readiness_score(
    factors: List[ReadinessFactor],
    confidence: float,
) -> float:

    penalty = 0.0

    penalty_map = {
        ReadinessSeverity.NONE:
            0.00,

        ReadinessSeverity.LOW:
            0.08,

        ReadinessSeverity.MEDIUM:
            0.18,

        ReadinessSeverity.HIGH:
            0.35,

        ReadinessSeverity.CRITICAL:
            0.60,
    }

    for factor in factors:

        penalty += penalty_map[
            factor.severity
        ]

        if factor.blocking:
            penalty += 0.15

    penalty = min(
        penalty,
        1.0,
    )

    evidence_factor = (
        0.70
        + 0.30
        * confidence
    )

    score = (
        1.0
        - penalty
    ) * evidence_factor

    return _clamp01(
        score
    )


def _overall_state(
    *,
    factors: List[ReadinessFactor],
    confidence: float,
    sensor_coverage: Optional[float],
) -> ReadinessState:

    blocking = [
        factor
        for factor in factors
        if factor.blocking
    ]

    if blocking:

        critical_block = any(
            factor.severity
            == ReadinessSeverity.CRITICAL
            for factor in blocking
        )

        high_block = any(
            factor.severity
            == ReadinessSeverity.HIGH
            for factor in blocking
        )

        if (
            critical_block
            or high_block
        ):
            return (
                ReadinessState.NOT_READY
            )

    if (
        sensor_coverage is None
        or sensor_coverage
        < MIN_SENSOR_COVERAGE
    ):

        return (
            ReadinessState.INSUFFICIENT_DATA
        )

    if (
        confidence
        < MIN_READINESS_CONFIDENCE
    ):

        return (
            ReadinessState.INSUFFICIENT_DATA
        )

    highest = _highest_severity(
        factors
    )

    if highest in {
        ReadinessSeverity.MEDIUM,
        ReadinessSeverity.HIGH,
        ReadinessSeverity.CRITICAL,
    }:

        return (
            ReadinessState.READY_WITH_CAUTION
        )

    return (
        ReadinessState.READY
    )


def assess_mission_readiness(
    *,
    sensor_validation:
        Optional[Dict[str, Any]] = None,

    fault_detection:
        Optional[Dict[str, Any]] = None,

    degradation:
        Optional[Dict[str, Any]] = None,

    rul:
        Optional[Dict[str, Any]] = None,

    maintenance:
        Optional[Dict[str, Any]] = None,

    timestamp:
        Optional[datetime] = None,

) -> MissionReadinessReport:

    global _latest_report
    global _assessment_count
    global _failed_assessment_count

    try:

        factors: List[
            ReadinessFactor
        ] = []

        factors.extend(
            _sensor_factors(
                sensor_validation
            )
        )

        factors.extend(
            _fault_factors(
                fault_detection
            )
        )

        factors.extend(
            _degradation_factors(
                degradation
            )
        )

        factors.extend(
            _rul_factors(
                rul
            )
        )

        factors.extend(
            _maintenance_factors(
                maintenance
            )
        )

        confidence = (
            _overall_confidence(
                sensor_validation=
                    sensor_validation,

                fault_detection=
                    fault_detection,

                degradation=
                    degradation,

                rul=
                    rul,

                maintenance=
                    maintenance,
            )
        )

        coverage = (
            _sensor_coverage(
                sensor_validation
            )
        )

        state = (
            _overall_state(
                factors=
                    factors,

                confidence=
                    confidence,

                sensor_coverage=
                    coverage,
            )
        )

        severity = (
            _highest_severity(
                factors
            )
        )

        score = (
            _readiness_score(
                factors,
                confidence,
            )
        )

        warnings: List[
            str
        ] = []

        if coverage is None:

            warnings.append(
                "READINESS_SENSOR_COVERAGE_UNAVAILABLE"
            )

        elif coverage < MIN_SENSOR_COVERAGE:

            warnings.append(
                "READINESS_SENSOR_COVERAGE_INSUFFICIENT"
            )

        if confidence < MIN_READINESS_CONFIDENCE:

            warnings.append(
                "READINESS_CONFIDENCE_LOW"
            )

        if (
            state
            == ReadinessState.NOT_READY
        ):

            warnings.append(
                "MISSION_NOT_READY_ENGINEERING_REVIEW_REQUIRED"
            )

        if (
            state
            == ReadinessState.READY_WITH_CAUTION
        ):

            warnings.append(
                "MISSION_READY_WITH_CAUTION"
            )

        if (
            state
            == ReadinessState.INSUFFICIENT_DATA
        ):

            warnings.append(
                "MISSION_READINESS_INSUFFICIENT_DATA"
            )

        blocking_count = sum(
            1
            for factor in factors
            if factor.blocking
        )

        report = (
            MissionReadinessReport(
                timestamp=
                    _normalize_timestamp(
                        timestamp
                    ),

                version=
                    READINESS_VERSION,

                state=
                    state,

                severity=
                    severity,

                confidence=
                    confidence,

                confidence_level=
                    _confidence_level(
                        confidence
                    ),

                readiness_score=
                    score,

                readiness_score_percent=
                    score * 100.0,

                factors=
                    factors,

                factor_count=
                    len(
                        factors
                    ),

                blocking_factor_count=
                    blocking_count,

                sensor_coverage=
                    coverage,

                maintenance_state=(
                    str(
                        maintenance.get(
                            "state"
                        )
                    )
                    if isinstance(
                        maintenance,
                        dict,
                    )
                    else None
                ),

                rul_state=(
                    str(
                        rul.get(
                            "state"
                        )
                    )
                    if isinstance(
                        rul,
                        dict,
                    )
                    else None
                ),

                degradation_state=(
                    str(
                        degradation.get(
                            "overall_state"
                        )
                    )
                    if isinstance(
                        degradation,
                        dict,
                    )
                    else None
                ),

                fault_state=(
                    str(
                        fault_detection.get(
                            "overall_state"
                        )
                    )
                    if isinstance(
                        fault_detection,
                        dict,
                    )
                    else None
                ),

                warnings=
                    warnings,
            )
        )

        _latest_report = report

        _assessment_count += 1

        return report

    except Exception:

        _failed_assessment_count += 1

        raise


def get_latest_readiness(
) -> Optional[Dict[str, Any]]:

    if _latest_report is None:
        return None

    return (
        _latest_report.to_dict()
    )


def get_readiness_status(
) -> Dict[str, Any]:

    latest = (
        get_latest_readiness()
    )

    return {
        "service":
            "mission_readiness",

        "status":
            "READY",

        "version":
            READINESS_VERSION,

        "assessment_count":
            _assessment_count,

        "failed_assessment_count":
            _failed_assessment_count,

        "latest_result_available":
            latest is not None,

        "latest_state": (
            latest.get(
                "state"
            )
            if latest
            else None
        ),

        "latest_severity": (
            latest.get(
                "severity"
            )
            if latest
            else None
        ),

        "latest_confidence": (
            latest.get(
                "confidence"
            )
            if latest
            else None
        ),

        "timestamp":
            _utc_now().isoformat(),
    }


def reset_readiness(
) -> None:

    global _latest_report
    global _assessment_count
    global _failed_assessment_count

    _latest_report = None

    _assessment_count = 0

    _failed_assessment_count = 0


def get_readiness_info(
) -> Dict[str, Any]:

    return {
        "service":
            "mission_readiness",

        "version":
            READINESS_VERSION,

        "states": [
            "INSUFFICIENT_DATA",
            "READY",
            "READY_WITH_CAUTION",
            "NOT_READY",
        ],

        "inputs": [
            "sensor_validation",
            "fault_detection",
            "degradation",
            "rul",
            "maintenance",
        ],

        "minimum_sensor_coverage":
            MIN_SENSOR_COVERAGE,

        "good_sensor_coverage":
            GOOD_SENSOR_COVERAGE,

        "minimum_readiness_confidence":
            MIN_READINESS_CONFIDENCE,

        "zero_is_valid":
            True,

        "none_means_unavailable":
            True,

        "missing_data_is_failure":
            False,

        "insufficient_data_is_not_ready":
            False,

        "not_ready_requires_blocking_evidence":
            True,

        "recalculates_sensor_validation":
            False,

        "recalculates_faults":
            False,

        "recalculates_degradation":
            False,

        "recalculates_rul":
            False,

        "recalculates_maintenance":
            False,

        "automatic_flight_authorization":
            False,

        "automatic_engine_shutdown":
            False,

        "official_drdo_vrde_release_logic":
            False,

        "official_airworthiness_decision":
            False,

        "certified_flight_safety_system":
            False,

        "sample_projection_is_operating_hours":
            False,
    }
