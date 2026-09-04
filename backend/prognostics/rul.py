from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any, Dict, List, Optional, Tuple


RUL_VERSION = "1.0.0"


MIN_HISTORY_FOR_RUL = 8

MIN_CONFIDENCE_FOR_RUL = 0.30

MIN_DEGRADATION_SCORE_FOR_RUL = 0.25

MIN_POSITIVE_TREND_DELTA = 0.08


MAX_DEMONSTRATOR_RUL_HOURS = 500.0


DEMONSTRATOR_END_SCORE = 1.0


PHYSICAL_TIME_BASE_AVAILABLE = False


class RULState(str, Enum):

    UNAVAILABLE = "UNAVAILABLE"

    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

    STABLE = "STABLE"

    ESTIMATING = "ESTIMATING"

    LIMITED_LIFE = "LIMITED_LIFE"

    CRITICAL = "CRITICAL"


class RULConfidenceLevel(str, Enum):

    NONE = "NONE"

    LOW = "LOW"

    MEDIUM = "MEDIUM"

    HIGH = "HIGH"


@dataclass
class ChannelRULEstimate:

    channel: str

    available: bool

    current_degradation_score: Optional[float]

    trend_delta: Optional[float]

    trend_direction: str

    persistence_ratio: Optional[float]

    historical_samples: int

    projected_samples_remaining: Optional[float]

    estimated_rul_hours: Optional[float]

    confidence: float

    confidence_level: RULConfidenceLevel

    reasons: List[str] = field(
        default_factory=list
    )

    def to_dict(self) -> Dict[str, Any]:

        return {

            "channel":
                self.channel,

            "available":
                self.available,

            "current_degradation_score":
                self.current_degradation_score,

            "trend_delta":
                self.trend_delta,

            "trend_direction":
                self.trend_direction,

            "persistence_ratio":
                self.persistence_ratio,

            "historical_samples":
                self.historical_samples,

            "projected_samples_remaining":
                self.projected_samples_remaining,

            "estimated_rul_hours":
                self.estimated_rul_hours,

            "confidence":
                self.confidence,

            "confidence_percent":
                self.confidence * 100.0,

            "confidence_level":
                self.confidence_level.value,

            "reasons":
                list(self.reasons),
        }


@dataclass
class RULReport:

    timestamp: datetime

    version: str

    state: RULState

    estimated_rul_hours: Optional[float]

    projected_samples_remaining: Optional[float]

    limiting_channel: Optional[str]

    confidence: float

    confidence_level: RULConfidenceLevel

    channel_estimates: List[ChannelRULEstimate]

    available_channel_count: int

    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:

        return {

            "timestamp":
                self.timestamp.isoformat(),

            "version":
                self.version,

            "state":
                self.state.value,

            "estimated_rul_hours":
                self.estimated_rul_hours,

            "projected_samples_remaining":
                self.projected_samples_remaining,

            "limiting_channel":
                self.limiting_channel,

            "confidence":
                self.confidence,

            "confidence_percent":
                self.confidence * 100.0,

            "confidence_level":
                self.confidence_level.value,

            "channel_estimates": [
                item.to_dict()
                for item in self.channel_estimates
            ],

            "available_channel_count":
                self.available_channel_count,

            "warnings":
                list(self.warnings),
        }


_latest_report: Optional[RULReport] = None

_estimation_count = 0

_failed_estimation_count = 0


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


def _integer(
    value: Any,
) -> Optional[int]:

    number = _numeric(value)

    if number is None:

        return None

    if number < 0:

        return None

    return int(number)


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


def _confidence_level(
    confidence: float,
) -> RULConfidenceLevel:

    confidence = _clamp01(
        confidence
    )

    if confidence <= 0.0:

        return RULConfidenceLevel.NONE

    if confidence < 0.50:

        return RULConfidenceLevel.LOW

    if confidence < 0.75:

        return RULConfidenceLevel.MEDIUM

    return RULConfidenceLevel.HIGH


def _degradation_evidence(
    degradation_report: Optional[
        Dict[str, Any]
    ],
) -> List[Dict[str, Any]]:

    if not isinstance(
        degradation_report,
        dict,
    ):

        return []

    evidence = degradation_report.get(
        "evidence"
    )

    if not isinstance(
        evidence,
        list,
    ):

        return []

    return [
        item
        for item in evidence
        if isinstance(
            item,
            dict,
        )
    ]


def _degradation_confidence(
    degradation_report: Optional[
        Dict[str, Any]
    ],
) -> float:

    if not isinstance(
        degradation_report,
        dict,
    ):

        return 0.0

    return _clamp01(
        degradation_report.get(
            "overall_confidence"
        )
    )


