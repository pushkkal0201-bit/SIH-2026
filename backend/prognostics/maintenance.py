from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any, Dict, List, Optional


MAINTENANCE_VERSION = "1.0.0"


MIN_CONFIDENCE_FOR_ACTION = 0.30

HIGH_CONFIDENCE = 0.75
MEDIUM_CONFIDENCE = 0.50

CRITICAL_SAMPLE_PROJECTION = 1.0
LIMITED_SAMPLE_PROJECTION = 5.0


class MaintenanceState(str, Enum):
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    CONTINUE_MONITORING = "CONTINUE_MONITORING"
    INSPECT = "INSPECT"
    MAINTENANCE_REQUIRED = "MAINTENANCE_REQUIRED"
    IMMEDIATE_ATTENTION = "IMMEDIATE_ATTENTION"


class MaintenancePriority(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MaintenanceConfidenceLevel(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class MaintenanceAction:
    code: str
    subsystem: str
    action: str
    reason: str
    priority: MaintenancePriority
    confidence: float
    source: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "subsystem": self.subsystem,
            "action": self.action,
            "reason": self.reason,
            "priority": self.priority.value,
            "confidence": self.confidence,
            "confidence_percent": self.confidence * 100.0,
            "source": self.source,
        }


@dataclass
class MaintenanceReport:
    timestamp: datetime
    version: str

    state: MaintenanceState
    priority: MaintenancePriority

    confidence: float
    confidence_level: MaintenanceConfidenceLevel

    actions: List[MaintenanceAction]
    action_count: int

    limiting_channel: Optional[str]
    estimated_rul_hours: Optional[float]
    projected_samples_remaining: Optional[float]

    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "state": self.state.value,
            "priority": self.priority.value,
            "confidence": self.confidence,
            "confidence_percent": self.confidence * 100.0,
            "confidence_level": self.confidence_level.value,
            "actions": [item.to_dict() for item in self.actions],
            "action_count": self.action_count,
            "limiting_channel": self.limiting_channel,
            "estimated_rul_hours": self.estimated_rul_hours,
            "projected_samples_remaining": self.projected_samples_remaining,
            "warnings": list(self.warnings),
        }


