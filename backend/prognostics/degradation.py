from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from statistics import mean
from typing import Any, Deque, Dict, List, Optional, Tuple


DEGRADATION_VERSION = "1.0.1"


MAX_HISTORY_PER_CHANNEL = 120

MIN_HISTORY_FOR_TREND = 6

MIN_HISTORY_FOR_PERSISTENCE = 5

TREND_WINDOW = 12


LOW_DEGRADATION_SCORE = 0.25

MODERATE_DEGRADATION_SCORE = 0.45

HIGH_DEGRADATION_SCORE = 0.70

CRITICAL_DEGRADATION_SCORE = 0.90


MIN_TREND_INCREASE = 0.08


PERSISTENCE_RATIO_THRESHOLD = 0.60


class DegradationState(str, Enum):

    NORMAL = "NORMAL"

    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

    EARLY_DEGRADATION = "EARLY_DEGRADATION"

    DEGRADING = "DEGRADING"

    SEVERE_DEGRADATION = "SEVERE_DEGRADATION"


class DegradationSeverity(str, Enum):

    NONE = "NONE"

    INFO = "INFO"

    LOW = "LOW"

    MEDIUM = "MEDIUM"

    HIGH = "HIGH"

    CRITICAL = "CRITICAL"


class TrendDirection(str, Enum):

    UNKNOWN = "UNKNOWN"

    STABLE = "STABLE"

    IMPROVING = "IMPROVING"

    DEGRADING = "DEGRADING"


TRACKED_CHANNELS: Tuple[str, ...] = (

    "engine.rpm",

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

    "electrical.alternator_current_a",
)


@dataclass
class DegradationEvidence:

    channel: str

    current_score: Optional[float]

    historical_mean: Optional[float]

    trend_delta: Optional[float]

    trend_direction: TrendDirection

    persistence_ratio: Optional[float]

    severity: DegradationSeverity

    confidence: float

    samples: int

    reasons: List[str] = field(
        default_factory=list
    )

    def to_dict(self) -> Dict[str, Any]:

        return {

            "channel":
                self.channel,

            "current_score":
                self.current_score,

            "historical_mean":
                self.historical_mean,

            "trend_delta":
                self.trend_delta,

            "trend_direction":
                self.trend_direction.value,

            "persistence_ratio":
                self.persistence_ratio,

            "severity":
                self.severity.value,

            "confidence":
                self.confidence,

            "confidence_percent":
                self.confidence * 100.0,

            "samples":
                self.samples,

            "reasons":
                list(self.reasons),
        }


@dataclass
class DegradationReport:

    timestamp: datetime

    version: str

    overall_state: DegradationState

    overall_severity: DegradationSeverity

    overall_score: float

    overall_confidence: float

    evidence: List[DegradationEvidence]

    degrading_channels: List[str]

    tracked_channels: int

    historical_channels: int

    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:

        return {

            "timestamp":
                self.timestamp.isoformat(),

            "version":
                self.version,

            "overall_state":
                self.overall_state.value,

            "overall_severity":
                self.overall_severity.value,

            "overall_score":
                self.overall_score,

            "overall_score_percent":
                self.overall_score * 100.0,

            "overall_confidence":
                self.overall_confidence,

            "overall_confidence_percent":
                self.overall_confidence * 100.0,

            "evidence": [
                item.to_dict()
                for item in self.evidence
            ],

            "degrading_channels":
                list(self.degrading_channels),

            "degrading_channel_count":
                len(self.degrading_channels),

            "tracked_channels":
                self.tracked_channels,

            "historical_channels":
                self.historical_channels,

            "warnings":
                list(self.warnings),
        }


_history: Dict[
    str,
    Deque[Tuple[datetime, float]]
] = {

    channel: deque(
        maxlen=MAX_HISTORY_PER_CHANNEL
    )

    for channel in TRACKED_CHANNELS
}


_latest_report: Optional[
    DegradationReport
] = None


_tracking_count = 0

_failed_tracking_count = 0


def _utc_now() -> datetime:

    return datetime.now(
        timezone.utc
    )