def _degradation_state(
    degradation_report: Optional[
        Dict[str, Any]
    ],
) -> str:

    if not isinstance(
        degradation_report,
        dict,
    ):

        return ""

    return str(
        degradation_report.get(
            "overall_state",
            "",
        )
    ).upper()


def _project_samples_remaining(
    *,
    current_score: float,
    trend_delta: float,
) -> Optional[float]:

    current_score = _clamp01(
        current_score
    )

    trend = _numeric(
        trend_delta
    )

    if trend is None:

        return None

    if trend <= 0.0:

        return None

    remaining_score = max(
        0.0,
        DEMONSTRATOR_END_SCORE
        - current_score,
    )

    if remaining_score <= 0.0:

        return 0.0

    samples_remaining = (
        remaining_score
        / trend
    )

    if not isfinite(
        samples_remaining
    ):

        return None

    return max(
        0.0,
        samples_remaining,
    )


def _estimate_channel(
    *,
    evidence: Dict[str, Any],
    overall_degradation_confidence: float,
) -> ChannelRULEstimate:

    channel = str(
        evidence.get(
            "channel",
            "unknown",
        )
    )

    score = _numeric(
        evidence.get(
            "current_score"
        )
    )

    trend_delta = _numeric(
        evidence.get(
            "trend_delta"
        )
    )

    trend_direction = str(
        evidence.get(
            "trend_direction",
            "UNKNOWN",
        )
    ).upper()

    persistence = _numeric(
        evidence.get(
            "persistence_ratio"
        )
    )

    samples = _integer(
        evidence.get(
            "samples"
        )
    )

    if samples is None:

        samples = 0

    channel_confidence = _clamp01(
        evidence.get(
            "confidence"
        )
    )

    reasons: List[str] = []


    if score is None:

        reasons.append(
            "DEGRADATION_SCORE_UNAVAILABLE"
        )

        return ChannelRULEstimate(
            channel=channel,
            available=False,
            current_degradation_score=None,
            trend_delta=trend_delta,
            trend_direction=trend_direction,
            persistence_ratio=persistence,
            historical_samples=samples,
            projected_samples_remaining=None,
            estimated_rul_hours=None,
            confidence=0.0,
            confidence_level=RULConfidenceLevel.NONE,
            reasons=reasons,
        )


    if samples < MIN_HISTORY_FOR_RUL:

        reasons.append(
            "RUL_HISTORY_INSUFFICIENT"
        )


    if score < MIN_DEGRADATION_SCORE_FOR_RUL:

        reasons.append(
            "DEGRADATION_BELOW_RUL_THRESHOLD"
        )


    if trend_direction != "DEGRADING":

        reasons.append(
            "WORSENING_TREND_NOT_CONFIRMED"
        )


    if (
        trend_delta is None
        or
        trend_delta < MIN_POSITIVE_TREND_DELTA
    ):

        reasons.append(
            "DEGRADATION_RATE_INSUFFICIENT"
        )


    sample_factor = min(
        1.0,
        samples
        / float(
            MIN_HISTORY_FOR_RUL
        ),
    )

    persistence_factor = (
        _clamp01(
            persistence
        )
        if persistence is not None
        else 0.0
    )

    confidence = _clamp01(

        0.45
        * overall_degradation_confidence

        +

        0.30
        * channel_confidence

        +

        0.15
        * sample_factor

        +

        0.10
        * persistence_factor
    )


    eligible = (

        samples
        >= MIN_HISTORY_FOR_RUL

        and

        score
        >= MIN_DEGRADATION_SCORE_FOR_RUL

        and

        trend_direction
        == "DEGRADING"

        and

        trend_delta
        is not None

        and

        trend_delta
        >= MIN_POSITIVE_TREND_DELTA

        and

        confidence
        >= MIN_CONFIDENCE_FOR_RUL
    )


    if not eligible:

        if (
            confidence
            < MIN_CONFIDENCE_FOR_RUL
        ):

            reasons.append(
                "RUL_CONFIDENCE_INSUFFICIENT"
            )

        return ChannelRULEstimate(

            channel=
                channel,

            available=
                False,

            current_degradation_score=
                score,

            trend_delta=
                trend_delta,

            trend_direction=
                trend_direction,

            persistence_ratio=
                persistence,

            historical_samples=
                samples,

            projected_samples_remaining=
                None,

            estimated_rul_hours=
                None,

            confidence=
                confidence,

            confidence_level=
                _confidence_level(
                    confidence
                ),

            reasons=
                reasons,
        )


    projected_samples = (
        _project_samples_remaining(

            current_score=
                score,

            trend_delta=
                trend_delta,
        )
    )


    if projected_samples is None:

        reasons.append(
            "RUL_PROJECTION_UNAVAILABLE"
        )

        return ChannelRULEstimate(

            channel=
                channel,

            available=
                False,

            current_degradation_score=
                score,

            trend_delta=
                trend_delta,

            trend_direction=
                trend_direction,

            persistence_ratio=
                persistence,

            historical_samples=
                samples,

            projected_samples_remaining=
                None,

            estimated_rul_hours=
                None,

            confidence=
                confidence,

            confidence_level=
                _confidence_level(
                    confidence
                ),

            reasons=
                reasons,
        )


    estimated_hours: Optional[
        float
    ] = None


    if PHYSICAL_TIME_BASE_AVAILABLE:

        estimated_hours = min(
            projected_samples,
            MAX_DEMONSTRATOR_RUL_HOURS,
        )

    else:

        reasons.append(
            "PHYSICAL_TIME_BASE_UNAVAILABLE"
        )


    reasons.append(
        "SAMPLE_DOMAIN_RUL_ESTIMATE_AVAILABLE"
    )


    return ChannelRULEstimate(

        channel=
            channel,

        available=
            True,

        current_degradation_score=
            score,

        trend_delta=
            trend_delta,

        trend_direction=
            trend_direction,

        persistence_ratio=
            persistence,

        historical_samples=
            samples,

        projected_samples_remaining=
            projected_samples,

        estimated_rul_hours=
            estimated_hours,

        confidence=
            confidence,

        confidence_level=
            _confidence_level(
                confidence
            ),

        reasons=
            reasons,
    )


