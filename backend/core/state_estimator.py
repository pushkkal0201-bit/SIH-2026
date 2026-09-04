from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import isfinite
from typing import Any, Dict, List, Optional

from backend.models.schemas import TelemetryFrame


STATE_ESTIMATOR_VERSION = "1.0.0"


EXPECTED_SENSOR_CHANNELS = 26


@dataclass
class EstimatedState:

    timestamp: datetime

    source: Optional[str]

    sequence: Optional[int]

    state: Dict[str, Any]

    available_channels: int

    total_channels: int

    coverage: float

    confidence: float

    missing_channels: List[str] = field(
        default_factory=list
    )

    warnings: List[str] = field(
        default_factory=list
    )

    estimator_version: str = (
        STATE_ESTIMATOR_VERSION
    )


    def to_dict(self) -> Dict[str, Any]:

        return {

            "timestamp":
                self.timestamp.isoformat(),

            "source":
                self.source,

            "sequence":
                self.sequence,

            "state":
                deepcopy(
                    self.state
                ),

            "coverage": {

                "available_channels":
                    self.available_channels,

                "total_channels":
                    self.total_channels,

                "fraction":
                    self.coverage,

                "percentage":
                    self.coverage * 100.0,

                "missing_channels":
                    list(
                        self.missing_channels
                    ),
            },

            "confidence":
                self.confidence,

            "warnings":
                list(
                    self.warnings
                ),

            "estimator_version":
                self.estimator_version,
        }


_latest_state: Optional[
    EstimatedState
] = None


_estimation_count = 0

_failed_estimation_count = 0


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
        float(
            value
        )
    )


def safe_number(
    value: Any,
) -> Optional[float]:

    if not is_number(
        value
    ):

        return None


    return float(
        value
    )


def telemetry_to_dict(
    telemetry: TelemetryFrame | Dict[str, Any],
) -> Dict[str, Any]:

    if isinstance(
        telemetry,
        dict,
    ):

        return deepcopy(
            telemetry
        )


    if hasattr(
        telemetry,
        "model_dump",
    ):

        return telemetry.model_dump(
            mode="python"
        )


    raise TypeError(
        "State estimator requires TelemetryFrame or dictionary."
    )


def get_nested(
    data: Dict[str, Any],
    path: str,
) -> Any:

    current: Any = data


    for key in path.split(
        "."
    ):

        if not isinstance(
            current,
            dict,
        ):

            return None


        if key not in current:

            return None


        current = current[
            key
        ]


    return current


SENSOR_CHANNELS = [

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
    "electrical.battery_current_a",
    "electrical.alternator_voltage_v",
    "electrical.alternator_current_a",

    "environment.altitude_m",
    "environment.ambient_temperature_c",
    "environment.ambient_pressure_kpa",
    "environment.air_density_kg_m3",
]


def calculate_coverage(
    telemetry: Dict[str, Any],
) -> tuple[
    int,
    int,
    float,
    List[str],
]:

    available = 0

    missing: List[str] = []


    for path in SENSOR_CHANNELS:

        value = get_nested(
            telemetry,
            path,
        )


        if is_number(
            value
        ):

            available += 1

        else:

            missing.append(
                path
            )


    total = len(
        SENSOR_CHANNELS
    )


    coverage = (
        available / total
        if total > 0
        else 0.0
    )


    return (
        available,
        total,
        coverage,
        missing,
    )


def calculate_confidence(
    coverage: float,
    source: Optional[str],
) -> float:

    confidence = coverage


    if source is None:

        confidence *= 0.90


    confidence = max(
        0.0,
        min(
            1.0,
            confidence,
        ),
    )


    return confidence


