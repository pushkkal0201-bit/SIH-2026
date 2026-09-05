from __future__ import annotations

import csv
import json

from collections import Counter, defaultdict
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from random import Random
from typing import Any, Dict, List

from backend.mission.scenario import (
    MissionScenarioController,
)

from backend.ingestion.simulation_adapter import (
    SimulationAdapter,
    SimulationFault,
)


DATASET_VERSION = "1.0.0"

BASE_RANDOM_SEED = 26054

MISSION_COUNT = 50

SAMPLE_INTERVAL_SEC = 0.5

OUTPUT_DIRECTORY = Path(
    "data/synthetic"
)

MASTER_DATASET_PATH = (
    OUTPUT_DIRECTORY
    / "pratirup_operational_dataset_v1.csv"
)

TRAIN_DATASET_PATH = (
    OUTPUT_DIRECTORY
    / "pratirup_train_v1.csv"
)

VALIDATION_DATASET_PATH = (
    OUTPUT_DIRECTORY
    / "pratirup_validation_v1.csv"
)

TEST_DATASET_PATH = (
    OUTPUT_DIRECTORY
    / "pratirup_test_v1.csv"
)

MISSION_MANIFEST_PATH = (
    OUTPUT_DIRECTORY
    / "pratirup_missions_v1.json"
)

DATASET_MANIFEST_PATH = (
    OUTPUT_DIRECTORY
    / "pratirup_dataset_manifest_v1.json"
)


FAULT_CLASSES = (
    SimulationFault.OIL_PRESSURE_LOSS.value,
    SimulationFault.COOLING_DEGRADATION.value,
    SimulationFault.EGT_IMBALANCE.value,
    SimulationFault.FUEL_PRESSURE_LOSS.value,
    SimulationFault.VIBRATION_INCREASE.value,
)


SPLIT_PLAN = {

    "NORMAL": {
        "train": 6,
        "validation": 2,
        "test": 2,
    },

    SimulationFault.OIL_PRESSURE_LOSS.value: {
        "train": 4,
        "validation": 2,
        "test": 2,
    },

    SimulationFault.COOLING_DEGRADATION.value: {
        "train": 4,
        "validation": 2,
        "test": 2,
    },

    SimulationFault.EGT_IMBALANCE.value: {
        "train": 5,
        "validation": 1,
        "test": 2,
    },

    SimulationFault.FUEL_PRESSURE_LOSS.value: {
        "train": 5,
        "validation": 2,
        "test": 1,
    },

    SimulationFault.VIBRATION_INCREASE.value: {
        "train": 6,
        "validation": 1,
        "test": 1,
    },
}


FAULT_SEVERITIES = [
    0.25,
    0.25,
    0.50,
    0.50,
    0.75,
    0.75,
    1.00,
    1.00,
]

FAULT_START_TIMES_SEC = [
    120.0,
    160.0,
    200.0,
    240.0,
    280.0,
    320.0,
    360.0,
    400.0,
]

FAULT_RAMP_TIMES_SEC = [
    0.0,
    5.0,
    15.0,
    30.0,
    0.0,
    5.0,
    15.0,
    30.0,
]


LABEL_COLUMNS = [

    "dataset_version",

    "mission_index",
    "dataset_mission_id",

    "split",

    "sample_index",

    "mission_fault_type",

    "sample_label",

    "anomaly_target",

    "fault_active",

    "fault_requested_severity",

    "fault_effective_severity",

    "fault_start_sec",

    "fault_ramp_sec",

    "synthetic_data",

    "real_operational_measurement",

    "official_drdo_vrde_measurement",
]


def scalar_value(
    value: Any,
) -> Any:

    if value is None:
        return None

    if isinstance(
        value,
        Enum,
    ):
        return value.value

    if isinstance(
        value,
        (
            datetime,
            date,
        ),
    ):
        return value.isoformat()

    if isinstance(
        value,
        bool,
    ):
        return int(value)

    return value


def flatten_dict(
    data: Dict[str, Any],
    *,
    prefix: str = "",
) -> Dict[str, Any]:

    result: Dict[
        str,
        Any,
    ] = {}

    for key, value in data.items():

        full_key = (
            f"{prefix}.{key}"
            if prefix
            else str(key)
        )

        if isinstance(
            value,
            dict,
        ):

            result.update(
                flatten_dict(
                    value,
                    prefix=full_key,
                )
            )

        else:

            result[
                full_key
            ] = scalar_value(
                value
            )

    return result


