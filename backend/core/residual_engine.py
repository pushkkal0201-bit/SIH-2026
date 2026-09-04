from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import isfinite, sqrt
from typing import Any, Dict, List, Optional

RESIDUAL_ENGINE_VERSION = "1.1.0"

ENGINE_OFF_RPM = 50.0
MIN_EXPECTED_DENOMINATOR = 1e-9
MAX_RELATIVE_RESIDUAL = 10.0
MIN_RESIDUAL_COVERAGE_FOR_CONFIDENCE = 0.25

RESIDUAL_CHANNELS: Dict[
    str,
    Dict[str, Any],
] = {
    "engine.rpm": {
        "subsystem": "mechanical",
        "tolerance": 120.0,
        "enabled_when_stopped": True,
        "description": "Engine speed residual",
    },
    "engine.power_kw": {
        "subsystem": "mechanical",
        "tolerance": 10.0,
        "enabled_when_stopped": False,
        "description": "Engine power residual",
    },
    "engine.torque_nm": {
        "subsystem": "mechanical",
        "tolerance": 40.0,
        "enabled_when_stopped": False,
        "description": "Engine torque residual",
    },
    "cht.cylinder1_c": {
        "subsystem": "thermal",
        "tolerance": 18.0,
        "enabled_when_stopped": False,
        "description": "Cylinder 1 CHT residual",
    },
    "cht.cylinder2_c": {
        "subsystem": "thermal",
        "tolerance": 18.0,
        "enabled_when_stopped": False,
        "description": "Cylinder 2 CHT residual",
    },
    "cht.cylinder3_c": {
        "subsystem": "thermal",
        "tolerance": 18.0,
        "enabled_when_stopped": False,
        "description": "Cylinder 3 CHT residual",
    },
    "cht.cylinder4_c": {
        "subsystem": "thermal",
        "tolerance": 18.0,
        "enabled_when_stopped": False,
        "description": "Cylinder 4 CHT residual",
    },
    "egt.cylinder1_c": {
        "subsystem": "combustion",
        "tolerance": 35.0,
        "enabled_when_stopped": False,
        "description": "Cylinder 1 EGT residual",
    },
    "egt.cylinder2_c": {
        "subsystem": "combustion",
        "tolerance": 35.0,
        "enabled_when_stopped": False,
        "description": "Cylinder 2 EGT residual",
    },
    "egt.cylinder3_c": {
        "subsystem": "combustion",
        "tolerance": 35.0,
        "enabled_when_stopped": False,
        "description": "Cylinder 3 EGT residual",
    },
    "egt.cylinder4_c": {
        "subsystem": "combustion",
        "tolerance": 35.0,
        "enabled_when_stopped": False,
        "description": "Cylinder 4 EGT residual",
    },
    "oil.pressure_kpa": {
        "subsystem": "lubrication",
        "tolerance": 70.0,
        "enabled_when_stopped": True,
        "description": "Oil-pressure residual",
    },
    "oil.temperature_c": {
        "subsystem": "lubrication",
        "tolerance": 15.0,
        "enabled_when_stopped": False,
        "description": "Oil-temperature residual",
    },
    "fuel.flow_kg_per_second": {
        "subsystem": "fuel_system",
        "tolerance_fraction": 0.15,
        "enabled_when_stopped": True,
        "description": "Fuel-flow residual",
    },
    "fuel.pressure_kpa": {
        "subsystem": "fuel_system",
        "tolerance": 30.0,
        "enabled_when_stopped": False,
        "description": "Fuel-pressure residual",
    },
    "vibration.overall_g": {
        "subsystem": "vibration",
        "tolerance": 0.35,
        "enabled_when_stopped": False,
        "description": "Overall vibration residual",
    },
    "electrical.battery_voltage_v": {
        "subsystem": "electrical",
        "tolerance": 1.5,
        "enabled_when_stopped": True,
        "description": "Battery-voltage residual",
    },
    "electrical.alternator_voltage_v": {
        "subsystem": "electrical",
        "tolerance": 1.5,
        "enabled_when_stopped": False,
        "description": "Alternator-voltage residual",
    },
    "electrical.alternator_current_a": {
        "subsystem": "electrical",
        "tolerance": 10.0,
        "enabled_when_stopped": False,
        "description": "Alternator-current residual",
    },
}

