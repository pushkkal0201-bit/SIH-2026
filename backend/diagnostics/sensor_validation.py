from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any, Dict, List, Mapping, Optional, Tuple


SENSOR_VALIDATION_VERSION = "1.0.0"


class SensorStatus(str, Enum):
    VALID = "VALID"
    MISSING = "MISSING"
    INVALID = "INVALID"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    RATE_VIOLATION = "RATE_VIOLATION"
    FROZEN = "FROZEN"
    INCONSISTENT = "INCONSISTENT"


@dataclass(frozen=True)
class SensorRule:
    path: str
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    max_rate_per_second: Optional[float] = None
    frozen_tolerance: float = 0.0
    frozen_samples: int = 5
    required: bool = False


@dataclass
class SensorValidationResult:
    path: str
    value: Optional[float]
    status: SensorStatus
    valid: bool
    quality: float
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "value": self.value,
            "status": self.status.value,
            "valid": self.valid,
            "quality": self.quality,
            "quality_percent": self.quality * 100.0,
            "reasons": list(self.reasons),
        }


@dataclass
class SensorValidationReport:
    timestamp: datetime
    results: Dict[str, SensorValidationResult]
    overall_quality: float
    coverage: float
    valid_channels: int
    available_channels: int
    configured_channels: int
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "version": SENSOR_VALIDATION_VERSION,
            "results": {
                path: result.to_dict()
                for path, result in self.results.items()
            },
            "overall_quality": self.overall_quality,
            "overall_quality_percent": self.overall_quality * 100.0,
            "coverage": self.coverage,
            "coverage_percent": self.coverage * 100.0,
            "valid_channels": self.valid_channels,
            "available_channels": self.available_channels,
            "configured_channels": self.configured_channels,
            "warnings": list(self.warnings),
        }