def build_class_specs(
    class_name: str,
    rng: Random,
) -> List[
    Dict[str, Any]
]:

    if class_name == "NORMAL":

        return [
            {
                "mission_fault_type":
                    "NORMAL",

                "fault_requested_severity":
                    0.0,

                "fault_start_sec":
                    None,

                "fault_ramp_sec":
                    0.0,
            }
            for _ in range(10)
        ]

    starts = list(
        FAULT_START_TIMES_SEC
    )

    ramps = list(
        FAULT_RAMP_TIMES_SEC
    )

    rng.shuffle(
        starts
    )

    rng.shuffle(
        ramps
    )

    specs = []

    for index in range(8):

        specs.append(
            {
                "mission_fault_type":
                    class_name,

                "fault_requested_severity":
                    FAULT_SEVERITIES[
                        index
                    ],

                "fault_start_sec":
                    starts[
                        index
                    ],

                "fault_ramp_sec":
                    ramps[
                        index
                    ],
            }
        )

    return specs


def assign_splits(
) -> List[
    Dict[str, Any]
]:

    rng = Random(
        BASE_RANDOM_SEED
    )

    missions: List[
        Dict[str, Any]
    ] = []

    classes = (
        "NORMAL",
        *FAULT_CLASSES,
    )

    for class_index, class_name in enumerate(
        classes
    ):

        local_rng = Random(
            BASE_RANDOM_SEED
            + class_index
            * 100
        )

        class_specs = (
            build_class_specs(
                class_name,
                local_rng,
            )
        )

        local_rng.shuffle(
            class_specs
        )

        offset = 0

        split_counts = (
            SPLIT_PLAN[
                class_name
            ]
        )

        for split_name in (
            "train",
            "validation",
            "test",
        ):

            count = (
                split_counts[
                    split_name
                ]
            )

            selected = (
                class_specs[
                    offset:
                    offset + count
                ]
            )

            offset += count

            for specification in selected:

                mission = dict(
                    specification
                )

                mission[
                    "split"
                ] = split_name

                missions.append(
                    mission
                )

    if len(
        missions
    ) != MISSION_COUNT:

        raise RuntimeError(
            "Mission split generation "
            f"created {len(missions)} "
            f"missions instead of "
            f"{MISSION_COUNT}."
        )

    rng.shuffle(
        missions
    )

    for index, mission in enumerate(
        missions,
        start=1,
    ):

        mission[
            "mission_index"
        ] = index

        mission[
            "dataset_mission_id"
        ] = (
            "PRATIRUP-ML-"
            f"{index:03d}"
        )

        mission[
            "random_seed"
        ] = (
            BASE_RANDOM_SEED
            + index
        )

    return missions


def discover_canonical_columns(
) -> List[str]:

    controller = (
        MissionScenarioController(
            mission_id=(
                "PRATIRUP-ML-HEADER"
            )
        )
    )

    adapter = (
        SimulationAdapter(
            random_seed=
                BASE_RANDOM_SEED
        )
    )

    command = (
        controller
        .start()
        .to_dict()
    )

    payload = (
        adapter.build_payload(
            command,
            delta_sec=
                SAMPLE_INTERVAL_SEC,
        )
    )

    return sorted(
        flatten_dict(
            payload
        ).keys()
    )


