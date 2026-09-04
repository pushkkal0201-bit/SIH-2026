from __future__ import annotations

import asyncio
import math
import random

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from backend.models.schemas import TelemetryFrame


SIMULATION_ADAPTER_VERSION = "1.2.0"

DEFAULT_RANDOM_SEED = 26054

ENGINE_MAX_POWER_KW = 134.226
ENGINE_MAX_TORQUE_NM = 585.0


class SimulationFault(str, Enum):
    OIL_PRESSURE_LOSS = "OIL_PRESSURE_LOSS"
    COOLING_DEGRADATION = "COOLING_DEGRADATION"
    EGT_IMBALANCE = "EGT_IMBALANCE"
    FUEL_PRESSURE_LOSS = "FUEL_PRESSURE_LOSS"
    VIBRATION_INCREASE = "VIBRATION_INCREASE"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:

    return max(
        minimum,
        min(maximum, value),
    )


def _finite_number(
    value: Any,
) -> Optional[float]:

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:
        result = float(value)

    except (TypeError, ValueError):
        return None

    if not math.isfinite(result):
        return None

    return result


def _lerp(
    current: float,
    target: float,
    response: float,
) -> float:

    factor = _clamp(
        response,
        0.0,
        1.0,
    )

    return current + (
        target - current
    ) * factor


def _atmosphere_pressure_kpa(
    altitude_m: float,
) -> float:

    altitude = max(
        0.0,
        altitude_m,
    )

    base = max(
        0.01,
        1.0 - 2.25577e-5 * altitude,
    )

    return 101.325 * (
        base ** 5.25588
    )


def _density_ratio(
    altitude_m: float,
    ambient_temperature_c: float,
) -> float:

    pressure_kpa = (
        _atmosphere_pressure_kpa(
            altitude_m
        )
    )

    temperature_k = max(
        150.0,
        ambient_temperature_c + 273.15,
    )

    density = (
        pressure_kpa * 1000.0
    ) / (
        287.05 * temperature_k
    )

    sea_level_density = 1.225

    return _clamp(
        density / sea_level_density,
        0.20,
        1.20,
    )


@dataclass
class ActiveSimulationFault:

    fault: SimulationFault

    severity: float

    ramp_sec: float = 0.0

    elapsed_sec: float = 0.0

    @property
    def ramp_factor(
        self,
    ) -> float:

        if self.ramp_sec <= 0.0:
            return 1.0

        return _clamp(
            self.elapsed_sec
            / self.ramp_sec,
            0.0,
            1.0,
        )

    @property
    def effective_severity(
        self,
    ) -> float:

        return _clamp(
            self.severity
            * self.ramp_factor,
            0.0,
            1.0,
        )

    def to_dict(
        self,
    ) -> Dict[str, Any]:

        return {
            "fault":
                self.fault.value,

            "severity":
                self.severity,

            "ramp_sec":
                self.ramp_sec,

            "elapsed_sec":
                self.elapsed_sec,

            "ramp_factor":
                self.ramp_factor,

            "effective_severity":
                self.effective_severity,
        }


@dataclass
class SimulatedEngineState:

    rpm: float = 0.0

    throttle_percent: float = 0.0

    load_percent: float = 0.0

    power_kw: float = 0.0

    torque_nm: float = 0.0

    cht1_c: float = 25.0
    cht2_c: float = 25.0
    cht3_c: float = 25.0
    cht4_c: float = 25.0

    egt1_c: float = 25.0
    egt2_c: float = 25.0
    egt3_c: float = 25.0
    egt4_c: float = 25.0

    oil_temperature_c: float = 25.0

    oil_pressure_kpa: float = 0.0

    fuel_flow_kg_s: float = 0.0

    fuel_pressure_kpa: float = 0.0

    vibration_g: float = 0.0

    alternator_voltage_v: float = 0.0

    battery_voltage_v: float = 12.6