@dataclass
class ResidualResult:
    timestamp: datetime
    engine_running: Optional[bool]
    residuals: Dict[str, Any]
    subsystem_scores: Dict[
        str,
        Optional[float],
    ]
    subsystem_coverage: Dict[
        str,
        Dict[str, Any],
    ]
    overall_score: Optional[float]
    overall_risk_percent: Optional[float]
    available_channels: int
    eligible_channels: int
    configured_channels: int
    coverage: float
    confidence: float
    warnings: List[str] = field(
        default_factory=list
    )
    version: str = (
        RESIDUAL_ENGINE_VERSION
    )

    def to_dict(
        self,
    ) -> Dict[str, Any]:
        return {
            "timestamp":
                self.timestamp.isoformat(),
            "version":
                self.version,
            "engine_running":
                self.engine_running,
            "residuals":
                deepcopy(
                    self.residuals
                ),
            "subsystem_scores":
                deepcopy(
                    self.subsystem_scores
                ),
            "subsystem_coverage":
                deepcopy(
                    self.subsystem_coverage
                ),
            "overall_score":
                self.overall_score,
            "overall_risk_percent":
                self.overall_risk_percent,
            "coverage": {
                "available_channels":
                    self.available_channels,
                "eligible_channels":
                    self.eligible_channels,
                "configured_channels":
                    self.configured_channels,
                "fraction":
                    self.coverage,
                "percentage":
                    self.coverage * 100.0,
            },
            "confidence":
                self.confidence,
            "warnings":
                list(
                    self.warnings
                ),
        }

_latest_result: Optional[
    ResidualResult
] = None

_calculation_count = 0
_failed_calculation_count = 0

def utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )

def is_number(
    value: Any,
) -> bool:
    if value is None:
        return False

    if isinstance(
        value,
        bool,
    ):
        return False

    if not isinstance(
        value,
        (int, float),
    ):
        return False

    return isfinite(
        float(value)
    )

def clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )

def get_nested(
    data: Dict[str, Any],
    path: str,
) -> Any:
    current: Any = data

    for key in path.split("."):
        if not isinstance(
            current,
            dict,
        ):
            return None

        if key not in current:
            return None

        current = current[key]

    return current

def determine_engine_running(
    observed_state: Dict[str, Any],
) -> Optional[bool]:
    rpm = get_nested(
        observed_state,
        "engine.rpm",
    )

    if not is_number(
        rpm
    ):
        return None

    return (
        float(rpm)
        >=
        ENGINE_OFF_RPM
    )

def is_channel_eligible(
    configuration: Dict[str, Any],
    engine_running: Optional[bool],
) -> bool:
    if engine_running is None:
        return True

    if engine_running:
        return True

    return bool(
        configuration.get(
            "enabled_when_stopped",
            False,
        )
    )

def calculate_absolute_residual(
    observed: Any,
    expected: Any,
) -> Optional[float]:
    if not is_number(
        observed
    ):
        return None

    if not is_number(
        expected
    ):
        return None

    return (
        float(observed)
        -
        float(expected)
    )

def calculate_relative_residual(
    observed: Any,
    expected: Any,
) -> Optional[float]:
    if not is_number(
        observed
    ):
        return None

    if not is_number(
        expected
    ):
        return None

    expected_value = float(
        expected
    )

    if (
        abs(expected_value)
        <=
        MIN_EXPECTED_DENOMINATOR
    ):
        return None

    relative = (
        (
            float(observed)
            -
            expected_value
        )
        /
        abs(expected_value)
    )

    return max(
        -MAX_RELATIVE_RESIDUAL,
        min(
            MAX_RELATIVE_RESIDUAL,
            relative,
        ),
    )