DEFAULT_SENSOR_RULES: Dict[str, SensorRule] = {

    "engine.rpm": SensorRule(
        path="engine.rpm",
        minimum=0.0,
        maximum=5000.0,
        max_rate_per_second=4000.0,
        frozen_tolerance=1.0,
        frozen_samples=8,
        required=True,
    ),

    "engine.throttle_percent": SensorRule(
        path="engine.throttle_percent",
        minimum=0.0,
        maximum=100.0,
        max_rate_per_second=300.0,
        frozen_tolerance=0.05,
        frozen_samples=12,
        required=True,
    ),

    "engine.load_percent": SensorRule(
        path="engine.load_percent",
        minimum=0.0,
        maximum=100.0,
        max_rate_per_second=300.0,
        frozen_tolerance=0.05,
        frozen_samples=12,
        required=True,
    ),

    "engine.power_kw": SensorRule(
        path="engine.power_kw",
        minimum=0.0,
        maximum=180.0,
        max_rate_per_second=300.0,
    ),

    "engine.torque_nm": SensorRule(
        path="engine.torque_nm",
        minimum=0.0,
        maximum=1000.0,
        max_rate_per_second=2000.0,
    ),

    "cht.cylinder1_c": SensorRule(
        path="cht.cylinder1_c",
        minimum=-50.0,
        maximum=350.0,
        max_rate_per_second=80.0,
        frozen_tolerance=0.1,
    ),

    "cht.cylinder2_c": SensorRule(
        path="cht.cylinder2_c",
        minimum=-50.0,
        maximum=350.0,
        max_rate_per_second=80.0,
        frozen_tolerance=0.1,
    ),

    "cht.cylinder3_c": SensorRule(
        path="cht.cylinder3_c",
        minimum=-50.0,
        maximum=350.0,
        max_rate_per_second=80.0,
        frozen_tolerance=0.1,
    ),

    "cht.cylinder4_c": SensorRule(
        path="cht.cylinder4_c",
        minimum=-50.0,
        maximum=350.0,
        max_rate_per_second=80.0,
        frozen_tolerance=0.1,
    ),

    "egt.cylinder1_c": SensorRule(
        path="egt.cylinder1_c",
        minimum=-50.0,
        maximum=1100.0,
        max_rate_per_second=300.0,
        frozen_tolerance=0.2,
    ),

    "egt.cylinder2_c": SensorRule(
        path="egt.cylinder2_c",
        minimum=-50.0,
        maximum=1100.0,
        max_rate_per_second=300.0,
        frozen_tolerance=0.2,
    ),

    "egt.cylinder3_c": SensorRule(
        path="egt.cylinder3_c",
        minimum=-50.0,
        maximum=1100.0,
        max_rate_per_second=300.0,
        frozen_tolerance=0.2,
    ),

    "egt.cylinder4_c": SensorRule(
        path="egt.cylinder4_c",
        minimum=-50.0,
        maximum=1100.0,
        max_rate_per_second=300.0,
        frozen_tolerance=0.2,
    ),

    "oil.pressure_kpa": SensorRule(
        path="oil.pressure_kpa",
        minimum=0.0,
        maximum=1200.0,
        max_rate_per_second=1500.0,
    ),

    "oil.temperature_c": SensorRule(
        path="oil.temperature_c",
        minimum=-50.0,
        maximum=220.0,
        max_rate_per_second=50.0,
    ),

    "fuel.flow_kg_per_second": SensorRule(
        path="fuel.flow_kg_per_second",
        minimum=0.0,
        maximum=0.10,
        max_rate_per_second=0.10,
    ),

    "fuel.pressure_kpa": SensorRule(
        path="fuel.pressure_kpa",
        minimum=0.0,
        maximum=300000.0,
    ),

    "vibration.overall_g": SensorRule(
        path="vibration.overall_g",
        minimum=0.0,
        maximum=50.0,
        max_rate_per_second=100.0,
    ),

    "electrical.battery_voltage_v": SensorRule(
        path="electrical.battery_voltage_v",
        minimum=0.0,
        maximum=40.0,
        max_rate_per_second=50.0,
    ),

    "electrical.alternator_voltage_v": SensorRule(
        path="electrical.alternator_voltage_v",
        minimum=0.0,
        maximum=40.0,
        max_rate_per_second=50.0,
    ),

    "environment.altitude_m": SensorRule(
        path="environment.altitude_m",
        minimum=-500.0,
        maximum=20000.0,
        max_rate_per_second=300.0,
    ),

    "environment.ambient_temperature_c": SensorRule(
        path="environment.ambient_temperature_c",
        minimum=-80.0,
        maximum=80.0,
        max_rate_per_second=20.0,
        required=True,
    ),

    "environment.ambient_pressure_kpa": SensorRule(
        path="environment.ambient_pressure_kpa",
        minimum=5.0,
        maximum=120.0,
        max_rate_per_second=20.0,
    ),
}


_previous_values: Dict[str, Tuple[float, datetime]] = {}
_frozen_counts: Dict[str, int] = {}

_validation_count = 0
_failed_validation_count = 0
_latest_report: Optional[SensorValidationReport] = None


def _get_nested_value(
    state: Mapping[str, Any],
    path: str,
) -> Any:

    current: Any = state

    for part in path.split("."):

        if not isinstance(current, Mapping):
            return None

        if part not in current:
            return None

        current = current[part]

    return current


def _numeric(value: Any) -> Optional[float]:

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    if not isinstance(value, (int, float)):
        return None

    value = float(value)

    if not isfinite(value):
        return None

    return value


