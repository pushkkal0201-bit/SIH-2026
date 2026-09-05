from __future__ import annotations

import csv
import json
import math

from collections import deque
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional


VERSION = "1.0.0"

INPUT_DIR = Path("data/synthetic")
OUTPUT_DIR = Path("data/processed")

INPUT_FILES = {
    "train":
        INPUT_DIR
        / "pratirup_train_v1.csv",

    "validation":
        INPUT_DIR
        / "pratirup_validation_v1.csv",

    "test":
        INPUT_DIR
        / "pratirup_test_v1.csv",
}

OUTPUT_FILES = {
    "train":
        OUTPUT_DIR
        / "pratirup_train_features_v1.csv",

    "validation":
        OUTPUT_DIR
        / "pratirup_validation_features_v1.csv",

    "test":
        OUTPUT_DIR
        / "pratirup_test_features_v1.csv",
}

MANIFEST_PATH = (
    OUTPUT_DIR
    / "pratirup_feature_manifest_v1.json"
)

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


ID_LABEL_COLUMNS = [
    "dataset_version",
    "dataset_mission_id",
    "mission_index",
    "sample_index",
    "split",

    "mission_fault_type",
    "sample_label",
    "anomaly_target",

    "fault_active",
    "fault_requested_severity",
    "fault_effective_severity",

    "synthetic_data",
    "real_operational_measurement",
    "official_drdo_vrde_measurement",

    "mission.phase",
    "mission.elapsedTimeSec",
]


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


def number(
    row: Dict[str, Any],
    key: str,
    default: float = 0.0,
) -> float:

    raw = row.get(
        key
    )

    if raw in (
        None,
        "",
    ):
        return default

    try:

        value = float(
            raw
        )

    except (
        TypeError,
        ValueError,
    ):
        return default

    if not math.isfinite(
        value
    ):
        return default

    return value


def mean_values(
    values: List[float],
) -> float:

    if not values:
        return 0.0

    return float(
        mean(
            values
        )
    )


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
    previous: Optional[float],
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

    avg = float(
        mean(
            data
        )
    )

    std = (
        float(
            pstdev(
                data
            )
        )
        if len(data) > 1
        else 0.0
    )

    return (
        avg,
        std,
    )