class SimulationAdapter:

    def __init__(
        self,
        *,
        random_seed: int = DEFAULT_RANDOM_SEED,
    ) -> None:

        self._random_seed = random_seed

        self._rng = random.Random(
            random_seed
        )

        self._state = (
            SimulatedEngineState()
        )

        self._sequence = 0

        self._generated_frames = 0

        self._ingestion_attempts = 0

        self._ingestion_successes = 0

        self._ingestion_failures = 0

        self._last_error: Optional[
            str
        ] = None

        self._latest_payload: Optional[
            Dict[str, Any]
        ] = None

        self._latest_result: Optional[
            Dict[str, Any]
        ] = None

        self._active_faults: Dict[
            SimulationFault,
            ActiveSimulationFault,
        ] = {}

        self._fault_injection_count = 0

        self._fault_clear_count = 0


    def _extract_targets(
        self,
        command: Dict[str, Any],
    ) -> Tuple[
        float,
        float,
        float,
        float,
        float,
    ]:

        targets = command.get(
            "targets"
        )

        if not isinstance(
            targets,
            dict,
        ):
            raise ValueError(
                "Scenario command does not contain targets."
            )

        engine = targets.get(
            "engine"
        )

        environment = targets.get(
            "environment"
        )

        if not isinstance(
            engine,
            dict,
        ):
            raise ValueError(
                "Scenario command does not contain engine targets."
            )

        if not isinstance(
            environment,
            dict,
        ):
            raise ValueError(
                "Scenario command does not contain environment targets."
            )

        rpm = _finite_number(
            engine.get("rpm")
        )

        throttle = _finite_number(
            engine.get(
                "throttle_percent"
            )
        )

        load = _finite_number(
            engine.get(
                "load_percent"
            )
        )

        altitude = _finite_number(
            environment.get(
                "altitude_m"
            )
        )

        ambient = _finite_number(
            environment.get(
                "ambient_temperature_c"
            )
        )

        required = {
            "rpm":
                rpm,

            "throttle_percent":
                throttle,

            "load_percent":
                load,

            "altitude_m":
                altitude,

            "ambient_temperature_c":
                ambient,
        }

        missing = [
            key
            for key, value
            in required.items()
            if value is None
        ]

        if missing:
            raise ValueError(
                "Scenario command is missing required "
                "simulation targets: "
                + ", ".join(missing)
            )

        return (
            float(rpm),
            float(throttle),
            float(load),
            float(altitude),
            float(ambient),
        )


    def _update_engine_state(
        self,
        *,
        rpm_target: float,
        throttle_target: float,
        load_target: float,
        altitude_m: float,
        ambient_temperature_c: float,
        delta_sec: float,
    ) -> None:

        delta = max(
            0.0,
            delta_sec,
        )

        engine_response = _clamp(
            delta / 1.5,
            0.0,
            1.0,
        )

        thermal_response = _clamp(
            delta / 20.0,
            0.0,
            1.0,
        )

        oil_response = _clamp(
            delta / 12.0,
            0.0,
            1.0,
        )

        self._state.rpm = _lerp(
            self._state.rpm,
            max(
                0.0,
                rpm_target,
            ),
            engine_response,
        )

        self._state.throttle_percent = (
            _lerp(
                self._state.throttle_percent,
                _clamp(
                    throttle_target,
                    0.0,
                    100.0,
                ),
                engine_response,
            )
        )

        self._state.load_percent = (
            _lerp(
                self._state.load_percent,
                _clamp(
                    load_target,
                    0.0,
                    100.0,
                ),
                engine_response,
            )
        )

        rpm = max(
            0.0,
            self._state.rpm,
        )

        throttle = _clamp(
            self._state.throttle_percent,
            0.0,
            100.0,
        )

        load = _clamp(
            self._state.load_percent,
            0.0,
            100.0,
        )


        if rpm < 50.0:

            self._state.power_kw = (
                _lerp(
                    self._state.power_kw,
                    0.0,
                    engine_response,
                )
            )

            self._state.torque_nm = (
                _lerp(
                    self._state.torque_nm,
                    0.0,
                    engine_response,
                )
            )

            self._state.fuel_flow_kg_s = (
                _lerp(
                    self._state.fuel_flow_kg_s,
                    0.0,
                    engine_response,
                )
            )

            self._state.fuel_pressure_kpa = (
                _lerp(
                    self._state.fuel_pressure_kpa,
                    0.0,
                    engine_response,
                )
            )

            self._state.oil_pressure_kpa = (
                _lerp(
                    self._state.oil_pressure_kpa,
                    0.0,
                    oil_response,
                )
            )

            self._state.vibration_g = (
                _lerp(
                    self._state.vibration_g,
                    0.0,
                    engine_response,
                )
            )

            self._state.alternator_voltage_v = (
                _lerp(
                    self._state.alternator_voltage_v,
                    0.0,
                    engine_response,
                )
            )

            self._state.battery_voltage_v = (
                _lerp(
                    self._state.battery_voltage_v,
                    12.6,
                    engine_response,
                )
            )

            for attribute in (
                "cht1_c",
                "cht2_c",
                "cht3_c",
                "cht4_c",
                "egt1_c",
                "egt2_c",
                "egt3_c",
                "egt4_c",
            ):

                current = getattr(
                    self._state,
                    attribute,
                )

                setattr(
                    self._state,
                    attribute,
                    _lerp(
                        current,
                        ambient_temperature_c,
                        thermal_response,
                    ),
                )

            self._state.oil_temperature_c = (
                _lerp(
                    self._state.oil_temperature_c,
                    ambient_temperature_c,
                    oil_response,
                )
            )

            return


        density_ratio = (
            _density_ratio(
                altitude_m,
                ambient_temperature_c,
            )
        )


        altitude_factor = _clamp(
            0.92
            + 0.08 * density_ratio,
            0.82,
            1.0,
        )

        rpm_factor = _clamp(
            rpm / 2500.0,
            0.0,
            1.0,
        )

        throttle_factor = _clamp(
            throttle / 100.0,
            0.0,
            1.0,
        )

        load_factor = _clamp(
            load / 100.0,
            0.0,
            1.0,
        )


        utilization = _clamp(
            1.20
            * load_factor
            * rpm_factor,
            0.0,
            1.0,
        )

        target_power_kw = (
            ENGINE_MAX_POWER_KW
            * utilization
            * altitude_factor
        )

        self._state.power_kw = (
            _lerp(
                self._state.power_kw,
                target_power_kw,
                engine_response,
            )
        )


        if rpm > 1.0:

            target_torque_nm = (
                target_power_kw
                * 60000.0
                / (
                    2.0
                    * math.pi
                    * rpm
                )
            )

        else:
            target_torque_nm = 0.0

        target_torque_nm = _clamp(
            target_torque_nm,
            0.0,
            ENGINE_MAX_TORQUE_NM,
        )

        self._state.torque_nm = (
            _lerp(
                self._state.torque_nm,
                target_torque_nm,
                engine_response,
            )
        )


        bsfc_kg_per_kwh = 0.367

        target_fuel_flow = (
            target_power_kw
            * bsfc_kg_per_kwh
            / 3600.0
        )

        self._state.fuel_flow_kg_s = (
            _lerp(
                self._state.fuel_flow_kg_s,
                target_fuel_flow,
                engine_response,
            )
        )

        target_fuel_pressure = (
            350.0
            + 650.0
            * load_factor
        )

        self._state.fuel_pressure_kpa = (
            _lerp(
                self._state.fuel_pressure_kpa,
                target_fuel_pressure,
                engine_response,
            )
        )


        base_cht = (
            ambient_temperature_c
            + 100.0
            + 190.0 * load_factor
            + 20.0 * throttle_factor
        )

        base_cht -= (
            8.0
            * (
                1.0
                - density_ratio
            )
        )

        cht_targets = (
            base_cht - 3.0,
            base_cht + 2.0,
            base_cht + 5.0,
            base_cht,
        )

        self._state.cht1_c = _lerp(
            self._state.cht1_c,
            cht_targets[0],
            thermal_response,
        )

        self._state.cht2_c = _lerp(
            self._state.cht2_c,
            cht_targets[1],
            thermal_response,
        )

        self._state.cht3_c = _lerp(
            self._state.cht3_c,
            cht_targets[2],
            thermal_response,
        )

        self._state.cht4_c = _lerp(
            self._state.cht4_c,
            cht_targets[3],
            thermal_response,
        )


        base_egt = (
            500.0
            + 350.0
            * throttle_factor
            + 100.0
            * load_factor
        )

        egt_targets = (
            base_egt - 8.0,
            base_egt + 3.0,
            base_egt + 8.0,
            base_egt,
        )

        self._state.egt1_c = _lerp(
            self._state.egt1_c,
            egt_targets[0],
            thermal_response,
        )

        self._state.egt2_c = _lerp(
            self._state.egt2_c,
            egt_targets[1],
            thermal_response,
        )

        self._state.egt3_c = _lerp(
            self._state.egt3_c,
            egt_targets[2],
            thermal_response,
        )

        self._state.egt4_c = _lerp(
            self._state.egt4_c,
            egt_targets[3],
            thermal_response,
        )


        target_oil_temperature = (
            ambient_temperature_c
            + 45.0
            + 40.0 * load_factor
        )

        self._state.oil_temperature_c = (
            _lerp(
                self._state.oil_temperature_c,
                target_oil_temperature,
                oil_response,
            )
        )

        target_oil_pressure = (
            230.0
            + 175.0 * rpm_factor
            - max(
                0.0,
                self._state.oil_temperature_c
                - 100.0,
            ) * 0.8
        )

        target_oil_pressure = max(
            80.0,
            target_oil_pressure,
        )

        self._state.oil_pressure_kpa = (
            _lerp(
                self._state.oil_pressure_kpa,
                target_oil_pressure,
                oil_response,
            )
        )


        target_vibration = (
            0.05
            + 0.11 * rpm_factor
            + 0.08 * load_factor
        )

        self._state.vibration_g = (
            _lerp(
                self._state.vibration_g,
                target_vibration,
                engine_response,
            )
        )


        target_alternator_voltage = (
            14.2
            if rpm >= 600.0
            else 0.0
        )

        target_battery_voltage = (
            13.8
            if rpm >= 600.0
            else 12.4
        )

        self._state.alternator_voltage_v = (
            _lerp(
                self._state.alternator_voltage_v,
                target_alternator_voltage,
                engine_response,
            )
        )

        self._state.battery_voltage_v = (
            _lerp(
                self._state.battery_voltage_v,
                target_battery_voltage,
                engine_response,
            )
        )


    def set_fault(
        self,
        fault: str | SimulationFault,
        *,
        severity: float = 1.0,
        ramp_sec: float = 0.0,
    ) -> Dict[str, Any]:

        try:

            fault_type = (
                fault
                if isinstance(
                    fault,
                    SimulationFault,
                )
                else SimulationFault(
                    str(fault).upper()
                )
            )

        except ValueError as exc:

            raise ValueError(
                f"Unsupported simulation fault: {fault}"
            ) from exc

        severity_value = (
            _finite_number(
                severity
            )
        )

        ramp_value = (
            _finite_number(
                ramp_sec
            )
        )

        if severity_value is None:
            raise ValueError(
                "Fault severity must be numeric."
            )

        if not (
            0.0
            <= severity_value
            <= 1.0
        ):
            raise ValueError(
                "Fault severity must be between 0.0 and 1.0."
            )

        if (
            ramp_value is None
            or ramp_value < 0.0
        ):
            raise ValueError(
                "Fault ramp_sec must be finite and non-negative."
            )

        self._active_faults[
            fault_type
        ] = ActiveSimulationFault(
            fault=fault_type,
            severity=severity_value,
            ramp_sec=ramp_value,
            elapsed_sec=0.0,
        )

        self._fault_injection_count += 1

        return self.get_fault_status()


    def clear_fault(
        self,
        fault: str | SimulationFault,
    ) -> Dict[str, Any]:

        try:

            fault_type = (
                fault
                if isinstance(
                    fault,
                    SimulationFault,
                )
                else SimulationFault(
                    str(fault).upper()
                )
            )

        except ValueError as exc:

            raise ValueError(
                f"Unsupported simulation fault: {fault}"
            ) from exc

        if (
            fault_type
            in self._active_faults
        ):

            del self._active_faults[
                fault_type
            ]

            self._fault_clear_count += 1

        return self.get_fault_status()


    def clear_faults(
        self,
    ) -> Dict[str, Any]:

        cleared = len(
            self._active_faults
        )

        self._active_faults.clear()

        self._fault_clear_count += (
            cleared
        )

        return self.get_fault_status()


    def get_fault_status(
        self,
    ) -> Dict[str, Any]:

        return {
            "enabled":
                bool(
                    self._active_faults
                ),

            "active_fault_count":
                len(
                    self._active_faults
                ),

            "active_faults": [
                item.to_dict()
                for item
                in self._active_faults.values()
            ],

            "injection_count":
                self._fault_injection_count,

            "clear_count":
                self._fault_clear_count,
        }


    def _apply_faults(
        self,
        payload: Dict[str, Any],
        *,
        delta_sec: float,
    ) -> None:

        if not self._active_faults:
            return

        delta = max(
            0.0,
            delta_sec,
        )

        for active in (
            self._active_faults.values()
        ):

            active.elapsed_sec += delta

            severity = (
                active.effective_severity
            )

            if severity <= 0.0:
                continue


            if (
                active.fault
                == SimulationFault.OIL_PRESSURE_LOSS
            ):

                current = (
                    payload["oil"]
                    .get("pressure_kpa")
                )

                if current is not None:

                    payload[
                        "oil"
                    ][
                        "pressure_kpa"
                    ] = max(
                        0.0,
                        current
                        * (
                            1.0
                            - 0.80
                            * severity
                        ),
                    )


            elif (
                active.fault
                == SimulationFault.COOLING_DEGRADATION
            ):

                temperature_rise = (
                    100.0
                    * severity
                )

                for key in (
                    "cylinder1_c",
                    "cylinder2_c",
                    "cylinder3_c",
                    "cylinder4_c",
                ):

                    current = (
                        payload["cht"]
                        .get(key)
                    )

                    if current is not None:

                        payload[
                            "cht"
                        ][
                            key
                        ] = (
                            current
                            + temperature_rise
                        )


            elif (
                active.fault
                == SimulationFault.EGT_IMBALANCE
            ):

                current = (
                    payload["egt"]
                    .get("cylinder3_c")
                )

                if current is not None:

                    payload[
                        "egt"
                    ][
                        "cylinder3_c"
                    ] = (
                        current
                        + 180.0
                        * severity
                    )


            elif (
                active.fault
                == SimulationFault.FUEL_PRESSURE_LOSS
            ):

                current = (
                    payload["fuel"]
                    .get("pressure_kpa")
                )

                if current is not None:

                    payload[
                        "fuel"
                    ][
                        "pressure_kpa"
                    ] = max(
                        0.0,
                        current
                        * (
                            1.0
                            - 0.75
                            * severity
                        ),
                    )


            elif (
                active.fault
                == SimulationFault.VIBRATION_INCREASE
            ):

                current = (
                    payload[
                        "vibration"
                    ].get(
                        "overall_g"
                    )
                )

                if current is not None:

                    payload[
                        "vibration"
                    ][
                        "overall_g"
                    ] = max(
                        0.0,
                        current
                        + 1.5
                        * severity,
                    )


    def build_payload(
        self,
        command: Dict[str, Any],
        *,
        delta_sec: float = 1.0,
    ) -> Dict[str, Any]:

        delta_value = (
            _finite_number(
                delta_sec
            )
        )

        if (
            delta_value is None
            or delta_value < 0.0
        ):
            raise ValueError(
                "delta_sec must be finite and non-negative."
            )

        delta = float(
            delta_value
        )

        (
            rpm_target,
            throttle_target,
            load_target,
            altitude_m,
            ambient_temperature_c,
        ) = self._extract_targets(
            command
        )

        self._update_engine_state(
            rpm_target=rpm_target,
            throttle_target=throttle_target,
            load_target=load_target,
            altitude_m=altitude_m,
            ambient_temperature_c=ambient_temperature_c,
            delta_sec=delta,
        )

        self._sequence += 1


        rpm_noise = (
            self._rng.uniform(
                -1.0,
                1.0,
            )
            if self._state.rpm >= 50.0
            else 0.0
        )

        thermal_noise = (
            lambda: self._rng.uniform(
                -0.35,
                0.35,
            )
        )

        pressure_noise = (
            lambda: self._rng.uniform(
                -0.8,
                0.8,
            )
        )

        vibration_noise = (
            self._rng.uniform(
                -0.004,
                0.004,
            )
            if self._state.rpm >= 50.0
            else 0.0
        )


        engine = {
            "rpm":
                max(
                    0.0,
                    self._state.rpm
                    + rpm_noise,
                ),

            "throttle_percent":
                self._state.throttle_percent,

            "load_percent":
                self._state.load_percent,

            "power_kw":
                max(
                    0.0,
                    self._state.power_kw,
                ),

            "torque_nm":
                max(
                    0.0,
                    self._state.torque_nm,
                ),
        }


        cht = {
            "cylinder1_c":
                self._state.cht1_c
                + thermal_noise(),

            "cylinder2_c":
                self._state.cht2_c
                + thermal_noise(),

            "cylinder3_c":
                self._state.cht3_c
                + thermal_noise(),

            "cylinder4_c":
                self._state.cht4_c
                + thermal_noise(),
        }


        egt = {
            "cylinder1_c":
                self._state.egt1_c
                + thermal_noise(),

            "cylinder2_c":
                self._state.egt2_c
                + thermal_noise(),

            "cylinder3_c":
                self._state.egt3_c
                + thermal_noise(),

            "cylinder4_c":
                self._state.egt4_c
                + thermal_noise(),
        }


        oil = {
            "temperature_c":
                self._state.oil_temperature_c
                + thermal_noise(),

            "pressure_kpa":
                max(
                    0.0,
                    self._state.oil_pressure_kpa
                    + pressure_noise(),
                ),
        }


        fuel = {
            "flow_kg_s":
                max(
                    0.0,
                    self._state.fuel_flow_kg_s,
                ),

            "pressure_kpa":
                max(
                    0.0,
                    self._state.fuel_pressure_kpa
                    + pressure_noise(),
                ),

            "injection_timing_deg":
                None,
        }


        vibration = {
            "overall_g":
                max(
                    0.0,
                    self._state.vibration_g
                    + vibration_noise,
                ),

            "x_g":
                None,

            "y_g":
                None,

            "z_g":
                None,
        }


        electrical = {
            "alternator_voltage_v":
                max(
                    0.0,
                    self._state.alternator_voltage_v,
                ),

            "battery_voltage_v":
                max(
                    0.0,
                    self._state.battery_voltage_v,
                ),
        }


        environment = {
            "ambient_temperature_c":
                ambient_temperature_c,

            "ambient_pressure_kpa":
                _atmosphere_pressure_kpa(
                    altitude_m
                ),

            "altitude_m":
                altitude_m,
        }


        mission = {
            "missionId":
                command.get(
                    "mission_id"
                ),

            "elapsedTimeSec":
                command.get(
                    "elapsed_time_sec"
                ),

            "phase":
                command.get(
                    "phase"
                ),
        }


        payload: Dict[
            str,
            Any,
        ] = {
            "meta": {
                "timestamp":
                    _utc_now(),

                "source":
                    "simulation",

                "sequence":
                    self._sequence,
            },

            "engine":
                engine,

            "cht":
                cht,

            "egt":
                egt,

            "oil":
                oil,

            "fuel":
                fuel,

            "vibration":
                vibration,

            "electrical":
                electrical,

            "environment":
                environment,

            "mission":
                mission,
        }


        self._apply_faults(
            payload,
            delta_sec=delta,
        )

        self._generated_frames += 1

        self._latest_payload = (
            payload
        )

        return payload


    def build_frame(
        self,
        command: Dict[str, Any],
        *,
        delta_sec: float = 1.0,
    ) -> TelemetryFrame:

        payload = self.build_payload(
            command,
            delta_sec=delta_sec,
        )

        return TelemetryFrame(
            **payload
        )


    async def process_command(
        self,
        command: Dict[str, Any],
        *,
        delta_sec: float = 1.0,
    ) -> Dict[str, Any]:

        self._ingestion_attempts += 1

        try:

            frame = self.build_frame(
                command,
                delta_sec=delta_sec,
            )


            from backend.api.telemetry import (
                ingest_telemetry,
            )

            ingestion = (
                await ingest_telemetry(
                    frame
                )
            )

            success = True

            if isinstance(
                ingestion,
                dict,
            ):
                success = bool(
                    ingestion.get(
                        "success",
                        True,
                    )
                )

            if success:

                self._ingestion_successes += 1

                self._last_error = None

            else:

                self._ingestion_failures += 1

                if isinstance(
                    ingestion,
                    dict,
                ):
                    self._last_error = (
                        ingestion.get(
                            "error"
                        )
                    )

            result = {
                "success":
                    success,

                "adapter_version":
                    SIMULATION_ADAPTER_VERSION,

                "source":
                    "simulation",

                "frame_sequence":
                    self._sequence,

                "fault_injection":
                    self.get_fault_status(),

                "ingestion":
                    ingestion,

                "error":
                    self._last_error,
            }

            self._latest_result = (
                result
            )

            return result

        except Exception as exc:

            self._ingestion_failures += 1

            self._last_error = str(
                exc
            )

            result = {
                "success":
                    False,

                "adapter_version":
                    SIMULATION_ADAPTER_VERSION,

                "source":
                    "simulation",

                "frame_sequence":
                    self._sequence,

                "fault_injection":
                    self.get_fault_status(),

                "ingestion":
                    None,

                "error":
                    str(exc),
            }

            self._latest_result = (
                result
            )

            return result


    def reset(
        self,
    ) -> None:

        self._rng = random.Random(
            self._random_seed
        )

        self._state = (
            SimulatedEngineState()
        )

        self._sequence = 0

        self._generated_frames = 0

        self._ingestion_attempts = 0

        self._ingestion_successes = 0

        self._ingestion_failures = 0

        self._last_error = None

        self._latest_payload = None

        self._latest_result = None

        self._active_faults.clear()

        self._fault_injection_count = 0

        self._fault_clear_count = 0


    def status(
        self,
    ) -> Dict[str, Any]:

        return {
            "service":
                "simulation_adapter",

            "version":
                SIMULATION_ADAPTER_VERSION,

            "source":
                "simulation",

            "sequence":
                self._sequence,

            "generated_frames":
                self._generated_frames,

            "ingestion_attempts":
                self._ingestion_attempts,

            "ingestion_successes":
                self._ingestion_successes,

            "ingestion_failures":
                self._ingestion_failures,

            "last_error":
                self._last_error,

            "latest_payload_available":
                self._latest_payload
                is not None,

            "latest_result_available":
                self._latest_result
                is not None,

            "fault_injection":
                self.get_fault_status(),
        }


    def latest_payload(
        self,
    ) -> Optional[
        Dict[str, Any]
    ]:

        return self._latest_payload


    def latest_result(
        self,
    ) -> Optional[
        Dict[str, Any]
    ]:

        return self._latest_result


