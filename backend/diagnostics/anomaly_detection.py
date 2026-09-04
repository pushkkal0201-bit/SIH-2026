from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from math import isfinite, sqrt
from statistics import mean
from typing import Any, Deque, Dict, List, Optional, Tuple


ANOMALY_DETECTION_VERSION = "1.0.1"


class AnomalySeverity(str, Enum):
    NONE = "NONE"
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnomalyType(str, Enum):
    SPIKE = "SPIKE"
    DRIFT = "DRIFT"
    PERSISTENT_DEVIATION = "PERSISTENT_DEVIATION"
    RATE_CHANGE = "RATE_CHANGE"
    MULTI_SENSOR = "MULTI_SENSOR"
    RESIDUAL = "RESIDUAL"
    DATA_QUALITY = "DATA_QUALITY"
    UNKNOWN = "UNKNOWN"


class AnomalyState(str, Enum):
    NORMAL = "NORMAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    SUSPECTED = "SUSPECTED"
    DETECTED = "DETECTED"


@dataclass
class AnomalyEvidence:
    channel: str
    anomaly_type: str
    score: float
    severity: str
    description: str
    current_value: Optional[float] = None
    baseline_value: Optional[float] = None
    deviation: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel,
            "anomaly_type": self.anomaly_type,
            "score": self.score,
            "score_percent": self.score * 100.0,
            "severity": self.severity,
            "description": self.description,
            "current_value": self.current_value,
            "baseline_value": self.baseline_value,
            "deviation": self.deviation,
        }


@dataclass
class AnomalyReport:
    timestamp: str
    version: str
    overall_state: str
    overall_severity: str
    overall_score: float
    overall_confidence: float
    anomalies: List[AnomalyEvidence]
    anomaly_count: int
    analyzed_channels: int
    historical_channels: int
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "version": self.version,
            "overall_state": self.overall_state,
            "overall_severity": self.overall_severity,
            "overall_score": self.overall_score,
            "overall_score_percent": self.overall_score * 100.0,
            "overall_confidence": self.overall_confidence,
            "overall_confidence_percent": (
                self.overall_confidence * 100.0
            ),
            "anomalies": [
                item.to_dict()
                for item in self.anomalies
            ],
            "anomaly_count": self.anomaly_count,
            "analyzed_channels": self.analyzed_channels,
            "historical_channels": self.historical_channels,
            "warnings": self.warnings,
        }


MAX_HISTORY_PER_CHANNEL = 60

MIN_HISTORY_FOR_BASELINE = 5

SPIKE_Z_THRESHOLD = 3.0

DRIFT_SCORE_THRESHOLD = 0.55

PERSISTENCE_SCORE_THRESHOLD = 0.60

RESIDUAL_SCORE_THRESHOLD = 0.65


LOW_SCORE = 0.35
MEDIUM_SCORE = 0.55
HIGH_SCORE = 0.75
CRITICAL_SCORE = 0.92


CHANNEL_PATHS = (
    "engine.rpm",
    "engine.throttle_percent",
    "engine.load_percent",
    "engine.power_kw",
    "engine.torque_nm",

    "cht.cylinder1_c",
    "cht.cylinder2_c",
    "cht.cylinder3_c",
    "cht.cylinder4_c",

    "egt.cylinder1_c",
    "egt.cylinder2_c",
    "egt.cylinder3_c",
    "egt.cylinder4_c",

    "oil.pressure_kpa",
    "oil.temperature_c",

    "fuel.flow_kg_per_second",
    "fuel.pressure_kpa",

    "vibration.overall_g",

    "electrical.battery_voltage_v",
    "electrical.alternator_voltage_v",

    "environment.altitude_m",
    "environment.ambient_temperature_c",
    "environment.ambient_pressure_kpa",
)


_history: Dict[
    str,
    Deque[Tuple[datetime, float]]
] = defaultdict(
    lambda: deque(
        maxlen=MAX_HISTORY_PER_CHANNEL
    )
)


_latest_report: Optional[
    AnomalyReport
] = None


_detection_count = 0

_failed_detection_count = 0


def _utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


