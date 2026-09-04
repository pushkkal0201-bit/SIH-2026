from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite, pi
from typing import Any, Dict, List, Optional

from backend.physics.atmosphere import (
    calculate_atmosphere,
)


COMBUSTION_MODEL_VERSION = "1.1.0"


BASELINE_POWER_HP = 180.0

HP_TO_KW = 0.745699872

BASELINE_POWER_KW = (
    BASELINE_POWER_HP
    *
    HP_TO_KW
)

REFERENCE_RPM = 2200.0

MAX_MODEL_RPM = 3000.0

ENGINE_OFF_RPM = 50.0


STOICHIOMETRIC_AFR = 14.7


REFERENCE_BSFC_KG_PER_KWH = 0.270

MIN_BSFC_KG_PER_KWH = 0.235

MAX_BSFC_KG_PER_KWH = 0.390


MIN_COMBUSTION_EFFICIENCY = 0.18

MAX_COMBUSTION_EFFICIENCY = 0.36

REFERENCE_COMBUSTION_EFFICIENCY = 0.32


BASE_EGT_C = 500.0

MAX_EXPECTED_EGT_C = 950.0

MIN_EXPECTED_EGT_C = 100.0


REFERENCE_DISPLACEMENT_M3 = 0.0040


@dataclass
class CombustionState:

    timestamp: datetime

    rpm: Optional[float]

    throttle_percent: Optional[float]

    load_percent: Optional[float]

    altitude_m: float

    ambient_pressure_pa: Optional[float]

    air_density_kg_m3: Optional[float]

    density_ratio: Optional[float]

    estimated_power_kw: Optional[float]

    estimated_torque_nm: Optional[float]

    expected_fuel_flow_kg_s: Optional[float]

    measured_fuel_flow_kg_s: Optional[float]

    bsfc_kg_per_kwh: Optional[float]

    estimated_air_flow_kg_s: Optional[float]

    air_fuel_ratio: Optional[float]

    combustion_efficiency: Optional[float]

    mean_effective_pressure_pa: Optional[float]

    peak_cylinder_pressure_pa: Optional[float]

    egt_cylinder1_c: Optional[float]

    egt_cylinder2_c: Optional[float]

    egt_cylinder3_c: Optional[float]

    egt_cylinder4_c: Optional[float]

    operating_state: str

    version: str = COMBUSTION_MODEL_VERSION


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

            "ambient_pressure_pa":
                self.ambient_pressure_pa,

            "air_density_kg_m3":
                self.air_density_kg_m3,

            "density_ratio":
                self.density_ratio,

            "estimated_power_kw":
                self.estimated_power_kw,

            "estimated_torque_nm":
                self.estimated_torque_nm,

            "expected_fuel_flow_kg_s":
                self.expected_fuel_flow_kg_s,

            "measured_fuel_flow_kg_s":
                self.measured_fuel_flow_kg_s,

            "bsfc_kg_per_kwh":
                self.bsfc_kg_per_kwh,

            "estimated_air_flow_kg_s":
                self.estimated_air_flow_kg_s,

            "air_fuel_ratio":
                self.air_fuel_ratio,

            "combustion_efficiency":
                self.combustion_efficiency,

            "mean_effective_pressure_pa":
                self.mean_effective_pressure_pa,

            "peak_cylinder_pressure_pa":
                self.peak_cylinder_pressure_pa,

            "egt": {

                "cylinder1_c":
                    self.egt_cylinder1_c,

                "cylinder2_c":
                    self.egt_cylinder2_c,

                "cylinder3_c":
                    self.egt_cylinder3_c,

                "cylinder4_c":
                    self.egt_cylinder4_c,
            },

            "operating_state":
                self.operating_state,
        }