def resolve_tolerance(
    *,
    expected: Any,
    configuration: Dict[str, Any],
) -> Optional[float]:
    tolerance = configuration.get(
        "tolerance"
    )

    if is_number(
        tolerance
    ):
        tolerance_value = float(
            tolerance
        )

        if tolerance_value > 0:
            return tolerance_value

    tolerance_fraction = (
        configuration.get(
            "tolerance_fraction"
        )
    )

    if (
        is_number(
            tolerance_fraction
        )
        and is_number(
            expected
        )
    ):
        expected_value = abs(
            float(expected)
        )

        if (
            expected_value
            <=
            MIN_EXPECTED_DENOMINATOR
        ):
            return None

        calculated = (
            expected_value
            *
            float(
                tolerance_fraction
            )
        )

        if calculated > 0:
            return calculated

    return None

def calculate_normalized_residual(
    residual: Optional[float],
    tolerance: Optional[float],
) -> Optional[float]:
    if (
        residual is None
        or tolerance is None
        or tolerance <= 0
    ):
        return None

    return (
        residual
        /
        tolerance
    )

def calculate_deviation_score(
    normalized_residual: Optional[float],
) -> Optional[float]:
    if normalized_residual is None:
        return None

    return clamp(
        abs(
            normalized_residual
        ),
        0.0,
        1.0,
    )

def calculate_channel_residual(
    *,
    path: str,
    observed_state: Dict[str, Any],
    expected_state: Dict[str, Any],
    configuration: Dict[str, Any],
    engine_running: Optional[bool],
) -> Dict[str, Any]:
    eligible = is_channel_eligible(
        configuration,
        engine_running,
    )

    observed = get_nested(
        observed_state,
        path,
    )

    expected = get_nested(
        expected_state,
        path,
    )

    if not eligible:
        return {
            "path":
                path,
            "subsystem":
                configuration[
                    "subsystem"
                ],
            "description":
                configuration.get(
                    "description"
                ),
            "eligible":
                False,
            "available":
                False,
            "reason":
                "CHANNEL_INACTIVE_FOR_CURRENT_ENGINE_STATE",
            "observed":
                (
                    float(observed)
                    if is_number(observed)
                    else None
                ),
            "expected":
                (
                    float(expected)
                    if is_number(expected)
                    else None
                ),
            "tolerance":
                None,
            "absolute":
                None,
            "relative":
                None,
            "relative_percent":
                None,
            "normalized":
                None,
            "deviation_score":
                None,
        }

    if not is_number(
        observed
    ):
        return {
            "path":
                path,
            "subsystem":
                configuration[
                    "subsystem"
                ],
            "description":
                configuration.get(
                    "description"
                ),
            "eligible":
                True,
            "available":
                False,
            "reason":
                "OBSERVED_VALUE_UNAVAILABLE",
            "observed":
                None,
            "expected":
                (
                    float(expected)
                    if is_number(expected)
                    else None
                ),
            "tolerance":
                None,
            "absolute":
                None,
            "relative":
                None,
            "relative_percent":
                None,
            "normalized":
                None,
            "deviation_score":
                None,
        }

    if not is_number(
        expected
    ):
        return {
            "path":
                path,
            "subsystem":
                configuration[
                    "subsystem"
                ],
            "description":
                configuration.get(
                    "description"
                ),
            "eligible":
                True,
            "available":
                False,
            "reason":
                "EXPECTED_VALUE_UNAVAILABLE",
            "observed":
                float(
                    observed
                ),
            "expected":
                None,
            "tolerance":
                None,
            "absolute":
                None,
            "relative":
                None,
            "relative_percent":
                None,
            "normalized":
                None,
            "deviation_score":
                None,
        }

    tolerance = resolve_tolerance(
        expected=expected,
        configuration=configuration,
    )

    if tolerance is None:
        return {
            "path":
                path,
            "subsystem":
                configuration[
                    "subsystem"
                ],
            "description":
                configuration.get(
                    "description"
                ),
            "eligible":
                True,
            "available":
                False,
            "reason":
                "TOLERANCE_UNAVAILABLE",
            "observed":
                float(
                    observed
                ),
            "expected":
                float(
                    expected
                ),
            "tolerance":
                None,
            "absolute":
                None,
            "relative":
                None,
            "relative_percent":
                None,
            "normalized":
                None,
            "deviation_score":
                None,
        }

    absolute = (
        calculate_absolute_residual(
            observed,
            expected,
        )
    )

    relative = (
        calculate_relative_residual(
            observed,
            expected,
        )
    )

    normalized = (
        calculate_normalized_residual(
            absolute,
            tolerance,
        )
    )

    deviation_score = (
        calculate_deviation_score(
            normalized
        )
    )

    return {
        "path":
            path,
        "subsystem":
            configuration[
                "subsystem"
            ],
        "description":
            configuration.get(
                "description"
            ),
        "eligible":
            True,
        "available":
            True,
        "reason":
            None,
        "observed":
            float(
                observed
            ),
        "expected":
            float(
                expected
            ),
        "tolerance":
            tolerance,
        "absolute":
            absolute,
        "absolute_magnitude":
            (
                abs(absolute)
                if absolute is not None
                else None
            ),
        "relative":
            relative,
        "relative_percent":
            (
                relative * 100.0
                if relative is not None
                else None
            ),
        "normalized":
            normalized,
        "normalized_magnitude":
            (
                abs(normalized)
                if normalized is not None
                else None
            ),
        "deviation_score":
            deviation_score,
    }