_latest_report: Optional[MaintenanceReport] = None
_evaluation_count = 0
_failed_evaluation_count = 0


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_timestamp(value: Optional[datetime]) -> datetime:
    if value is None:
        return _utc_now()

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _numeric(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if not isfinite(number):
        return None

    return number


def _clamp01(value: Any) -> float:
    number = _numeric(value)

    if number is None:
        return 0.0

    return max(0.0, min(1.0, number))


def _confidence_level(value: float) -> MaintenanceConfidenceLevel:
    if value <= 0.0:
        return MaintenanceConfidenceLevel.NONE

    if value < MEDIUM_CONFIDENCE:
        return MaintenanceConfidenceLevel.LOW

    if value < HIGH_CONFIDENCE:
        return MaintenanceConfidenceLevel.MEDIUM

    return MaintenanceConfidenceLevel.HIGH


def _priority_rank(priority: MaintenancePriority) -> int:
    order = {
        MaintenancePriority.NONE: 0,
        MaintenancePriority.LOW: 1,
        MaintenancePriority.MEDIUM: 2,
        MaintenancePriority.HIGH: 3,
        MaintenancePriority.CRITICAL: 4,
    }

    return order[priority]


def _fault_confidence(report: Optional[Dict[str, Any]]) -> float:
    if not isinstance(report, dict):
        return 0.0

    return _clamp01(report.get("overall_confidence"))


def _degradation_confidence(report: Optional[Dict[str, Any]]) -> float:
    if not isinstance(report, dict):
        return 0.0

    return _clamp01(report.get("overall_confidence"))


def _rul_confidence(report: Optional[Dict[str, Any]]) -> float:
    if not isinstance(report, dict):
        return 0.0

    return _clamp01(report.get("confidence"))


def _faults(report: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict):
        return []

    values = report.get("active_faults")

    if not isinstance(values, list):
        return []

    return [item for item in values if isinstance(item, dict)]


def _degradation_evidence(
    report: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not isinstance(report, dict):
        return []

    values = report.get("evidence")

    if not isinstance(values, list):
        return []

    return [item for item in values if isinstance(item, dict)]


def _severity_to_priority(value: Any) -> MaintenancePriority:
    text = str(value or "").upper()

    if text == "CRITICAL":
        return MaintenancePriority.CRITICAL

    if text == "HIGH":
        return MaintenancePriority.HIGH

    if text == "MEDIUM":
        return MaintenancePriority.MEDIUM

    if text in {"LOW", "INFO"}:
        return MaintenancePriority.LOW

    return MaintenancePriority.NONE


def _channel_subsystem(channel: str) -> str:
    if not channel:
        return "unknown"

    return channel.split(".", 1)[0]


def _deduplicate_actions(
    actions: List[MaintenanceAction],
) -> List[MaintenanceAction]:

    best: Dict[str, MaintenanceAction] = {}

    for action in actions:
        key = f"{action.code}:{action.subsystem}"

        current = best.get(key)

        if current is None:
            best[key] = action
            continue

        if _priority_rank(action.priority) > _priority_rank(current.priority):
            best[key] = action

    return list(best.values())


def _actions_from_faults(
    fault_detection: Optional[Dict[str, Any]],
) -> List[MaintenanceAction]:

    actions: List[MaintenanceAction] = []

    confidence = _fault_confidence(fault_detection)

    for fault in _faults(fault_detection):

        state = str(fault.get("state") or "").upper()

        if state not in {"SUSPECTED", "DETECTED"}:
            continue

        code = str(
            fault.get("code")
            or fault.get("fault_code")
            or "FAULT_EVIDENCE"
        )

        category = str(
            fault.get("category")
            or "UNKNOWN"
        ).lower()

        severity = _severity_to_priority(fault.get("severity"))

        if severity == MaintenancePriority.NONE:
            severity = MaintenancePriority.MEDIUM

        if state == "SUSPECTED":
            action_text = (
                "Inspect the indicated subsystem and verify the supporting "
                "sensor and Digital Twin evidence."
            )
        else:
            action_text = (
                "Perform focused maintenance inspection of the indicated "
                "subsystem before relying on continued operation."
            )

        actions.append(
            MaintenanceAction(
                code=f"FAULT_{code}",
                subsystem=category,
                action=action_text,
                reason=(
                    f"Fault Detection reported {state} evidence "
                    f"for {code}."
                ),
                priority=severity,
                confidence=confidence,
                source="fault_detection",
            )
        )

    return actions


def _actions_from_degradation(
    degradation: Optional[Dict[str, Any]],
) -> List[MaintenanceAction]:

    actions: List[MaintenanceAction] = []

    overall_confidence = _degradation_confidence(degradation)

    for item in _degradation_evidence(degradation):

        trend = str(item.get("trend_direction") or "").upper()

        if trend != "DEGRADING":
            continue

        channel = str(item.get("channel") or "unknown")

        score = _numeric(item.get("current_score"))

        if score is None:
            continue

        severity = _severity_to_priority(item.get("severity"))

        if severity == MaintenancePriority.NONE:
            severity = MaintenancePriority.LOW

        channel_confidence = _clamp01(item.get("confidence"))

        confidence = (
            0.60 * overall_confidence
            + 0.40 * channel_confidence
        )

        actions.append(
            MaintenanceAction(
                code=f"DEGRADATION_{channel.upper().replace('.', '_')}",
                subsystem=_channel_subsystem(channel),
                action=(
                    "Inspect this channel/subsystem for progressive "
                    "degradation and compare with recent operating history."
                ),
                reason=(
                    f"Confirmed worsening degradation trend on {channel}; "
                    f"current degradation score={score:.3f}."
                ),
                priority=severity,
                confidence=_clamp01(confidence),
                source="degradation",
            )
        )

    return actions


def _actions_from_rul(
    rul: Optional[Dict[str, Any]],
) -> List[MaintenanceAction]:

    if not isinstance(rul, dict):
        return []

    state = str(rul.get("state") or "").upper()

    projected = _numeric(
        rul.get("projected_samples_remaining")
    )

    hours = _numeric(
        rul.get("estimated_rul_hours")
    )

    channel = str(
        rul.get("limiting_channel")
        or "unknown"
    )

    confidence = _rul_confidence(rul)

    actions: List[MaintenanceAction] = []

    if hours is not None:

        actions.append(
            MaintenanceAction(
                code="RUL_PHYSICAL_ESTIMATE",
                subsystem=_channel_subsystem(channel),
                action=(
                    "Review the limiting subsystem against the available "
                    "physical-time RUL estimate and plan maintenance."
                ),
                reason=(
                    f"Physical-time RUL estimate available: "
                    f"{hours:.2f} hours."
                ),
                priority=(
                    MaintenancePriority.HIGH
                    if state in {"LIMITED_LIFE", "CRITICAL"}
                    else MaintenancePriority.MEDIUM
                ),
                confidence=confidence,
                source="rul",
            )
        )

        return actions

    if projected is None:
        return actions

    if projected <= CRITICAL_SAMPLE_PROJECTION:

        priority = MaintenancePriority.CRITICAL

        action = (
            "Immediate engineering review is recommended because the "
            "sample-domain degradation projection is near its demonstrator "
            "end condition."
        )

    elif projected <= LIMITED_SAMPLE_PROJECTION:

        priority = MaintenancePriority.HIGH

        action = (
            "Schedule focused inspection of the limiting subsystem because "
            "the sample-domain degradation projection is short."
        )

    else:

        priority = MaintenancePriority.MEDIUM

        action = (
            "Continue enhanced monitoring and plan inspection of the "
            "limiting subsystem."
        )

    actions.append(
        MaintenanceAction(
            code="RUL_SAMPLE_PROJECTION",
            subsystem=_channel_subsystem(channel),
            action=action,
            reason=(
                f"Sample-domain projection={projected:.2f} samples "
                f"for limiting channel {channel}. This is not an "
                f"operating-hour estimate."
            ),
            priority=priority,
            confidence=confidence,
            source="rul",
        )
    )

    return actions


def _overall_priority(
    actions: List[MaintenanceAction],
) -> MaintenancePriority:

    if not actions:
        return MaintenancePriority.NONE

    return max(
        (item.priority for item in actions),
        key=_priority_rank,
    )


def _overall_state(
    *,
    actions: List[MaintenanceAction],
    confidence: float,
    evidence_available: bool,
) -> MaintenanceState:

    if not evidence_available:
        return MaintenanceState.INSUFFICIENT_DATA

    if not actions:
        return MaintenanceState.CONTINUE_MONITORING

    priority = _overall_priority(actions)

    if priority == MaintenancePriority.CRITICAL:
        return MaintenanceState.IMMEDIATE_ATTENTION

    if priority == MaintenancePriority.HIGH:
        return MaintenanceState.MAINTENANCE_REQUIRED

    if priority in {
        MaintenancePriority.MEDIUM,
        MaintenancePriority.LOW,
    }:
        return MaintenanceState.INSPECT

    if confidence < MIN_CONFIDENCE_FOR_ACTION:
        return MaintenanceState.INSUFFICIENT_DATA

    return MaintenanceState.CONTINUE_MONITORING


def recommend_maintenance(
    *,
    fault_detection: Optional[Dict[str, Any]] = None,
    degradation: Optional[Dict[str, Any]] = None,
    rul: Optional[Dict[str, Any]] = None,
    timestamp: Optional[datetime] = None,
) -> MaintenanceReport:

    global _latest_report
    global _evaluation_count
    global _failed_evaluation_count

    try:

        actions: List[MaintenanceAction] = []

        actions.extend(
            _actions_from_faults(fault_detection)
        )

        actions.extend(
            _actions_from_degradation(degradation)
        )

        actions.extend(
            _actions_from_rul(rul)
        )

        actions = _deduplicate_actions(actions)

        fault_conf = _fault_confidence(fault_detection)
        degradation_conf = _degradation_confidence(degradation)
        rul_conf = _rul_confidence(rul)

        confidence_sources = [
            value
            for value in (
                fault_conf,
                degradation_conf,
                rul_conf,
            )
            if value > 0.0
        ]

        if confidence_sources:
            confidence = sum(confidence_sources) / len(confidence_sources)
        else:
            confidence = 0.0

        confidence = _clamp01(confidence)

        fault_available = isinstance(fault_detection, dict)
        degradation_available = isinstance(degradation, dict)
        rul_available = isinstance(rul, dict)

        evidence_available = (
            fault_available
            or degradation_available
            or rul_available
        )

        priority = _overall_priority(actions)

        state = _overall_state(
            actions=actions,
            confidence=confidence,
            evidence_available=evidence_available,
        )

        warnings: List[str] = []

        if not evidence_available:
            warnings.append(
                "MAINTENANCE_EVIDENCE_UNAVAILABLE"
            )

        if confidence < MIN_CONFIDENCE_FOR_ACTION:
            warnings.append(
                "MAINTENANCE_CONFIDENCE_LOW"
            )

        if (
            isinstance(rul, dict)
            and rul.get("estimated_rul_hours") is None
        ):
            warnings.append(
                "PHYSICAL_RUL_HOURS_UNAVAILABLE"
            )

        if not actions and evidence_available:
            warnings.append(
                "NO_MAINTENANCE_ACTION_TRIGGERED"
            )

        limiting_channel = None
        estimated_rul_hours = None
        projected_samples_remaining = None

        if isinstance(rul, dict):
            limiting_channel = rul.get("limiting_channel")
            estimated_rul_hours = _numeric(
                rul.get("estimated_rul_hours")
            )
            projected_samples_remaining = _numeric(
                rul.get("projected_samples_remaining")
            )

        report = MaintenanceReport(
            timestamp=_normalize_timestamp(timestamp),
            version=MAINTENANCE_VERSION,
            state=state,
            priority=priority,
            confidence=confidence,
            confidence_level=_confidence_level(confidence),
            actions=actions,
            action_count=len(actions),
            limiting_channel=limiting_channel,
            estimated_rul_hours=estimated_rul_hours,
            projected_samples_remaining=projected_samples_remaining,
            warnings=warnings,
        )

        _latest_report = report
        _evaluation_count += 1

        return report

    except Exception:
        _failed_evaluation_count += 1
        raise


def get_latest_maintenance() -> Optional[Dict[str, Any]]:
    if _latest_report is None:
        return None

    return _latest_report.to_dict()


def get_maintenance_status() -> Dict[str, Any]:

    latest = get_latest_maintenance()

    return {
        "service": "maintenance_recommendation",
        "status": "READY",
        "version": MAINTENANCE_VERSION,
        "evaluation_count": _evaluation_count,
        "failed_evaluation_count": _failed_evaluation_count,
        "latest_result_available": latest is not None,
        "latest_state": (
            latest.get("state")
            if latest
            else None
        ),
        "latest_priority": (
            latest.get("priority")
            if latest
            else None
        ),
        "latest_action_count": (
            latest.get("action_count")
            if latest
            else None
        ),
        "latest_confidence": (
            latest.get("confidence")
            if latest
            else None
        ),
        "timestamp": _utc_now().isoformat(),
    }


def reset_maintenance() -> None:

    global _latest_report
    global _evaluation_count
    global _failed_evaluation_count

    _latest_report = None
    _evaluation_count = 0
    _failed_evaluation_count = 0


def get_maintenance_info() -> Dict[str, Any]:

    return {
        "service": "maintenance_recommendation",
        "version": MAINTENANCE_VERSION,

        "minimum_confidence_for_action":
            MIN_CONFIDENCE_FOR_ACTION,

        "critical_sample_projection":
            CRITICAL_SAMPLE_PROJECTION,

        "limited_sample_projection":
            LIMITED_SAMPLE_PROJECTION,

        "inputs": [
            "fault_detection",
            "degradation",
            "rul",
        ],

        "states": {
            "INSUFFICIENT_DATA":
                "Evidence is insufficient for a useful recommendation.",

            "CONTINUE_MONITORING":
                "No maintenance trigger is currently supported by evidence.",

            "INSPECT":
                "Evidence supports focused engineering inspection.",

            "MAINTENANCE_REQUIRED":
                "Strong evidence supports maintenance attention.",

            "IMMEDIATE_ATTENTION":
                "Critical demonstrator evidence requires immediate engineering review.",
        },

        "zero_is_valid": True,
        "none_means_unavailable": True,

        "missing_data_is_maintenance_trigger": False,

        "recalculates_faults": False,
        "recalculates_degradation": False,
        "recalculates_rul": False,

        "automatic_hardware_shutdown": False,
        "automatic_airworthiness_decision": False,

        "sample_projection_is_operating_hours": False,

        "official_drdo_vrde_maintenance_logic": False,
        "official_oem_maintenance_interval": False,
        "certified_maintenance_system": False,
        "validated_for_airworthiness": False,
    }
