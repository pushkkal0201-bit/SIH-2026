from __future__ import annotations

import math

from collections import deque
from statistics import mean, pstdev
from typing import Any, Mapping


VERSION = "1.0.0"

SAMPLE_INTERVAL_SEC = 0.5
ROLLING_WINDOW_SEC = 5.0

ROLLING_WINDOW_SAMPLES = int(
    ROLLING_WINDOW_SEC
    / SAMPLE_INTERVAL_SEC
)


PHASE_INDEX = {
    "ENGINE_START": 0,
    "WARMUP": 1,
    "TAKEOFF": 2,
    "CLIMB": 3,
    "CRUISE": 4,
    "HIGH_ALTITUDE": 5,
    "DESCENT": 6,
    "LANDING": 7,
    "ENGINE_SHUTDOWN": 8,
}


RAW_FEATURES = [
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

    "fuel.flow_kg_s",
    "fuel.pressure_kpa",

    "vibration.overall_g",

    "electrical.alternator_voltage_v",
    "electrical.battery_voltage_v",

    "environment.altitude_m",
    "environment.ambient_temperature_c",
    "environment.ambient_pressure_kpa",
]


DERIVED_FEATURES = [
    "phase_index",

    "cht_mean_c",
    "cht_min_c",
    "cht_max_c",
    "cht_spread_c",

    "egt_mean_c",
    "egt_min_c",
    "egt_max_c",
    "egt_spread_c",

    "thermal_gap_c",

    "oil_pressure_per_1000rpm",
    "fuel_flow_per_load",
    "vibration_per_1000rpm",

    "rpm_delta",
    "oil_pressure_delta",
    "oil_temperature_delta",
    "fuel_pressure_delta",
    "fuel_flow_delta",
    "vibration_delta",
    "cht_mean_delta",
    "egt_mean_delta",
    "altitude_delta",

    "rpm_rate_per_sec",
    "oil_pressure_rate_per_sec",
    "oil_temperature_rate_per_sec",
    "fuel_pressure_rate_per_sec",
    "vibration_rate_per_sec",
    "cht_mean_rate_per_sec",
    "egt_mean_rate_per_sec",

    "oil_pressure_5s_mean",
    "oil_pressure_5s_std",

    "vibration_5s_mean",
    "vibration_5s_std",

    "cht_mean_5s_mean",
    "cht_mean_5s_std",

    "egt_mean_5s_mean",
    "egt_mean_5s_std",
]


FEATURES = (
    RAW_FEATURES
    + DERIVED_FEATURES
)


class LiveFeatureBuilderError(RuntimeError):
    pass


def finite_number(
    row: Mapping[str, Any],
    key: str,
) -> float:

    if key not in row:

        raise LiveFeatureBuilderError(
            f"Missing telemetry field: {key}"
        )

    raw = row[key]

    if raw is None or raw == "":

        raise LiveFeatureBuilderError(
            f"Telemetry field unavailable: {key}"
        )

    try:

        value = float(
            raw
        )

    except (
        TypeError,
        ValueError,
    ) as exc:

        raise LiveFeatureBuilderError(
            f"Telemetry field is not numeric: {key}"
        ) from exc

    if not math.isfinite(
        value
    ):

        raise LiveFeatureBuilderError(
            f"Telemetry field is not finite: {key}"
        )

    return value


def safe_ratio(
    numerator: float,
    denominator: float,
    *,
    minimum_denominator: float,
) -> float:

    if abs(
        denominator
    ) < minimum_denominator:

        return 0.0

    return (
        numerator
        / denominator
    )


def delta(
    current: float,
    previous: float | None,
) -> float:

    if previous is None:

        return 0.0

    return (
        current
        - previous
    )


def rolling_statistics(
    values: deque,
) -> tuple[float, float]:

    data = list(
        values
    )

    if not data:

        return (
            0.0,
            0.0,
        )

    average = float(
        mean(
            data
        )
    )

    standard_deviation = (
        float(
            pstdev(
                data
            )
        )
        if len(
            data
        ) > 1
        else 0.0
    )

    return (
        average,
        standard_deviation,
    )


