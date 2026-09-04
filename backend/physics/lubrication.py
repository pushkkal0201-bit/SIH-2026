from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Any, Dict, Optional

from backend.physics.thermodynamics import (
    calculate_thermodynamics,
)

from backend.physics.cooling import (
    calculate_cooling,
)


LUBRICATION_MODEL_VERSION = "1.0.0"


REFERENCE_RPM = 2200.0

REFERENCE_LOAD_PERCENT = 60.0

REFERENCE_AMBIENT_C = 15.0


IDLE_OIL_PRESSURE_KPA = 200.0

REFERENCE_OIL_PRESSURE_KPA = 380.0

MAX_OIL_PRESSURE_KPA = 520.0


BASE_OIL_TEMPERATURE_C = 75.0

REFERENCE_OIL_TEMPERATURE_C = 95.0

MAX_EXPECTED_OIL_TEMPERATURE_C = 135.0

MIN_EXPECTED_OIL_TEMPERATURE_C = 20.0


RPM_PRESSURE_GAIN_KPA = 210.0

LOAD_PRESSURE_GAIN_KPA = 35.0

TEMPERATURE_PRESSURE_LOSS_KPA = 1.25


LOAD_TEMP_GAIN_C = 35.0

RPM_TEMP_GAIN_C = 15.0

THERMAL_TEMP_GAIN_C = 25.0

COOLING_TEMP_REDUCTION_C = 20.0


ENGINE_OFF_RPM = 50.0

LOW_RPM_THRESHOLD = 800.0


@dataclass
class LubricationState:

    timestamp: datetime

    rpm: Optional[float]

    throttle_percent: Optional[float]

    load_percent: Optional[float]

    altitude_m: float

    ambient_temperature_c: float

    expected_oil_pressure_kpa: Optional[float]

    expected_oil_temperature_c: Optional[float]

    lubrication_effectiveness: Optional[float]

    pressure_factor: Optional[float]

    temperature_factor: Optional[float]

    thermal_load_factor: Optional[float]

    cooling_effectiveness: Optional[float]

    operating_state: str

    version: str = LUBRICATION_MODEL_VERSION


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

            "expected_oil_pressure_kpa":
                self.expected_oil_pressure_kpa,

            "expected_oil_temperature_c":
                self.expected_oil_temperature_c,

            "lubrication_effectiveness":
                self.lubrication_effectiveness,

            "pressure_factor":
                self.pressure_factor,

            "temperature_factor":
                self.temperature_factor,

            "thermal_load_factor":
                self.thermal_load_factor,

            "cooling_effectiveness":
                self.cooling_effectiveness,

            "operating_state":
                self.operating_state,
        }