def build_observed_state(
    telemetry: Dict[str, Any],
) -> Dict[str, Any]:

    return {

        "engine": {

            "rpm":
                safe_number(
                    get_nested(
                        telemetry,
                        "engine.rpm",
                    )
                ),

            "throttle_percent":
                safe_number(
                    get_nested(
                        telemetry,
                        "engine.throttle_percent",
                    )
                ),

            "load_percent":
                safe_number(
                    get_nested(
                        telemetry,
                        "engine.load_percent",
                    )
                ),

            "power_kw":
                safe_number(
                    get_nested(
                        telemetry,
                        "engine.power_kw",
                    )
                ),

            "torque_nm":
                safe_number(
                    get_nested(
                        telemetry,
                        "engine.torque_nm",
                    )
                ),
        },


        "cht": {

            "cylinder1_c":
                safe_number(
                    get_nested(
                        telemetry,
                        "cht.cylinder1_c",
                    )
                ),

            "cylinder2_c":
                safe_number(
                    get_nested(
                        telemetry,
                        "cht.cylinder2_c",
                    )
                ),

            "cylinder3_c":
                safe_number(
                    get_nested(
                        telemetry,
                        "cht.cylinder3_c",
                    )
                ),

            "cylinder4_c":
                safe_number(
                    get_nested(
                        telemetry,
                        "cht.cylinder4_c",
                    )
                ),
        },


        "egt": {

            "cylinder1_c":
                safe_number(
                    get_nested(
                        telemetry,
                        "egt.cylinder1_c",
                    )
                ),

            "cylinder2_c":
                safe_number(
                    get_nested(
                        telemetry,
                        "egt.cylinder2_c",
                    )
                ),

            "cylinder3_c":
                safe_number(
                    get_nested(
                        telemetry,
                        "egt.cylinder3_c",
                    )
                ),

            "cylinder4_c":
                safe_number(
                    get_nested(
                        telemetry,
                        "egt.cylinder4_c",
                    )
                ),
        },


        "oil": {

            "pressure_kpa":
                safe_number(
                    get_nested(
                        telemetry,
                        "oil.pressure_kpa",
                    )
                ),

            "temperature_c":
                safe_number(
                    get_nested(
                        telemetry,
                        "oil.temperature_c",
                    )
                ),
        },


        "fuel": {

            "flow_kg_per_second":
                safe_number(
                    get_nested(
                        telemetry,
                        "fuel.flow_kg_per_second",
                    )
                ),

            "pressure_kpa":
                safe_number(
                    get_nested(
                        telemetry,
                        "fuel.pressure_kpa",
                    )
                ),

            "injection_timing_deg":
                safe_number(
                    get_nested(
                        telemetry,
                        "fuel.injection_timing_deg",
                    )
                ),
        },


        "vibration": {

            "overall_g":
                safe_number(
                    get_nested(
                        telemetry,
                        "vibration.overall_g",
                    )
                ),

            "x_g":
                safe_number(
                    get_nested(
                        telemetry,
                        "vibration.x_g",
                    )
                ),

            "y_g":
                safe_number(
                    get_nested(
                        telemetry,
                        "vibration.y_g",
                    )
                ),

            "z_g":
                safe_number(
                    get_nested(
                        telemetry,
                        "vibration.z_g",
                    )
                ),
        },


        "electrical": {

            "battery_voltage_v":
                safe_number(
                    get_nested(
                        telemetry,
                        "electrical.battery_voltage_v",
                    )
                ),

            "battery_current_a":
                safe_number(
                    get_nested(
                        telemetry,
                        "electrical.battery_current_a",
                    )
                ),

            "alternator_voltage_v":
                safe_number(
                    get_nested(
                        telemetry,
                        "electrical.alternator_voltage_v",
                    )
                ),

            "alternator_current_a":
                safe_number(
                    get_nested(
                        telemetry,
                        "electrical.alternator_current_a",
                    )
                ),
        },


        "environment": {

            "altitude_m":
                safe_number(
                    get_nested(
                        telemetry,
                        "environment.altitude_m",
                    )
                ),

            "altitude_ft":
                safe_number(
                    get_nested(
                        telemetry,
                        "environment.altitude_ft",
                    )
                ),

            "ambient_temperature_c":
                safe_number(
                    get_nested(
                        telemetry,
                        "environment.ambient_temperature_c",
                    )
                ),

            "ambient_pressure_kpa":
                safe_number(
                    get_nested(
                        telemetry,
                        "environment.ambient_pressure_kpa",
                    )
                ),

            "air_density_kg_m3":
                safe_number(
                    get_nested(
                        telemetry,
                        "environment.air_density_kg_m3",
                    )
                ),
        },


        "mission": deepcopy(
            telemetry.get(
                "mission",
                {},
            )
        ),
    }