def calculate_subsystem_scores(
    residuals: Dict[str, Any],
) -> Dict[
    str,
    Optional[float],
]:
    grouped: Dict[
        str,
        List[float],
    ] = {}

    all_subsystems = {
        configuration[
            "subsystem"
        ]
        for configuration
        in RESIDUAL_CHANNELS.values()
    }

    for residual in residuals.values():
        if not isinstance(
            residual,
            dict,
        ):
            continue

        if not residual.get(
            "available",
            False,
        ):
            continue

        subsystem = residual.get(
            "subsystem"
        )

        score = residual.get(
            "deviation_score"
        )

        if (
            subsystem is None
            or not is_number(
                score
            )
        ):
            continue

        grouped.setdefault(
            str(subsystem),
            [],
        ).append(
            float(score)
        )

    scores: Dict[
        str,
        Optional[float],
    ] = {}

    for subsystem in sorted(
        all_subsystems
    ):
        values = grouped.get(
            subsystem,
            [],
        )

        if not values:
            scores[
                subsystem
            ] = None
            continue

        squared = sum(
            value * value
            for value
            in values
        )

        rms = sqrt(
            squared
            /
            len(values)
        )

        scores[
            subsystem
        ] = clamp(
            rms,
            0.0,
            1.0,
        )

    return scores

def calculate_subsystem_coverage(
    residuals: Dict[str, Any],
) -> Dict[
    str,
    Dict[str, Any],
]:
    result: Dict[
        str,
        Dict[str, Any],
    ] = {}

    all_subsystems = {
        configuration[
            "subsystem"
        ]
        for configuration
        in RESIDUAL_CHANNELS.values()
    }

    for subsystem in sorted(
        all_subsystems
    ):
        eligible = 0
        available = 0

        for residual in residuals.values():
            if not isinstance(
                residual,
                dict,
            ):
                continue

            if (
                residual.get(
                    "subsystem"
                )
                != subsystem
            ):
                continue

            if residual.get(
                "eligible",
                False,
            ):
                eligible += 1

            if residual.get(
                "available",
                False,
            ):
                available += 1

        fraction = (
            available / eligible
            if eligible > 0
            else 0.0
        )

        result[
            subsystem
        ] = {
            "available_channels":
                available,
            "eligible_channels":
                eligible,
            "fraction":
                fraction,
            "percentage":
                fraction * 100.0,
        }

    return result

def calculate_overall_score(
    subsystem_scores: Dict[
        str,
        Optional[float],
    ],
) -> Optional[float]:
    available_scores = [
        float(score)
        for score
        in subsystem_scores.values()
        if is_number(
            score
        )
    ]

    if not available_scores:
        return None

    squared = sum(
        score * score
        for score
        in available_scores
    )

    rms = sqrt(
        squared
        /
        len(
            available_scores
        )
    )

    return clamp(
        rms,
        0.0,
        1.0,
    )

