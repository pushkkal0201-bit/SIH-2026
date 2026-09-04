from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite, pi
from typing import Any, Dict, Optional


PERFORMANCE_MAP_VERSION = "1.0.0"


BASELINE_POWER_HP = 180.0

HP_TO_KW = 0.745699872

BASELINE_POWER_KW = (
    BASELINE_POWER_HP
    *
    HP_TO_KW
)


IDLE_RPM = 700.0

REFERENCE_RPM = 2200.0

MAX_MODEL_RPM = 3000.0


CONSTANT_POWER_ALTITUDE_FT = 11000.0

FT_TO_M = 0.3048

CONSTANT_POWER_ALTITUDE_M = (
    CONSTANT_POWER_ALTITUDE_FT
    *
    FT_TO_M
)


SEA_LEVEL_DENSITY_KG_M3 = 1.225


MIN_POWER_FACTOR = 0.0

MAX_POWER_FACTOR = 1.0


@dataclass
class PerformanceState:

    timestamp: datetime

    rpm: Optional[float]

    throttle_percent: Optional[float]

    load_percent: Optional[float]

    altitude_m: float

    air_density_kg_m3: Optional[float]

    density_ratio: Optional[float]

    rpm_factor: Optional[float]

    throttle_factor: Optional[float]

    load_factor: Optional[float]

    altitude_power_factor: Optional[float]

    available_power_kw: Optional[float]

    expected_power_kw: Optional[float]

    available_torque_nm: Optional[float]

    expected_torque_nm: Optional[float]

    power_utilization: Optional[float]

    power_margin_kw: Optional[float]

    operating_region: str

    version: str = PERFORMANCE_MAP_VERSION


    def to_dict(
        self,
    ) -> Dict[str, Any]:

        return {

            "timestamp":
                self.timestamp.isoformat(),

            "version":
                self.version,

            "baseline_power_hp":
                BASELINE_POWER_HP,

            "baseline_power_kw":
                BASELINE_POWER_KW,

            "rpm":
                self.rpm,

            "throttle_percent":
                self.throttle_percent,

            "load_percent":
                self.load_percent,

            "altitude_m":
                self.altitude_m,

            "air_density_kg_m3":
                self.air_density_kg_m3,

            "density_ratio":
                self.density_ratio,

            "rpm_factor":
                self.rpm_factor,

            "throttle_factor":
                self.throttle_factor,

            "load_factor":
                self.load_factor,

            "altitude_power_factor":
                self.altitude_power_factor,

            "available_power_kw":
                self.available_power_kw,

            "expected_power_kw":
                self.expected_power_kw,

            "available_torque_nm":
                self.available_torque_nm,

            "expected_torque_nm":
                self.expected_torque_nm,

            "power_utilization":
                self.power_utilization,

            "power_margin_kw":
                self.power_margin_kw,

            "operating_region":
                self.operating_region,
        }