_latest_state: Optional[
    LubricationState
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


def determine_operating_state(
    rpm: Optional[float],
) -> str:

    if rpm is None:

        return "UNKNOWN"


    if rpm < ENGINE_OFF_RPM:

        return "STOPPED"


    if rpm < LOW_RPM_THRESHOLD:

        return "LOW_RPM"


    return "RUNNING"


def calculate_expected_oil_temperature(
    *,
    rpm: Optional[float],
    load_percent: Optional[float],
    ambient_temperature_c: Optional[float],
    thermal_load_factor: Optional[float],
    cooling_effectiveness: Optional[float],
) -> Optional[float]:

    if rpm is None:

        return None


    ambient = (

        ambient_temperature_c

        if ambient_temperature_c
        is not None

        else REFERENCE_AMBIENT_C
    )


    if rpm < ENGINE_OFF_RPM:

        return clamp(
            ambient + 20.0,
            MIN_EXPECTED_OIL_TEMPERATURE_C,
            MAX_EXPECTED_OIL_TEMPERATURE_C,
        )


    rpm_fraction = clamp(
        rpm / REFERENCE_RPM,
        0.0,
        1.5,
    )


    load_fraction = (

        load_percent / 100.0

        if load_percent is not None

        else 0.5
    )


    thermal_fraction = (

        thermal_load_factor

        if thermal_load_factor is not None

        else load_fraction
    )


    cooling = (

        cooling_effectiveness

        if cooling_effectiveness is not None

        else 1.0
    )


    temperature = (

        BASE_OIL_TEMPERATURE_C

        +

        (
            LOAD_TEMP_GAIN_C
            *
            load_fraction
        )

        +

        (
            RPM_TEMP_GAIN_C
            *
            rpm_fraction
        )

        +

        (
            THERMAL_TEMP_GAIN_C
            *
            thermal_fraction
        )

        -

        (
            COOLING_TEMP_REDUCTION_C
            *
            cooling
        )

        +

        (
            (
                ambient
                -
                REFERENCE_AMBIENT_C
            )
            *
            0.30
        )
    )


    return clamp(
        temperature,
        MIN_EXPECTED_OIL_TEMPERATURE_C,
        MAX_EXPECTED_OIL_TEMPERATURE_C,
    )


def calculate_expected_oil_pressure(
    *,
    rpm: Optional[float],
    load_percent: Optional[float],
    oil_temperature_c: Optional[float],
) -> Optional[float]:

    if rpm is None:

        return None


    if rpm < ENGINE_OFF_RPM:

        return 0.0


    rpm_fraction = clamp(
        rpm / REFERENCE_RPM,
        0.0,
        1.5,
    )


    load_fraction = (

        load_percent / 100.0

        if load_percent is not None

        else 0.5
    )


    pressure = (

        IDLE_OIL_PRESSURE_KPA

        +

        (
            RPM_PRESSURE_GAIN_KPA
            *
            rpm_fraction
        )

        +

        (
            LOAD_PRESSURE_GAIN_KPA
            *
            load_fraction
        )
    )


    if oil_temperature_c is not None:

        temperature_excess = max(
            0.0,
            oil_temperature_c
            -
            REFERENCE_OIL_TEMPERATURE_C,
        )


        pressure -= (
            temperature_excess
            *
            TEMPERATURE_PRESSURE_LOSS_KPA
        )


    return clamp(
        pressure,
        0.0,
        MAX_OIL_PRESSURE_KPA,
    )


def calculate_pressure_factor(
    oil_pressure_kpa: Optional[float],
    rpm: Optional[float],
) -> Optional[float]:

    if (
        oil_pressure_kpa is None
        or rpm is None
    ):

        return None


    if rpm < ENGINE_OFF_RPM:

        return 1.0


    return clamp(
        oil_pressure_kpa
        /
        REFERENCE_OIL_PRESSURE_KPA,
        0.0,
        1.0,
    )


def calculate_temperature_factor(
    oil_temperature_c: Optional[float],
) -> Optional[float]:

    if oil_temperature_c is None:

        return None


    deviation = abs(
        oil_temperature_c
        -
        REFERENCE_OIL_TEMPERATURE_C
    )


    factor = (
        1.0
        -
        (
            deviation
            /
            100.0
        )
    )


    return clamp(
        factor,
        0.0,
        1.0,
    )


def calculate_lubrication_effectiveness(
    *,
    pressure_factor: Optional[float],
    temperature_factor: Optional[float],
) -> Optional[float]:

    available = [

        value

        for value
        in (
            pressure_factor,
            temperature_factor,
        )

        if value is not None
    ]


    if not available:

        return None


    return clamp(
        sum(available)
        /
        len(available),
        0.0,
        1.0,
    )


def calculate_lubrication(
    *,
    rpm: Any,
    throttle_percent: Any,
    load_percent: Any,
    altitude_m: Any = 0.0,
    fuel_flow_kg_s: Any = None,
) -> LubricationState:

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


        cooling = calculate_cooling(

            rpm=rpm_value,

            throttle_percent=throttle,

            load_percent=load,

            altitude_m=altitude_m,

            fuel_flow_kg_s=fuel_flow_kg_s,
        )


        operating_state = (
            determine_operating_state(
                rpm_value
            )
        )


        oil_temperature = (
            calculate_expected_oil_temperature(

                rpm=rpm_value,

                load_percent=load,

                ambient_temperature_c=(
                    thermo
                    .ambient_temperature_c
                ),

                thermal_load_factor=(
                    thermo
                    .thermal_load_factor
                ),

                cooling_effectiveness=(
                    cooling
                    .cooling_effectiveness
                ),
            )
        )


        oil_pressure = (
            calculate_expected_oil_pressure(

                rpm=rpm_value,

                load_percent=load,

                oil_temperature_c=(
                    oil_temperature
                ),
            )
        )


        pressure_factor = (
            calculate_pressure_factor(

                oil_pressure,

                rpm_value,
            )
        )


        temperature_factor = (
            calculate_temperature_factor(
                oil_temperature
            )
        )


        lubrication_effectiveness = (
            calculate_lubrication_effectiveness(

                pressure_factor=(
                    pressure_factor
                ),

                temperature_factor=(
                    temperature_factor
                ),
            )
        )


        result = LubricationState(

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

            expected_oil_pressure_kpa=(
                oil_pressure
            ),

            expected_oil_temperature_c=(
                oil_temperature
            ),

            lubrication_effectiveness=(
                lubrication_effectiveness
            ),

            pressure_factor=(
                pressure_factor
            ),

            temperature_factor=(
                temperature_factor
            ),

            thermal_load_factor=(
                thermo
                .thermal_load_factor
            ),

            cooling_effectiveness=(
                cooling
                .cooling_effectiveness
            ),

            operating_state=(
                operating_state
            ),
        )


        _latest_state = result

        _calculation_count += 1


        return result


    except Exception:

        _failed_calculation_count += 1

        raise


def lubrication_model(
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


    result = calculate_lubrication(

        rpm=rpm,

        throttle_percent=throttle,

        load_percent=load,

        altitude_m=altitude,

        fuel_flow_kg_s=fuel_flow,
    )


    return {

        "oil": {

            "pressure_kpa":
                result
                .expected_oil_pressure_kpa,

            "temperature_c":
                result
                .expected_oil_temperature_c,
        },


        "_physics": {

            "lubrication": {

                "model":
                    "PRATIRUP Baseline Lubrication",

                "version":
                    result.version,

                "operating_state":
                    result.operating_state,

                "lubrication_effectiveness":
                    result
                    .lubrication_effectiveness,

                "pressure_factor":
                    result.pressure_factor,

                "temperature_factor":
                    result.temperature_factor,

                "thermal_load_factor":
                    result.thermal_load_factor,

                "cooling_effectiveness":
                    result.cooling_effectiveness,
            }
        },
    }


def get_latest_lubrication() -> Optional[
    LubricationState
]:

    return _latest_state


def get_latest_lubrication_dict() -> Optional[
    Dict[str, Any]
]:

    if _latest_state is None:

        return None


    return _latest_state.to_dict()


def get_lubrication_status() -> Dict[str, Any]:

    return {

        "service":
            "lubrication_model",

        "status":
            "READY",

        "version":
            LUBRICATION_MODEL_VERSION,

        "calculation_count":
            _calculation_count,

        "failed_calculation_count":
            _failed_calculation_count,

        "latest_result_available":
            _latest_state is not None,

        "latest_operating_state":
            (
                _latest_state.operating_state

                if _latest_state
                is not None

                else None
            ),

        "latest_oil_pressure_kpa":
            (
                _latest_state
                .expected_oil_pressure_kpa

                if _latest_state
                is not None

                else None
            ),

        "latest_oil_temperature_c":
            (
                _latest_state
                .expected_oil_temperature_c

                if _latest_state
                is not None

                else None
            ),

        "timestamp":
            utc_now().isoformat(),
    }


def reset_lubrication_model() -> None:

    global _latest_state

    global _calculation_count
    global _failed_calculation_count


    _latest_state = None

    _calculation_count = 0

    _failed_calculation_count = 0


def get_lubrication_info() -> Dict[str, Any]:

    return {

        "name":
            "PRATIRUP Lubrication Model",

        "version":
            LUBRICATION_MODEL_VERSION,

        "type":
            "physics",

        "purpose":
            (
                "Estimate expected oil-pressure and "
                "oil-temperature behaviour for the "
                "Digital Twin."
            ),

        "outputs": [
            "expected_oil_pressure_kpa",
            "expected_oil_temperature_c",
            "lubrication_effectiveness",
            "pressure_factor",
            "temperature_factor",
            "operating_state",
        ],

        "dependencies": [
            "atmosphere.py",
            "thermodynamics.py",
            "combustion.py",
            "cooling.py",
        ],

        "important":
            (
                "Baseline simulation model only. "
                "Replace coefficients using verified "
                "engine lubrication data."
            ),
    }
