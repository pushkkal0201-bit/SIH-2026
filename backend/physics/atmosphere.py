from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Any, Dict, Optional


ATMOSPHERE_MODEL_VERSION = "1.0.0"


SEA_LEVEL_TEMPERATURE_K = 288.15

SEA_LEVEL_TEMPERATURE_C = 15.0

SEA_LEVEL_PRESSURE_PA = 101325.0

SEA_LEVEL_DENSITY_KG_M3 = 1.225


TEMPERATURE_LAPSE_RATE_K_M = 0.0065


GRAVITY_M_S2 = 9.80665


AIR_GAS_CONSTANT_J_KG_K = 287.05


TROPOPAUSE_ALTITUDE_M = 11000.0


METERS_TO_FEET = 3.280839895


@dataclass
class AtmosphereState:

    timestamp: datetime

    altitude_m: float

    altitude_ft: float

    temperature_c: float

    temperature_k: float

    pressure_pa: float

    pressure_kpa: float

    air_density_kg_m3: float

    density_ratio: float

    temperature_ratio: float

    pressure_ratio: float

    model: str = "ISA"

    version: str = ATMOSPHERE_MODEL_VERSION


    def to_dict(
        self,
    ) -> Dict[str, Any]:

        return {

            "timestamp":
                self.timestamp.isoformat(),

            "model":
                self.model,

            "version":
                self.version,

            "altitude_m":
                self.altitude_m,

            "altitude_ft":
                self.altitude_ft,

            "temperature_c":
                self.temperature_c,

            "temperature_k":
                self.temperature_k,

            "pressure_pa":
                self.pressure_pa,

            "pressure_kpa":
                self.pressure_kpa,

            "air_density_kg_m3":
                self.air_density_kg_m3,

            "density_ratio":
                self.density_ratio,

            "temperature_ratio":
                self.temperature_ratio,

            "pressure_ratio":
                self.pressure_ratio,
        }


