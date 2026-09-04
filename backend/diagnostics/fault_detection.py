from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any, Dict, List, Optional, Sequence, Tuple


FAULT_DETECTION_VERSION = "1.0.0"


class FaultSeverity(str, Enum):

    NONE = "NONE"

    INFO = "INFO"

    LOW = "LOW"

    MEDIUM = "MEDIUM"

    HIGH = "HIGH"

    CRITICAL = "CRITICAL"


class FaultCategory(str, Enum):

    DATA_QUALITY = "DATA_QUALITY"

    MECHANICAL = "MECHANICAL"

    THERMAL = "THERMAL"

    COMBUSTION = "COMBUSTION"

    LUBRICATION = "LUBRICATION"

    FUEL_SYSTEM = "FUEL_SYSTEM"

    VIBRATION = "VIBRATION"

    ELECTRICAL = "ELECTRICAL"

    PERFORMANCE = "PERFORMANCE"

    UNKNOWN = "UNKNOWN"


class FaultState(str, Enum):

    NORMAL = "NORMAL"

    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

    SUSPECTED = "SUSPECTED"

    DETECTED = "DETECTED"


@dataclass
class FaultEvidence:

    source: str

    path: Optional[str]

    description: str

    score: float

    available: bool = True

    observed: Optional[float] = None

    expected: Optional[float] = None

    residual: Optional[float] = None

    normalized_residual: Optional[float] = None


    def to_dict(
        self,
    ) -> Dict[str, Any]:

        return {

            "source":
                self.source,

            "path":
                self.path,

            "description":
                self.description,

            "score":
                self.score,

            "score_percent":
                self.score * 100.0,

            "available":
                self.available,

            "observed":
                self.observed,

            "expected":
                self.expected,

            "residual":
                self.residual,

            "normalized_residual":
                self.normalized_residual,
        }


@dataclass
class FaultCandidate:

    fault_id: str

    name: str

    category: FaultCategory

    severity: FaultSeverity

    state: FaultState

    confidence: float

    score: float

    affected_paths: List[str]

    evidence: List[FaultEvidence]

    explanation: str

    recommendation: str

    data_coverage: float


    def to_dict(
        self,
    ) -> Dict[str, Any]:

        return {

            "fault_id":
                self.fault_id,

            "name":
                self.name,

            "category":
                self.category.value,

            "severity":
                self.severity.value,

            "state":
                self.state.value,

            "confidence":
                self.confidence,

            "confidence_percent":
                self.confidence * 100.0,

            "score":
                self.score,

            "score_percent":
                self.score * 100.0,

            "affected_paths":
                self.affected_paths,

            "evidence": [
                item.to_dict()
                for item in self.evidence
            ],

            "explanation":
                self.explanation,

            "recommendation":
                self.recommendation,

            "data_coverage":
                self.data_coverage,

            "data_coverage_percent":
                self.data_coverage
                * 100.0,
        }


@dataclass
class FaultDetectionReport:

    timestamp: datetime

    version: str

    overall_state: FaultState

    overall_severity: FaultSeverity

    overall_fault_score: float

    overall_confidence: float

    candidates: List[FaultCandidate]

    active_faults: List[FaultCandidate]

    data_quality_issues: List[FaultCandidate]

    residual_coverage: float

    sensor_coverage: float

    warnings: List[str] = field(
        default_factory=list
    )


    def to_dict(
        self,
    ) -> Dict[str, Any]:

        return {

            "timestamp":
                self.timestamp.isoformat(),

            "version":
                self.version,

            "overall_state":
                self.overall_state.value,

            "overall_severity":
                self.overall_severity.value,

            "overall_fault_score":
                self.overall_fault_score,

            "overall_fault_score_percent":
                self.overall_fault_score
                * 100.0,

            "overall_confidence":
                self.overall_confidence,

            "overall_confidence_percent":
                self.overall_confidence
                * 100.0,

            "candidates": [
                item.to_dict()
                for item
                in self.candidates
            ],

            "active_faults": [
                item.to_dict()
                for item
                in self.active_faults
            ],

            "data_quality_issues": [
                item.to_dict()
                for item
                in self.data_quality_issues
            ],

            "fault_count":
                len(
                    self.active_faults
                ),

            "data_quality_issue_count":
                len(
                    self.data_quality_issues
                ),

            "residual_coverage":
                self.residual_coverage,

            "residual_coverage_percent":
                self.residual_coverage
                * 100.0,

            "sensor_coverage":
                self.sensor_coverage,

            "sensor_coverage_percent":
                self.sensor_coverage
                * 100.0,

            "warnings":
                self.warnings,
        }


_detection_count = 0

_failed_detection_count = 0

_latest_report: Optional[
    FaultDetectionReport
] = None


def _utc_now() -> datetime:

    return datetime.now(
        timezone.utc
    )


def _clamp01(
    value: float,
) -> float:

    return max(
        0.0,
        min(
            1.0,
            float(value),
        ),
    )