_latest_state: Optional[
    PerformanceState
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


def safe_float(
    value: Any,
    default: Optional[float] = None,
) -> Optional[float]:

    if not is_number(
        value
    ):

        return default

    return float(
        value
    )


def clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:

    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def normalize_percent(
    value: Any,
) -> Optional[float]:

    numeric = safe_float(
        value
    )

    if numeric is None:

        return None

    return clamp(
        numeric,
        0.0,
        100.0,
    )


def get_nested(
    data: Dict[str, Any],
    *paths: str,
) -> Any:

    for path in paths:

        current: Any = data

        found = True

        for key in path.split("."):

            if not isinstance(
                current,
                dict,
            ):

                found = False
                break

            if key not in current:

                found = False
                break

            current = current[key]

        if found:

            return current

    return None


def get_atmosphere(
    altitude_m: float,
) -> Dict[str, Optional[float]]:

    try:

        from backend.physics.atmosphere import (
            calculate_atmosphere,
        )

        atmosphere = calculate_atmosphere(
            altitude_m
        )

        density = safe_float(
            getattr(
                atmosphere,
                "air_density_kg_m3",
                None,
            )
        )

        density_ratio = safe_float(
            getattr(
                atmosphere,
                "density_ratio",
                None,
            )
        )

        if density is None:

            density = safe_float(
                getattr(
                    atmosphere,
                    "density_kg_m3",
                    None,
                )
            )

        if (
            density_ratio is None
            and density is not None
        ):

            density_ratio = (
                density
                /
                SEA_LEVEL_DENSITY_KG_M3
            )

        return {

            "air_density_kg_m3":
                density,

            "density_ratio":
                density_ratio,
        }

    except Exception:

        return {

            "air_density_kg_m3":
                None,

            "density_ratio":
                None,
        }


def calculate_rpm_factor(
    rpm: Optional[float],
) -> Optional[float]:

    if rpm is None:

        return None

    if rpm <= 0:

        return 0.0


    if rpm < IDLE_RPM:

        return clamp(
            rpm / IDLE_RPM * 0.30,
            0.0,
            0.30,
        )


    if rpm <= REFERENCE_RPM:

        progress = (
            rpm - IDLE_RPM
        ) / (
            REFERENCE_RPM
            -
            IDLE_RPM
        )

        return clamp(
            0.30
            +
            (
                0.70
                *
                progress
            ),
            0.0,
            1.0,
        )


    if rpm <= MAX_MODEL_RPM:

        progress = (
            rpm
            -
            REFERENCE_RPM
        ) / (
            MAX_MODEL_RPM
            -
            REFERENCE_RPM
        )

        return clamp(
            1.0
            -
            (
                0.12
                *
                progress
            ),
            0.0,
            1.0,
        )


    return 0.80


def calculate_throttle_factor(
    throttle_percent: Optional[float],
) -> Optional[float]:

    if throttle_percent is None:

        return None

    return clamp(
        throttle_percent / 100.0,
        0.0,
        1.0,
    )


def calculate_load_factor(
    load_percent: Optional[float],
) -> Optional[float]:

    if load_percent is None:

        return None

    return clamp(
        load_percent / 100.0,
        0.0,
        1.0,
    )


def calculate_altitude_power_factor(
    altitude_m: float,
    density_ratio: Optional[float],
) -> float:

    altitude = max(
        0.0,
        altitude_m,
    )


    if altitude <= CONSTANT_POWER_ALTITUDE_M:

        return 1.0


    if density_ratio is None:

        excess_altitude = (
            altitude
            -
            CONSTANT_POWER_ALTITUDE_M
        )

        fallback = (
            1.0
            -
            (
                excess_altitude
                /
                10000.0
            )
            *
            0.35
        )

        return clamp(
            fallback,
            0.30,
            1.0,
        )


    reference_atmosphere = (
        get_atmosphere(
            CONSTANT_POWER_ALTITUDE_M
        )
    )


    reference_density_ratio = (
        reference_atmosphere.get(
            "density_ratio"
        )
    )


    if (
        reference_density_ratio is None
        or reference_density_ratio <= 0
    ):

        reference_density_ratio = 0.72


    factor = (
        density_ratio
        /
        reference_density_ratio
    )


    return clamp(
        factor,
        0.30,
        1.0,
    )


def calculate_available_power_kw(
    *,
    rpm_factor: Optional[float],
    altitude_power_factor: Optional[float],
) -> Optional[float]:

    if (
        rpm_factor is None
        or altitude_power_factor is None
    ):

        return None


    return (
        BASELINE_POWER_KW
        *
        rpm_factor
        *
        altitude_power_factor
    )


def calculate_expected_power_kw(
    *,
    available_power_kw: Optional[float],
    throttle_factor: Optional[float],
    load_factor: Optional[float],
) -> Optional[float]:

    if available_power_kw is None:

        return None


    factors = [

        value

        for value in (
            throttle_factor,
            load_factor,
        )

        if value is not None
    ]


    if not factors:

        return None


    if (
        throttle_factor is not None
        and load_factor is not None
    ):

        demand_factor = (

            0.45
            *
            throttle_factor

            +

            0.55
            *
            load_factor
        )

    else:

        demand_factor = factors[0]


    demand_factor = clamp(
        demand_factor,
        0.0,
        1.0,
    )


    return (
        available_power_kw
        *
        demand_factor
    )


def power_to_torque_nm(
    power_kw: Optional[float],
    rpm: Optional[float],
) -> Optional[float]:

    if (
        power_kw is None
        or rpm is None
    ):

        return None


    if rpm <= 0:

        return 0.0


    angular_velocity = (

        2.0
        *
        pi
        *
        rpm
        /
        60.0
    )


    if angular_velocity <= 0:

        return 0.0


    return (

        power_kw
        *
        1000.0

        /
        angular_velocity
    )


def calculate_power_utilization(
    expected_power_kw: Optional[float],
    available_power_kw: Optional[float],
) -> Optional[float]:

    if (
        expected_power_kw is None
        or available_power_kw is None
    ):

        return None


    if available_power_kw <= 0:

        if expected_power_kw <= 0:

            return 0.0

        return None


    return clamp(
        expected_power_kw
        /
        available_power_kw,
        0.0,
        1.0,
    )


def calculate_power_margin_kw(
    available_power_kw: Optional[float],
    expected_power_kw: Optional[float],
) -> Optional[float]:

    if (
        available_power_kw is None
        or expected_power_kw is None
    ):

        return None


    return max(
        0.0,
        available_power_kw
        -
        expected_power_kw,
    )


def determine_operating_region(
    *,
    rpm: Optional[float],
    load_factor: Optional[float],
    altitude_m: float,
) -> str:

    if rpm is None:

        return "UNKNOWN"


    if rpm <= 50.0:

        return "STOPPED"


    if rpm < IDLE_RPM:

        return "STARTING"


    if rpm < 1000.0:

        return "IDLE"


    if altitude_m > CONSTANT_POWER_ALTITUDE_M:

        if (
            load_factor is not None
            and load_factor >= 0.80
        ):

            return "HIGH_ALTITUDE_HIGH_LOAD"

        return "HIGH_ALTITUDE"


    if (
        load_factor is not None
        and load_factor >= 0.85
    ):

        return "HIGH_LOAD"


    if (
        load_factor is not None
        and load_factor <= 0.30
    ):

        return "LOW_LOAD"


    return "NORMAL"


def calculate_performance(
    *,
    rpm: Any,
    throttle_percent: Any,
    load_percent: Any,
    altitude_m: Any = 0.0,
) -> PerformanceState:

    global _latest_state
    global _calculation_count
    global _failed_calculation_count


    try:

        rpm_value = safe_float(
            rpm
        )


        if (
            rpm_value is not None
            and rpm_value < 0
        ):

            rpm_value = 0.0


        throttle = normalize_percent(
            throttle_percent
        )


        load = normalize_percent(
            load_percent
        )


        altitude = safe_float(
            altitude_m,
            0.0,
        )


        if altitude is None:

            altitude = 0.0


        altitude = max(
            0.0,
            altitude,
        )


        atmosphere = (
            get_atmosphere(
                altitude
            )
        )


        air_density = (
            atmosphere.get(
                "air_density_kg_m3"
            )
        )


        density_ratio = (
            atmosphere.get(
                "density_ratio"
            )
        )


        rpm_factor = (
            calculate_rpm_factor(
                rpm_value
            )
        )


        throttle_factor = (
            calculate_throttle_factor(
                throttle
            )
        )


        load_factor = (
            calculate_load_factor(
                load
            )
        )


        altitude_factor = (
            calculate_altitude_power_factor(

                altitude,

                density_ratio,
            )
        )


        available_power = (
            calculate_available_power_kw(

                rpm_factor=(
                    rpm_factor
                ),

                altitude_power_factor=(
                    altitude_factor
                ),
            )
        )


        expected_power = (
            calculate_expected_power_kw(

                available_power_kw=(
                    available_power
                ),

                throttle_factor=(
                    throttle_factor
                ),

                load_factor=(
                    load_factor
                ),
            )
        )


        available_torque = (
            power_to_torque_nm(

                available_power,

                rpm_value,
            )
        )


        expected_torque = (
            power_to_torque_nm(

                expected_power,

                rpm_value,
            )
        )


        utilization = (
            calculate_power_utilization(

                expected_power,

                available_power,
            )
        )


        margin = (
            calculate_power_margin_kw(

                available_power,

                expected_power,
            )
        )


        operating_region = (
            determine_operating_region(

                rpm=rpm_value,

                load_factor=(
                    load_factor
                ),

                altitude_m=altitude,
            )
        )


        result = PerformanceState(

            timestamp=utc_now(),

            rpm=rpm_value,

            throttle_percent=throttle,

            load_percent=load,

            altitude_m=altitude,

            air_density_kg_m3=(
                air_density
            ),

            density_ratio=(
                density_ratio
            ),

            rpm_factor=(
                rpm_factor
            ),

            throttle_factor=(
                throttle_factor
            ),

            load_factor=(
                load_factor
            ),

            altitude_power_factor=(
                altitude_factor
            ),

            available_power_kw=(
                available_power
            ),

            expected_power_kw=(
                expected_power
            ),

            available_torque_nm=(
                available_torque
            ),

            expected_torque_nm=(
                expected_torque
            ),

            power_utilization=(
                utilization
            ),

            power_margin_kw=(
                margin
            ),

            operating_region=(
                operating_region
            ),
        )


        _latest_state = result

        _calculation_count += 1


        return result


    except Exception:

        _failed_calculation_count += 1

        raise


def performance_model(
    observed_state: Dict[str, Any],
) -> Dict[str, Any]:

    if not isinstance(
        observed_state,
        dict,
    ):

        raise TypeError(
            "Observed state must be a dictionary."
        )


    rpm = get_nested(
        observed_state,
        "engine.rpm",
    )


    throttle = get_nested(
        observed_state,
        "engine.throttle_percent",
        "engine.throttlePercent",
    )


    load = get_nested(
        observed_state,
        "engine.load_percent",
        "engine.loadPercent",
    )


    altitude = get_nested(
        observed_state,
        "environment.altitude_m",
        "environment.altitudeM",
    )


    if not is_number(
        altitude
    ):

        altitude = 0.0


    result = calculate_performance(

        rpm=rpm,

        throttle_percent=throttle,

        load_percent=load,

        altitude_m=altitude,
    )


    return {

        "engine": {

            "rpm":
                result.rpm,

            "power_kw":
                result.expected_power_kw,

            "torque_nm":
                result.expected_torque_nm,

            "available_power_kw":
                result.available_power_kw,

            "available_torque_nm":
                result.available_torque_nm,

            "power_margin_kw":
                result.power_margin_kw,
        },


        "_physics": {

            "performance": {

                "model":
                    "PRATIRUP Baseline Performance Map",

                "version":
                    result.version,

                "baseline_power_hp":
                    BASELINE_POWER_HP,

                "baseline_power_kw":
                    BASELINE_POWER_KW,

                "operating_region":
                    result.operating_region,

                "rpm_factor":
                    result.rpm_factor,

                "throttle_factor":
                    result.throttle_factor,

                "load_factor":
                    result.load_factor,

                "altitude_power_factor":
                    result.altitude_power_factor,

                "power_utilization":
                    result.power_utilization,

                "power_margin_kw":
                    result.power_margin_kw,

                "air_density_kg_m3":
                    result.air_density_kg_m3,

                "density_ratio":
                    result.density_ratio,
            }
        },
    }


def performance_map_model(
    observed_state: Dict[str, Any],
) -> Dict[str, Any]:

    return performance_model(
        observed_state
    )


def get_latest_performance() -> Optional[
    PerformanceState
]:

    return _latest_state


def get_latest_performance_dict() -> Optional[
    Dict[str, Any]
]:

    if _latest_state is None:

        return None


    return _latest_state.to_dict()


def get_performance_status() -> Dict[str, Any]:

    return {

        "service":
            "performance_map",

        "status":
            "READY",

        "version":
            PERFORMANCE_MAP_VERSION,

        "baseline_power_hp":
            BASELINE_POWER_HP,

        "baseline_power_kw":
            BASELINE_POWER_KW,

        "constant_power_altitude_ft":
            CONSTANT_POWER_ALTITUDE_FT,

        "constant_power_altitude_m":
            CONSTANT_POWER_ALTITUDE_M,

        "calculation_count":
            _calculation_count,

        "failed_calculation_count":
            _failed_calculation_count,

        "latest_result_available":
            _latest_state is not None,

        "latest_operating_region":
            (
                _latest_state.operating_region

                if _latest_state is not None

                else None
            ),

        "latest_expected_power_kw":
            (
                _latest_state.expected_power_kw

                if _latest_state is not None

                else None
            ),

        "latest_expected_torque_nm":
            (
                _latest_state.expected_torque_nm

                if _latest_state is not None

                else None
            ),

        "timestamp":
            utc_now().isoformat(),
    }


def reset_performance_map() -> None:

    global _latest_state
    global _calculation_count
    global _failed_calculation_count


    _latest_state = None

    _calculation_count = 0

    _failed_calculation_count = 0


def get_performance_info() -> Dict[str, Any]:

    return {

        "name":
            "PRATIRUP Engine Performance Map",

        "version":
            PERFORMANCE_MAP_VERSION,

        "type":
            "physics",

        "baseline": {

            "power_hp":
                BASELINE_POWER_HP,

            "power_kw":
                BASELINE_POWER_KW,

            "constant_power_altitude_ft":
                CONSTANT_POWER_ALTITUDE_FT,

            "constant_power_altitude_m":
                CONSTANT_POWER_ALTITUDE_M,
        },

        "outputs": [

            "available_power_kw",

            "expected_power_kw",

            "available_torque_nm",

            "expected_torque_nm",

            "rpm_factor",

            "throttle_factor",

            "load_factor",

            "altitude_power_factor",

            "power_utilization",

            "power_margin_kw",

            "operating_region",
        ],

        "important":
            (
                "Baseline Digital Twin performance model. "
                "Replace the analytical envelope with verified "
                "engine performance maps when test data becomes "
                "available."
            ),
    }