def _validate_sensor(
    state: Mapping[str, Any],
    rule: SensorRule,
    timestamp: datetime,
) -> SensorValidationResult:

    raw_value = _get_nested_value(
        state,
        rule.path,
    )

    if raw_value is None:

        return SensorValidationResult(
            path=rule.path,
            value=None,
            status=SensorStatus.MISSING,
            valid=False,
            quality=0.0,
            reasons=["MEASUREMENT_UNAVAILABLE"],
        )

    value = _numeric(raw_value)

    if value is None:

        return SensorValidationResult(
            path=rule.path,
            value=None,
            status=SensorStatus.INVALID,
            valid=False,
            quality=0.0,
            reasons=["NON_NUMERIC_OR_NON_FINITE_VALUE"],
        )

    reasons: List[str] = []

    if (
        rule.minimum is not None
        and value < rule.minimum
    ):
        reasons.append("BELOW_ENGINEERING_RANGE")

    if (
        rule.maximum is not None
        and value > rule.maximum
    ):
        reasons.append("ABOVE_ENGINEERING_RANGE")

    if reasons:

        _previous_values[rule.path] = (
            value,
            timestamp,
        )

        return SensorValidationResult(
            path=rule.path,
            value=value,
            status=SensorStatus.OUT_OF_RANGE,
            valid=False,
            quality=0.1,
            reasons=reasons,
        )

    previous = _previous_values.get(
        rule.path
    )

    rate_violation = False

    if (
        previous is not None
        and rule.max_rate_per_second is not None
    ):

        previous_value, previous_time = previous

        elapsed = (
            timestamp - previous_time
        ).total_seconds()

        if elapsed > 0.0:

            rate = abs(
                value - previous_value
            ) / elapsed

            if rate > rule.max_rate_per_second:
                rate_violation = True
                reasons.append(
                    "RATE_OF_CHANGE_EXCEEDED"
                )

    frozen = False

    if previous is not None:

        previous_value, _ = previous

        if (
            abs(value - previous_value)
            <= rule.frozen_tolerance
        ):

            _frozen_counts[rule.path] = (
                _frozen_counts.get(
                    rule.path,
                    0,
                ) + 1
            )

        else:

            _frozen_counts[rule.path] = 0

        if (
            _frozen_counts.get(rule.path, 0)
            >= rule.frozen_samples
        ):
            frozen = True
            reasons.append(
                "POSSIBLE_FROZEN_SENSOR"
            )

    else:

        _frozen_counts[rule.path] = 0

    _previous_values[rule.path] = (
        value,
        timestamp,
    )

    if rate_violation:

        return SensorValidationResult(
            path=rule.path,
            value=value,
            status=SensorStatus.RATE_VIOLATION,
            valid=False,
            quality=0.35,
            reasons=reasons,
        )

    if frozen:

        return SensorValidationResult(
            path=rule.path,
            value=value,
            status=SensorStatus.FROZEN,
            valid=False,
            quality=0.4,
            reasons=reasons,
        )

    return SensorValidationResult(
        path=rule.path,
        value=value,
        status=SensorStatus.VALID,
        valid=True,
        quality=1.0,
        reasons=[],
    )


def _apply_cross_sensor_checks(
    state: Mapping[str, Any],
    results: Dict[str, SensorValidationResult],
) -> List[str]:

    warnings: List[str] = []

    rpm = _numeric(
        _get_nested_value(
            state,
            "engine.rpm",
        )
    )

    power = _numeric(
        _get_nested_value(
            state,
            "engine.power_kw",
        )
    )

    torque = _numeric(
        _get_nested_value(
            state,
            "engine.torque_nm",
        )
    )

    if (
        rpm is not None
        and power is not None
        and torque is not None
        and rpm > 100.0
    ):

        calculated_power = (
            torque * rpm / 9549.0
        )

        denominator = max(
            abs(power),
            1.0,
        )

        relative_error = (
            abs(
                power - calculated_power
            )
            / denominator
        )

        if relative_error > 0.25:

            warnings.append(
                "ENGINE_POWER_TORQUE_RPM_INCONSISTENCY"
            )

            for path in (
                "engine.power_kw",
                "engine.torque_nm",
            ):

                result = results.get(path)

                if (
                    result is not None
                    and result.valid
                ):

                    result.status = (
                        SensorStatus.INCONSISTENT
                    )

                    result.valid = False

                    result.quality = min(
                        result.quality,
                        0.5,
                    )

                    result.reasons.append(
                        "POWER_TORQUE_RPM_RELATIONSHIP_MISMATCH"
                    )

    if (
        rpm is not None
        and power is not None
        and rpm < 50.0
        and power > 5.0
    ):

        warnings.append(
            "POWER_REPORTED_WHILE_ENGINE_APPEARS_STOPPED"
        )

    return warnings