def _select_limiting_estimate(
    estimates: List[
        ChannelRULEstimate
    ],
) -> Optional[
    ChannelRULEstimate
]:

    available = [

        item

        for item in estimates

        if (
            item.available

            and

            item.projected_samples_remaining
            is not None
        )
    ]

    if not available:

        return None

    return min(

        available,

        key=lambda item:
            item.projected_samples_remaining
            if item.projected_samples_remaining
            is not None
            else float("inf"),
    )


def _determine_state(
    *,
    degradation_state: str,
    limiting_estimate: Optional[
        ChannelRULEstimate
    ],
    evidence_exists: bool,
) -> RULState:

    if not evidence_exists:

        return (
            RULState.INSUFFICIENT_DATA
        )

    if limiting_estimate is None:

        if degradation_state in (
            "NORMAL",
            "",
        ):

            return RULState.STABLE

        return (
            RULState.INSUFFICIENT_DATA
        )

    remaining = (
        limiting_estimate
        .projected_samples_remaining
    )

    if remaining is None:

        return (
            RULState.INSUFFICIENT_DATA
        )

    if remaining <= 1.0:

        return RULState.CRITICAL

    if remaining <= 5.0:

        return RULState.LIMITED_LIFE

    return RULState.ESTIMATING


def estimate_rul(
    *,
    degradation_report: Optional[
        Dict[str, Any]
    ] = None,
    timestamp: Optional[
        datetime
    ] = None,
) -> RULReport:

    global _latest_report
    global _estimation_count
    global _failed_estimation_count

    current_timestamp = (
        _normalize_timestamp(
            timestamp
        )
    )

    try:

        evidence = (
            _degradation_evidence(
                degradation_report
            )
        )

        degradation_confidence = (
            _degradation_confidence(
                degradation_report
            )
        )

        degradation_state = (
            _degradation_state(
                degradation_report
            )
        )


        channel_estimates = [

            _estimate_channel(

                evidence=item,

                overall_degradation_confidence=
                    degradation_confidence,
            )

            for item in evidence
        ]


        limiting = (
            _select_limiting_estimate(
                channel_estimates
            )
        )


        state = _determine_state(

            degradation_state=
                degradation_state,

            limiting_estimate=
                limiting,

            evidence_exists=
                bool(evidence),
        )


        if limiting is not None:

            projected_samples = (
                limiting
                .projected_samples_remaining
            )

            estimated_hours = (
                limiting
                .estimated_rul_hours
            )

            limiting_channel = (
                limiting.channel
            )

            confidence = (
                limiting.confidence
            )

        else:

            projected_samples = None

            estimated_hours = None

            limiting_channel = None

            confidence = min(

                degradation_confidence,

                0.49,
            )


        warnings: List[str] = []


        if not evidence:

            warnings.append(
                "RUL_DEGRADATION_EVIDENCE_UNAVAILABLE"
            )


        mature_evidence = any(

            item.historical_samples
            >= MIN_HISTORY_FOR_RUL

            for item in channel_estimates
        )


        if (
            evidence
            and
            not mature_evidence
        ):

            warnings.append(
                "RUL_HISTORY_INSUFFICIENT"
            )


        if (
            confidence
            < MIN_CONFIDENCE_FOR_RUL
        ):

            warnings.append(
                "RUL_CONFIDENCE_LOW"
            )


        if (
            not PHYSICAL_TIME_BASE_AVAILABLE
        ):

            warnings.append(
                "RUL_PHYSICAL_TIME_BASE_UNAVAILABLE"
            )


        if (
            projected_samples is None
        ):

            warnings.append(
                "RUL_PROJECTION_UNAVAILABLE"
            )


        if estimated_hours is None:

            warnings.append(
                "RUL_HOURS_UNAVAILABLE"
            )


        report = RULReport(

            timestamp=
                current_timestamp,

            version=
                RUL_VERSION,

            state=
                state,

            estimated_rul_hours=
                estimated_hours,

            projected_samples_remaining=
                projected_samples,

            limiting_channel=
                limiting_channel,

            confidence=
                _clamp01(
                    confidence
                ),

            confidence_level=
                _confidence_level(
                    confidence
                ),

            channel_estimates=
                channel_estimates,

            available_channel_count=
                sum(
                    1
                    for item
                    in channel_estimates
                    if item.available
                ),

            warnings=
                warnings,
        )


        _latest_report = report

        _estimation_count += 1

        return report


    except Exception:

        _failed_estimation_count += 1

        raise