_latest_state: Optional[
    AtmosphereState
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


            current = current[
                key
            ]


        if found:

            return current


    return None


def normalize_altitude(
    altitude_m: Any,
) -> float:

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


    altitude = min(
        altitude,
        TROPOPAUSE_ALTITUDE_M,
    )


    return altitude


def calculate_temperature_k(
    altitude_m: float,
) -> float:

    return (
        SEA_LEVEL_TEMPERATURE_K
        -
        (
            TEMPERATURE_LAPSE_RATE_K_M
            *
            altitude_m
        )
    )


def calculate_pressure_pa(
    altitude_m: float,
    temperature_k: float,
) -> float:

    exponent = (
        GRAVITY_M_S2
        /
        (
            AIR_GAS_CONSTANT_J_KG_K
            *
            TEMPERATURE_LAPSE_RATE_K_M
        )
    )


    temperature_ratio = (
        temperature_k
        /
        SEA_LEVEL_TEMPERATURE_K
    )


    return (
        SEA_LEVEL_PRESSURE_PA
        *
        (
            temperature_ratio
            **
            exponent
        )
    )


def calculate_air_density(
    pressure_pa: float,
    temperature_k: float,
) -> float:

    return (
        pressure_pa
        /
        (
            AIR_GAS_CONSTANT_J_KG_K
            *
            temperature_k
        )
    )


def calculate_atmosphere(
    altitude_m: Any = 0.0,
) -> AtmosphereState:

    global _latest_state

    global _calculation_count
    global _failed_calculation_count


    try:

        altitude = normalize_altitude(
            altitude_m
        )


        temperature_k = (
            calculate_temperature_k(
                altitude
            )
        )


        temperature_c = (
            temperature_k
            -
            273.15
        )


        pressure_pa = (
            calculate_pressure_pa(
                altitude,
                temperature_k,
            )
        )


        pressure_kpa = (
            pressure_pa
            /
            1000.0
        )


        air_density = (
            calculate_air_density(
                pressure_pa,
                temperature_k,
            )
        )


        density_ratio = (
            air_density
            /
            SEA_LEVEL_DENSITY_KG_M3
        )


        temperature_ratio = (
            temperature_k
            /
            SEA_LEVEL_TEMPERATURE_K
        )


        pressure_ratio = (
            pressure_pa
            /
            SEA_LEVEL_PRESSURE_PA
        )


        result = AtmosphereState(

            timestamp=utc_now(),

            altitude_m=altitude,

            altitude_ft=(
                altitude
                *
                METERS_TO_FEET
            ),

            temperature_c=(
                temperature_c
            ),

            temperature_k=(
                temperature_k
            ),

            pressure_pa=(
                pressure_pa
            ),

            pressure_kpa=(
                pressure_kpa
            ),

            air_density_kg_m3=(
                air_density
            ),

            density_ratio=(
                density_ratio
            ),

            temperature_ratio=(
                temperature_ratio
            ),

            pressure_ratio=(
                pressure_ratio
            ),
        )


        _latest_state = result

        _calculation_count += 1


        return result


    except Exception:

        _failed_calculation_count += 1

        raise


def atmosphere_model(
    observed_state: Dict[str, Any],
) -> Dict[str, Any]:

    if not isinstance(
        observed_state,
        dict,
    ):

        raise TypeError(
            "Observed state must be a dictionary."
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


    atmosphere = (
        calculate_atmosphere(
            altitude
        )
    )


    return {

        "environment": {

            "altitude_m":
                atmosphere.altitude_m,

            "altitude_ft":
                atmosphere.altitude_ft,

            "ambient_temperature_c":
                atmosphere.temperature_c,

            "ambient_pressure_kpa":
                atmosphere.pressure_kpa,

            "air_density_kg_m3":
                atmosphere.air_density_kg_m3,

        },

        "_physics": {

            "atmosphere": {

                "model":
                    atmosphere.model,

                "version":
                    atmosphere.version,

                "temperature_k":
                    atmosphere.temperature_k,

                "pressure_pa":
                    atmosphere.pressure_pa,

                "density_ratio":
                    atmosphere.density_ratio,

                "temperature_ratio":
                    atmosphere.temperature_ratio,

                "pressure_ratio":
                    atmosphere.pressure_ratio,
            }
        },
    }


def get_latest_atmosphere() -> Optional[
    AtmosphereState
]:

    return _latest_state


def get_latest_atmosphere_dict() -> Optional[
    Dict[str, Any]
]:

    if _latest_state is None:

        return None


    return _latest_state.to_dict()


def get_atmosphere_status() -> Dict[str, Any]:

    return {

        "service":
            "atmosphere_model",

        "status":
            "READY",

        "version":
            ATMOSPHERE_MODEL_VERSION,

        "model":
            "ISA Troposphere",

        "supported_altitude_m": {
            "minimum":
                0.0,

            "maximum":
                TROPOPAUSE_ALTITUDE_M,
        },

        "calculation_count":
            _calculation_count,

        "failed_calculation_count":
            _failed_calculation_count,

        "latest_result_available":
            _latest_state is not None,

        "timestamp":
            utc_now().isoformat(),
    }


def reset_atmosphere_model() -> None:

    global _latest_state

    global _calculation_count
    global _failed_calculation_count


    _latest_state = None

    _calculation_count = 0

    _failed_calculation_count = 0


def get_atmosphere_info() -> Dict[str, Any]:

    return {

        "name":
            "PRATIRUP ISA Atmosphere Model",

        "version":
            ATMOSPHERE_MODEL_VERSION,

        "type":
            "physics",

        "purpose":
            (
                "Calculate atmospheric conditions required "
                "by the aero-piston Digital Twin."
            ),

        "outputs": [
            "altitude_m",
            "altitude_ft",
            "ambient_temperature_c",
            "ambient_pressure_kpa",
            "air_density_kg_m3",
            "density_ratio",
            "temperature_ratio",
            "pressure_ratio",
        ],

        "assumptions": [
            "ISA baseline atmosphere",
            "Troposphere model",
            "Altitude currently limited to 0-11000 m",
        ],

        "null_policy":
            (
                "Unavailable calculated quantities are not "
                "silently replaced with sensor measurements."
            ),
    }