def build_warnings(
    state: Dict[str, Any],
    coverage: float,
) -> List[str]:

    warnings: List[str] = []


    if coverage < 0.25:

        warnings.append(
            "Observed-state telemetry coverage is very low."
        )

    elif coverage < 0.50:

        warnings.append(
            "Observed-state telemetry coverage is limited."
        )


    rpm = get_nested(
        state,
        "engine.rpm",
    )

    throttle = get_nested(
        state,
        "engine.throttle_percent",
    )

    load = get_nested(
        state,
        "engine.load_percent",
    )


    if (
        is_number(rpm)
        and rpm == 0
        and is_number(throttle)
        and throttle > 20
    ):

        warnings.append(
            "RPM is zero while throttle command is elevated."
        )


    if (
        is_number(rpm)
        and rpm == 0
        and is_number(load)
        and load > 20
    ):

        warnings.append(
            "RPM is zero while reported engine load is elevated."
        )


    return warnings


def estimate_state(
    telemetry: TelemetryFrame | Dict[str, Any],
) -> EstimatedState:

    global _latest_state
    global _estimation_count
    global _failed_estimation_count


    try:

        raw = telemetry_to_dict(
            telemetry
        )


        meta = raw.get(
            "meta"
        )

        if not isinstance(
            meta,
            dict,
        ):

            meta = {}


        source = meta.get(
            "source"
        )


        sequence = meta.get(
            "sequence"
        )


        observed_state = build_observed_state(
            raw
        )


        (
            available_channels,
            total_channels,
            coverage,
            missing_channels,
        ) = calculate_coverage(
            raw
        )


        confidence = calculate_confidence(
            coverage,
            source,
        )


        warnings = build_warnings(
            observed_state,
            coverage,
        )


        result = EstimatedState(

            timestamp=utc_now(),

            source=(
                str(source)
                if source is not None
                else None
            ),

            sequence=(
                int(sequence)
                if isinstance(sequence, int)
                and not isinstance(sequence, bool)
                else None
            ),

            state=observed_state,

            available_channels=available_channels,

            total_channels=total_channels,

            coverage=coverage,

            confidence=confidence,

            missing_channels=missing_channels,

            warnings=warnings,
        )


        _latest_state = result

        _estimation_count += 1


        return result


    except Exception:

        _failed_estimation_count += 1

        raise


def get_latest_state() -> Optional[EstimatedState]:

    return _latest_state


def get_latest_state_dict() -> Optional[Dict[str, Any]]:

    if _latest_state is None:

        return None


    return _latest_state.to_dict()


def get_state_estimator_status() -> Dict[str, Any]:

    return {

        "service":
            "state_estimator",

        "status":
            "READY",

        "version":
            STATE_ESTIMATOR_VERSION,

        "estimation_count":
            _estimation_count,

        "failed_estimation_count":
            _failed_estimation_count,

        "latest_state_available":
            _latest_state is not None,

        "latest_coverage":
            (
                _latest_state.coverage
                if _latest_state is not None
                else None
            ),

        "latest_confidence":
            (
                _latest_state.confidence
                if _latest_state is not None
                else None
            ),

        "timestamp":
            utc_now().isoformat(),
    }


def reset_state_estimator() -> None:

    global _latest_state
    global _estimation_count
    global _failed_estimation_count


    _latest_state = None

    _estimation_count = 0

    _failed_estimation_count = 0


def get_state_estimator_info() -> Dict[str, Any]:

    return {

        "name":
            "PRATIRUP State Estimator",

        "version":
            STATE_ESTIMATOR_VERSION,

        "purpose":
            "Validated telemetry to observed Digital Twin state.",

        "null_policy":
            "None means unavailable; zero remains a genuine numeric value.",

        "sensor_channels":
            len(
                SENSOR_CHANNELS
            ),
    }