def calculate_confidence(
    coverage: float,
    subsystem_scores: Dict[
        str,
        Optional[float],
    ],
) -> float:
    if coverage <= 0:
        return 0.0

    available_subsystems = sum(
        1
        for score
        in subsystem_scores.values()
        if is_number(
            score
        )
    )

    total_subsystems = len(
        subsystem_scores
    )

    subsystem_fraction = (
        available_subsystems
        /
        total_subsystems
        if total_subsystems > 0
        else 0.0
    )

    confidence = (
        0.75
        *
        coverage
        +
        0.25
        *
        subsystem_fraction
    )

    return clamp(
        confidence,
        0.0,
        1.0,
    )

def build_warnings(
    *,
    engine_running: Optional[bool],
    coverage: float,
    confidence: float,
    overall_score: Optional[float],
) -> List[str]:
    warnings: List[str] = []

    if engine_running is None:
        warnings.append(
            "Engine operating state is unavailable."
        )

    if coverage == 0:
        warnings.append(
            "No comparable observed/expected diagnostic channels are available."
        )

    elif (
        coverage
        <
        MIN_RESIDUAL_COVERAGE_FOR_CONFIDENCE
    ):
        warnings.append(
            "Residual calculation coverage is very low."
        )

    elif coverage < 0.50:
        warnings.append(
            "Residual calculation coverage is limited."
        )

    if confidence < 0.25:
        warnings.append(
            "Residual confidence is low."
        )

    if (
        overall_score is not None
        and overall_score >= 0.75
    ):
        warnings.append(
            "Large observed-versus-expected deviation detected."
        )

    return warnings

def calculate_residuals(
    observed_state: Dict[str, Any],
    expected_state: Dict[str, Any],
) -> ResidualResult:
    global _latest_result
    global _calculation_count
    global _failed_calculation_count

    try:
        if not isinstance(
            observed_state,
            dict,
        ):
            raise TypeError(
                "Observed state must be a dictionary."
            )

        if not isinstance(
            expected_state,
            dict,
        ):
            raise TypeError(
                "Expected state must be a dictionary."
            )

        engine_running = (
            determine_engine_running(
                observed_state
            )
        )

        residuals: Dict[
            str,
            Any,
        ] = {}

        available_channels = 0
        eligible_channels = 0

        for (
            path,
            configuration,
        ) in RESIDUAL_CHANNELS.items():

            result = (
                calculate_channel_residual(
                    path=path,
                    observed_state=(
                        observed_state
                    ),
                    expected_state=(
                        expected_state
                    ),
                    configuration=(
                        configuration
                    ),
                    engine_running=(
                        engine_running
                    ),
                )
            )

            residuals[
                path
            ] = result

            if result.get(
                "eligible",
                False,
            ):
                eligible_channels += 1

            if result.get(
                "available",
                False,
            ):
                available_channels += 1

        configured_channels = len(
            RESIDUAL_CHANNELS
        )

        coverage = (
            available_channels
            /
            eligible_channels
            if eligible_channels > 0
            else 0.0
        )

        subsystem_scores = (
            calculate_subsystem_scores(
                residuals
            )
        )

        subsystem_coverage = (
            calculate_subsystem_coverage(
                residuals
            )
        )

        overall_score = (
            calculate_overall_score(
                subsystem_scores
            )
        )

        overall_risk_percent = (
            overall_score * 100.0
            if overall_score
            is not None
            else None
        )

        confidence = (
            calculate_confidence(
                coverage,
                subsystem_scores,
            )
        )

        warnings = (
            build_warnings(
                engine_running=(
                    engine_running
                ),
                coverage=coverage,
                confidence=confidence,
                overall_score=(
                    overall_score
                ),
            )
        )

        result = ResidualResult(
            timestamp=utc_now(),

            engine_running=(
                engine_running
            ),

            residuals=residuals,

            subsystem_scores=(
                subsystem_scores
            ),

            subsystem_coverage=(
                subsystem_coverage
            ),

            overall_score=(
                overall_score
            ),

            overall_risk_percent=(
                overall_risk_percent
            ),

            available_channels=(
                available_channels
            ),

            eligible_channels=(
                eligible_channels
            ),

            configured_channels=(
                configured_channels
            ),

            coverage=coverage,

            confidence=confidence,

            warnings=warnings,
        )

        _latest_result = result
        _calculation_count += 1

        return result

    except Exception:
        _failed_calculation_count += 1
        raise

