from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Any, Dict, Optional, Tuple

from backend.physics.atmosphere import (
    SEA_LEVEL_DENSITY_KG_M3,
)

from backend.physics.thermodynamics import (
    calculate_thermodynamics,
)

from backend.physics.combustion import (
    calculate_combustion,
)


COOLING_MODEL_VERSION = "1.0.0"


BASE_CHT_C = 145.0


MIN_EXPECTED_CHT_C = 70.0

MAX_EXPECTED_CHT_C = 260.0


REFERENCE_RPM = 2200.0

REFERENCE_LOAD_PERCENT = 60.0

REFERENCE_AMBIENT_C = 15.0


LOAD_HEATING_GAIN_C = 70.0

THROTTLE_HEATING_GAIN_C = 25.0

RPM_HEATING_GAIN_C = 20.0

COMBUSTION_HEATING_GAIN_C = 35.0


RPM_COOLING_GAIN_C = 25.0

AIR_DENSITY_COOLING_GAIN_C = 20.0

AMBIENT_TEMP_GAIN = 0.45


CYLINDER_CHT_OFFSETS_C: Tuple[
    float,
    float,
    float,
    float,
] = (
    -3.0,
    1.5,
    4.0,
    -1.0,
)


@dataclass
class CoolingState:

    timestamp: datetime

    rpm: Optional[float]

    throttle_percent: Optional[float]

    load_percent: Optional[float]

    altitude_m: float

    ambient_temperature_c: float

    air_density_kg_m3: float

    thermal_load_factor: Optional[float]

    cooling_effectiveness: Optional[float]

    ambient_cooling_factor: Optional[float]

    density_cooling_factor: Optional[float]

    rpm_cooling_factor: Optional[float]

    mean_cht_c: Optional[float]

    cylinder1_c: Optional[float]

    cylinder2_c: Optional[float]

    cylinder3_c: Optional[float]

    cylinder4_c: Optional[float]

    cht_spread_c: Optional[float]

    version: str = COOLING_MODEL_VERSION


    def to_dict(
        self,
    ) -> Dict[str, Any]:

        return {

            "timestamp":
                self.timestamp.isoformat(),

            "version":
                self.version,

            "rpm":
                self.rpm,

            "throttle_percent":
                self.throttle_percent,

            "load_percent":
                self.load_percent,

            "altitude_m":
                self.altitude_m,

            "ambient_temperature_c":
                self.ambient_temperature_c,

            "air_density_kg_m3":
                self.air_density_kg_m3,

            "thermal_load_factor":
                self.thermal_load_factor,

            "cooling_effectiveness":
                self.cooling_effectiveness,

            "ambient_cooling_factor":
                self.ambient_cooling_factor,

            "density_cooling_factor":
                self.density_cooling_factor,

            "rpm_cooling_factor":
                self.rpm_cooling_factor,

            "mean_cht_c":
                self.mean_cht_c,

            "cht": {

                "cylinder1_c":
                    self.cylinder1_c,

                "cylinder2_c":
                    self.cylinder2_c,

                "cylinder3_c":
                    self.cylinder3_c,

                "cylinder4_c":
                    self.cylinder4_c,
            },

            "cht_spread_c":
                self.cht_spread_c,
        }