def generate_mission(
    specification: Dict[str, Any],
    writers: Dict[str, csv.DictWriter],
    counters: Dict[str, Any],
) -> Dict[str, Any]:

    mission_id = (
        specification[
            "dataset_mission_id"
        ]
    )

    controller = (
        MissionScenarioController(
            mission_id=
                mission_id
        )
    )

    adapter = (
        SimulationAdapter(
            random_seed=
                specification[
                    "random_seed"
                ]
        )
    )

    command = (
        controller.start()
    )

    fault_type = (
        specification[
            "mission_fault_type"
        ]
    )

    fault_start = (
        specification[
            "fault_start_sec"
        ]
    )

    requested_severity = (
        specification[
            "fault_requested_severity"
        ]
    )

    ramp_sec = (
        specification[
            "fault_ramp_sec"
        ]
    )

    fault_injected = False

    sample_count = 0

    active_fault_samples = 0

    sample_index = 0

    while True:

        elapsed_sec = (
            float(
                command.elapsed_time_sec
            )
        )

        if (
            fault_type != "NORMAL"
            and
            not fault_injected
            and
            fault_start is not None
            and
            elapsed_sec
            >= float(
                fault_start
            )
        ):

            adapter.set_fault(
                fault_type,
                severity=
                    float(
                        requested_severity
                    ),
                ramp_sec=
                    float(
                        ramp_sec
                    ),
            )

            fault_injected = True

        payload = (
            adapter.build_payload(
                command.to_dict(),
                delta_sec=
                    SAMPLE_INTERVAL_SEC,
            )
        )

        fault_status = (
            adapter.get_fault_status()
        )

        active_faults = (
            fault_status.get(
                "active_faults",
                [],
            )
        )

        fault_active = bool(
            active_faults
        )

        effective_severity = 0.0

        if active_faults:

            effective_severity = float(
                active_faults[
                    0
                ].get(
                    "effective_severity",
                    0.0,
                )
                or 0.0
            )

        if (
            fault_active
            and
            effective_severity > 0.0
        ):

            sample_label = (
                fault_type
            )

            anomaly_target = 1

            active_fault_samples += 1

        else:

            sample_label = (
                "NORMAL"
            )

            anomaly_target = 0

        row = {

            "dataset_version":
                DATASET_VERSION,

            "mission_index":
                specification[
                    "mission_index"
                ],

            "dataset_mission_id":
                mission_id,

            "split":
                specification[
                    "split"
                ],

            "sample_index":
                sample_index,

            "mission_fault_type":
                fault_type,

            "sample_label":
                sample_label,

            "anomaly_target":
                anomaly_target,

            "fault_active":
                int(
                    fault_active
                ),

            "fault_requested_severity":
                requested_severity,

            "fault_effective_severity":
                effective_severity,

            "fault_start_sec":
                fault_start,

            "fault_ramp_sec":
                ramp_sec,

            "synthetic_data":
                1,

            "real_operational_measurement":
                0,

            "official_drdo_vrde_measurement":
                0,
        }

        row.update(
            flatten_dict(
                payload
            )
        )

        writers[
            "all"
        ].writerow(
            row
        )

        writers[
            specification[
                "split"
            ]
        ].writerow(
            row
        )

        sample_count += 1

        sample_index += 1

        counters[
            "total_rows"
        ] += 1

        counters[
            "split_rows"
        ][
            specification[
                "split"
            ]
        ] += 1

        counters[
            "sample_labels"
        ][
            sample_label
        ] += 1

        if (
            elapsed_sec
            >= controller
            .total_duration_sec
        ):
            break

        command = (
            controller.update(
                SAMPLE_INTERVAL_SEC
            )
        )

    result = dict(
        specification
    )

    result[
        "sample_count"
    ] = sample_count

    result[
        "active_fault_samples"
    ] = active_fault_samples

    result[
        "mission_duration_sec"
    ] = (
        controller
        .total_duration_sec
    )

    return result