_default_adapter = (
    SimulationAdapter()
)


def get_simulation_adapter(
) -> SimulationAdapter:

    return _default_adapter


def build_simulation_payload(
    command: Dict[str, Any],
    *,
    delta_sec: float = 1.0,
) -> Dict[str, Any]:

    return (
        _default_adapter.build_payload(
            command,
            delta_sec=delta_sec,
        )
    )


def build_simulation_frame(
    command: Dict[str, Any],
    *,
    delta_sec: float = 1.0,
) -> TelemetryFrame:

    return (
        _default_adapter.build_frame(
            command,
            delta_sec=delta_sec,
        )
    )


async def process_simulation_command(
    command: Dict[str, Any],
    *,
    delta_sec: float = 1.0,
) -> Dict[str, Any]:

    return await (
        _default_adapter.process_command(
            command,
            delta_sec=delta_sec,
        )
    )


async def ingest_simulation_command(
    command: Dict[str, Any],
    *,
    delta_sec: float = 1.0,
) -> Dict[str, Any]:

    return await (
        process_simulation_command(
            command,
            delta_sec=delta_sec,
        )
    )


def set_simulation_fault(
    fault: str | SimulationFault,
    *,
    severity: float = 1.0,
    ramp_sec: float = 0.0,
) -> Dict[str, Any]:

    return (
        _default_adapter.set_fault(
            fault,
            severity=severity,
            ramp_sec=ramp_sec,
        )
    )


