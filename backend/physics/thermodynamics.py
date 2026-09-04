from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Any, Dict, Optional

from backend.physics.atmosphere import (
    AIR_GAS_CONSTANT_J_KG_K,
    calculate_atmosphere,
)


THERMODYNAMICS_MODEL_VERSION = "1.0.0"


BASELINE_ENGINE_POWER_HP = 180.0

HP_TO_KW = 0.745699872

BASELINE_ENGINE_POWER_KW = (
    BASELINE_ENGINE_POWER_HP
    *
    HP_TO_KW
)


DEFAULT_DISPLACEMENT_L = 5.5

LITERS_TO_M3 = 0.001


FOUR_STROKE_CYCLE_REVOLUTIONS = 2.0


MIN_VOLUMETRIC_EFFICIENCY = 0.55

MAX_VOLUMETRIC_EFFICIENCY = 0.92

BASE_VOLUMETRIC_EFFICIENCY = 0.82


STOICHIOMETRIC_AFR = 14.7


MIN_MANIFOLD_PRESSURE_RATIO = 0.30

MAX_MANIFOLD_PRESSURE_RATIO = 1.00


MAX_INTAKE_HEATING_C = 15.0


@dataclass
class ThermodynamicState:

    timestamp: datetime

    rpm: Optional[float]

    throttle_percent: Optional[float]

    load_percent: Optional[float]

    altitude_m: float

    ambient_temperature_c: float

    ambient_pressure_kpa: float

    ambient_air_density_kg_m3: float

    manifold_pressure_kpa: Optional[float]

    manifold_pressure_pa: Optional[float]

    intake_temperature_c: Optional[float]

    intake_temperature_k: Optional[float]

    intake_air_density_kg_m3: Optional[float]

    volumetric_efficiency: Optional[float]

    air_mass_flow_kg_s: Optional[float]

    air_mass_per_cycle_kg: Optional[float]

    fuel_flow_kg_s: Optional[float]

    estimated_afr: Optional[float]

    equivalence_ratio: Optional[float]

    thermal_load_factor: Optional[float]

    version: str = THERMODYNAMICS_MODEL_VERSION


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

            "ambient_pressure_kpa":
                self.ambient_pressure_kpa,

            "ambient_air_density_kg_m3":
                self.ambient_air_density_kg_m3,

            "manifold_pressure_kpa":
                self.manifold_pressure_kpa,

            "manifold_pressure_pa":
                self.manifold_pressure_pa,

            "intake_temperature_c":
                self.intake_temperature_c,

            "intake_temperature_k":
                self.intake_temperature_k,

            "intake_air_density_kg_m3":
                self.intake_air_density_kg_m3,

            "volumetric_efficiency":
                self.volumetric_efficiency,

            "air_mass_flow_kg_s":
                self.air_mass_flow_kg_s,

            "air_mass_per_cycle_kg":
                self.air_mass_per_cycle_kg,

            "fuel_flow_kg_s":
                self.fuel_flow_kg_s,

            "estimated_afr":
                self.estimated_afr,

            "equivalence_ratio":
                self.equivalence_ratio,

            "thermal_load_factor":
                self.thermal_load_factor,
        }