def _parse_timestamp(
    value: Any,
) -> datetime:

    if isinstance(
        value,
        datetime,
    ):

        if value.tzinfo is None:
            return value.replace(
                tzinfo=timezone.utc
            )

        return value

    if isinstance(
        value,
        str,
    ):

        try:

            parsed = datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00",
                )
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            return parsed

        except ValueError:
            pass

    return _utc_now()


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

    if not isinstance(
        value,
        (int, float),
    ):
        return None

    result = float(
        value
    )

    if not isfinite(
        result
    ):
        return None

    return result


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


def _nested_get(
    data: Optional[Dict[str, Any]],
    path: str,
) -> Any:

    if not isinstance(
        data,
        dict,
    ):
        return None

    current: Any = data

    for part in path.split("."):

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


def _sensor_is_usable(
    sensor_validation: Optional[
        Dict[str, Any]
    ],
    path: str,
) -> bool:

    if not isinstance(
        sensor_validation,
        dict,
    ):
        return True

    results = sensor_validation.get(
        "results"
    )

    if not isinstance(
        results,
        dict,
    ):
        return True

    entry = results.get(
        path
    )

    if not isinstance(
        entry,
        dict,
    ):
        return True

    status = str(
        entry.get(
            "status",
            "",
        )
    ).upper()

    if not status:
        return True

    return status == "VALID"


def _severity(
    score: float,
) -> str:

    if score >= CRITICAL_SCORE:
        return (
            AnomalySeverity
            .CRITICAL
            .value
        )

    if score >= HIGH_SCORE:
        return (
            AnomalySeverity
            .HIGH
            .value
        )

    if score >= MEDIUM_SCORE:
        return (
            AnomalySeverity
            .MEDIUM
            .value
        )

    if score >= LOW_SCORE:
        return (
            AnomalySeverity
            .LOW
            .value
        )

    if score > 0:
        return (
            AnomalySeverity
            .INFO
            .value
        )

    return (
        AnomalySeverity
        .NONE
        .value
    )


def _standard_deviation(
    values: List[float],
) -> float:

    if len(values) < 2:
        return 0.0

    average = mean(
        values
    )

    variance = sum(
        (
            value
            - average
        ) ** 2
        for value in values
    ) / len(values)

    return sqrt(
        variance
    )


def _detect_spike(
    path: str,
    current_value: float,
) -> Optional[AnomalyEvidence]:

    history = _history[
        path
    ]

    if (
        len(history)
        <
        MIN_HISTORY_FOR_BASELINE
    ):
        return None

    values = [
        value
        for _, value in history
    ]

    baseline = mean(
        values
    )

    sigma = _standard_deviation(
        values
    )

    absolute_change = abs(
        current_value
        - baseline
    )


    if sigma <= 1e-9:

        baseline_scale = max(
            abs(
                baseline
            ),
            1.0,
        )

        relative_change = (
            absolute_change
            /
            baseline_scale
        )

        absolute_floor = max(
            baseline_scale
            * 0.01,
            1e-6,
        )

        if (
            relative_change
            < 0.05
            or
            absolute_change
            < absolute_floor
        ):
            return None


        score = _clamp01(
            (
                relative_change
                - 0.05
            )
            /
            0.20
        )

        score = max(
            score,
            LOW_SCORE,
        )

        return AnomalyEvidence(
            channel=path,

            anomaly_type=(
                AnomalyType
                .SPIKE
                .value
            ),

            score=score,

            severity=_severity(
                score
            ),

            description=(
                "Current value changed sharply from a "
                "previously stable channel baseline."
            ),

            current_value=(
                current_value
            ),

            baseline_value=(
                baseline
            ),

            deviation=(
                current_value
                - baseline
            ),
        )


    z_score = (
        absolute_change
        /
        sigma
    )

    if (
        z_score
        <
        SPIKE_Z_THRESHOLD
    ):
        return None

    score = _clamp01(
        z_score
        / 6.0
    )

    return AnomalyEvidence(
        channel=path,

        anomaly_type=(
            AnomalyType
            .SPIKE
            .value
        ),

        score=score,

        severity=_severity(
            score
        ),

        description=(
            "Current value deviates sharply from recent "
            "channel baseline."
        ),

        current_value=(
            current_value
        ),

        baseline_value=(
            baseline
        ),

        deviation=(
            current_value
            - baseline
        ),
    )