def clear_simulation_fault(
    fault: str | SimulationFault,
) -> Dict[str, Any]:

    return (
        _default_adapter.clear_fault(
            fault
        )
    )


def clear_simulation_faults(
) -> Dict[str, Any]:

    return (
        _default_adapter.clear_faults()
    )


def get_simulation_fault_status(
) -> Dict[str, Any]:

    return (
        _default_adapter.get_fault_status()
    )


def get_simulation_status(
) -> Dict[str, Any]:

    return (
        _default_adapter.status()
    )


def reset_simulation_adapter(
) -> Dict[str, Any]:

    _default_adapter.reset()

    return (
        _default_adapter.status()
    )


def get_latest_simulation_payload(
) -> Optional[
    Dict[str, Any]
]:

    return (
        _default_adapter.latest_payload()
    )


def get_latest_simulation_result(
) -> Optional[
    Dict[str, Any]
]:

    return (
        _default_adapter.latest_result()
    )


def get_simulation_info(
) -> Dict[str, Any]:

    return {
        "service":
            "simulation_adapter",

        "version":
            SIMULATION_ADAPTER_VERSION,

        "input":
            "mission_scenario_command",

        "output":
            "TelemetryFrame",

        "canonical_source":
            "simulation",

        "supports_pipeline_ingestion":
            True,

        "healthy_plant_calibration":
            True,

        "supports_fault_injection":
            True,

        "supported_faults": [
            fault.value
            for fault
            in SimulationFault
        ],

        "faults_are_demonstrator_models":
            True,

        "faults_force_diagnostic_results":
            False,

        "modifies_can_fadec":
            False,

        "shares_can_transport":
            False,

        "uses_official_drdo_vrde_maps":
            False,

        "certified_engine_simulator":
            False,

        "zero_is_valid":
            True,

        "none_means_unavailable":
            True,

        "notes": [
            (
                "Simulation values are PRATIRUP "
                "engineering-demonstrator estimates."
            ),
            (
                "Healthy-plant equations are calibrated "
                "against the PRATIRUP Digital Twin baseline."
            ),
            (
                "Calibration does not represent an official "
                "DRDO/VRDE engine performance map."
            ),
            (
                "Injected faults modify simulated telemetry "
                "only and do not force diagnostic results."
            ),
            (
                "Fault amplitudes are PRATIRUP demonstrator "
                "models and are not OEM failure thresholds."
            ),
        ],
    }
