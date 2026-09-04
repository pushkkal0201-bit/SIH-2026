from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.models.schemas import MissionReadinessResult
from backend.mission.readiness import (
    MissionReadinessReport,
    ReadinessState,
)


OPERATOR_READINESS_ADAPTER_VERSION = "1.0.0"
OPERATOR_READINESS_ADAPTER_SERVICE = "operator_readiness_adapter"


def _clamp_percent(value: Optional[float]) -> float:
    if value is None:
        return 0.0

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0

    return max(0.0, min(100.0, numeric))


def _operator_label(
    state: ReadinessState,
) -> str:
    mapping = {
        ReadinessState.READY:
            "GO",

        ReadinessState.READY_WITH_CAUTION:
            "CAUTION",

        ReadinessState.NOT_READY:
            "NO-GO",

        ReadinessState.INSUFFICIENT_DATA:
            "UNKNOWN",
    }

    return mapping.get(
        state,
        "UNKNOWN",
    )


def _propulsion_health_risk(
    report: MissionReadinessReport,
) -> float:
    score = report.readiness_score_percent

    if score is None:
        return 0.0

    return _clamp_percent(
        100.0 - score
    )


def _mission_risk(
    report: MissionReadinessReport,
) -> float:

    if report.state == ReadinessState.INSUFFICIENT_DATA:
        return 100.0

    return _propulsion_health_risk(
        report
    )


def _reasons(
    report: MissionReadinessReport,
) -> List[str]:
    reasons: List[str] = []

    for factor in report.factors:
        description = getattr(
            factor,
            "description",
            None,
        )

        if description:
            reasons.append(
                str(description)
            )

    for warning in report.warnings:
        warning_text = str(warning)

        if warning_text not in reasons:
            reasons.append(
                warning_text
            )

    if (
        report.state
        == ReadinessState.INSUFFICIENT_DATA
    ):
        reasons.insert(
            0,
            "INSUFFICIENT DATA: Mission readiness cannot be determined confidently from the available evidence.",
        )

    if (
        report.state
        == ReadinessState.NOT_READY
    ):
        reasons.insert(
            0,
            "Positive blocking engine-health evidence requires engineering review before mission release.",
        )

    return reasons


def _recommendation(
    report: MissionReadinessReport,
) -> str:
    if report.state == ReadinessState.READY:
        return (
            "GO recommendation from the PRATIRUP engineering "
            "readiness demonstrator. Final mission release "
            "remains the responsibility of authorized personnel."
        )

    if (
        report.state
        == ReadinessState.READY_WITH_CAUTION
    ):
        return (
            "CAUTION: Review the reported non-blocking health "
            "or maintenance evidence before mission release."
        )

    if report.state == ReadinessState.NOT_READY:
        return (
            "NO-GO recommendation: Blocking engine-health "
            "evidence requires engineering review and corrective "
            "action before mission release."
        )

    return (
        "INSUFFICIENT DATA: Acquire adequate trustworthy "
        "telemetry and health evidence before making a mission "
        "readiness decision."
    )


def build_operator_readiness(
    report: MissionReadinessReport,
    *,
    environmental_risk: float = 0.0,
) -> MissionReadinessResult:

    if not isinstance(
        report,
        MissionReadinessReport,
    ):
        raise TypeError(
            "report must be a MissionReadinessReport"
        )

    return MissionReadinessResult(
        readiness=_operator_label(
            report.state
        ),

        mission_risk=_mission_risk(
            report
        ),

        propulsion_health_risk=
            _propulsion_health_risk(
                report
            ),

        environmental_risk=
            _clamp_percent(
                environmental_risk
            ),

        reasons=_reasons(
            report
        ),

        recommendation=
            _recommendation(
                report
            ),

        flight_authorization=False,
    )


def get_operator_readiness_info() -> Dict[str, Any]:
    return {
        "service":
            OPERATOR_READINESS_ADAPTER_SERVICE,

        "version":
            OPERATOR_READINESS_ADAPTER_VERSION,

        "architecture":
            "PRESENTATION_MAPPING_ONLY",

        "authoritative_source":
            "backend.mission.readiness",

        "state_mapping": {
            "READY":
                "GO",

            "READY_WITH_CAUTION":
                "CAUTION",

            "NOT_READY":
                "NO-GO",

            "INSUFFICIENT_DATA":
                "UNKNOWN",
        },

        "automatic_flight_authorization":
            False,

        "notes": [
            (
                "GO/CAUTION/NO-GO are engineering "
                "decision-support labels."
            ),
            (
                "UNKNOWN is used when readiness evidence "
                "is insufficient."
            ),
            (
                "This adapter does not run health, fault, "
                "degradation, RUL, or maintenance models."
            ),
        ],
    }