_latest_state: Optional[
    CoolingState
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


def calculate_rpm_cooling_factor(
    rpm: Optional[float],
) -> Optional[float]:

    if rpm is None:

        return None


    if rpm <= 0:

        return 0.0


    return clamp(
        rpm / REFERENCE_RPM,
        0.0,
        1.25,
    )


def calculate_density_cooling_factor(
    air_density_kg_m3: Optional[float],
) -> Optional[float]:

    if air_density_kg_m3 is None:

        return None


    if air_density_kg_m3 <= 0:

        return 0.0


    return clamp(
        (
            air_density_kg_m3
            /
            SEA_LEVEL_DENSITY_KG_M3
        ),
        0.0,
        1.2,
    )


def calculate_ambient_cooling_factor(
    ambient_temperature_c: Optional[float],
) -> Optional[float]:

    if ambient_temperature_c is None:

        return None


    difference = (
        REFERENCE_AMBIENT_C
        -
        ambient_temperature_c
    )


    factor = (
        1.0
        +
        difference
        /
        100.0
    )


    return clamp(
        factor,
        0.6,
        1.4,
    )


def calculate_cooling_effectiveness(
    rpm_factor: Optional[float],
    density_factor: Optional[float],
    ambient_factor: Optional[float],
) -> Optional[float]:

    factors = [

        value

        for value in (
            rpm_factor,
            density_factor,
            ambient_factor,
        )

        if value is not None
    ]


    if not factors:

        return None


    return clamp(
        sum(factors)
        /
        len(factors),
        0.0,
        1.3,
    )


def calculate_expected_mean_cht(
    *,
    rpm: Optional[float],
    throttle_percent: Optional[float],
    load_percent: Optional[float],
    thermal_load_factor: Optional[float],
    ambient_temperature_c: Optional[float],
    cooling_effectiveness: Optional[float],
) -> Optional[float]:

    available = (

        rpm is not None
        or throttle_percent is not None
        or load_percent is not None
        or thermal_load_factor is not None

    )


    if not available:

        return None


    if (
        rpm is not None
        and rpm <= 0
    ):

        if ambient_temperature_c is None:

            return None


        return clamp(
            ambient_temperature_c + 25.0,
            ambient_temperature_c,
            MAX_EXPECTED_CHT_C,
        )


    load_fraction = (

        load_percent
        /
        100.0

        if load_percent is not None

        else 0.5
    )


    throttle_fraction = (

        throttle_percent
        /
        100.0

        if throttle_percent is not None

        else 0.5
    )


    rpm_fraction = (

        clamp(
            rpm / REFERENCE_RPM,
            0.0,
            1.5,
        )

        if rpm is not None

        else 1.0
    )


    thermal_fraction = (

        thermal_load_factor

        if thermal_load_factor
        is not None

        else (
            load_fraction
            +
            throttle_fraction
        ) / 2.0
    )


    load_heating = (
        LOAD_HEATING_GAIN_C
        *
        load_fraction
    )


    throttle_heating = (
        THROTTLE_HEATING_GAIN_C
        *
        throttle_fraction
    )


    rpm_heating = (
        RPM_HEATING_GAIN_C
        *
        rpm_fraction
    )


    combustion_heating = (
        COMBUSTION_HEATING_GAIN_C
        *
        thermal_fraction
    )


    cooling = (

        cooling_effectiveness

        if cooling_effectiveness
        is not None

        else 1.0
    )


    cooling_correction = (
        RPM_COOLING_GAIN_C
        *
        cooling
    )


    ambient_correction = 0.0


    if ambient_temperature_c is not None:

        ambient_correction = (
            (
                ambient_temperature_c
                -
                REFERENCE_AMBIENT_C
            )
            *
            AMBIENT_TEMP_GAIN
        )


    expected_cht = (

        BASE_CHT_C

        +
        load_heating

        +
        throttle_heating

        +
        rpm_heating

        +
        combustion_heating

        -
        cooling_correction

        +
        ambient_correction
    )


    return clamp(
        expected_cht,
        MIN_EXPECTED_CHT_C,
        MAX_EXPECTED_CHT_C,
    )


def calculate_cylinder_cht(
    mean_cht_c: Optional[float],
) -> Tuple[
    Optional[float],
    Optional[float],
    Optional[float],
    Optional[float],
]:

    if mean_cht_c is None:

        return (
            None,
            None,
            None,
            None,
        )


    values = tuple(

        clamp(
            mean_cht_c + offset,
            MIN_EXPECTED_CHT_C,
            MAX_EXPECTED_CHT_C,
        )

        for offset
        in CYLINDER_CHT_OFFSETS_C
    )


    return values


def calculate_cht_spread(
    cylinders: Tuple[
        Optional[float],
        Optional[float],
        Optional[float],
        Optional[float],
    ],
) -> Optional[float]:

    available = [

        value

        for value
        in cylinders

        if value is not None
    ]


    if len(available) < 2:

        return None


    return (
        max(available)
        -
        min(available)
    )


def calculate_cooling(
    *,
    rpm: Any,
    throttle_percent: Any,
    load_percent: Any,
    altitude_m: Any = 0.0,
    fuel_flow_kg_s: Any = None,
) -> CoolingState:

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


        thermo = calculate_thermodynamics(

            rpm=rpm_value,

            throttle_percent=throttle,

            load_percent=load,

            altitude_m=altitude_m,

            fuel_flow_kg_s=fuel_flow_kg_s,
        )


        combustion = calculate_combustion(

            rpm=rpm_value,

            throttle_percent=throttle,

            load_percent=load,

            altitude_m=altitude_m,

            fuel_flow_kg_s=fuel_flow_kg_s,
        )


        rpm_cooling = (
            calculate_rpm_cooling_factor(
                rpm_value
            )
        )


        density_cooling = (
            calculate_density_cooling_factor(
                thermo
                .ambient_air_density_kg_m3
            )
        )


        ambient_cooling = (
            calculate_ambient_cooling_factor(
                thermo
                .ambient_temperature_c
            )
        )


        cooling_effectiveness = (
            calculate_cooling_effectiveness(

                rpm_factor=(
                    rpm_cooling
                ),

                density_factor=(
                    density_cooling
                ),

                ambient_factor=(
                    ambient_cooling
                ),
            )
        )


        thermal_load = (
            thermo
            .thermal_load_factor
        )


        mean_cht = (
            calculate_expected_mean_cht(

                rpm=rpm_value,

                throttle_percent=throttle,

                load_percent=load,

                thermal_load_factor=(
                    thermal_load
                ),

                ambient_temperature_c=(
                    thermo
                    .ambient_temperature_c
                ),

                cooling_effectiveness=(
                    cooling_effectiveness
                ),
            )
        )


        cylinders = (
            calculate_cylinder_cht(
                mean_cht
            )
        )


        spread = (
            calculate_cht_spread(
                cylinders
            )
        )


        result = CoolingState(

            timestamp=utc_now(),

            rpm=rpm_value,

            throttle_percent=throttle,

            load_percent=load,

            altitude_m=(
                thermo.altitude_m
            ),

            ambient_temperature_c=(
                thermo
                .ambient_temperature_c
            ),

            air_density_kg_m3=(
                thermo
                .ambient_air_density_kg_m3
            ),

            thermal_load_factor=(
                thermal_load
            ),

            cooling_effectiveness=(
                cooling_effectiveness
            ),

            ambient_cooling_factor=(
                ambient_cooling
            ),

            density_cooling_factor=(
                density_cooling
            ),

            rpm_cooling_factor=(
                rpm_cooling
            ),

            mean_cht_c=(
                mean_cht
            ),

            cylinder1_c=(
                cylinders[0]
            ),

            cylinder2_c=(
                cylinders[1]
            ),

            cylinder3_c=(
                cylinders[2]
            ),

            cylinder4_c=(
                cylinders[3]
            ),

            cht_spread_c=(
                spread
            ),
        )


        _latest_state = result

        _calculation_count += 1


        return result


    except Exception:

        _failed_calculation_count += 1

        raise


def cooling_model(
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


    fuel_flow = get_nested(
        observed_state,
        "fuel.flow_kg_per_second",
        "fuel.flowKgPerSecond",
    )


    result = calculate_cooling(

        rpm=rpm,

        throttle_percent=throttle,

        load_percent=load,

        altitude_m=altitude,

        fuel_flow_kg_s=fuel_flow,
    )


    return {

        "cht": {

            "cylinder1_c":
                result.cylinder1_c,

            "cylinder2_c":
                result.cylinder2_c,

            "cylinder3_c":
                result.cylinder3_c,

            "cylinder4_c":
                result.cylinder4_c,
        },


        "_physics": {

            "cooling": {

                "model":
                    "PRATIRUP Baseline Cooling Model",

                "version":
                    result.version,

                "mean_cht_c":
                    result.mean_cht_c,

                "cht_spread_c":
                    result.cht_spread_c,

                "thermal_load_factor":
                    result.thermal_load_factor,

                "cooling_effectiveness":
                    result.cooling_effectiveness,

                "rpm_cooling_factor":
                    result.rpm_cooling_factor,

                "density_cooling_factor":
                    result.density_cooling_factor,

                "ambient_cooling_factor":
                    result.ambient_cooling_factor,

                "combustion_efficiency":
                    combustion_efficiency_from_latest(),
            }
        },
    }


def combustion_efficiency_from_latest() -> Optional[float]:

    try:

        from backend.physics.combustion import (
            get_latest_combustion,
        )


        latest = (
            get_latest_combustion()
        )


        if latest is None:

            return None


        return (
            latest.combustion_efficiency
        )


    except Exception:

        return None


def get_latest_cooling() -> Optional[
    CoolingState
]:

    return _latest_state


def get_latest_cooling_dict() -> Optional[
    Dict[str, Any]
]:

    if _latest_state is None:

        return None


    return _latest_state.to_dict()


def get_cooling_status() -> Dict[str, Any]:

    return {

        "service":
            "cooling_model",

        "status":
            "READY",

        "version":
            COOLING_MODEL_VERSION,

        "calculation_count":
            _calculation_count,

        "failed_calculation_count":
            _failed_calculation_count,

        "latest_result_available":
            _latest_state is not None,

        "latest_mean_cht_c":
            (
                _latest_state.mean_cht_c

                if _latest_state
                is not None

                else None
            ),

        "timestamp":
            utc_now().isoformat(),
    }


def reset_cooling_model() -> None:

    global _latest_state

    global _calculation_count
    global _failed_calculation_count


    _latest_state = None

    _calculation_count = 0

    _failed_calculation_count = 0


def get_cooling_info() -> Dict[str, Any]:

    return {

        "name":
            "PRATIRUP Engine Cooling Model",

        "version":
            COOLING_MODEL_VERSION,

        "type":
            "physics",

        "purpose":
            (
                "Estimate expected cylinder-head "
                "temperature and cooling behaviour."
            ),

        "outputs": [
            "cylinder1_cht",
            "cylinder2_cht",
            "cylinder3_cht",
            "cylinder4_cht",
            "mean_cht",
            "cht_spread",
            "cooling_effectiveness",
            "thermal_load_factor",
        ],

        "dependencies": [
            "atmosphere.py",
            "thermodynamics.py",
            "combustion.py",
        ],

        "important":
            (
                "Baseline engineering model only. "
                "Real engine thermal data must be used "
                "for final calibration."
            ),
    }