_latest_state: Optional[
    CombustionState
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

    if rpm < 800.0:

        return "IDLE"

    return "RUNNING"


def calculate_rpm_factor(
    rpm: Optional[float],
) -> Optional[float]:

    if rpm is None:

        return None

    if rpm <= 0:

        return 0.0

    return clamp(
        rpm / REFERENCE_RPM,
        0.0,
        1.20,
    )


def calculate_combustion_efficiency(
    *,
    rpm: Optional[float],
    throttle_percent: Optional[float],
    load_percent: Optional[float],
) -> Optional[float]:

    if rpm is None:

        return None

    if rpm < ENGINE_OFF_RPM:

        return 0.0


    rpm_factor = clamp(
        rpm / REFERENCE_RPM,
        0.0,
        1.5,
    )


    throttle_factor = (

        throttle_percent / 100.0

        if throttle_percent is not None

        else 0.5
    )


    load_factor = (

        load_percent / 100.0

        if load_percent is not None

        else 0.5
    )


    load_quality = (
        1.0
        -
        abs(
            load_factor - 0.70
        )
    )

    load_quality = clamp(
        load_quality,
        0.0,
        1.0,
    )


    rpm_quality = (
        1.0
        -
        abs(
            rpm_factor - 1.0
        )
        *
        0.30
    )

    rpm_quality = clamp(
        rpm_quality,
        0.0,
        1.0,
    )


    efficiency = (

        0.22

        +

        0.06
        *
        load_quality

        +

        0.04
        *
        rpm_quality

        +

        0.02
        *
        throttle_factor
    )


    return clamp(
        efficiency,
        MIN_COMBUSTION_EFFICIENCY,
        MAX_COMBUSTION_EFFICIENCY,
    )


def calculate_estimated_power_kw(
    *,
    rpm: Optional[float],
    throttle_percent: Optional[float],
    load_percent: Optional[float],
    density_ratio: Optional[float],
) -> Optional[float]:

    if rpm is None:

        return None

    if rpm < ENGINE_OFF_RPM:

        return 0.0


    rpm_factor = clamp(
        rpm / REFERENCE_RPM,
        0.0,
        1.0,
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


    available_demand_factors = [

        value

        for value in (
            throttle_factor,
            load_factor,
        )

        if value is not None
    ]


    if not available_demand_factors:

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

        demand_factor = (
            available_demand_factors[0]
        )


    density_factor = (

        clamp(
            density_ratio,
            0.45,
            1.0,
        )

        if density_ratio is not None

        else 1.0
    )


    power = (

        BASELINE_POWER_KW

        *
        rpm_factor

        *
        clamp(
            demand_factor,
            0.0,
            1.0,
        )

        *
        density_factor
    )


    return max(
        0.0,
        power,
    )


def calculate_torque_nm(
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


def calculate_bsfc(
    *,
    rpm: Optional[float],
    load_percent: Optional[float],
) -> Optional[float]:

    if rpm is None:

        return None

    if rpm < ENGINE_OFF_RPM:

        return None


    rpm_factor = clamp(
        rpm / REFERENCE_RPM,
        0.0,
        1.5,
    )


    load_factor = (

        load_percent / 100.0

        if load_percent is not None

        else 0.5
    )


    load_penalty = (

        abs(
            load_factor
            -
            0.70
        )
        *
        0.10
    )


    rpm_penalty = (

        abs(
            rpm_factor
            -
            1.0
        )
        *
        0.055
    )


    bsfc = (

        REFERENCE_BSFC_KG_PER_KWH

        +
        load_penalty

        +
        rpm_penalty
    )


    return clamp(
        bsfc,
        MIN_BSFC_KG_PER_KWH,
        MAX_BSFC_KG_PER_KWH,
    )


def calculate_expected_fuel_flow(
    *,
    power_kw: Optional[float],
    bsfc_kg_per_kwh: Optional[float],
    rpm: Optional[float],
) -> Optional[float]:

    if rpm is None:

        return None


    if rpm < ENGINE_OFF_RPM:

        return 0.0


    if (
        power_kw is None
        or bsfc_kg_per_kwh is None
    ):

        return None


    fuel_flow = (

        power_kw

        *
        bsfc_kg_per_kwh

        /
        3600.0
    )


    return max(
        0.0,
        fuel_flow,
    )


def calculate_air_flow(
    expected_fuel_flow_kg_s: Optional[float],
    *,
    load_percent: Optional[float],
) -> Optional[float]:

    if expected_fuel_flow_kg_s is None:

        return None


    if expected_fuel_flow_kg_s <= 0:

        return 0.0


    load_factor = (

        load_percent / 100.0

        if load_percent is not None

        else 0.5
    )


    target_afr = (

        STOICHIOMETRIC_AFR

        -
        (
            1.5
            *
            load_factor
        )
    )


    target_afr = clamp(
        target_afr,
        12.5,
        STOICHIOMETRIC_AFR,
    )


    return (

        expected_fuel_flow_kg_s

        *
        target_afr
    )


def calculate_air_fuel_ratio(
    air_flow_kg_s: Optional[float],
    fuel_flow_kg_s: Optional[float],
) -> Optional[float]:

    if (
        air_flow_kg_s is None
        or fuel_flow_kg_s is None
    ):

        return None


    if fuel_flow_kg_s <= 0:

        return None


    return (
        air_flow_kg_s
        /
        fuel_flow_kg_s
    )


def calculate_egt_values(
    *,
    rpm: Optional[float],
    load_percent: Optional[float],
    throttle_percent: Optional[float],
    combustion_efficiency: Optional[float],
    ambient_temperature_c: Optional[float],
) -> List[Optional[float]]:

    if rpm is None:

        return [
            None,
            None,
            None,
            None,
        ]


    if rpm < ENGINE_OFF_RPM:

        ambient = (

            ambient_temperature_c

            if ambient_temperature_c
            is not None

            else 15.0
        )

        residual_temperature = (
            ambient
            +
            35.0
        )


        return [
            residual_temperature,
            residual_temperature,
            residual_temperature,
            residual_temperature,
        ]


    rpm_factor = clamp(
        rpm / REFERENCE_RPM,
        0.0,
        1.5,
    )


    load_factor = (

        load_percent / 100.0

        if load_percent is not None

        else 0.5
    )


    throttle_factor = (

        throttle_percent / 100.0

        if throttle_percent is not None

        else 0.5
    )


    efficiency = (

        combustion_efficiency

        if combustion_efficiency is not None

        else REFERENCE_COMBUSTION_EFFICIENCY
    )


    ambient = (

        ambient_temperature_c

        if ambient_temperature_c is not None

        else 15.0
    )


    mean_egt = (

        BASE_EGT_C

        +

        130.0
        *
        load_factor

        +

        80.0
        *
        throttle_factor

        +

        35.0
        *
        rpm_factor

        +

        80.0
        *
        efficiency

        +

        (
            ambient
            -
            15.0
        )
        *
        0.20
    )


    mean_egt = clamp(
        mean_egt,
        MIN_EXPECTED_EGT_C,
        MAX_EXPECTED_EGT_C,
    )


    offsets = (
        -7.0,
        2.5,
        7.0,
        -1.5,
    )


    return [

        clamp(
            mean_egt + offset,
            MIN_EXPECTED_EGT_C,
            MAX_EXPECTED_EGT_C,
        )

        for offset in offsets
    ]


def calculate_mean_effective_pressure(
    torque_nm: Optional[float],
) -> Optional[float]:

    if torque_nm is None:

        return None


    if REFERENCE_DISPLACEMENT_M3 <= 0:

        return None


    return (

        4.0
        *
        pi
        *
        torque_nm

        /
        REFERENCE_DISPLACEMENT_M3
    )


def calculate_combustion(
    *,
    rpm: Any,
    throttle_percent: Any,
    load_percent: Any,
    altitude_m: Any = 0.0,
    fuel_flow_kg_s: Any = None,
) -> CombustionState:

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


        measured_fuel_flow = safe_float(
            fuel_flow_kg_s
        )


        if (
            measured_fuel_flow is not None
            and measured_fuel_flow < 0
        ):

            measured_fuel_flow = None


        atmosphere = calculate_atmosphere(
            altitude
        )


        ambient_pressure_pa = (
            safe_float(
                getattr(
                    atmosphere,
                    "pressure_pa",
                    None,
                )
            )
        )


        ambient_temperature_c = (
            safe_float(
                getattr(
                    atmosphere,
                    "temperature_c",
                    None,
                )
            )
        )


        air_density = (
            safe_float(
                getattr(
                    atmosphere,
                    "air_density_kg_m3",
                    None,
                )
            )
        )


        if air_density is None:

            air_density = (
                safe_float(
                    getattr(
                        atmosphere,
                        "density_kg_m3",
                        None,
                    )
                )
            )


        density_ratio = (
            safe_float(
                getattr(
                    atmosphere,
                    "density_ratio",
                    None,
                )
            )
        )


        operating_state = (
            determine_operating_state(
                rpm_value
            )
        )


        combustion_efficiency = (
            calculate_combustion_efficiency(

                rpm=rpm_value,

                throttle_percent=throttle,

                load_percent=load,
            )
        )


        estimated_power_kw = (
            calculate_estimated_power_kw(

                rpm=rpm_value,

                throttle_percent=throttle,

                load_percent=load,

                density_ratio=density_ratio,
            )
        )


        estimated_torque_nm = (
            calculate_torque_nm(

                estimated_power_kw,

                rpm_value,
            )
        )


        bsfc = calculate_bsfc(

            rpm=rpm_value,

            load_percent=load,
        )


        expected_fuel_flow = (
            calculate_expected_fuel_flow(

                power_kw=(
                    estimated_power_kw
                ),

                bsfc_kg_per_kwh=(
                    bsfc
                ),

                rpm=rpm_value,
            )
        )


        air_flow = (
            calculate_air_flow(

                expected_fuel_flow,

                load_percent=load,
            )
        )


        afr = (
            calculate_air_fuel_ratio(

                air_flow,

                expected_fuel_flow,
            )
        )


        egt_values = (
            calculate_egt_values(

                rpm=rpm_value,

                load_percent=load,

                throttle_percent=throttle,

                combustion_efficiency=(
                    combustion_efficiency
                ),

                ambient_temperature_c=(
                    ambient_temperature_c
                ),
            )
        )


        mean_effective_pressure = (
            calculate_mean_effective_pressure(
                estimated_torque_nm
            )
        )


        peak_cylinder_pressure = None


        result = CombustionState(

            timestamp=utc_now(),

            rpm=rpm_value,

            throttle_percent=throttle,

            load_percent=load,

            altitude_m=altitude,

            ambient_pressure_pa=(
                ambient_pressure_pa
            ),

            air_density_kg_m3=(
                air_density
            ),

            density_ratio=(
                density_ratio
            ),

            estimated_power_kw=(
                estimated_power_kw
            ),

            estimated_torque_nm=(
                estimated_torque_nm
            ),

            expected_fuel_flow_kg_s=(
                expected_fuel_flow
            ),

            measured_fuel_flow_kg_s=(
                measured_fuel_flow
            ),

            bsfc_kg_per_kwh=(
                bsfc
            ),

            estimated_air_flow_kg_s=(
                air_flow
            ),

            air_fuel_ratio=(
                afr
            ),

            combustion_efficiency=(
                combustion_efficiency
            ),

            mean_effective_pressure_pa=(
                mean_effective_pressure
            ),

            peak_cylinder_pressure_pa=(
                peak_cylinder_pressure
            ),

            egt_cylinder1_c=(
                egt_values[0]
            ),

            egt_cylinder2_c=(
                egt_values[1]
            ),

            egt_cylinder3_c=(
                egt_values[2]
            ),

            egt_cylinder4_c=(
                egt_values[3]
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


def combustion_model(
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


    measured_fuel_flow = get_nested(
        observed_state,
        "fuel.flow_kg_per_second",
        "fuel.flowKgPerSecond",
    )


    result = calculate_combustion(

        rpm=rpm,

        throttle_percent=throttle,

        load_percent=load,

        altitude_m=altitude,

        fuel_flow_kg_s=(
            measured_fuel_flow
        ),
    )


    return {

        "engine": {

            "power_kw":
                result.estimated_power_kw,

            "torque_nm":
                result.estimated_torque_nm,
        },


        "egt": {

            "cylinder1_c":
                result.egt_cylinder1_c,

            "cylinder2_c":
                result.egt_cylinder2_c,

            "cylinder3_c":
                result.egt_cylinder3_c,

            "cylinder4_c":
                result.egt_cylinder4_c,
        },


        "fuel": {

            "flow_kg_per_second":
                result.expected_fuel_flow_kg_s,
        },


        "_physics": {

            "combustion": {

                "model":
                    "PRATIRUP Baseline Combustion Model",

                "version":
                    result.version,

                "operating_state":
                    result.operating_state,

                "combustion_efficiency":
                    result.combustion_efficiency,

                "bsfc_kg_per_kwh":
                    result.bsfc_kg_per_kwh,

                "estimated_air_flow_kg_s":
                    result.estimated_air_flow_kg_s,

                "air_fuel_ratio":
                    result.air_fuel_ratio,

                "mean_effective_pressure_pa":
                    result.mean_effective_pressure_pa,

                "peak_cylinder_pressure_pa":
                    result.peak_cylinder_pressure_pa,

                "measured_fuel_flow_kg_s":
                    result.measured_fuel_flow_kg_s,

                "expected_fuel_flow_kg_s":
                    result.expected_fuel_flow_kg_s,

                "fuel_prediction_independent":
                    True,
            }
        },
    }


def get_latest_combustion() -> Optional[
    CombustionState
]:

    return _latest_state


def get_latest_combustion_dict() -> Optional[
    Dict[str, Any]
]:

    if _latest_state is None:

        return None

    return _latest_state.to_dict()


def get_combustion_status() -> Dict[str, Any]:

    return {

        "service":
            "combustion_model",

        "status":
            "READY",

        "version":
            COMBUSTION_MODEL_VERSION,

        "fuel_prediction_independent":
            True,

        "calculation_count":
            _calculation_count,

        "failed_calculation_count":
            _failed_calculation_count,

        "latest_result_available":
            _latest_state is not None,

        "latest_operating_state":
            (
                _latest_state.operating_state

                if _latest_state is not None

                else None
            ),

        "latest_expected_fuel_flow_kg_s":
            (
                _latest_state
                .expected_fuel_flow_kg_s

                if _latest_state is not None

                else None
            ),

        "latest_measured_fuel_flow_kg_s":
            (
                _latest_state
                .measured_fuel_flow_kg_s

                if _latest_state is not None

                else None
            ),

        "timestamp":
            utc_now().isoformat(),
    }


def reset_combustion_model() -> None:

    global _latest_state
    global _calculation_count
    global _failed_calculation_count


    _latest_state = None

    _calculation_count = 0

    _failed_calculation_count = 0


def get_combustion_info() -> Dict[str, Any]:

    return {

        "name":
            "PRATIRUP Combustion Model",

        "version":
            COMBUSTION_MODEL_VERSION,

        "type":
            "physics",

        "baseline_power_hp":
            BASELINE_POWER_HP,

        "baseline_power_kw":
            BASELINE_POWER_KW,

        "fuel_prediction": {

            "method":
                "BSFC-based independent estimation",

            "uses_measured_fuel_flow":
                False,

            "reference_bsfc_kg_per_kwh":
                REFERENCE_BSFC_KG_PER_KWH,
        },

        "outputs": [

            "expected_fuel_flow_kg_s",

            "estimated_power_kw",

            "estimated_torque_nm",

            "combustion_efficiency",

            "air_fuel_ratio",

            "egt_cylinder1_c",

            "egt_cylinder2_c",

            "egt_cylinder3_c",

            "egt_cylinder4_c",

            "mean_effective_pressure_pa",
        ],

        "important":
            (
                "Fuel prediction is independent from the "
                "measured fuel-flow sensor so that fuel-flow "
                "residuals remain diagnostically meaningful."
            ),
    }