def process_split(
    split: str,
    input_path: Path,
    output_path: Path,
) -> Dict[str, Any]:

    print()
    print(
        f"[ML-B] Processing {split}"
    )

    with input_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:

        rows = list(
            csv.DictReader(
                handle
            )
        )

    rows.sort(
        key=lambda row: (
            row[
                "dataset_mission_id"
            ],
            int(
                row[
                    "sample_index"
                ]
            ),
        )
    )

    available_raw_features = [
        feature
        for feature
        in RAW_FEATURES
        if feature
        in rows[0]
    ]

    output_columns = (
        ID_LABEL_COLUMNS
        + available_raw_features
        + DERIVED_FEATURES
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    current_mission = None

    previous = {}

    oil_window = deque(
        maxlen=
            ROLLING_WINDOW_SAMPLES
    )

    vibration_window = deque(
        maxlen=
            ROLLING_WINDOW_SAMPLES
    )

    cht_window = deque(
        maxlen=
            ROLLING_WINDOW_SAMPLES
    )

    egt_window = deque(
        maxlen=
            ROLLING_WINDOW_SAMPLES
    )

    mission_count = 0

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=
                output_columns,
        )

        writer.writeheader()

        for row in rows:

            mission_id = (
                row[
                    "dataset_mission_id"
                ]
            )

            if (
                mission_id
                != current_mission
            ):

                current_mission = (
                    mission_id
                )

                mission_count += 1

                previous = {}

                oil_window.clear()
                vibration_window.clear()
                cht_window.clear()
                egt_window.clear()

            rpm = number(
                row,
                "engine.rpm",
            )

            load = number(
                row,
                "engine.load_percent",
            )

            oil_pressure = number(
                row,
                "oil.pressure_kpa",
            )

            oil_temperature = number(
                row,
                "oil.temperature_c",
            )

            fuel_pressure = number(
                row,
                "fuel.pressure_kpa",
            )

            fuel_flow = number(
                row,
                "fuel.flow_kg_s",
            )

            vibration = number(
                row,
                "vibration.overall_g",
            )

            altitude = number(
                row,
                "environment.altitude_m",
            )

            cht_values = [
                number(
                    row,
                    f"cht.cylinder{i}_c",
                )
                for i
                in range(
                    1,
                    5,
                )
            ]

            egt_values = [
                number(
                    row,
                    f"egt.cylinder{i}_c",
                )
                for i
                in range(
                    1,
                    5,
                )
            ]

            cht_mean = mean_values(
                cht_values
            )

            egt_mean = mean_values(
                egt_values
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
                previous.get(
                    "rpm"
                ),
            )

            oil_pressure_delta = delta(
                oil_pressure,
                previous.get(
                    "oil_pressure"
                ),
            )

            oil_temperature_delta = delta(
                oil_temperature,
                previous.get(
                    "oil_temperature"
                ),
            )

            fuel_pressure_delta = delta(
                fuel_pressure,
                previous.get(
                    "fuel_pressure"
                ),
            )

            fuel_flow_delta = delta(
                fuel_flow,
                previous.get(
                    "fuel_flow"
                ),
            )

            vibration_delta = delta(
                vibration,
                previous.get(
                    "vibration"
                ),
            )

            cht_mean_delta = delta(
                cht_mean,
                previous.get(
                    "cht_mean"
                ),
            )

            egt_mean_delta = delta(
                egt_mean,
                previous.get(
                    "egt_mean"
                ),
            )

            altitude_delta = delta(
                altitude,
                previous.get(
                    "altitude"
                ),
            )

            oil_window.append(
                oil_pressure
            )

            vibration_window.append(
                vibration
            )

            cht_window.append(
                cht_mean
            )

            egt_window.append(
                egt_mean
            )

            (
                oil_roll_mean,
                oil_roll_std,
            ) = rolling_statistics(
                oil_window
            )

            (
                vibration_roll_mean,
                vibration_roll_std,
            ) = rolling_statistics(
                vibration_window
            )

            (
                cht_roll_mean,
                cht_roll_std,
            ) = rolling_statistics(
                cht_window
            )

            (
                egt_roll_mean,
                egt_roll_std,
            ) = rolling_statistics(
                egt_window
            )

            output = {}

            for column in (
                ID_LABEL_COLUMNS
                + available_raw_features
            ):

                output[
                    column
                ] = row.get(
                    column,
                    ""
                )

            output.update(
                {
                    "phase_index":
                        PHASE_INDEX.get(
                            row.get(
                                "mission.phase",
                                "",
                            ),
                            -1,
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
                            rpm
                            / 1000.0,
                            minimum_denominator=
                                0.1,
                        ),

                    "fuel_flow_per_load":
                        safe_ratio(
                            fuel_flow,
                            load
                            / 100.0,
                            minimum_denominator=
                                0.01,
                        ),

                    "vibration_per_1000rpm":
                        safe_ratio(
                            vibration,
                            rpm
                            / 1000.0,
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
                        / SAMPLE_INTERVAL_SEC,

                    "oil_pressure_rate_per_sec":
                        oil_pressure_delta
                        / SAMPLE_INTERVAL_SEC,

                    "oil_temperature_rate_per_sec":
                        oil_temperature_delta
                        / SAMPLE_INTERVAL_SEC,

                    "fuel_pressure_rate_per_sec":
                        fuel_pressure_delta
                        / SAMPLE_INTERVAL_SEC,

                    "vibration_rate_per_sec":
                        vibration_delta
                        / SAMPLE_INTERVAL_SEC,

                    "cht_mean_rate_per_sec":
                        cht_mean_delta
                        / SAMPLE_INTERVAL_SEC,

                    "egt_mean_rate_per_sec":
                        egt_mean_delta
                        / SAMPLE_INTERVAL_SEC,

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
            )

            writer.writerow(
                output
            )

            previous = {
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

    print(
        "Rows:",
        len(
            rows
        )
    )

    print(
        "Missions:",
        mission_count
    )

    print(
        "Raw features:",
        len(
            available_raw_features
        )
    )

    print(
        "Derived features:",
        len(
            DERIVED_FEATURES
        )
    )

    return {
        "split":
            split,

        "rows":
            len(
                rows
            ),

        "missions":
            mission_count,

        "raw_features":
            available_raw_features,

        "derived_features":
            list(
                DERIVED_FEATURES
            ),

        "output":
            str(
                output_path
            ),
    }


def main() -> None:

    print(
        "=" * 82
    )

    print(
        "PRATIRUP ML-B FEATURE ENGINEERING"
    )

    print(
        "=" * 82
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    results = {}

    for split in (
        "train",
        "validation",
        "test",
    ):

        results[
            split
        ] = process_split(
            split,
            INPUT_FILES[
                split
            ],
            OUTPUT_FILES[
                split
            ],
        )

    if (
        results[
            "train"
        ][
            "rows"
        ]
        != 45630
    ):
        raise RuntimeError(
            "Train row count changed."
        )

    if (
        results[
            "validation"
        ][
            "rows"
        ]
        != 15210
    ):
        raise RuntimeError(
            "Validation row count changed."
        )

    if (
        results[
            "test"
        ][
            "rows"
        ]
        != 15210
    ):
        raise RuntimeError(
            "Test row count changed."
        )

    manifest = {
        "name":
            "PRATIRUP ML Feature Dataset",

        "version":
            VERSION,

        "source_dataset":
            "ML-A synthetic operational dataset v1",

        "mission_level_split_preserved":
            True,

        "future_information_used":
            False,

        "causal_rolling_features":
            True,

        "sampling_interval_sec":
            SAMPLE_INTERVAL_SEC,

        "rolling_window_sec":
            ROLLING_WINDOW_SEC,

        "labels_used_for_feature_calculation":
            False,

        "database_writes":
            False,

        "digital_twin_reprocessing":
            False,

        "synthetic":
            True,

        "real_operational_data":
            False,

        "results":
            results,
    }

    with MANIFEST_PATH.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            manifest,
            handle,
            indent=2,
        )

    print()
    print(
        "=" * 82
    )

    print(
        "ML-B FEATURE ENGINEERING COMPLETE"
    )

    print(
        "=" * 82
    )

    print(
        "TRAIN      :",
        results[
            "train"
        ][
            "rows"
        ],
    )

    print(
        "VALIDATION :",
        results[
            "validation"
        ][
            "rows"
        ],
    )

    print(
        "TEST       :",
        results[
            "test"
        ][
            "rows"
        ],
    )

    print()
    print(
        "Mission split preserved : TRUE"
    )

    print(
        "Future leakage           : FALSE"
    )

    print(
        "Labels used as features  : FALSE"
    )

    print(
        "Database writes          : 0"
    )

    print(
        "Digital Twin reprocessing: 0"
    )

    print()
    print(
        "ML-B STATUS: FEATURES GENERATED / READY FOR ACCEPTANCE"
    )

    print(
        "=" * 82
    )


if __name__ == "__main__":
    main()
