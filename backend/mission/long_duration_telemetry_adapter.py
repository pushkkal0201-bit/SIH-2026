from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from math import isfinite
from typing import Any, Dict, Mapping, Optional

from backend.prognostics.synthetic_degradation_profile import (
    SyntheticDegradationProfile,
)


LONG_DURATION_TELEMETRY_ADAPTER_VERSION = "1.0.0"


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

    if not isfinite(result):
        return None

    return result


def _clamp01(
    value: float,
) -> float:

    return max(
        0.0,
        min(1.0, value),
    )


def _read_numeric(
    payload: Mapping[str, Any],
    key: str,
) -> Optional[float]:

    if key not in payload:
        return None

    return _finite_number(
        payload.get(key)
    )


def _apply_multiplier(
    value: Optional[float],
    multiplier: float,
) -> Optional[float]:

    if value is None:
        return None

    return value * multiplier


def _apply_offset(
    value: Optional[float],
    offset: float,
) -> Optional[float]:

    if value is None:
        return None

    return value + offset


@dataclass(frozen=True)
class LongDurationTelemetryEffects:

    engine_hours: float
    degradation_index: float
    wear_band: str

    thermal_wear: float
    lubrication_wear: float
    vibration_growth: float
    efficiency_loss: float
    combustion_wear: float

    cht_offset_c: float
    egt_offset_c: float
    oil_temperature_offset_c: float

    oil_pressure_multiplier: float
    fuel_pressure_multiplier: float

    vibration_multiplier: float
    manifold_pressure_multiplier: float

    rpm_multiplier: float

    synthetic: bool = True

    def to_dict(self) -> Dict[str, Any]:

        return {
            "engine_hours":
                self.engine_hours,

            "degradation_index":
                self.degradation_index,

            "degradation_percent":
                self.degradation_index * 100.0,

            "wear_band":
                self.wear_band,

            "wear": {
                "thermal":
                    self.thermal_wear,

                "lubrication":
                    self.lubrication_wear,

                "vibration_growth":
                    self.vibration_growth,

                "efficiency_loss":
                    self.efficiency_loss,

                "combustion":
                    self.combustion_wear,
            },

            "telemetry_effects": {
                "cht_offset_c":
                    self.cht_offset_c,

                "egt_offset_c":
                    self.egt_offset_c,

                "oil_temperature_offset_c":
                    self.oil_temperature_offset_c,

                "oil_pressure_multiplier":
                    self.oil_pressure_multiplier,

                "fuel_pressure_multiplier":
                    self.fuel_pressure_multiplier,

                "vibration_multiplier":
                    self.vibration_multiplier,

                "manifold_pressure_multiplier":
                    self.manifold_pressure_multiplier,

                "rpm_multiplier":
                    self.rpm_multiplier,
            },

            "synthetic":
                self.synthetic,
        }