def _detect_drift(
    path: str,
    current_value: float,
) -> Optional[AnomalyEvidence]:

    history = _history[
        path
    ]

    if len(history) < 8:
        return None

    values = [
        value
        for _, value in history
    ]

    half = max(
        3,
        len(values) // 2,
    )

    older = values[
        :half
    ]

    newer = values[
        -half:
    ]

    older_mean = mean(
        older
    )

    newer_mean = mean(
        newer
    )

    scale = max(
        abs(
            older_mean
        ),
        1.0,
    )

    relative_shift = (
        abs(
            newer_mean
            - older_mean
        )
        /
        scale
    )


    if relative_shift < 0.05:
        return None


    score = _clamp01(
        relative_shift
        / 0.20
    )


    if (
        score
        <
        DRIFT_SCORE_THRESHOLD
    ):
        return None


    return AnomalyEvidence(
        channel=path,

        anomaly_type=(
            AnomalyType
            .DRIFT
            .value
        ),

        score=score,

        severity=_severity(
            score
        ),

        description=(
            "Recent channel baseline is drifting from its "
            "earlier baseline."
        ),

        current_value=(
            current_value
        ),

        baseline_value=(
            older_mean
        ),

        deviation=(
            newer_mean
            - older_mean
        ),
    )


def _detect_residual_anomalies(
    residual_state: Optional[
        Dict[str, Any]
    ],
) -> List[AnomalyEvidence]:

    anomalies: List[
        AnomalyEvidence
    ] = []

    if not isinstance(
        residual_state,
        dict,
    ):
        return anomalies

    residuals = residual_state.get(
        "residuals"
    )

    if not isinstance(
        residuals,
        dict,
    ):
        return anomalies


    for path, entry in residuals.items():

        if not isinstance(
            entry,
            dict,
        ):
            continue


        if (
            entry.get(
                "available"
            )
            is not True
        ):
            continue


        score = _numeric(
            entry.get(
                "deviation_score"
            )
        )


        if score is None:

            score = _numeric(
                entry.get(
                    "normalized_magnitude"
                )
            )


        if score is None:
            continue


        score = _clamp01(
            score
        )


        if (
            score
            <
            RESIDUAL_SCORE_THRESHOLD
        ):
            continue


        observed = _numeric(
            entry.get(
                "observed"
            )
        )

        expected = _numeric(
            entry.get(
                "expected"
            )
        )

        deviation = _numeric(
            entry.get(
                "absolute"
            )
        )


        anomalies.append(
            AnomalyEvidence(
                channel=path,

                anomaly_type=(
                    AnomalyType
                    .RESIDUAL
                    .value
                ),

                score=score,

                severity=_severity(
                    score
                ),

                description=(
                    "Observed Digital Twin state deviates "
                    "significantly from the expected "
                    "physics-based state."
                ),

                current_value=(
                    observed
                ),

                baseline_value=(
                    expected
                ),

                deviation=(
                    deviation
                ),
            )
        )


    return anomalies


def _detect_multi_sensor_anomaly(
    anomalies: List[
        AnomalyEvidence
    ],
) -> Optional[AnomalyEvidence]:

    meaningful = [
        item
        for item in anomalies
        if (
            item.score
            >=
            MEDIUM_SCORE
        )
    ]

    channels = {
        item.channel
        for item in meaningful
    }


    if len(channels) < 2:
        return None


    score = _clamp01(
        mean(
            item.score
            for item in meaningful
        )
        + 0.10
    )


    return AnomalyEvidence(
        channel=(
            "multi_sensor"
        ),

        anomaly_type=(
            AnomalyType
            .MULTI_SENSOR
            .value
        ),

        score=score,

        severity=_severity(
            score
        ),

        description=(
            "Multiple channels show correlated unusual "
            "behavior."
        ),

        current_value=None,

        baseline_value=None,

        deviation=None,
    )