_latest_state: Optional[
    ThermodynamicState
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


def calculate_manifold_pressure_kpa(
    ambient_pressure_kpa: float,
    throttle_percent: Optional[float],
) -> Optional[float]:

    if throttle_percent is None:

        return None


    throttle_fraction = (
        throttle_percent
        /
        100.0
    )


    pressure_ratio = (
        MIN_MANIFOLD_PRESSURE_RATIO
        +
        (
            MAX_MANIFOLD_PRESSURE_RATIO
            -
            MIN_MANIFOLD_PRESSURE_RATIO
        )
        *
        throttle_fraction
    )


    pressure_ratio = clamp(
        pressure_ratio,
        MIN_MANIFOLD_PRESSURE_RATIO,
        MAX_MANIFOLD_PRESSURE_RATIO,
    )


    return (
        ambient_pressure_kpa
        *
        pressure_ratio
    )


def calculate_intake_temperature_c(
    ambient_temperature_c: float,
    throttle_percent: Optional[float],
    load_percent: Optional[float],
) -> float:

    load_fraction = (
        load_percent / 100.0
        if load_percent is not None
        else 0.0
    )


    throttle_fraction = (
        throttle_percent / 100.0
        if throttle_percent is not None
        else 0.0
    )


    heating_factor = clamp(
        (
            0.6 * load_fraction
            +
            0.4 * throttle_fraction
        ),
        0.0,
        1.0,
    )


    return (
        ambient_temperature_c
        +
        (
            MAX_INTAKE_HEATING_C
            *
            heating_factor
        )
    )


def calculate_volumetric_efficiency(
    rpm: Optional[float],
    load_percent: Optional[float],
) -> Optional[float]:

    if rpm is None:

        return None


    if rpm <= 0:

        return 0.0


    target_rpm = 2200.0

    rpm_deviation = (
        abs(
            rpm
            -
            target_rpm
        )
        /
        target_rpm
    )


    rpm_penalty = min(
        rpm_deviation * 0.20,
        0.20,
    )


    load_bonus = 0.0


    if load_percent is not None:

        load_bonus = (
            (
                load_percent
                /
                100.0
            )
            *
            0.08
        )


    efficiency = (
        BASE_VOLUMETRIC_EFFICIENCY
        -
        rpm_penalty
        +
        load_bonus
    )


    return clamp(
        efficiency,
        MIN_VOLUMETRIC_EFFICIENCY,
        MAX_VOLUMETRIC_EFFICIENCY,
    )


def calculate_intake_density(
    manifold_pressure_pa: Optional[float],
    intake_temperature_k: Optional[float],
) -> Optional[float]:

    if (
        manifold_pressure_pa is None
        or intake_temperature_k is None
    ):

        return None


    if (
        manifold_pressure_pa < 0
        or intake_temperature_k <= 0
    ):

        return None


    return (
        manifold_pressure_pa
        /
        (
            AIR_GAS_CONSTANT_J_KG_K
            *
            intake_temperature_k
        )
    )


def calculate_air_mass_flow(
    rpm: Optional[float],
    intake_density_kg_m3: Optional[float],
    volumetric_efficiency: Optional[float],
    displacement_l: float = DEFAULT_DISPLACEMENT_L,
) -> Optional[float]:

    if (
        rpm is None
        or intake_density_kg_m3 is None
        or volumetric_efficiency is None
    ):

        return None


    if rpm <= 0:

        return 0.0


    displacement_m3 = (
        displacement_l
        *
        LITERS_TO_M3
    )


    intake_cycles_per_second = (
        rpm
        /
        (
            FOUR_STROKE_CYCLE_REVOLUTIONS
            *
            60.0
        )
    )


    return (
        intake_density_kg_m3
        *
        displacement_m3
        *
        volumetric_efficiency
        *
        intake_cycles_per_second
    )


def calculate_air_mass_per_cycle(
    air_mass_flow_kg_s: Optional[float],
    rpm: Optional[float],
) -> Optional[float]:

    if (
        air_mass_flow_kg_s is None
        or rpm is None
    ):

        return None


    if rpm <= 0:

        return None


    cycles_per_second = (
        rpm
        /
        (
            FOUR_STROKE_CYCLE_REVOLUTIONS
            *
            60.0
        )
    )


    if cycles_per_second <= 0:

        return None


    return (
        air_mass_flow_kg_s
        /
        cycles_per_second
    )


def calculate_afr(
    air_mass_flow_kg_s: Optional[float],
    fuel_flow_kg_s: Optional[float],
) -> Optional[float]:

    if (
        air_mass_flow_kg_s is None
        or fuel_flow_kg_s is None
    ):

        return None


    if fuel_flow_kg_s <= 0:

        return None


    if air_mass_flow_kg_s < 0:

        return None


    return (
        air_mass_flow_kg_s
        /
        fuel_flow_kg_s
    )


def calculate_equivalence_ratio(
    afr: Optional[float],
) -> Optional[float]:

    if afr is None:

        return None


    if afr <= 0:

        return None


    return (
        STOICHIOMETRIC_AFR
        /
        afr
    )


def calculate_thermal_load_factor(
    rpm: Optional[float],
    throttle_percent: Optional[float],
    load_percent: Optional[float],
) -> Optional[float]:

    available = [
        value
        for value
        in (
            rpm,
            throttle_percent,
            load_percent,
        )
        if value is not None
    ]


    if not available:

        return None


    rpm_factor = (
        clamp(
            rpm / 3000.0,
            0.0,
            1.0,
        )
        if rpm is not None
        else None
    )


    throttle_factor = (
        throttle_percent / 100.0
        if throttle_percent is not None
        else None
    )


    load_factor = (
        load_percent / 100.0
        if load_percent is not None
        else None
    )


    factors = [
        factor
        for factor
        in (
            rpm_factor,
            throttle_factor,
            load_factor,
        )
        if factor is not None
    ]


    if not factors:

        return None


    return clamp(
        sum(factors)
        /
        len(factors),
        0.0,
        1.0,
    )


def calculate_thermodynamics(
    *,
    rpm: Any,
    throttle_percent: Any,
    load_percent: Any,
    altitude_m: Any = 0.0,
    fuel_flow_kg_s: Any = None,
    displacement_l: float = DEFAULT_DISPLACEMENT_L,
) -> ThermodynamicState:

    global _latest_state

    global _calculation_count
    global _failed_calculation_count


    try:

        normalized_rpm = (
            safe_float(
                rpm
            )
        )


        if (
            normalized_rpm is not None
            and normalized_rpm < 0
        ):

            normalized_rpm = 0.0


        throttle = normalize_percent(
            throttle_percent
        )


        load = normalize_percent(
            load_percent
        )


        fuel_flow = safe_float(
            fuel_flow_kg_s
        )


        if (
            fuel_flow is not None
            and fuel_flow < 0
        ):

            fuel_flow = None


        atmosphere = calculate_atmosphere(
            altitude_m
        )


        manifold_pressure_kpa = (
            calculate_manifold_pressure_kpa(
                atmosphere.pressure_kpa,
                throttle,
            )
        )


        manifold_pressure_pa = (
            manifold_pressure_kpa
            *
            1000.0

            if manifold_pressure_kpa
            is not None

            else None
        )


        intake_temperature_c = (
            calculate_intake_temperature_c(
                atmosphere.temperature_c,
                throttle,
                load,
            )
        )


        intake_temperature_k = (
            intake_temperature_c
            +
            273.15
        )


        volumetric_efficiency = (
            calculate_volumetric_efficiency(
                normalized_rpm,
                load,
            )
        )


        intake_density = (
            calculate_intake_density(
                manifold_pressure_pa,
                intake_temperature_k,
            )
        )


        air_mass_flow = (
            calculate_air_mass_flow(
                rpm=normalized_rpm,
                intake_density_kg_m3=(
                    intake_density
                ),
                volumetric_efficiency=(
                    volumetric_efficiency
                ),
                displacement_l=(
                    displacement_l
                ),
            )
        )


        air_mass_per_cycle = (
            calculate_air_mass_per_cycle(
                air_mass_flow,
                normalized_rpm,
            )
        )


        afr = calculate_afr(
            air_mass_flow,
            fuel_flow,
        )


        equivalence_ratio = (
            calculate_equivalence_ratio(
                afr
            )
        )


        thermal_load = (
            calculate_thermal_load_factor(
                normalized_rpm,
                throttle,
                load,
            )
        )


        result = ThermodynamicState(

            timestamp=utc_now(),

            rpm=normalized_rpm,

            throttle_percent=throttle,

            load_percent=load,

            altitude_m=(
                atmosphere.altitude_m
            ),

            ambient_temperature_c=(
                atmosphere.temperature_c
            ),

            ambient_pressure_kpa=(
                atmosphere.pressure_kpa
            ),

            ambient_air_density_kg_m3=(
                atmosphere
                .air_density_kg_m3
            ),

            manifold_pressure_kpa=(
                manifold_pressure_kpa
            ),

            manifold_pressure_pa=(
                manifold_pressure_pa
            ),

            intake_temperature_c=(
                intake_temperature_c
            ),

            intake_temperature_k=(
                intake_temperature_k
            ),

            intake_air_density_kg_m3=(
                intake_density
            ),

            volumetric_efficiency=(
                volumetric_efficiency
            ),

            air_mass_flow_kg_s=(
                air_mass_flow
            ),

            air_mass_per_cycle_kg=(
                air_mass_per_cycle
            ),

            fuel_flow_kg_s=(
                fuel_flow
            ),

            estimated_afr=(
                afr
            ),

            equivalence_ratio=(
                equivalence_ratio
            ),

            thermal_load_factor=(
                thermal_load
            ),
        )


        _latest_state = result

        _calculation_count += 1


        return result


    except Exception:

        _failed_calculation_count += 1

        raise


def thermodynamics_model(
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


    thermo = calculate_thermodynamics(

        rpm=rpm,

        throttle_percent=throttle,

        load_percent=load,

        altitude_m=altitude,

        fuel_flow_kg_s=fuel_flow,
    )


    return {

        "environment": {

            "altitude_m":
                thermo.altitude_m,

            "ambient_temperature_c":
                thermo.ambient_temperature_c,

            "ambient_pressure_kpa":
                thermo.ambient_pressure_kpa,

            "air_density_kg_m3":
                thermo
                .ambient_air_density_kg_m3,
        },


        "_physics": {

            "thermodynamics": {

                "model":
                    "PRATIRUP Baseline Thermodynamics",

                "version":
                    thermo.version,

                "manifold_pressure_kpa":
                    thermo.manifold_pressure_kpa,

                "manifold_pressure_pa":
                    thermo.manifold_pressure_pa,

                "intake_temperature_c":
                    thermo.intake_temperature_c,

                "intake_temperature_k":
                    thermo.intake_temperature_k,

                "intake_air_density_kg_m3":
                    thermo
                    .intake_air_density_kg_m3,

                "volumetric_efficiency":
                    thermo.volumetric_efficiency,

                "air_mass_flow_kg_s":
                    thermo.air_mass_flow_kg_s,

                "air_mass_per_cycle_kg":
                    thermo.air_mass_per_cycle_kg,

                "fuel_flow_kg_s":
                    thermo.fuel_flow_kg_s,

                "estimated_afr":
                    thermo.estimated_afr,

                "equivalence_ratio":
                    thermo.equivalence_ratio,

                "thermal_load_factor":
                    thermo.thermal_load_factor,
            }
        },
    }


def get_latest_thermodynamics() -> Optional[
    ThermodynamicState
]:

    return _latest_state


def get_latest_thermodynamics_dict() -> Optional[
    Dict[str, Any]
]:

    if _latest_state is None:

        return None


    return _latest_state.to_dict()


def get_thermodynamics_status() -> Dict[str, Any]:

    return {

        "service":
            "thermodynamics_model",

        "status":
            "READY",

        "version":
            THERMODYNAMICS_MODEL_VERSION,

        "engine_baseline_power_hp":
            BASELINE_ENGINE_POWER_HP,

        "engine_baseline_power_kw":
            BASELINE_ENGINE_POWER_KW,

        "baseline_displacement_l":
            DEFAULT_DISPLACEMENT_L,

        "calculation_count":
            _calculation_count,

        "failed_calculation_count":
            _failed_calculation_count,

        "latest_result_available":
            _latest_state is not None,

        "timestamp":
            utc_now().isoformat(),
    }


def reset_thermodynamics_model() -> None:

    global _latest_state

    global _calculation_count
    global _failed_calculation_count


    _latest_state = None

    _calculation_count = 0

    _failed_calculation_count = 0


def get_thermodynamics_info() -> Dict[str, Any]:

    return {

        "name":
            "PRATIRUP Engine Thermodynamics Model",

        "version":
            THERMODYNAMICS_MODEL_VERSION,

        "type":
            "physics",

        "purpose":
            (
                "Estimate baseline intake and thermodynamic "
                "conditions for the aero-piston Digital Twin."
            ),

        "outputs": [
            "manifold_pressure",
            "intake_temperature",
            "intake_density",
            "volumetric_efficiency",
            "air_mass_flow",
            "air_mass_per_cycle",
            "air_fuel_ratio",
            "equivalence_ratio",
            "thermal_load_factor",
        ],

        "assumptions": [
            "Four-stroke piston engine",
            "Baseline naturally aspirated manifold approximation",
            "Approximate volumetric-efficiency curve",
            "Gasoline-like stoichiometric AFR baseline",
            "Engine displacement is currently a configurable placeholder",
        ],

        "important":
            (
                "Replace baseline assumptions with verified "
                "engine calibration data when available."
            ),
    }