def _normalize_timestamp(
    timestamp: Optional[datetime],
) -> datetime:

    if timestamp is None:

        return _utc_now()

    if timestamp.tzinfo is None:

        return timestamp.replace(
            tzinfo=timezone.utc
        )

    return timestamp


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

        number = float(value)

    except (
        TypeError,
        ValueError,
    ):

        return None

    if not isfinite(number):

        return None

    return number


def _clamp01(
    value: Any,
) -> float:

    number = _numeric(value)

    if number is None:

        return 0.0

    return max(
        0.0,
        min(
            1.0,
            number,
        ),
    )


def _residual_entries(
    residual_state: Optional[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    if not isinstance(
        residual_state,
        dict,
    ):

        return {}

    residuals = residual_state.get(
        "residuals"
    )

    if not isinstance(
        residuals,
        dict,
    ):

        return {}

    return residuals


def _residual_score(
    residual_state: Optional[
        Dict[str, Any]
    ],
    channel: str,
) -> Optional[float]:

    residuals = _residual_entries(
        residual_state
    )

    entry = residuals.get(
        channel
    )

    if not isinstance(
        entry,
        dict,
    ):

        return None

    if entry.get(
        "available"
    ) is False:

        return None

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

        return None

    return _clamp01(score)


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

    return _clamp01(
        residual_state.get(
            "confidence"
        )
    )


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

        return _clamp01(
            coverage.get(
                "fraction"
            )
        )

    return _clamp01(
        coverage
    )


def _sensor_results(
    sensor_validation: Optional[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    if not isinstance(
        sensor_validation,
        dict,
    ):

        return {}

    results = sensor_validation.get(
        "results"
    )

    if not isinstance(
        results,
        dict,
    ):

        return {}

    return results


def _sensor_is_usable(
    sensor_validation: Optional[
        Dict[str, Any]
    ],
    channel: str,
) -> bool:

    results = _sensor_results(
        sensor_validation
    )

    result = results.get(
        channel
    )

    if result is None:

        return True

    if not isinstance(
        result,
        dict,
    ):

        return False

    return (
        str(
            result.get(
                "status",
                "",
            )
        ).upper()
        == "VALID"
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

    return _clamp01(

        sensor_validation.get(

            "overall_quality",

            sensor_validation.get(
                "quality"
            ),
        )
    )


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

    coverage = sensor_validation.get(
        "coverage"
    )

    if isinstance(
        coverage,
        dict,
    ):

        return _clamp01(
            coverage.get(
                "fraction"
            )
        )

    return _clamp01(
        coverage
    )


def _anomaly_score_for_channel(
    anomaly_detection: Optional[
        Dict[str, Any]
    ],
    channel: str,
) -> float:

    if not isinstance(
        anomaly_detection,
        dict,
    ):

        return 0.0

    anomalies = anomaly_detection.get(
        "anomalies"
    )

    if not isinstance(
        anomalies,
        list,
    ):

        return 0.0

    highest = 0.0

    for anomaly in anomalies:

        if not isinstance(
            anomaly,
            dict,
        ):

            continue

        if anomaly.get(
            "channel"
        ) != channel:

            continue

        score = _numeric(
            anomaly.get(
                "score"
            )
        )

        if score is None:

            score = _numeric(
                anomaly.get(
                    "anomaly_score"
                )
            )

        if score is not None:

            highest = max(
                highest,
                _clamp01(score),
            )

    return highest


def _anomaly_confidence(
    anomaly_detection: Optional[
        Dict[str, Any]
    ],
) -> float:

    if not isinstance(
        anomaly_detection,
        dict,
    ):

        return 0.0

    return _clamp01(
        anomaly_detection.get(
            "overall_confidence"
        )
    )


def _history_values(
    channel: str,
) -> List[float]:

    history = _history.get(
        channel
    )

    if history is None:

        return []

    return [
        value
        for _, value
        in history
    ]


def _historical_mean(
    values: List[float],
) -> Optional[float]:

    if not values:

        return None

    return float(
        mean(values)
    )


def _calculate_trend(
    values: List[float],
) -> Tuple[
    Optional[float],
    TrendDirection,
]:

    if len(values) < MIN_HISTORY_FOR_TREND:

        return (
            None,
            TrendDirection.UNKNOWN,
        )

    recent = values[
        -TREND_WINDOW:
    ]

    midpoint = (
        len(recent)
        // 2
    )

    if midpoint < 2:

        return (
            None,
            TrendDirection.UNKNOWN,
        )

    older = recent[
        :midpoint
    ]

    newer = recent[
        midpoint:
    ]

    if (
        not older
        or
        not newer
    ):

        return (
            None,
            TrendDirection.UNKNOWN,
        )

    older_mean = mean(
        older
    )

    newer_mean = mean(
        newer
    )

    delta = float(
        newer_mean
        - older_mean
    )

    if delta >= MIN_TREND_INCREASE:

        direction = (
            TrendDirection.DEGRADING
        )

    elif delta <= -MIN_TREND_INCREASE:

        direction = (
            TrendDirection.IMPROVING
        )

    else:

        direction = (
            TrendDirection.STABLE
        )

    return (
        delta,
        direction,
    )


def _persistence_ratio(
    values: List[float],
) -> Optional[float]:

    if (
        len(values)
        < MIN_HISTORY_FOR_PERSISTENCE
    ):

        return None

    recent = values[
        -TREND_WINDOW:
    ]

    degraded = sum(

        1

        for value in recent

        if value
        >= LOW_DEGRADATION_SCORE
    )

    return (
        degraded
        / len(recent)
    )


def _combined_channel_score(
    *,
    residual_score: Optional[float],
    anomaly_score: float,
) -> Optional[float]:

    if residual_score is None:

        return None

    residual = _clamp01(
        residual_score
    )

    anomaly = _clamp01(
        anomaly_score
    )

    combined = (

        0.80
        * residual

        +

        0.20
        * anomaly
    )

    return _clamp01(
        combined
    )


def _severity_from_score(
    score: Optional[float],
) -> DegradationSeverity:

    if score is None:

        return (
            DegradationSeverity.NONE
        )

    if score >= CRITICAL_DEGRADATION_SCORE:

        return (
            DegradationSeverity.CRITICAL
        )

    if score >= HIGH_DEGRADATION_SCORE:

        return (
            DegradationSeverity.HIGH
        )

    if score >= MODERATE_DEGRADATION_SCORE:

        return (
            DegradationSeverity.MEDIUM
        )

    if score >= LOW_DEGRADATION_SCORE:

        return (
            DegradationSeverity.LOW
        )

    return (
        DegradationSeverity.NONE
    )


def _severity_rank(
    severity: DegradationSeverity,
) -> int:

    ranks = {

        DegradationSeverity.NONE:
            0,

        DegradationSeverity.INFO:
            1,

        DegradationSeverity.LOW:
            2,

        DegradationSeverity.MEDIUM:
            3,

        DegradationSeverity.HIGH:
            4,

        DegradationSeverity.CRITICAL:
            5,
    }

    return ranks[
        severity
    ]


def _analyze_channel(
    *,
    channel: str,
    current_score: float,
    anomaly_score: float,
    residual_confidence: float,
    sensor_validation: Optional[
        Dict[str, Any]
    ],
) -> DegradationEvidence:

    history_values = (
        _history_values(
            channel
        )
    )

    historical_mean = (
        _historical_mean(
            history_values
        )
    )

    (
        trend_delta,
        trend_direction,
    ) = _calculate_trend(
        history_values
    )

    persistence = (
        _persistence_ratio(
            history_values
        )
    )

    severity = (
        _severity_from_score(
            current_score
        )
    )

    reasons: List[str] = []


    if (
        current_score
        >= LOW_DEGRADATION_SCORE
    ):

        reasons.append(
            "CURRENT_DEVIATION_ELEVATED"
        )


    if (
        trend_direction
        == TrendDirection.DEGRADING
    ):

        reasons.append(
            "DEGRADATION_TREND_INCREASING"
        )


    if (
        persistence is not None

        and

        persistence
        >= PERSISTENCE_RATIO_THRESHOLD
    ):

        reasons.append(
            "DEGRADATION_PERSISTENT"
        )


    if (
        anomaly_score
        >= MODERATE_DEGRADATION_SCORE
    ):

        reasons.append(
            "ANOMALY_EVIDENCE_PRESENT"
        )


    sample_factor = min(

        1.0,

        len(history_values)
        /
        float(
            MIN_HISTORY_FOR_TREND
        ),
    )


    sensor_results = (
        _sensor_results(
            sensor_validation
        )
    )

    sensor_result = (
        sensor_results.get(
            channel
        )
    )

    channel_sensor_quality = 1.0

    if isinstance(
        sensor_result,
        dict,
    ):

        quality = _numeric(
            sensor_result.get(
                "quality"
            )
        )

        if quality is not None:

            channel_sensor_quality = (
                _clamp01(
                    quality
                )
            )


    confidence = _clamp01(

        0.45
        * residual_confidence

        +

        0.35
        * sample_factor

        +

        0.20
        * channel_sensor_quality
    )


    if (
        persistence is not None

        and

        persistence
        >= PERSISTENCE_RATIO_THRESHOLD

        and

        trend_direction
        == TrendDirection.DEGRADING
    ):

        if (
            severity
            == DegradationSeverity.LOW
        ):

            severity = (
                DegradationSeverity.MEDIUM
            )

        elif (
            severity
            == DegradationSeverity.MEDIUM
        ):

            severity = (
                DegradationSeverity.HIGH
            )


    return DegradationEvidence(

        channel=
            channel,

        current_score=
            current_score,

        historical_mean=
            historical_mean,

        trend_delta=
            trend_delta,

        trend_direction=
            trend_direction,

        persistence_ratio=
            persistence,

        severity=
            severity,

        confidence=
            confidence,

        samples=
            len(history_values),

        reasons=
            reasons,
    )


def _overall_state(
    *,
    evidence: List[
        DegradationEvidence
    ],
    historical_channels: int,
) -> Tuple[
    DegradationState,
    DegradationSeverity,
    float,
]:

    if not evidence:

        return (
            DegradationState.INSUFFICIENT_DATA,
            DegradationSeverity.NONE,
            0.0,
        )


    overall_score = max(

        (
            item.current_score
            or 0.0
        )

        for item in evidence
    )


    overall_severity = max(

        (
            item.severity
            for item in evidence
        ),

        key=_severity_rank,
    )


    trending_degradation = [

        item

        for item in evidence

        if (
            item.trend_direction
            == TrendDirection.DEGRADING
        )
    ]


    persistent_degrading = [

        item

        for item in trending_degradation

        if (
            item.persistence_ratio
            is not None

            and

            item.persistence_ratio
            >= PERSISTENCE_RATIO_THRESHOLD
        )
    ]


    severe_temporal_evidence = [

        item

        for item in persistent_degrading

        if item.severity in (

            DegradationSeverity.HIGH,

            DegradationSeverity.CRITICAL,
        )
    ]


    if severe_temporal_evidence:

        state = (
            DegradationState.SEVERE_DEGRADATION
        )


    elif trending_degradation:

        state = (
            DegradationState.DEGRADING
        )


    elif (
        overall_score
        >= LOW_DEGRADATION_SCORE
    ):

        state = (
            DegradationState.EARLY_DEGRADATION
        )


    elif (
        historical_channels
        < 1
    ):

        state = (
            DegradationState.INSUFFICIENT_DATA
        )


    else:

        state = (
            DegradationState.NORMAL
        )


    return (
        state,

        overall_severity,

        _clamp01(
            overall_score
        ),
    )


def track_degradation(
    *,
    residual_state: Optional[
        Dict[str, Any]
    ] = None,
    anomaly_detection: Optional[
        Dict[str, Any]
    ] = None,
    sensor_validation: Optional[
        Dict[str, Any]
    ] = None,
    timestamp: Optional[
        datetime
    ] = None,
) -> DegradationReport:

    global _latest_report
    global _tracking_count
    global _failed_tracking_count

    current_timestamp = (
        _normalize_timestamp(
            timestamp
        )
    )

    try:

        residual_confidence = (
            _residual_confidence(
                residual_state
            )
        )

        residual_coverage = (
            _residual_coverage(
                residual_state
            )
        )

        sensor_quality = (
            _sensor_quality(
                sensor_validation
            )
        )

        sensor_coverage = (
            _sensor_coverage(
                sensor_validation
            )
        )

        anomaly_confidence = (
            _anomaly_confidence(
                anomaly_detection
            )
        )


        evidence: List[
            DegradationEvidence
        ] = []

        pending_history: List[
            Tuple[str, float]
        ] = []


        for channel in TRACKED_CHANNELS:

            if not _sensor_is_usable(
                sensor_validation,
                channel,
            ):

                continue


            residual_score = (
                _residual_score(
                    residual_state,
                    channel,
                )
            )

            if residual_score is None:

                continue


            anomaly_score = (
                _anomaly_score_for_channel(
                    anomaly_detection,
                    channel,
                )
            )


            combined_score = (
                _combined_channel_score(

                    residual_score=
                        residual_score,

                    anomaly_score=
                        anomaly_score,
                )
            )

            if combined_score is None:

                continue


            item = _analyze_channel(

                channel=
                    channel,

                current_score=
                    combined_score,

                anomaly_score=
                    anomaly_score,

                residual_confidence=
                    residual_confidence,

                sensor_validation=
                    sensor_validation,
            )

            evidence.append(
                item
            )

            pending_history.append(
                (
                    channel,
                    combined_score,
                )
            )


        historical_channels = sum(

            1

            for channel in TRACKED_CHANNELS

            if len(
                _history[channel]
            )
            >= MIN_HISTORY_FOR_TREND
        )


        (
            state,
            severity,
            overall_score,
        ) = _overall_state(

            evidence=
                evidence,

            historical_channels=
                historical_channels,
        )


        history_coverage = (

            historical_channels

            /

            len(
                TRACKED_CHANNELS
            )
        )


        overall_confidence = (
            _clamp01(

                0.30
                * residual_confidence

                +

                0.20
                * residual_coverage

                +

                0.20
                * sensor_quality

                +

                0.10
                * sensor_coverage

                +

                0.10
                * anomaly_confidence

                +

                0.10
                * history_coverage
            )
        )


        degrading_channels = [

            item.channel

            for item in evidence

            if (

                item.severity
                not in (

                    DegradationSeverity.NONE,

                    DegradationSeverity.INFO,
                )

                or

                item.trend_direction
                == TrendDirection.DEGRADING
            )
        ]


        warnings: List[str] = []


        if historical_channels == 0:

            warnings.append(
                "DEGRADATION_HISTORY_LIMITED"
            )


        if residual_coverage < 0.50:

            warnings.append(
                "DEGRADATION_RESIDUAL_COVERAGE_LOW"
            )


        if sensor_coverage < 0.50:

            warnings.append(
                "DEGRADATION_SENSOR_COVERAGE_LOW"
            )


        if overall_confidence < 0.50:

            warnings.append(
                "DEGRADATION_CONFIDENCE_LOW"
            )


        if not evidence:

            warnings.append(
                "DEGRADATION_EVIDENCE_UNAVAILABLE"
            )


        report = DegradationReport(

            timestamp=
                current_timestamp,

            version=
                DEGRADATION_VERSION,

            overall_state=
                state,

            overall_severity=
                severity,

            overall_score=
                overall_score,

            overall_confidence=
                overall_confidence,

            evidence=
                evidence,

            degrading_channels=
                degrading_channels,

            tracked_channels=
                len(
                    TRACKED_CHANNELS
                ),

            historical_channels=
                historical_channels,

            warnings=
                warnings,
        )


        for (
            channel,
            score,
        ) in pending_history:

            _history[
                channel
            ].append(
                (
                    current_timestamp,
                    score,
                )
            )


        _latest_report = report

        _tracking_count += 1

        return report


    except Exception:

        _failed_tracking_count += 1

        raise


def get_latest_degradation(
) -> Optional[Dict[str, Any]]:

    if _latest_report is None:

        return None

    return (
        _latest_report.to_dict()
    )


def get_degradation_status(
) -> Dict[str, Any]:

    historical_channels = sum(

        1

        for channel in TRACKED_CHANNELS

        if len(
            _history[channel]
        )
        > 0
    )

    mature_channels = sum(

        1

        for channel in TRACKED_CHANNELS

        if len(
            _history[channel]
        )
        >= MIN_HISTORY_FOR_TREND
    )


    return {

        "service":
            "degradation_tracking",

        "status":
            "READY",

        "version":
            DEGRADATION_VERSION,

        "tracking_count":
            _tracking_count,

        "failed_tracking_count":
            _failed_tracking_count,

        "latest_result_available":
            _latest_report
            is not None,

        "latest_overall_state":
            (
                _latest_report
                .overall_state
                .value

                if _latest_report
                else None
            ),

        "latest_overall_severity":
            (
                _latest_report
                .overall_severity
                .value

                if _latest_report
                else None
            ),

        "latest_degrading_channels":
            (
                len(
                    _latest_report
                    .degrading_channels
                )

                if _latest_report
                else None
            ),

        "latest_confidence":
            (
                _latest_report
                .overall_confidence

                if _latest_report
                else None
            ),

        "configured_channels":
            len(
                TRACKED_CHANNELS
            ),

        "historical_channels":
            historical_channels,

        "mature_historical_channels":
            mature_channels,

        "timestamp":
            _utc_now().isoformat(),
    }


def reset_degradation(
) -> None:

    global _latest_report
    global _tracking_count
    global _failed_tracking_count


    for history in _history.values():

        history.clear()


    _latest_report = None

    _tracking_count = 0

    _failed_tracking_count = 0


def get_degradation_info(
) -> Dict[str, Any]:

    return {

        "service":
            "degradation_tracking",

        "version":
            DEGRADATION_VERSION,

        "configured_channels":
            len(
                TRACKED_CHANNELS
            ),

        "history_per_channel":
            MAX_HISTORY_PER_CHANNEL,

        "minimum_history_for_trend":
            MIN_HISTORY_FOR_TREND,

        "minimum_history_for_persistence":
            MIN_HISTORY_FOR_PERSISTENCE,

        "trend_window":
            TREND_WINDOW,

        "low_degradation_score":
            LOW_DEGRADATION_SCORE,

        "moderate_degradation_score":
            MODERATE_DEGRADATION_SCORE,

        "high_degradation_score":
            HIGH_DEGRADATION_SCORE,

        "critical_degradation_score":
            CRITICAL_DEGRADATION_SCORE,

        "minimum_trend_increase":
            MIN_TREND_INCREASE,

        "persistence_ratio_threshold":
            PERSISTENCE_RATIO_THRESHOLD,

        "score_fusion": {

            "residual_weight":
                0.80,

            "anomaly_weight":
                0.20,
        },

        "state_model": {

            "normal":
                "No meaningful degradation evidence.",

            "early_degradation":
                "Elevated current degradation without confirmed worsening trend.",

            "degrading":
                "Confirmed increasing temporal degradation trend.",

            "severe_degradation":
                "Persistent increasing degradation with HIGH or CRITICAL severity.",
        },

        "current_sample_excluded_from_own_baseline":
            True,

        "sensor_quality_gate":
            True,

        "zero_is_valid":
            True,

        "none_means_unavailable":
            True,

        "missing_data_is_degradation":
            False,

        "anomaly_is_not_degradation":
            True,

        "single_high_residual_is_confirmed_degradation":
            False,

        "fault_detection_required":
            False,

        "rul_estimation_in_this_module":
            False,

        "official_vrde_thresholds":
            False,

        "validated_for_airworthiness":
            False,
    }