def detect_anomalies(
    *,
    observed_state: Optional[
        Dict[str, Any]
    ] = None,

    residual_state: Optional[
        Dict[str, Any]
    ] = None,

    sensor_validation: Optional[
        Dict[str, Any]
    ] = None,

    timestamp: Any = None,

) -> AnomalyReport:

    global _latest_report
    global _detection_count
    global _failed_detection_count


    try:

        now = _parse_timestamp(
            timestamp
        )

        anomalies: List[
            AnomalyEvidence
        ] = []

        analyzed_channels = 0


        if isinstance(
            observed_state,
            dict,
        ):

            for path in CHANNEL_PATHS:

                value = _numeric(
                    _nested_get(
                        observed_state,
                        path,
                    )
                )


                if value is None:
                    continue


                if not _sensor_is_usable(
                    sensor_validation,
                    path,
                ):
                    continue


                analyzed_channels += 1


                spike = _detect_spike(
                    path,
                    value,
                )

                if spike is not None:

                    anomalies.append(
                        spike
                    )


                drift = _detect_drift(
                    path,
                    value,
                )

                if drift is not None:

                    anomalies.append(
                        drift
                    )


        residual_anomalies = (
            _detect_residual_anomalies(
                residual_state
            )
        )

        anomalies.extend(
            residual_anomalies
        )


        multi_sensor = (
            _detect_multi_sensor_anomaly(
                anomalies
            )
        )

        if multi_sensor is not None:

            anomalies.append(
                multi_sensor
            )


        if isinstance(
            observed_state,
            dict,
        ):

            for path in CHANNEL_PATHS:

                value = _numeric(
                    _nested_get(
                        observed_state,
                        path,
                    )
                )

                if value is None:
                    continue

                if not _sensor_is_usable(
                    sensor_validation,
                    path,
                ):
                    continue


                _history[
                    path
                ].append(
                    (
                        now,
                        value,
                    )
                )


        if anomalies:

            overall_score = max(
                item.score
                for item in anomalies
            )

        else:

            overall_score = 0.0


        historical_channels = sum(
            1
            for path in CHANNEL_PATHS
            if (
                len(
                    _history[path]
                )
                >=
                MIN_HISTORY_FOR_BASELINE
            )
        )


        if CHANNEL_PATHS:

            temporal_coverage = (
                historical_channels
                /
                len(
                    CHANNEL_PATHS
                )
            )

        else:

            temporal_coverage = 0.0


        residual_confidence = 0.0

        if isinstance(
            residual_state,
            dict,
        ):

            value = _numeric(
                residual_state.get(
                    "confidence"
                )
            )

            if value is not None:

                residual_confidence = (
                    _clamp01(
                        value
                    )
                )


        sensor_quality = 0.0

        if isinstance(
            sensor_validation,
            dict,
        ):

            value = _numeric(
                sensor_validation.get(
                    "overall_quality"
                )
            )

            if value is not None:

                sensor_quality = (
                    _clamp01(
                        value
                    )
                )


        confidence = _clamp01(
            (
                temporal_coverage
                * 0.45
            )
            +
            (
                sensor_quality
                * 0.30
            )
            +
            (
                residual_confidence
                * 0.25
            )
        )


        if (
            analyzed_channels == 0
            and
            not residual_anomalies
        ):

            overall_state = (
                AnomalyState
                .INSUFFICIENT_DATA
                .value
            )


        elif (
            overall_score
            >=
            HIGH_SCORE
        ):

            overall_state = (
                AnomalyState
                .DETECTED
                .value
            )


        elif (
            overall_score
            >=
            MEDIUM_SCORE
        ):

            overall_state = (
                AnomalyState
                .SUSPECTED
                .value
            )


        else:

            overall_state = (
                AnomalyState
                .NORMAL
                .value
            )


        warnings: List[
            str
        ] = []


        if historical_channels < 3:

            warnings.append(
                "ANOMALY_HISTORY_LIMITED"
            )


        if confidence < 0.50:

            warnings.append(
                "ANOMALY_CONFIDENCE_LOW"
            )


        if analyzed_channels < 3:

            warnings.append(
                "ANOMALY_SENSOR_COVERAGE_LOW"
            )


        if (
            not anomalies
            and
            confidence < 0.50
        ):

            warnings.append(
                "NO_ANOMALY_DETECTED_WITH_LIMITED_CONFIDENCE"
            )


        report = AnomalyReport(

            timestamp=(
                now.isoformat()
            ),

            version=(
                ANOMALY_DETECTION_VERSION
            ),

            overall_state=(
                overall_state
            ),

            overall_severity=(
                _severity(
                    overall_score
                )
            ),

            overall_score=(
                overall_score
            ),

            overall_confidence=(
                confidence
            ),

            anomalies=(
                anomalies
            ),

            anomaly_count=(
                len(
                    anomalies
                )
            ),

            analyzed_channels=(
                analyzed_channels
            ),

            historical_channels=(
                historical_channels
            ),

            warnings=(
                warnings
            ),
        )


        _latest_report = report

        _detection_count += 1


        return report


    except Exception:

        _failed_detection_count += 1

        raise