def _numeric(
    value: Any,
) -> Optional[float]:

    if value is None:

        return None


    if isinstance(
        value,
        bool,
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


def _dict_value(
    data: Optional[Dict[str, Any]],
    key: str,
    default: Any = None,
) -> Any:

    if not isinstance(
        data,
        dict,
    ):

        return default


    return data.get(
        key,
        default,
    )


def _get_nested(
    data: Optional[Dict[str, Any]],
    path: str,
) -> Any:

    if not isinstance(
        data,
        dict,
    ):

        return None


    current: Any = data


    for part in path.split(
        "."
    ):

        if not isinstance(
            current,
            dict,
        ):

            return None


        if part not in current:

            return None


        current = current[
            part
        ]


    return current


def _severity_rank(
    severity: FaultSeverity,
) -> int:

    ranking = {

        FaultSeverity.NONE:
            0,

        FaultSeverity.INFO:
            1,

        FaultSeverity.LOW:
            2,

        FaultSeverity.MEDIUM:
            3,

        FaultSeverity.HIGH:
            4,

        FaultSeverity.CRITICAL:
            5,
    }


    return ranking[
        severity
    ]


def _severity_from_score(
    score: float,
) -> FaultSeverity:

    score = _clamp01(
        score
    )


    if score >= 0.90:

        return FaultSeverity.CRITICAL


    if score >= 0.70:

        return FaultSeverity.HIGH


    if score >= 0.50:

        return FaultSeverity.MEDIUM


    if score >= 0.30:

        return FaultSeverity.LOW


    if score > 0.0:

        return FaultSeverity.INFO


    return FaultSeverity.NONE


def _state_from_score(
    score: float,
    confidence: float,
) -> FaultState:

    score = _clamp01(
        score
    )

    confidence = _clamp01(
        confidence
    )


    if confidence < 0.15:

        return FaultState.INSUFFICIENT_DATA


    if score >= 0.55:

        return FaultState.DETECTED


    if score >= 0.25:

        return FaultState.SUSPECTED


    return FaultState.NORMAL


def _sensor_coverage(
    sensor_validation: Optional[
        Dict[str, Any]
    ],
) -> float:

    if not isinstance(
        sensor_validation,
        dict,
    ):

        return 0.0


    value = _numeric(
        sensor_validation.get(
            "coverage"
        )
    )


    if value is None:

        return 0.0


    return _clamp01(
        value
    )


def _sensor_quality(
    sensor_validation: Optional[
        Dict[str, Any]
    ],
) -> float:

    if not isinstance(
        sensor_validation,
        dict,
    ):

        return 0.0


    value = _numeric(
        sensor_validation.get(
            "overall_quality"
        )
    )


    if value is None:

        return 0.0


    return _clamp01(
        value
    )


def _sensor_result(
    sensor_validation: Optional[
        Dict[str, Any]
    ],
    path: str,
) -> Optional[Dict[str, Any]]:

    if not isinstance(
        sensor_validation,
        dict,
    ):

        return None


    results = sensor_validation.get(
        "results"
    )


    if not isinstance(
        results,
        dict,
    ):

        return None


    result = results.get(
        path
    )


    if not isinstance(
        result,
        dict,
    ):

        return None


    return result


def _residual_coverage(
    residual_state: Optional[
        Dict[str, Any]
    ],
) -> float:

    if not isinstance(
        residual_state,
        dict,
    ):

        return 0.0


    coverage = residual_state.get(
        "coverage"
    )


    if isinstance(
        coverage,
        dict,
    ):

        value = _numeric(
            coverage.get(
                "fraction"
            )
        )

    else:

        value = _numeric(
            coverage
        )


    if value is None:

        return 0.0


    return _clamp01(
        value
    )


def _residual_confidence(
    residual_state: Optional[
        Dict[str, Any]
    ],
) -> float:

    if not isinstance(
        residual_state,
        dict,
    ):

        return 0.0


    value = _numeric(
        residual_state.get(
            "confidence"
        )
    )


    if value is None:

        return 0.0


    return _clamp01(
        value
    )


def _residual_entry(
    residual_state: Optional[
        Dict[str, Any]
    ],
    path: str,
) -> Optional[Dict[str, Any]]:

    if not isinstance(
        residual_state,
        dict,
    ):

        return None


    residuals = residual_state.get(
        "residuals"
    )


    if not isinstance(
        residuals,
        dict,
    ):

        return None


    entry = residuals.get(
        path
    )


    if not isinstance(
        entry,
        dict,
    ):

        return None


    return entry


def _residual_score(
    residual_state: Optional[
        Dict[str, Any]
    ],
    path: str,
) -> Optional[float]:

    entry = _residual_entry(
        residual_state,
        path,
    )


    if entry is None:

        return None


    if entry.get(
        "available"
    ) is not True:

        return None


    value = _numeric(
        entry.get(
            "deviation_score"
        )
    )


    if value is None:

        value = _numeric(
            entry.get(
                "normalized_magnitude"
            )
        )


    if value is None:

        return None


    return _clamp01(
        value
    )


def _build_residual_evidence(
    residual_state: Optional[
        Dict[str, Any]
    ],
    path: str,
    description: str,
) -> Optional[FaultEvidence]:

    entry = _residual_entry(
        residual_state,
        path,
    )


    if entry is None:

        return None


    if entry.get(
        "available"
    ) is not True:

        return None


    score = _residual_score(
        residual_state,
        path,
    )


    if score is None:

        return None


    return FaultEvidence(

        source=
            "RESIDUAL_ENGINE",

        path=
            path,

        description=
            description,

        score=
            score,

        available=
            True,

        observed=
            _numeric(
                entry.get(
                    "observed"
                )
            ),

        expected=
            _numeric(
                entry.get(
                    "expected"
                )
            ),

        residual=
            _numeric(
                entry.get(
                    "absolute"
                )
            ),

        normalized_residual=
            _numeric(
                entry.get(
                    "normalized"
                )
            ),
    )


def _detect_sensor_quality_issues(
    sensor_validation: Optional[
        Dict[str, Any]
    ],
) -> List[FaultCandidate]:

    issues: List[
        FaultCandidate
    ] = []


    if not isinstance(
        sensor_validation,
        dict,
    ):

        return issues


    results = sensor_validation.get(
        "results"
    )


    if not isinstance(
        results,
        dict,
    ):

        return issues


    for path, result in (
        results.items()
    ):

        if not isinstance(
            result,
            dict,
        ):

            continue


        status = str(
            result.get(
                "status",
                ""
            )
        ).upper()


        if status == "MISSING":

            continue


        if status == "VALID":

            continue


        quality = _numeric(
            result.get(
                "quality"
            )
        )


        if quality is None:

            quality = 0.0


        score = _clamp01(
            1.0
            - quality
        )


        reasons = result.get(
            "reasons"
        )


        if not isinstance(
            reasons,
            list,
        ):

            reasons = []


        evidence = [

            FaultEvidence(

                source=
                    "SENSOR_VALIDATION",

                path=
                    path,

                description=
                    (
                        f"Sensor validation status "
                        f"{status}"
                    ),

                score=
                    score,

                available=
                    True,

                observed=
                    _numeric(
                        result.get(
                            "value"
                        )
                    ),
            )
        ]


        severity = (
            FaultSeverity.MEDIUM
            if status
            in {
                "OUT_OF_RANGE",
                "INVALID",
                "INCONSISTENT",
            }
            else
            FaultSeverity.LOW
        )


        issues.append(

            FaultCandidate(

                fault_id=
                    (
                        "SENSOR_"
                        + path
                        .replace(
                            ".",
                            "_",
                        )
                        .upper()
                    ),

                name=
                    (
                        "Sensor/Data Quality Issue: "
                        + path
                    ),

                category=
                    FaultCategory.DATA_QUALITY,

                severity=
                    severity,

                state=
                    FaultState.DETECTED,

                confidence=
                    max(
                        0.50,
                        score,
                    ),

                score=
                    score,

                affected_paths=[
                    path
                ],

                evidence=
                    evidence,

                explanation=
                    (
                        f"{path} was classified as "
                        f"{status}. "
                        f"Reasons: "
                        f"{', '.join(reasons) if reasons else 'not supplied'}."
                    ),

                recommendation=
                    (
                        "Verify sensor integrity, signal "
                        "conditioning, wiring, calibration "
                        "and telemetry freshness before "
                        "using this channel for engine "
                        "fault diagnosis."
                    ),

                data_coverage=
                    1.0,
            )
        )


    return issues


def _build_single_residual_fault(
    *,
    fault_id: str,
    name: str,
    category: FaultCategory,
    path: str,
    residual_state: Optional[
        Dict[str, Any]
    ],
    sensor_validation: Optional[
        Dict[str, Any]
    ],
    explanation: str,
    recommendation: str,
    minimum_score: float = 0.25,
) -> Optional[FaultCandidate]:

    residual_score = (
        _residual_score(
            residual_state,
            path,
        )
    )


    if residual_score is None:

        return None


    if residual_score < minimum_score:

        return None


    sensor_result = (
        _sensor_result(
            sensor_validation,
            path,
        )
    )


    if isinstance(
        sensor_result,
        dict,
    ):

        sensor_status = str(
            sensor_result.get(
                "status",
                ""
            )
        ).upper()


        if sensor_status not in {
            "",
            "VALID",
        }:

            return None


    evidence = (
        _build_residual_evidence(
            residual_state,
            path,
            (
                f"{path} differs from "
                f"Digital Twin expectation."
            ),
        )
    )


    if evidence is None:

        return None


    residual_confidence = (
        _residual_confidence(
            residual_state
        )
    )


    sensor_quality = (
        _sensor_quality(
            sensor_validation
        )
    )


    confidence = _clamp01(

        (
            0.60
            * max(
                residual_confidence,
                residual_score,
            )
        )

        +

        (
            0.40
            * max(
                sensor_quality,
                0.25,
            )
        )
    )


    state = _state_from_score(
        residual_score,
        confidence,
    )


    return FaultCandidate(

        fault_id=
            fault_id,

        name=
            name,

        category=
            category,

        severity=
            _severity_from_score(
                residual_score
            ),

        state=
            state,

        confidence=
            confidence,

        score=
            residual_score,

        affected_paths=[
            path
        ],

        evidence=[
            evidence
        ],

        explanation=
            explanation,

        recommendation=
            recommendation,

        data_coverage=
            max(
                _sensor_coverage(
                    sensor_validation
                ),
                _residual_coverage(
                    residual_state
                ),
            ),
    )


def _detect_mechanical_faults(
    residual_state: Optional[
        Dict[str, Any]
    ],
    sensor_validation: Optional[
        Dict[str, Any]
    ],
) -> List[FaultCandidate]:

    candidates: List[
        FaultCandidate
    ] = []


    power = _build_single_residual_fault(

        fault_id=
            "PERFORMANCE_POWER_DEVIATION",

        name=
            "Engine Power Deviation",

        category=
            FaultCategory.PERFORMANCE,

        path=
            "engine.power_kw",

        residual_state=
            residual_state,

        sensor_validation=
            sensor_validation,

        explanation=
            (
                "Measured engine power differs from the "
                "Digital Twin expected operating-point power."
            ),

        recommendation=
            (
                "Correlate power deviation with RPM, torque, "
                "fuel flow, temperatures and operating "
                "conditions before isolating a propulsion fault."
            ),
    )


    if power is not None:

        candidates.append(
            power
        )


    torque = _build_single_residual_fault(

        fault_id=
            "MECHANICAL_TORQUE_DEVIATION",

        name=
            "Engine Torque Deviation",

        category=
            FaultCategory.MECHANICAL,

        path=
            "engine.torque_nm",

        residual_state=
            residual_state,

        sensor_validation=
            sensor_validation,

        explanation=
            (
                "Measured torque differs from the expected "
                "Digital Twin torque at the current operating point."
            ),

        recommendation=
            (
                "Correlate torque with power, RPM, load and "
                "combustion evidence before diagnosing "
                "mechanical degradation."
            ),
    )


    if torque is not None:

        candidates.append(
            torque
        )


    rpm = _build_single_residual_fault(

        fault_id=
            "MECHANICAL_RPM_DEVIATION",

        name=
            "Engine Speed Deviation",

        category=
            FaultCategory.MECHANICAL,

        path=
            "engine.rpm",

        residual_state=
            residual_state,

        sensor_validation=
            sensor_validation,

        explanation=
            (
                "Observed engine speed deviates from the "
                "Digital Twin expected engine speed."
            ),

        recommendation=
            (
                "Inspect command/load consistency and correlate "
                "with power, torque and propulsive loading."
            ),
    )


    if rpm is not None:

        candidates.append(
            rpm
        )


    return candidates


def _detect_thermal_faults(
    residual_state: Optional[
        Dict[str, Any]
    ],
    sensor_validation: Optional[
        Dict[str, Any]
    ],
) -> List[FaultCandidate]:

    candidates: List[
        FaultCandidate
    ] = []


    paths = [

        "cht.cylinder1_c",

        "cht.cylinder2_c",

        "cht.cylinder3_c",

        "cht.cylinder4_c",
    ]


    available_scores: List[
        Tuple[str, float]
    ] = []


    evidence: List[
        FaultEvidence
    ] = []


    for path in paths:

        sensor = _sensor_result(
            sensor_validation,
            path,
        )


        if (
            isinstance(
                sensor,
                dict,
            )
            and
            str(
                sensor.get(
                    "status",
                    ""
                )
            ).upper()
            not in {
                "",
                "VALID",
            }
        ):

            continue


        score = _residual_score(
            residual_state,
            path,
        )


        if score is None:

            continue


        available_scores.append(
            (
                path,
                score,
            )
        )


        item = (
            _build_residual_evidence(
                residual_state,
                path,
                "Cylinder-head temperature deviation.",
            )
        )


        if item is not None:

            evidence.append(
                item
            )


    if not available_scores:

        return candidates


    max_score = max(
        score
        for _,
        score
        in available_scores
    )


    average_score = (
        sum(
            score
            for _,
            score
            in available_scores
        )
        /
        len(
            available_scores
        )
    )


    combined_score = _clamp01(

        (
            0.65
            * max_score
        )

        +

        (
            0.35
            * average_score
        )
    )


    if combined_score < 0.25:

        return candidates


    confidence = _clamp01(

        0.50
        * max(
            combined_score,
            _residual_confidence(
                residual_state
            ),
        )

        +

        0.50
        * (
            len(
                available_scores
            )
            /
            len(
                paths
            )
        )
    )


    candidates.append(

        FaultCandidate(

            fault_id=
                "THERMAL_CHT_DEVIATION",

            name=
                "Cylinder Head Temperature Deviation",

            category=
                FaultCategory.THERMAL,

            severity=
                _severity_from_score(
                    combined_score
                ),

            state=
                _state_from_score(
                    combined_score,
                    confidence,
                ),

            confidence=
                confidence,

            score=
                combined_score,

            affected_paths=[
                path
                for path, score
                in available_scores
                if score >= 0.25
            ],

            evidence=
                evidence,

            explanation=
                (
                    "One or more cylinder-head temperatures "
                    "differ from the Digital Twin thermal model."
                ),

            recommendation=
                (
                    "Correlate CHT deviation with EGT, airflow, "
                    "load and cooling conditions. Do not infer "
                    "overheating solely from model residuals."
                ),

            data_coverage=
                len(
                    available_scores
                )
                /
                len(
                    paths
                ),
        )
    )


    return candidates


def _detect_combustion_faults(
    residual_state: Optional[
        Dict[str, Any]
    ],
    sensor_validation: Optional[
        Dict[str, Any]
    ],
) -> List[FaultCandidate]:

    candidates: List[
        FaultCandidate
    ] = []


    paths = [

        "egt.cylinder1_c",

        "egt.cylinder2_c",

        "egt.cylinder3_c",

        "egt.cylinder4_c",
    ]


    scores: List[
        Tuple[str, float]
    ] = []


    evidence: List[
        FaultEvidence
    ] = []


    for path in paths:

        sensor = _sensor_result(
            sensor_validation,
            path,
        )


        if (
            isinstance(
                sensor,
                dict,
            )
            and
            str(
                sensor.get(
                    "status",
                    ""
                )
            ).upper()
            not in {
                "",
                "VALID",
            }
        ):

            continue


        score = _residual_score(
            residual_state,
            path,
        )


        if score is None:

            continue


        scores.append(
            (
                path,
                score,
            )
        )


        item = (
            _build_residual_evidence(
                residual_state,
                path,
                "Exhaust-gas temperature deviation.",
            )
        )


        if item is not None:

            evidence.append(
                item
            )


    if scores:

        strongest = max(
            score
            for _,
            score
            in scores
        )


        mean_score = (
            sum(
                score
                for _,
                score
                in scores
            )
            /
            len(
                scores
            )
        )


        combined = _clamp01(
            0.70
            * strongest
            +
            0.30
            * mean_score
        )


        if combined >= 0.25:

            confidence = _clamp01(

                0.55
                * max(
                    combined,
                    _residual_confidence(
                        residual_state
                    ),
                )

                +

                0.45
                * (
                    len(
                        scores
                    )
                    /
                    len(
                        paths
                    )
                )
            )


            candidates.append(

                FaultCandidate(

                    fault_id=
                        "COMBUSTION_EGT_DEVIATION",

                    name=
                        "Combustion Temperature Deviation",

                    category=
                        FaultCategory.COMBUSTION,

                    severity=
                        _severity_from_score(
                            combined
                        ),

                    state=
                        _state_from_score(
                            combined,
                            confidence,
                        ),

                    confidence=
                        confidence,

                    score=
                        combined,

                    affected_paths=[
                        path
                        for path, score
                        in scores
                        if score >= 0.25
                    ],

                    evidence=
                        evidence,

                    explanation=
                        (
                            "Observed EGT behaviour differs "
                            "from expected combustion-model behaviour."
                        ),

                    recommendation=
                        (
                            "Correlate EGT with fuel flow, load, "
                            "CHT and cylinder-to-cylinder spread "
                            "before isolating a combustion fault."
                        ),

                    data_coverage=
                        len(
                            scores
                        )
                        /
                        len(
                            paths
                        ),
                )
            )


    return candidates


def _detect_lubrication_faults(
    residual_state: Optional[
        Dict[str, Any]
    ],
    sensor_validation: Optional[
        Dict[str, Any]
    ],
) -> List[FaultCandidate]:

    candidates: List[
        FaultCandidate
    ] = []


    pressure = _build_single_residual_fault(

        fault_id=
            "LUBRICATION_PRESSURE_DEVIATION",

        name=
            "Oil Pressure Deviation",

        category=
            FaultCategory.LUBRICATION,

        path=
            "oil.pressure_kpa",

        residual_state=
            residual_state,

        sensor_validation=
            sensor_validation,

        explanation=
            (
                "Measured oil pressure differs from the "
                "Digital Twin lubrication-model expectation."
            ),

        recommendation=
            (
                "Correlate with oil temperature, RPM and load. "
                "Verify pressure-sensor integrity before "
                "diagnosing lubrication-system degradation."
            ),
    )


    if pressure is not None:

        candidates.append(
            pressure
        )


    temperature = _build_single_residual_fault(

        fault_id=
            "LUBRICATION_TEMPERATURE_DEVIATION",

        name=
            "Oil Temperature Deviation",

        category=
            FaultCategory.LUBRICATION,

        path=
            "oil.temperature_c",

        residual_state=
            residual_state,

        sensor_validation=
            sensor_validation,

        explanation=
            (
                "Oil temperature differs from the expected "
                "lubrication thermal state."
            ),

        recommendation=
            (
                "Correlate with oil pressure, load, ambient "
                "temperature and cooling-system behaviour."
            ),
    )


    if temperature is not None:

        candidates.append(
            temperature
        )


    return candidates


def _detect_fuel_faults(
    residual_state: Optional[
        Dict[str, Any]
    ],
    sensor_validation: Optional[
        Dict[str, Any]
    ],
) -> List[FaultCandidate]:

    candidates: List[
        FaultCandidate
    ] = []


    fuel_flow = _build_single_residual_fault(

        fault_id=
            "FUEL_FLOW_DEVIATION",

        name=
            "Fuel Flow Deviation",

        category=
            FaultCategory.FUEL_SYSTEM,

        path=
            "fuel.flow_kg_per_second",

        residual_state=
            residual_state,

        sensor_validation=
            sensor_validation,

        explanation=
            (
                "Measured fuel flow differs from the independently "
                "predicted Digital Twin fuel-flow expectation."
            ),

        recommendation=
            (
                "Correlate fuel flow with power, RPM, load and "
                "combustion temperatures before diagnosing "
                "fuel-system degradation."
            ),
    )


    if fuel_flow is not None:

        candidates.append(
            fuel_flow
        )


    return candidates


def _detect_vibration_faults(
    residual_state: Optional[
        Dict[str, Any]
    ],
    sensor_validation: Optional[
        Dict[str, Any]
    ],
) -> List[FaultCandidate]:

    candidates: List[
        FaultCandidate
    ] = []


    vibration = _build_single_residual_fault(

        fault_id=
            "VIBRATION_DEVIATION",

        name=
            "Abnormal Vibration Evidence",

        category=
            FaultCategory.VIBRATION,

        path=
            "vibration.overall_g",

        residual_state=
            residual_state,

        sensor_validation=
            sensor_validation,

        explanation=
            (
                "Observed vibration differs from its expected "
                "Digital Twin reference."
            ),

        recommendation=
            (
                "Correlate vibration with RPM and operating "
                "condition and inspect mechanical sources "
                "before isolating a component-level fault."
            ),
    )


    if vibration is not None:

        candidates.append(
            vibration
        )


    return candidates


def _detect_electrical_faults(
    residual_state: Optional[
        Dict[str, Any]
    ],
    sensor_validation: Optional[
        Dict[str, Any]
    ],
) -> List[FaultCandidate]:

    candidates: List[
        FaultCandidate
    ] = []


    for (
        fault_id,
        name,
        path,
    ) in [

        (
            "BATTERY_VOLTAGE_DEVIATION",
            "Battery Voltage Deviation",
            "electrical.battery_voltage_v",
        ),

        (
            "ALTERNATOR_VOLTAGE_DEVIATION",
            "Alternator Voltage Deviation",
            "electrical.alternator_voltage_v",
        ),
    ]:

        candidate = (
            _build_single_residual_fault(

                fault_id=
                    fault_id,

                name=
                    name,

                category=
                    FaultCategory.ELECTRICAL,

                path=
                    path,

                residual_state=
                    residual_state,

                sensor_validation=
                    sensor_validation,

                explanation=
                    (
                        f"{path} differs from "
                        f"the expected electrical state."
                    ),

                recommendation=
                    (
                        "Verify electrical measurement quality "
                        "and correlate with generator/battery "
                        "operating condition."
                    ),
            )
        )


        if candidate is not None:

            candidates.append(
                candidate
            )


    return candidates


def _build_correlated_power_torque_fault(
    residual_state: Optional[
        Dict[str, Any]
    ],
    sensor_validation: Optional[
        Dict[str, Any]
    ],
) -> Optional[FaultCandidate]:

    power_score = _residual_score(
        residual_state,
        "engine.power_kw",
    )


    torque_score = _residual_score(
        residual_state,
        "engine.torque_nm",
    )


    if (
        power_score is None
        or
        torque_score is None
    ):

        return None


    if (
        power_score < 0.25
        or
        torque_score < 0.25
    ):

        return None


    for path in [
        "engine.power_kw",
        "engine.torque_nm",
    ]:

        sensor = _sensor_result(
            sensor_validation,
            path,
        )


        if isinstance(
            sensor,
            dict,
        ):

            status = str(
                sensor.get(
                    "status",
                    ""
                )
            ).upper()


            if status not in {
                "",
                "VALID",
            }:

                return None


    combined_score = _clamp01(

        0.50
        * power_score

        +

        0.50
        * torque_score
    )


    evidence: List[
        FaultEvidence
    ] = []


    for path in [
        "engine.power_kw",
        "engine.torque_nm",
    ]:

        item = _build_residual_evidence(
            residual_state,
            path,
            (
                "Correlated mechanical/performance "
                "residual evidence."
            ),
        )


        if item is not None:

            evidence.append(
                item
            )


    confidence = _clamp01(

        0.70
        * max(
            combined_score,
            _residual_confidence(
                residual_state
            ),
        )

        +

        0.30
        * max(
            _sensor_quality(
                sensor_validation
            ),
            0.25,
        )
    )


    return FaultCandidate(

        fault_id=
            "CORRELATED_POWER_TORQUE_DEGRADATION",

        name=
            "Correlated Power/Torque Degradation",

        category=
            FaultCategory.PERFORMANCE,

        severity=
            _severity_from_score(
                combined_score
            ),

        state=
            _state_from_score(
                combined_score,
                confidence,
            ),

        confidence=
            confidence,

        score=
            combined_score,

        affected_paths=[
            "engine.power_kw",
            "engine.torque_nm",
        ],

        evidence=
            evidence,

        explanation=
            (
                "Power and torque simultaneously deviate from "
                "Digital Twin expectations. Correlated evidence "
                "is stronger than either residual alone."
            ),

        recommendation=
            (
                "Correlate with fuel flow, thermal behaviour, "
                "RPM stability and operating load before "
                "isolating the physical cause."
            ),

        data_coverage=
            max(
                _sensor_coverage(
                    sensor_validation
                ),
                _residual_coverage(
                    residual_state
                ),
            ),
    )


def _sort_candidates(
    candidates: Sequence[
        FaultCandidate
    ],
) -> List[FaultCandidate]:

    return sorted(

        candidates,

        key=lambda item: (

            _severity_rank(
                item.severity
            ),

            item.score,

            item.confidence,
        ),

        reverse=True,
    )


def detect_faults(
    *,
    observed_state: Optional[
        Dict[str, Any]
    ] = None,
    expected_state: Optional[
        Dict[str, Any]
    ] = None,
    sensor_validation: Optional[
        Dict[str, Any]
    ] = None,
    residual_state: Optional[
        Dict[str, Any]
    ] = None,
    timestamp: Optional[
        datetime
    ] = None,
) -> FaultDetectionReport:

    del observed_state
    del expected_state


    global _detection_count
    global _failed_detection_count
    global _latest_report


    try:

        if timestamp is None:

            timestamp = _utc_now()


        elif timestamp.tzinfo is None:

            timestamp = timestamp.replace(
                tzinfo=timezone.utc
            )


        sensor_cov = (
            _sensor_coverage(
                sensor_validation
            )
        )


        residual_cov = (
            _residual_coverage(
                residual_state
            )
        )


        sensor_quality = (
            _sensor_quality(
                sensor_validation
            )
        )


        residual_conf = (
            _residual_confidence(
                residual_state
            )
        )


        data_quality_issues = (
            _detect_sensor_quality_issues(
                sensor_validation
            )
        )


        candidates: List[
            FaultCandidate
        ] = []


        candidates.extend(
            _detect_mechanical_faults(
                residual_state,
                sensor_validation,
            )
        )


        candidates.extend(
            _detect_thermal_faults(
                residual_state,
                sensor_validation,
            )
        )


        candidates.extend(
            _detect_combustion_faults(
                residual_state,
                sensor_validation,
            )
        )


        candidates.extend(
            _detect_lubrication_faults(
                residual_state,
                sensor_validation,
            )
        )


        candidates.extend(
            _detect_fuel_faults(
                residual_state,
                sensor_validation,
            )
        )


        candidates.extend(
            _detect_vibration_faults(
                residual_state,
                sensor_validation,
            )
        )


        candidates.extend(
            _detect_electrical_faults(
                residual_state,
                sensor_validation,
            )
        )


        correlated = (
            _build_correlated_power_torque_fault(
                residual_state,
                sensor_validation,
            )
        )


        if correlated is not None:

            candidates.append(
                correlated
            )


        candidates = _sort_candidates(
            candidates
        )


        active_faults = [

            item

            for item in candidates

            if item.state
            in {
                FaultState.SUSPECTED,
                FaultState.DETECTED,
            }
        ]


        if active_faults:

            overall_fault_score = max(
                item.score
                for item
                in active_faults
            )

        else:

            overall_fault_score = 0.0


        overall_confidence = _clamp01(

            (
                0.40
                * sensor_quality
            )

            +

            (
                0.35
                * residual_conf
            )

            +

            (
                0.15
                * sensor_cov
            )

            +

            (
                0.10
                * residual_cov
            )
        )


        if active_faults:

            if any(
                item.state
                == FaultState.DETECTED
                for item
                in active_faults
            ):

                overall_state = (
                    FaultState.DETECTED
                )

            else:

                overall_state = (
                    FaultState.SUSPECTED
                )


        elif (
            overall_confidence < 0.15
            and
            (
                sensor_cov < 0.25
                or
                residual_cov < 0.10
            )
        ):

            overall_state = (
                FaultState.INSUFFICIENT_DATA
            )


        else:

            overall_state = (
                FaultState.NORMAL
            )


        if active_faults:

            overall_severity = max(

                (
                    item.severity
                    for item
                    in active_faults
                ),

                key=
                    _severity_rank,
            )

        elif data_quality_issues:

            overall_severity = (
                FaultSeverity.INFO
            )

        else:

            overall_severity = (
                FaultSeverity.NONE
            )


        warnings: List[
            str
        ] = []


        if sensor_cov < 0.50:

            warnings.append(
                "FAULT_DETECTION_SENSOR_COVERAGE_LOW"
            )


        if residual_cov < 0.50:

            warnings.append(
                "FAULT_DETECTION_RESIDUAL_COVERAGE_LOW"
            )


        if overall_confidence < 0.30:

            warnings.append(
                "FAULT_DETECTION_CONFIDENCE_LOW"
            )


        if data_quality_issues:

            warnings.append(
                "SENSOR_QUALITY_ISSUES_PRESENT"
            )


        if (
            not active_faults
            and
            overall_state
            == FaultState.NORMAL
            and
            overall_confidence < 0.50
        ):

            warnings.append(
                "NO_FAULT_DETECTED_WITH_LIMITED_CONFIDENCE"
            )


        report = FaultDetectionReport(

            timestamp=
                timestamp,

            version=
                FAULT_DETECTION_VERSION,

            overall_state=
                overall_state,

            overall_severity=
                overall_severity,

            overall_fault_score=
                overall_fault_score,

            overall_confidence=
                overall_confidence,

            candidates=
                candidates,

            active_faults=
                active_faults,

            data_quality_issues=
                data_quality_issues,

            residual_coverage=
                residual_cov,

            sensor_coverage=
                sensor_cov,

            warnings=
                warnings,
        )


        _latest_report = (
            report
        )


        _detection_count += 1


        return report


    except Exception:

        _failed_detection_count += 1

        raise


def get_latest_fault_detection(
) -> Optional[Dict[str, Any]]:

    if _latest_report is None:

        return None


    return (
        _latest_report.to_dict()
    )


def get_fault_detection_status(
) -> Dict[str, Any]:

    return {

        "service":
            "fault_detection",

        "status":
            "READY",

        "version":
            FAULT_DETECTION_VERSION,

        "detection_count":
            _detection_count,

        "failed_detection_count":
            _failed_detection_count,

        "latest_result_available":
            _latest_report
            is not None,

        "latest_overall_state":
            (
                _latest_report
                .overall_state
                .value

                if _latest_report
                is not None

                else None
            ),

        "latest_overall_severity":
            (
                _latest_report
                .overall_severity
                .value

                if _latest_report
                is not None

                else None
            ),

        "latest_fault_count":
            (
                len(
                    _latest_report
                    .active_faults
                )

                if _latest_report
                is not None

                else None
            ),

        "latest_confidence":
            (
                _latest_report
                .overall_confidence

                if _latest_report
                is not None

                else None
            ),

        "timestamp":
            _utc_now().isoformat(),
    }


def reset_fault_detection(
) -> None:

    global _detection_count
    global _failed_detection_count
    global _latest_report


    _detection_count = 0

    _failed_detection_count = 0

    _latest_report = None


def get_fault_detection_info(
) -> Dict[str, Any]:

    return {

        "name":
            "PRATIRUP Fault Detection Engine",

        "version":
            FAULT_DETECTION_VERSION,

        "method":
            (
                "Evidence-based hybrid diagnostic "
                "rule engine"
            ),

        "inputs": [

            "sensor validation",

            "Digital Twin residuals",

            "observed state",

            "expected state",
        ],

        "fault_categories": [
            category.value
            for category
            in FaultCategory
        ],

        "states": [
            state.value
            for state
            in FaultState
        ],

        "severity_levels": [
            severity.value
            for severity
            in FaultSeverity
        ],

        "principles": [

            "missing data is not automatically a fault",

            "sensor-quality faults are separated from engine faults",

            "invalid sensors suppress dependent engine-fault inference",

            "Digital Twin residuals provide fault evidence",

            "correlated evidence increases diagnostic strength",

            "confidence decreases when diagnostic coverage is limited",
        ],

        "zero_is_valid":
            True,

        "none_means_unavailable":
            True,

        "official_vrde_thresholds":
            False,

        "validated_for_airworthiness":
            False,

        "engineering_disclaimer":
            (
                "PRATIRUP fault rules are demonstrator "
                "engineering rules and require calibration "
                "and validation against engine/test-rig data."
            ),
    }