def validate_sensor_state(
    state: Mapping[str, Any],
    *,
    timestamp: Optional[datetime] = None,
    rules: Optional[Mapping[str, SensorRule]] = None,
) -> SensorValidationReport:

    global _validation_count
    global _failed_validation_count
    global _latest_report

    if timestamp is None:

        timestamp = datetime.now(
            timezone.utc
        )

    if timestamp.tzinfo is None:

        timestamp = timestamp.replace(
            tzinfo=timezone.utc
        )

    active_rules = (
        rules
        if rules is not None
        else DEFAULT_SENSOR_RULES
    )

    try:

        results: Dict[
            str,
            SensorValidationResult,
        ] = {}

        for path, rule in active_rules.items():

            results[path] = _validate_sensor(
                state,
                rule,
                timestamp,
            )

        warnings = _apply_cross_sensor_checks(
            state,
            results,
        )

        configured = len(results)

        available = sum(
            1
            for result in results.values()
            if result.status
            != SensorStatus.MISSING
        )

        valid = sum(
            1
            for result in results.values()
            if result.valid
        )

        coverage = (
            available / configured
            if configured
            else 1.0
        )

        if available:

            quality = (
                sum(
                    result.quality
                    for result in results.values()
                    if result.status
                    != SensorStatus.MISSING
                )
                / available
            )

        else:

            quality = 0.0

        overall_quality = (
            quality * coverage
        )

        required_missing = [
            path
            for path, rule
            in active_rules.items()
            if (
                rule.required
                and results[path].status
                == SensorStatus.MISSING
            )
        ]

        if required_missing:

            warnings.append(
                "REQUIRED_SENSOR_DATA_MISSING"
            )

        if coverage < 0.5:

            warnings.append(
                "SENSOR_COVERAGE_LOW"
            )

        if overall_quality < 0.5:

            warnings.append(
                "SENSOR_CONFIDENCE_LOW"
            )

        report = SensorValidationReport(
            timestamp=timestamp,
            results=results,
            overall_quality=overall_quality,
            coverage=coverage,
            valid_channels=valid,
            available_channels=available,
            configured_channels=configured,
            warnings=warnings,
        )

        _validation_count += 1

        _latest_report = report

        return report

    except Exception:

        _failed_validation_count += 1
        raise


def get_latest_sensor_validation(
) -> Optional[Dict[str, Any]]:

    if _latest_report is None:
        return None

    return _latest_report.to_dict()


def get_sensor_validation_status(
) -> Dict[str, Any]:

    return {
        "service": "sensor_validation",
        "status": "READY",
        "version": SENSOR_VALIDATION_VERSION,
        "configured_channels": len(
            DEFAULT_SENSOR_RULES
        ),
        "validation_count": _validation_count,
        "failed_validation_count":
            _failed_validation_count,
        "latest_report_available":
            _latest_report is not None,
        "latest_coverage": (
            _latest_report.coverage
            if _latest_report
            else None
        ),
        "latest_overall_quality": (
            _latest_report.overall_quality
            if _latest_report
            else None
        ),
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }


def reset_sensor_validation(
) -> None:

    global _validation_count
    global _failed_validation_count
    global _latest_report

    _previous_values.clear()
    _frozen_counts.clear()

    _validation_count = 0
    _failed_validation_count = 0
    _latest_report = None


def get_sensor_validation_info(
) -> Dict[str, Any]:

    return {
        "name":
            "PRATIRUP Sensor Validation Engine",

        "version":
            SENSOR_VALIDATION_VERSION,

        "configured_channels":
            len(DEFAULT_SENSOR_RULES),

        "checks": [
            "missing measurement",
            "numeric validity",
            "finite-value validation",
            "engineering range",
            "rate of change",
            "frozen sensor",
            "power/torque/RPM consistency",
        ],

        "zero_is_valid":
            True,

        "none_means_unavailable":
            True,

        "official_vrde_limits":
            False,

        "engineering_disclaimer":
            (
                "Validation thresholds are PRATIRUP "
                "demonstrator engineering limits and "
                "require calibration against validated "
                "engine/test-rig data."
            ),
    }