def main(
) -> None:

    print(
        "=" * 80
    )

    print(
        "PRATIRUP SYNTHETIC OPERATIONAL DATASET GENERATOR"
    )

    print(
        "=" * 80
    )

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    missions = (
        assign_splits()
    )

    canonical_columns = (
        discover_canonical_columns()
    )

    fieldnames = (
        LABEL_COLUMNS
        + [
            column
            for column
            in canonical_columns
            if column
            not in LABEL_COLUMNS
        ]
    )

    handles = {

        "all":
            MASTER_DATASET_PATH.open(
                "w",
                newline="",
                encoding="utf-8",
            ),

        "train":
            TRAIN_DATASET_PATH.open(
                "w",
                newline="",
                encoding="utf-8",
            ),

        "validation":
            VALIDATION_DATASET_PATH.open(
                "w",
                newline="",
                encoding="utf-8",
            ),

        "test":
            TEST_DATASET_PATH.open(
                "w",
                newline="",
                encoding="utf-8",
            ),
    }

    writers = {

        name:
            csv.DictWriter(
                handle,
                fieldnames=
                    fieldnames,
                extrasaction=
                    "ignore",
            )

        for name, handle
        in handles.items()
    }

    for writer in writers.values():
        writer.writeheader()

    counters = {

        "total_rows":
            0,

        "split_rows":
            Counter(),

        "sample_labels":
            Counter(),
    }

    generated_missions = []

    try:

        for mission in missions:

            generated = (
                generate_mission(
                    mission,
                    writers,
                    counters,
                )
            )

            generated_missions.append(
                generated
            )

            print(
                f"{generated['dataset_mission_id']} | "
                f"{generated['split']:<10} | "
                f"{generated['mission_fault_type']:<24} | "
                f"samples={generated['sample_count']}"
            )

    finally:

        for handle in handles.values():
            handle.close()

    mission_split_counts = Counter(
        mission[
            "split"
        ]
        for mission
        in generated_missions
    )

    mission_class_counts = Counter(
        mission[
            "mission_fault_type"
        ]
        for mission
        in generated_missions
    )

    if mission_split_counts != Counter(
        {
            "train": 30,
            "validation": 10,
            "test": 10,
        }
    ):
        raise RuntimeError(
            "Mission-level split contract failed: "
            f"{dict(mission_split_counts)}"
        )

    if counters[
        "total_rows"
    ] < 50_000:

        raise RuntimeError(
            "Dataset contains fewer than "
            "50,000 samples."
        )

    if counters[
        "total_rows"
    ] > 100_000:

        raise RuntimeError(
            "Dataset contains more than "
            "100,000 samples."
        )

    with MISSION_MANIFEST_PATH.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            generated_missions,
            handle,
            indent=2,
        )

    manifest = {

        "dataset":
            "PRATIRUP Synthetic Operational Dataset",

        "version":
            DATASET_VERSION,

        "problem_statement_id":
            26054,

        "data_origin":
            "PRATIRUP_SYNTHETIC_SIMULATOR",

        "synthetic":
            True,

        "real_operational_data":
            False,

        "official_drdo_vrde_measurements":
            False,

        "classified_data":
            False,

        "sampling_interval_sec":
            SAMPLE_INTERVAL_SEC,

        "sampling_frequency_hz":
            1.0
            / SAMPLE_INTERVAL_SEC,

        "mission_count":
            len(
                generated_missions
            ),

        "mission_split_counts":
            dict(
                mission_split_counts
            ),

        "mission_class_counts":
            dict(
                mission_class_counts
            ),

        "total_samples":
            counters[
                "total_rows"
            ],

        "split_sample_counts":
            dict(
                counters[
                    "split_rows"
                ]
            ),

        "sample_label_counts":
            dict(
                counters[
                    "sample_labels"
                ]
            ),

        "fault_classes":
            list(
                FAULT_CLASSES
            ),

        "normal_class":
            "NORMAL",

        "targets": {

            "anomaly_detection":
                "anomaly_target",

            "fault_classification":
                "sample_label",
        },

        "rul_target_included":
            False,

        "rul_dataset_policy":
            (
                "RUL/lifecycle dataset is generated "
                "separately from frozen D9 synthetic "
                "lifecycle modules."
            ),

        "canonical_column_count":
            len(
                canonical_columns
            ),

        "total_column_count":
            len(
                fieldnames
            ),

        "files": {

            "all":
                str(
                    MASTER_DATASET_PATH
                ),

            "train":
                str(
                    TRAIN_DATASET_PATH
                ),

            "validation":
                str(
                    VALIDATION_DATASET_PATH
                ),

            "test":
                str(
                    TEST_DATASET_PATH
                ),

            "missions":
                str(
                    MISSION_MANIFEST_PATH
                ),
        },
    }

    with DATASET_MANIFEST_PATH.open(
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
        "=" * 80
    )

    print(
        "DATASET GENERATION COMPLETE"
    )

    print(
        "=" * 80
    )

    print(
        "Missions:",
        len(
            generated_missions
        ),
    )

    print(
        "Mission splits:",
        dict(
            mission_split_counts
        ),
    )

    print(
        "Mission classes:",
        dict(
            mission_class_counts
        ),
    )

    print(
        "Total samples:",
        counters[
            "total_rows"
        ],
    )

    print(
        "Split samples:",
        dict(
            counters[
                "split_rows"
            ]
        ),
    )

    print(
        "Sample labels:",
        dict(
            counters[
                "sample_labels"
            ]
        ),
    )

    print()
    print(
        "MASTER:",
        MASTER_DATASET_PATH,
    )

    print(
        "TRAIN :",
        TRAIN_DATASET_PATH,
    )

    print(
        "VALID :",
        VALIDATION_DATASET_PATH,
    )

    print(
        "TEST  :",
        TEST_DATASET_PATH,
    )

    print(
        "MANIFEST:",
        DATASET_MANIFEST_PATH,
    )

    print()
    print(
        "DATABASE WRITES          : 0"
    )

    print(
        "TELEMETRY API POSTS      : 0"
    )

    print(
        "DIGITAL TWIN REPROCESSING: 0"
    )

    print(
        "REAL / CLASSIFIED DATA   : 0"
    )

    print()
    print(
        "ML-A STATUS: DATASET GENERATED / READY FOR ACCEPTANCE"
    )

    print(
        "=" * 80
    )


if __name__ == "__main__":

    main()