class LongDurationTelemetryAdapter:

    def __init__(
        self,
        *,
        reference_life_hours: float = 1000.0,
    ) -> None:

        self._profile = (
            SyntheticDegradationProfile(
                reference_life_hours=
                    reference_life_hours
            )
        )

        self._application_count = 0

        self._latest_effects: Optional[
            LongDurationTelemetryEffects
        ] = None

    @property
    def application_count(self) -> int:
        return self._application_count

    def calculate_effects(
        self,
        engine_hours: float,
    ) -> LongDurationTelemetryEffects:

        degradation = (
            self._profile.evaluate(
                engine_hours
            )
        )

        thermal = _clamp01(
            degradation.thermal_wear
        )

        lubrication = _clamp01(
            degradation.lubrication_wear
        )

        vibration = _clamp01(
            degradation.vibration_growth
        )

        efficiency = _clamp01(
            degradation.efficiency_loss
        )

        combustion = _clamp01(
            degradation.combustion_wear
        )

        cht_offset_c = (
            18.0 * thermal
        )

        egt_offset_c = (
            25.0 * combustion
        )

        oil_temperature_offset_c = (
            15.0 * lubrication
        )

        oil_pressure_multiplier = max(
            0.85,
            1.0 - (
                0.12 * lubrication
            ),
        )

        fuel_pressure_multiplier = max(
            0.90,
            1.0 - (
                0.08 * combustion
            ),
        )

        vibration_multiplier = (
            1.0
            + (
                0.80 * vibration
            )
        )

        manifold_pressure_multiplier = max(
            0.90,
            1.0 - (
                0.07 * efficiency
            ),
        )

        rpm_multiplier = max(
            0.95,
            1.0 - (
                0.03 * efficiency
            ),
        )

        return LongDurationTelemetryEffects(
            engine_hours=
                degradation.engine_hours,

            degradation_index=
                degradation.degradation_index,

            wear_band=
                degradation.wear_band.value,

            thermal_wear=
                thermal,

            lubrication_wear=
                lubrication,

            vibration_growth=
                vibration,

            efficiency_loss=
                efficiency,

            combustion_wear=
                combustion,

            cht_offset_c=
                cht_offset_c,

            egt_offset_c=
                egt_offset_c,

            oil_temperature_offset_c=
                oil_temperature_offset_c,

            oil_pressure_multiplier=
                oil_pressure_multiplier,

            fuel_pressure_multiplier=
                fuel_pressure_multiplier,

            vibration_multiplier=
                vibration_multiplier,

            manifold_pressure_multiplier=
                manifold_pressure_multiplier,

            rpm_multiplier=
                rpm_multiplier,
        )

    def apply(
        self,
        payload: Mapping[str, Any],
        *,
        engine_hours: float,
    ) -> Dict[str, Any]:

        if not isinstance(
            payload,
            Mapping,
        ):
            raise TypeError(
                "payload must be a mapping."
            )

        result: Dict[str, Any] = deepcopy(
            dict(payload)
        )

        effects = self.calculate_effects(
            engine_hours
        )

        for key in (
            "cht_c",
            "cylinder_head_temperature_c",
        ):

            if key in result:

                original = _read_numeric(
                    result,
                    key,
                )

                result[key] = (
                    _apply_offset(
                        original,
                        effects.cht_offset_c,
                    )
                    if original is not None
                    else result[key]
                )

        for key in (
            "egt_c",
            "exhaust_gas_temperature_c",
        ):

            if key in result:

                original = _read_numeric(
                    result,
                    key,
                )

                result[key] = (
                    _apply_offset(
                        original,
                        effects.egt_offset_c,
                    )
                    if original is not None
                    else result[key]
                )

        for key in (
            "oil_temperature_c",
            "oil_temp_c",
        ):

            if key in result:

                original = _read_numeric(
                    result,
                    key,
                )

                result[key] = (
                    _apply_offset(
                        original,
                        effects.oil_temperature_offset_c,
                    )
                    if original is not None
                    else result[key]
                )

        for key in (
            "oil_pressure_kpa",
            "oil_pressure_bar",
            "oil_pressure_psi",
        ):

            if key in result:

                original = _read_numeric(
                    result,
                    key,
                )

                result[key] = (
                    _apply_multiplier(
                        original,
                        effects.oil_pressure_multiplier,
                    )
                    if original is not None
                    else result[key]
                )

        for key in (
            "fuel_pressure_kpa",
            "fuel_pressure_bar",
            "fuel_pressure_psi",
        ):

            if key in result:

                original = _read_numeric(
                    result,
                    key,
                )

                result[key] = (
                    _apply_multiplier(
                        original,
                        effects.fuel_pressure_multiplier,
                    )
                    if original is not None
                    else result[key]
                )

        for key in (
            "vibration",
            "vibration_g",
            "engine_vibration_g",
        ):

            if key in result:

                original = _read_numeric(
                    result,
                    key,
                )

                result[key] = (
                    _apply_multiplier(
                        original,
                        effects.vibration_multiplier,
                    )
                    if original is not None
                    else result[key]
                )

        for key in (
            "manifold_pressure_kpa",
            "manifold_pressure_bar",
        ):

            if key in result:

                original = _read_numeric(
                    result,
                    key,
                )

                result[key] = (
                    _apply_multiplier(
                        original,
                        effects.manifold_pressure_multiplier,
                    )
                    if original is not None
                    else result[key]
                )

        if "rpm" in result:

            original = _read_numeric(
                result,
                "rpm",
            )

            result["rpm"] = (
                _apply_multiplier(
                    original,
                    effects.rpm_multiplier,
                )
                if original is not None
                else result["rpm"]
            )

        result[
            "synthetic_engine_life"
        ] = {
            "engine_hours":
                effects.engine_hours,

            "synthetic":
                True,

            "real_engine_hours":
                False,

            "measured_engine_data":
                False,

            "degradation_index":
                effects.degradation_index,

            "wear_band":
                effects.wear_band,

            "effects":
                effects.to_dict()[
                    "telemetry_effects"
                ],

            "authoritative_health_state":
                False,

            "official_engine_calibration":
                False,
        }

        self._application_count += 1
        self._latest_effects = effects

        return result

    def status(
        self,
    ) -> Dict[str, Any]:

        return {
            "service":
                "long_duration_telemetry_adapter",

            "version":
                LONG_DURATION_TELEMETRY_ADAPTER_VERSION,

            "architecture":
                "SYNTHETIC_WEAR_TO_TELEMETRY_ONLY",

            "application_count":
                self._application_count,

            "latest_effects":
                (
                    self._latest_effects
                    .to_dict()
                    if self._latest_effects
                    is not None
                    else None
                ),

            "semantics": {
                "synthetic":
                    True,

                "real_engine_hours":
                    False,

                "measured_engine_data":
                    False,

                "official_engine_calibration":
                    False,

                "zero":
                    "GENUINE_NUMERIC_ZERO",

                "null":
                    "UNAVAILABLE",
            },

            "isolation": {
                "database_writes":
                    False,

                "fault_state_calculation":
                    False,

                "anomaly_calculation":
                    False,

                "authoritative_degradation":
                    False,

                "rul_calculation":
                    False,

                "maintenance_calculation":
                    False,

                "readiness_calculation":
                    False,

                "flight_authorization":
                    False,
            },
        }


_long_duration_telemetry_adapter = (
    LongDurationTelemetryAdapter()
)


def get_long_duration_telemetry_adapter(
) -> LongDurationTelemetryAdapter:

    return (
        _long_duration_telemetry_adapter
    )


def apply_long_duration_wear(
    payload: Mapping[str, Any],
    *,
    engine_hours: float,
) -> Dict[str, Any]:

    return (
        _long_duration_telemetry_adapter
        .apply(
            payload,
            engine_hours=
                engine_hours,
        )
    )


def get_long_duration_telemetry_status(
) -> Dict[str, Any]:

    return (
        _long_duration_telemetry_adapter
        .status()
    )