def get_latest_rul(
) -> Optional[Dict[str, Any]]:

    if _latest_report is None:

        return None

    return (
        _latest_report.to_dict()
    )


def get_rul_status(
) -> Dict[str, Any]:

    return {

        "service":
            "rul_estimation",

        "status":
            "READY",

        "version":
            RUL_VERSION,

        "estimation_count":
            _estimation_count,

        "failed_estimation_count":
            _failed_estimation_count,

        "latest_result_available":
            _latest_report
            is not None,

        "latest_state":
            (
                _latest_report
                .state
                .value

                if _latest_report
                else None
            ),

        "latest_rul_hours":
            (
                _latest_report
                .estimated_rul_hours

                if _latest_report
                else None
            ),

        "latest_projected_samples_remaining":
            (
                _latest_report
                .projected_samples_remaining

                if _latest_report
                else None
            ),

        "latest_limiting_channel":
            (
                _latest_report
                .limiting_channel

                if _latest_report
                else None
            ),

        "latest_confidence":
            (
                _latest_report
                .confidence

                if _latest_report
                else None
            ),

        "timestamp":
            _utc_now().isoformat(),
    }


def reset_rul(
) -> None:

    global _latest_report
    global _estimation_count
    global _failed_estimation_count

    _latest_report = None

    _estimation_count = 0

    _failed_estimation_count = 0


def get_rul_info(
) -> Dict[str, Any]:

    return {

        "service":
            "rul_estimation",

        "version":
            RUL_VERSION,

        "minimum_history_for_rul":
            MIN_HISTORY_FOR_RUL,

        "minimum_confidence_for_rul":
            MIN_CONFIDENCE_FOR_RUL,

        "minimum_degradation_score_for_rul":
            MIN_DEGRADATION_SCORE_FOR_RUL,

        "minimum_positive_trend_delta":
            MIN_POSITIVE_TREND_DELTA,

        "demonstrator_end_score":
            DEMONSTRATOR_END_SCORE,

        "maximum_demonstrator_rul_hours":
            MAX_DEMONSTRATOR_RUL_HOURS,

        "physical_time_base_available":
            PHYSICAL_TIME_BASE_AVAILABLE,

        "sample_domain_projection_supported":
            True,

        "physical_hour_projection_supported":
            PHYSICAL_TIME_BASE_AVAILABLE,

        "requires_degradation_evidence":
            True,

        "requires_confirmed_worsening_trend":
            True,

        "single_residual_can_generate_rul":
            False,

        "single_anomaly_can_generate_rul":
            False,

        "zero_is_valid":
            True,

        "none_means_unavailable":
            True,

        "missing_data_generates_rul":
            False,

        "official_vrde_life_model":
            False,

        "certified_maintenance_interval":
            False,

        "validated_for_airworthiness":
            False,
    }