def calculate_from_digital_twin() -> Optional[
    ResidualResult
]:
    from backend.core.digital_twin import (
        get_observed_state,
        get_expected_state,
        set_residual_state,
    )

    observed_state = (
        get_observed_state()
    )

    expected_state = (
        get_expected_state()
    )

    if observed_state is None:
        return None

    if expected_state is None:
        return None

    result = calculate_residuals(
        observed_state=(
            observed_state
        ),
        expected_state=(
            expected_state
        ),
    )

    set_residual_state(
        result.to_dict()
    )

    return result

def get_latest_residual_result() -> Optional[
    ResidualResult
]:
    return _latest_result

def get_latest_residual_dict() -> Optional[
    Dict[str, Any]
]:
    if _latest_result is None:
        return None

    return _latest_result.to_dict()

def get_residual_engine_status() -> Dict[
    str,
    Any,
]:
    return {
        "service":
            "residual_engine",

        "status":
            "READY",

        "version":
            RESIDUAL_ENGINE_VERSION,

        "configured_channels":
            len(
                RESIDUAL_CHANNELS
            ),

        "calculation_count":
            _calculation_count,

        "failed_calculation_count":
            _failed_calculation_count,

        "latest_result_available":
            _latest_result is not None,

        "latest_engine_running":
            (
                _latest_result
                .engine_running

                if _latest_result
                is not None

                else None
            ),

        "latest_coverage":
            (
                _latest_result
                .coverage

                if _latest_result
                is not None

                else None
            ),

        "latest_confidence":
            (
                _latest_result
                .confidence

                if _latest_result
                is not None

                else None
            ),

        "latest_overall_score":
            (
                _latest_result
                .overall_score

                if _latest_result
                is not None

                else None
            ),

        "latest_overall_risk_percent":
            (
                _latest_result
                .overall_risk_percent

                if _latest_result
                is not None

                else None
            ),

        "timestamp":
            utc_now().isoformat(),
    }

def reset_residual_engine() -> None:
    global _latest_result
    global _calculation_count
    global _failed_calculation_count

    _latest_result = None
    _calculation_count = 0
    _failed_calculation_count = 0

def get_residual_engine_info() -> Dict[
    str,
    Any,
]:
    return {
        "name":
            "PRATIRUP Residual Engine",

        "version":
            RESIDUAL_ENGINE_VERSION,

        "purpose":
            (
                "Calculate operating-state-aware "
                "observed-versus-expected diagnostic residuals."
            ),

        "configured_channels":
            len(
                RESIDUAL_CHANNELS
            ),

        "excluded_control_inputs": [
            "engine.throttle_percent",
            "engine.load_percent",
        ],

        "subsystems":
            sorted(
                {
                    configuration[
                        "subsystem"
                    ]

                    for configuration
                    in RESIDUAL_CHANNELS.values()
                }
            ),

        "outputs": [
            "absolute_residual",
            "relative_residual",
            "normalized_residual",
            "deviation_score",
            "subsystem_scores",
            "subsystem_coverage",
            "overall_score",
            "coverage",
            "confidence",
        ],

        "null_policy":
            (
                "Residual remains None whenever observed "
                "or expected measurement is unavailable."
            ),

        "control_policy":
            (
                "Throttle/load commands are excluded from "
                "diagnostic residual scoring."
            ),

        "important":
            (
                "Deviation scores are diagnostic evidence, "
                "not confirmed fault probabilities."
            ),
    }