def get_latest_anomaly_detection(
) -> Optional[Dict[str, Any]]:

    if _latest_report is None:
        return None

    return (
        _latest_report
        .to_dict()
    )


def get_anomaly_detection_status(
) -> Dict[str, Any]:

    latest = (
        _latest_report.to_dict()
        if _latest_report
        else None
    )


    return {

        "service":
            "anomaly_detection",

        "status":
            "READY",

        "version":
            ANOMALY_DETECTION_VERSION,

        "detection_count":
            _detection_count,

        "failed_detection_count":
            _failed_detection_count,

        "latest_result_available":
            latest is not None,

        "latest_overall_state":
            (
                latest.get(
                    "overall_state"
                )
                if latest
                else None
            ),

        "latest_overall_severity":
            (
                latest.get(
                    "overall_severity"
                )
                if latest
                else None
            ),

        "latest_anomaly_count":
            (
                latest.get(
                    "anomaly_count"
                )
                if latest
                else None
            ),

        "latest_confidence":
            (
                latest.get(
                    "overall_confidence"
                )
                if latest
                else None
            ),

        "historical_channels":
            sum(
                1
                for path in CHANNEL_PATHS
                if (
                    len(
                        _history[path]
                    )
                    >=
                    MIN_HISTORY_FOR_BASELINE
                )
            ),

        "timestamp":
            _utc_now().isoformat(),
    }


def reset_anomaly_detection(
) -> None:

    global _latest_report
    global _detection_count
    global _failed_detection_count


    _history.clear()

    _latest_report = None

    _detection_count = 0

    _failed_detection_count = 0


def get_anomaly_detection_info(
) -> Dict[str, Any]:

    return {

        "name":
            "PRATIRUP Anomaly Detection Engine",

        "version":
            ANOMALY_DETECTION_VERSION,

        "method":
            (
                "Temporal telemetry + Digital Twin residual "
                "anomaly detection"
            ),

        "supported_types":
            [
                item.value
                for item in AnomalyType
            ],

        "states":
            [
                item.value
                for item in AnomalyState
            ],

        "severities":
            [
                item.value
                for item in AnomalySeverity
            ],

        "configured_channels":
            len(
                CHANNEL_PATHS
            ),

        "history_per_channel":
            MAX_HISTORY_PER_CHANNEL,

        "minimum_history":
            MIN_HISTORY_FOR_BASELINE,

        "spike_z_threshold":
            SPIKE_Z_THRESHOLD,

        "residual_score_threshold":
            RESIDUAL_SCORE_THRESHOLD,

        "constant_baseline_detection":
            True,

        "current_sample_excluded_from_own_baseline":
            True,

        "sensor_quality_gate":
            True,

        "zero_is_valid":
            True,

        "none_means_unavailable":
            True,

        "missing_data_is_anomaly":
            False,

        "anomaly_is_not_fault":
            True,

        "official_vrde_thresholds":
            False,

        "validated_for_airworthiness":
            False,
    }