class PRATIRUPLiveFeatureBuilder:

    def __init__(
        self,
        *,
        sample_interval_sec: float =
            SAMPLE_INTERVAL_SEC,
        rolling_window_samples: int =
            ROLLING_WINDOW_SAMPLES,
    ) -> None:

        if (
            not math.isfinite(
                sample_interval_sec
            )
            or sample_interval_sec
            <= 0.0
        ):

            raise LiveFeatureBuilderError(
                "sample_interval_sec must be > 0."
            )

        if rolling_window_samples < 1:

            raise LiveFeatureBuilderError(
                "rolling_window_samples must be >= 1."
            )

        self.sample_interval_sec = float(
            sample_interval_sec
        )

        self.rolling_window_samples = int(
            rolling_window_samples
        )

        self.current_mission_id = None

        self.previous: dict[
            str,
            float
        ] = {}

        self.oil_window = deque(
            maxlen=
                self.rolling_window_samples
        )

        self.vibration_window = deque(
            maxlen=
                self.rolling_window_samples
        )

        self.cht_window = deque(
            maxlen=
                self.rolling_window_samples
        )

        self.egt_window = deque(
            maxlen=
                self.rolling_window_samples
        )

        self.samples_processed = 0


    def get_status(
        self,
    ) -> dict[str, Any]:

        return {
            "service":
                "pratirup_live_feature_builder",

            "version":
                VERSION,

            "status":
                "READY",

            "raw_feature_count":
                len(
                    RAW_FEATURES
                ),

            "derived_feature_count":
                len(
                    DERIVED_FEATURES
                ),

            "feature_count":
                len(
                    FEATURES
                ),

            "sample_interval_sec":
                self.sample_interval_sec,

            "rolling_window_samples":
                self.rolling_window_samples,

            "causal":
                True,

            "future_information":
                False,

            "labels_required":
                False,

            "database_writes":
                False,

            "digital_twin_modification":
                False,

            "flight_authorization":
                False,
        }


    def reset(
        self,
        *,
        mission_id: str | None = None,
    ) -> None:

        self.current_mission_id = (
            mission_id
        )

        self.previous = {}

        self.oil_window.clear()
        self.vibration_window.clear()
        self.cht_window.clear()
        self.egt_window.clear()


    def _mission_id(
        self,
        row: Mapping[str, Any],
    ) -> str:

        possible_keys = (
            "dataset_mission_id",
            "mission.missionId",
            "mission.mission_id",
        )

        for key in possible_keys:

            value = row.get(
                key
            )

            if (
                value is not None
                and str(
                    value
                ).strip()
            ):

                return str(
                    value
                )

        raise LiveFeatureBuilderError(
            "No mission identifier supplied."
        )


    def _mission_phase(
        self,
        row: Mapping[str, Any],
    ) -> str:

        phase = row.get(
            "mission.phase"
        )

        if phase is None:

            raise LiveFeatureBuilderError(
                "mission.phase is required."
            )

        return str(
            phase
        )


    def build(
        self,
        row: Mapping[str, Any],
    ) -> dict[str, float]:

        mission_id = (
            self._mission_id(
                row
            )
        )

        if (
            mission_id
            != self.current_mission_id
        ):

            self.reset(
                mission_id=
                    mission_id
            )

        phase = self._mission_phase(
            row
        )

        raw = {
            feature:
                finite_number(
                    row,
                    feature,
                )
            for feature
            in RAW_FEATURES
        }


        rpm = raw[
            "engine.rpm"
        ]

        load = raw[
            "engine.load_percent"
        ]

        oil_pressure = raw[
            "oil.pressure_kpa"
        ]

        oil_temperature = raw[
            "oil.temperature_c"
        ]

        fuel_pressure = raw[
            "fuel.pressure_kpa"
        ]

        fuel_flow = raw[
            "fuel.flow_kg_s"
        ]

        vibration = raw[
            "vibration.overall_g"
        ]

        altitude = raw[
            "environment.altitude_m"
        ]


        cht_values = [
            raw[
                f"cht.cylinder{i}_c"
            ]
            for i
            in range(
                1,
                5,
            )
        ]


        egt_values = [
            raw[
                f"egt.cylinder{i}_c"
            ]
            for i
            in range(
                1,
                5,
            )
        ]


        cht_mean = float(
            mean(
                cht_values
            )
        )

        egt_mean = float(
            mean(
                egt_values
            )
        )


        cht_min = min(
            cht_values
        )

        cht_max = max(
            cht_values
        )

        egt_min = min(
            egt_values
        )

        egt_max = max(
            egt_values
        )


        rpm_delta = delta(
            rpm,
            self.previous.get(
                "rpm"
            ),
        )

        oil_pressure_delta = delta(
            oil_pressure,
            self.previous.get(
                "oil_pressure"
            ),
        )

        oil_temperature_delta = delta(
            oil_temperature,
            self.previous.get(
                "oil_temperature"
            ),
        )

        fuel_pressure_delta = delta(
            fuel_pressure,
            self.previous.get(
                "fuel_pressure"
            ),
        )

        fuel_flow_delta = delta(
            fuel_flow,
            self.previous.get(
                "fuel_flow"
            ),
        )

        vibration_delta = delta(
            vibration,
            self.previous.get(
                "vibration"
            ),
        )

        cht_mean_delta = delta(
            cht_mean,
            self.previous.get(
                "cht_mean"
            ),
        )

        egt_mean_delta = delta(
            egt_mean,
            self.previous.get(
                "egt_mean"
            ),
        )

        altitude_delta = delta(
            altitude,
            self.previous.get(
                "altitude"
            ),
        )


        self.oil_window.append(
            oil_pressure
        )

        self.vibration_window.append(
            vibration
        )

        self.cht_window.append(
            cht_mean
        )

        self.egt_window.append(
            egt_mean
        )


        (
            oil_roll_mean,
            oil_roll_std,
        ) = rolling_statistics(
            self.oil_window
        )

        (
            vibration_roll_mean,
            vibration_roll_std,
        ) = rolling_statistics(
            self.vibration_window
        )

        (
            cht_roll_mean,
            cht_roll_std,
        ) = rolling_statistics(
            self.cht_window
        )

        (
            egt_roll_mean,
            egt_roll_std,
        ) = rolling_statistics(
            self.egt_window
        )


        derived = {
            "phase_index":
                float(
                    PHASE_INDEX.get(
                        phase,
                        -1,
                    )
                ),

            "cht_mean_c":
                cht_mean,

            "cht_min_c":
                cht_min,

            "cht_max_c":
                cht_max,

            "cht_spread_c":
                cht_max
                - cht_min,

            "egt_mean_c":
                egt_mean,

            "egt_min_c":
                egt_min,

            "egt_max_c":
                egt_max,

            "egt_spread_c":
                egt_max
                - egt_min,

            "thermal_gap_c":
                egt_mean
                - cht_mean,

            "oil_pressure_per_1000rpm":
                safe_ratio(
                    oil_pressure,
                    rpm / 1000.0,
                    minimum_denominator=
                        0.1,
                ),

            "fuel_flow_per_load":
                safe_ratio(
                    fuel_flow,
                    load / 100.0,
                    minimum_denominator=
                        0.01,
                ),

            "vibration_per_1000rpm":
                safe_ratio(
                    vibration,
                    rpm / 1000.0,
                    minimum_denominator=
                        0.1,
                ),

            "rpm_delta":
                rpm_delta,

            "oil_pressure_delta":
                oil_pressure_delta,

            "oil_temperature_delta":
                oil_temperature_delta,

            "fuel_pressure_delta":
                fuel_pressure_delta,

            "fuel_flow_delta":
                fuel_flow_delta,

            "vibration_delta":
                vibration_delta,

            "cht_mean_delta":
                cht_mean_delta,

            "egt_mean_delta":
                egt_mean_delta,

            "altitude_delta":
                altitude_delta,

            "rpm_rate_per_sec":
                rpm_delta
                / self.sample_interval_sec,

            "oil_pressure_rate_per_sec":
                oil_pressure_delta
                / self.sample_interval_sec,

            "oil_temperature_rate_per_sec":
                oil_temperature_delta
                / self.sample_interval_sec,

            "fuel_pressure_rate_per_sec":
                fuel_pressure_delta
                / self.sample_interval_sec,

            "vibration_rate_per_sec":
                vibration_delta
                / self.sample_interval_sec,

            "cht_mean_rate_per_sec":
                cht_mean_delta
                / self.sample_interval_sec,

            "egt_mean_rate_per_sec":
                egt_mean_delta
                / self.sample_interval_sec,

            "oil_pressure_5s_mean":
                oil_roll_mean,

            "oil_pressure_5s_std":
                oil_roll_std,

            "vibration_5s_mean":
                vibration_roll_mean,

            "vibration_5s_std":
                vibration_roll_std,

            "cht_mean_5s_mean":
                cht_roll_mean,

            "cht_mean_5s_std":
                cht_roll_std,

            "egt_mean_5s_mean":
                egt_roll_mean,

            "egt_mean_5s_std":
                egt_roll_std,
        }


        features = {
            **raw,
            **derived,
        }


        if set(
            features
        ) != set(
            FEATURES
        ):

            raise LiveFeatureBuilderError(
                "Generated runtime feature contract "
                "does not match frozen ML-B contract."
            )


        for feature, value in (
            features.items()
        ):

            if not math.isfinite(
                float(
                    value
                )
            ):

                raise LiveFeatureBuilderError(
                    f"Generated non-finite feature: {feature}"
                )


        self.previous = {
            "rpm":
                rpm,

            "oil_pressure":
                oil_pressure,

            "oil_temperature":
                oil_temperature,

            "fuel_pressure":
                fuel_pressure,

            "fuel_flow":
                fuel_flow,

            "vibration":
                vibration,

            "cht_mean":
                cht_mean,

            "egt_mean":
                egt_mean,

            "altitude":
                altitude,
        }


        self.samples_processed += 1


        return {
            feature:
                features[
                    feature
                ]
            for feature
            in FEATURES
        }
