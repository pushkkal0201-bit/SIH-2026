from __future__ import annotations

import csv
import hashlib
import json
import math

from collections import Counter, defaultdict
from pathlib import Path

import joblib
import numpy as np

from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


TEST_PATH = Path(
    "data/processed/pratirup_test_features_v1.csv"
)

TRAINING_REPORT_PATH = Path(
    "reports/ml/pratirup_ml_c_training_report_v1.json"
)

MODEL_MANIFEST_PATH = Path(
    "ml/artifacts/pratirup_ml_model_manifest_v1.json"
)

ANOMALY_MODEL_PATH = Path(
    "ml/artifacts/pratirup_anomaly_model_v1.joblib"
)

FAULT_MODEL_PATH = Path(
    "ml/artifacts/pratirup_fault_model_v1.joblib"
)

OUTPUT_REPORT_PATH = Path(
    "reports/ml/pratirup_ml_d_test_report_v1.json"
)

PREDICTIONS_PATH = Path(
    "reports/ml/pratirup_ml_d_predictions_v1.csv"
)


ANOMALY_MIN_F1 = 0.95
ANOMALY_MIN_BALANCED_ACCURACY = 0.95
ANOMALY_MAX_FALSE_POSITIVE_RATE = 0.05
ANOMALY_MAX_FALSE_NEGATIVE_RATE = 0.10

FAULT_MIN_MACRO_F1 = 0.90
FAULT_MIN_BALANCED_ACCURACY = 0.90

MAX_ANOMALY_VALIDATION_DROP = 0.05
MAX_FAULT_VALIDATION_DROP = 0.05


FAULT_CLASSES = [
    "NORMAL",
    "OIL_PRESSURE_LOSS",
    "COOLING_DEGRADATION",
    "EGT_IMBALANCE",
    "FUEL_PRESSURE_LOSS",
    "VIBRATION_INCREASE",
]


def sha256(path: Path) -> str:

    digest = hashlib.sha256()

    with path.open("rb") as handle:

        while True:

            block = handle.read(
                1024 * 1024
            )

            if not block:
                break

            digest.update(
                block
            )

    return digest.hexdigest()


def json_safe(value):

    if isinstance(value, dict):

        return {
            str(key):
                json_safe(item)
            for key, item
            in value.items()
        }

    if isinstance(value, (list, tuple)):

        return [
            json_safe(item)
            for item in value
        ]

    if isinstance(value, np.ndarray):

        return value.tolist()

    if isinstance(value, np.bool_):

        return bool(value)

    if isinstance(value, np.integer):

        return int(value)

    if isinstance(value, np.floating):

        return float(value)

    return value


def safe_rate(
    numerator,
    denominator,
):

    if denominator == 0:
        return 0.0

    return (
        numerator
        / denominator
    )


print("=" * 92)
print("PRATIRUP ML-D — UNSEEN TEST-MISSION EVALUATION")
print("=" * 92)


with TRAINING_REPORT_PATH.open(
    "r",
    encoding="utf-8",
) as handle:

    training_report = json.load(
        handle
    )


with MODEL_MANIFEST_PATH.open(
    "r",
    encoding="utf-8",
) as handle:

    model_manifest = json.load(
        handle
    )


FEATURES = training_report[
    "feature_names"
]


print("\n[D1] TEST ARTIFACT IDENTITY")

recorded_test_hash = (
    training_report[
        "test_file_sha256"
    ]
)

current_test_hash = sha256(
    TEST_PATH
)


print(
    "ML-C recorded SHA256:",
    recorded_test_hash,
)

print(
    "ML-D current SHA256 :",
    current_test_hash,
)


if (
    current_test_hash
    != recorded_test_hash
):

    raise RuntimeError(
        "TEST ARTIFACT CHANGED SINCE ML-C. "
        "ML-D evaluation aborted."
    )


print(
    "Test artifact identity: PASS"
)


print("\n[D2] FROZEN MODEL ARTIFACTS")

anomaly_model_hash = sha256(
    ANOMALY_MODEL_PATH
)

fault_model_hash = sha256(
    FAULT_MODEL_PATH
)


anomaly_model = joblib.load(
    ANOMALY_MODEL_PATH
)

fault_model = joblib.load(
    FAULT_MODEL_PATH
)


print(
    "Anomaly model:",
    model_manifest[
        "anomaly_model"
    ][
        "algorithm"
    ],
)

print(
    "Fault model:",
    model_manifest[
        "fault_model"
    ][
        "algorithm"
    ],
)

print(
    "Features:",
    len(
        FEATURES
    ),
)


print("\n[D3] FIRST HOLDOUT DATA LOAD")

with TEST_PATH.open(
    "r",
    encoding="utf-8",
    newline="",
) as handle:

    reader = csv.DictReader(
        handle
    )

    rows = list(
        reader
    )

    columns = (
        reader.fieldnames
        or []
    )


missing = [
    feature
    for feature
    in FEATURES
    if feature
    not in columns
]


if missing:

    raise RuntimeError(
        "Missing frozen feature(s): "
        + ", ".join(
            missing
        )
    )


X = np.empty(
    (
        len(rows),
        len(FEATURES),
    ),
    dtype=np.float64,
)

y_anomaly = np.empty(
    len(rows),
    dtype=np.int8,
)

y_fault = np.empty(
    len(rows),
    dtype=object,
)

missions = np.empty(
    len(rows),
    dtype=object,
)

sample_indices = np.empty(
    len(rows),
    dtype=np.int32,
)


for row_index, row in enumerate(
    rows
):

    for feature_index, feature in enumerate(
        FEATURES
    ):

        value = float(
            row[
                feature
            ]
        )

        if not math.isfinite(
            value
        ):

            raise RuntimeError(
                "Non-finite test feature: "
                f"{feature}"
            )

        X[
            row_index,
            feature_index,
        ] = value


    y_anomaly[
        row_index
    ] = int(
        row[
            "anomaly_target"
        ]
    )

    y_fault[
        row_index
    ] = row[
        "sample_label"
    ]

    missions[
        row_index
    ] = row[
        "dataset_mission_id"
    ]

    sample_indices[
        row_index
    ] = int(
        row[
            "sample_index"
        ]
    )


unique_missions = sorted(
    set(
        missions.tolist()
    )
)


print(
    "Test rows    :",
    len(rows),
)

print(
    "Test missions:",
    len(
        unique_missions
    ),
)

print(
    "Model inputs :",
    X.shape[
        1
    ],
)


if len(
    rows
) != 15210:

    raise RuntimeError(
        "Unexpected test row count."
    )


if len(
    unique_missions
) != 10:

    raise RuntimeError(
        "Unexpected test mission count."
    )


print("\n[D4] FROZEN MODEL INFERENCE")

anomaly_prediction = (
    anomaly_model.predict(
        X
    )
)

fault_prediction = (
    fault_model.predict(
        X
    )
)


anomaly_probability = None

if hasattr(
    anomaly_model,
    "predict_proba",
):

    probabilities = (
        anomaly_model.predict_proba(
            X
        )
    )

    if probabilities.shape[
        1
    ] >= 2:

        anomaly_probability = (
            probabilities[
                :,
                1,
            ]
        )


fault_confidence = None

if hasattr(
    fault_model,
    "predict_proba",
):

    probabilities = (
        fault_model.predict_proba(
            X
        )
    )

    fault_confidence = (
        probabilities.max(
            axis=1
        )
    )


print(
    "Inference samples:",
    len(
        anomaly_prediction
    ),
)

print(
    "Model fitting performed:",
    False,
)

print(
    "Threshold tuning performed:",
    False,
)


print("\n[D5] ANOMALY HOLDOUT METRICS")

anomaly_matrix = confusion_matrix(
    y_anomaly,
    anomaly_prediction,
    labels=[
        0,
        1,
    ],
)


tn, fp, fn, tp = (
    anomaly_matrix.ravel()
)


anomaly_accuracy = (
    accuracy_score(
        y_anomaly,
        anomaly_prediction,
    )
)

anomaly_balanced = (
    balanced_accuracy_score(
        y_anomaly,
        anomaly_prediction,
    )
)

anomaly_precision = (
    precision_score(
        y_anomaly,
        anomaly_prediction,
        zero_division=0,
    )
)

anomaly_recall = (
    recall_score(
        y_anomaly,
        anomaly_prediction,
        zero_division=0,
    )
)

anomaly_f1 = (
    f1_score(
        y_anomaly,
        anomaly_prediction,
        zero_division=0,
    )
)

false_positive_rate = (
    safe_rate(
        fp,
        fp + tn,
    )
)

false_negative_rate = (
    safe_rate(
        fn,
        fn + tp,
    )
)


anomaly_auc = None

if anomaly_probability is not None:

    anomaly_auc = (
        roc_auc_score(
            y_anomaly,
            anomaly_probability,
        )
    )


print(
    "Accuracy           :",
    round(
        anomaly_accuracy,
        6,
    ),
)

print(
    "Balanced accuracy  :",
    round(
        anomaly_balanced,
        6,
    ),
)

print(
    "Precision          :",
    round(
        anomaly_precision,
        6,
    ),
)

print(
    "Recall             :",
    round(
        anomaly_recall,
        6,
    ),
)

print(
    "F1                 :",
    round(
        anomaly_f1,
        6,
    ),
)

print(
    "False positive rate:",
    round(
        false_positive_rate,
        6,
    ),
)

print(
    "False negative rate:",
    round(
        false_negative_rate,
        6,
    ),
)

print(
    "Confusion matrix:"
)

print(
    anomaly_matrix
)

if anomaly_auc is not None:

    print(
        "ROC-AUC            :",
        round(
            anomaly_auc,
            6,
        )
    )


print("\n[D6] FAULT HOLDOUT METRICS")

fault_accuracy = (
    accuracy_score(
        y_fault,
        fault_prediction,
    )
)

fault_balanced = (
    balanced_accuracy_score(
        y_fault,
        fault_prediction,
    )
)

fault_macro_precision = (
    precision_score(
        y_fault,
        fault_prediction,
        average="macro",
        zero_division=0,
    )
)

fault_macro_recall = (
    recall_score(
        y_fault,
        fault_prediction,
        average="macro",
        zero_division=0,
    )
)

fault_macro_f1 = (
    f1_score(
        y_fault,
        fault_prediction,
        average="macro",
        zero_division=0,
    )
)

fault_weighted_f1 = (
    f1_score(
        y_fault,
        fault_prediction,
        average="weighted",
        zero_division=0,
    )
)


fault_matrix = confusion_matrix(
    y_fault,
    fault_prediction,
    labels=
        FAULT_CLASSES,
)


fault_report = classification_report(
    y_fault,
    fault_prediction,
    labels=
        FAULT_CLASSES,
    output_dict=True,
    zero_division=0,
)


print(
    "Accuracy          :",
    round(
        fault_accuracy,
        6,
    ),
)

print(
    "Balanced accuracy :",
    round(
        fault_balanced,
        6,
    ),
)

print(
    "Macro precision   :",
    round(
        fault_macro_precision,
        6,
    ),
)

print(
    "Macro recall      :",
    round(
        fault_macro_recall,
        6,
    ),
)

print(
    "Macro F1          :",
    round(
        fault_macro_f1,
        6,
    ),
)

print(
    "Weighted F1       :",
    round(
        fault_weighted_f1,
        6,
    ),
)


print(
    "\nPer-class recall:"
)

for fault_class in (
    FAULT_CLASSES
):

    print(
        f"{fault_class:<28}",
        round(
            fault_report[
                fault_class
            ][
                "recall"
            ],
            6,
        ),
    )


print(
    "\nFault confusion matrix:"
)

print(
    fault_matrix
)


print("\n[D7] MISSION-LEVEL GENERALIZATION")

mission_results = {}


for mission_id in (
    unique_missions
):

    mask = (
        missions
        == mission_id
    )

    true_anomaly = (
        y_anomaly[
            mask
        ]
    )

    predicted_anomaly = (
        anomaly_prediction[
            mask
        ]
    )

    true_fault = (
        y_fault[
            mask
        ]
    )

    predicted_fault = (
        fault_prediction[
            mask
        ]
    )


    mission_fault_types = {
        row["mission_fault_type"]
        for row in rows
        if row["dataset_mission_id"] == mission_id
    }

    if len(mission_fault_types) != 1:
        raise RuntimeError(
            f"Mission {mission_id} has inconsistent "
            "mission_fault_type values."
        )

    mission_primary_class = next(
        iter(
            mission_fault_types
        )
    )


    mission_accuracy = (
        accuracy_score(
            true_anomaly,
            predicted_anomaly,
        )
    )


    mission_fault_accuracy = (
        accuracy_score(
            true_fault,
            predicted_fault,
        )
    )


    positive_count = int(
        np.sum(
            true_anomaly
            == 1
        )
    )

    negative_count = int(
        np.sum(
            true_anomaly
            == 0
        )
    )


    if positive_count > 0:

        mission_anomaly_recall = (
            recall_score(
                true_anomaly,
                predicted_anomaly,
                zero_division=0,
            )
        )

    else:

        mission_anomaly_recall = None


    if negative_count > 0:

        mission_false_positive_rate = (
            safe_rate(
                int(
                    np.sum(
                        (
                            true_anomaly
                            == 0
                        )
                        &
                        (
                            predicted_anomaly
                            == 1
                        )
                    )
                ),
                negative_count,
            )
        )

    else:

        mission_false_positive_rate = None


    mission_results[
        mission_id
    ] = {
        "primary_fault_class":
            mission_primary_class,

        "samples":
            int(
                np.sum(
                    mask
                )
            ),

        "anomaly_accuracy":
            mission_accuracy,

        "anomaly_recall_if_fault_present":
            mission_anomaly_recall,

        "false_positive_rate":
            mission_false_positive_rate,

        "fault_accuracy":
            mission_fault_accuracy,
    }


    print()
    print(
        mission_id,
        "|",
        mission_primary_class,
    )

    print(
        "  anomaly accuracy:",
        round(
            mission_accuracy,
            6,
        ),
    )

    if (
        mission_anomaly_recall
        is not None
    ):

        print(
            "  anomaly recall  :",
            round(
                mission_anomaly_recall,
                6,
            ),
        )

    print(
        "  fault accuracy  :",
        round(
            mission_fault_accuracy,
            6,
        ),
    )


print("\n[D8] VALIDATION -> TEST GENERALIZATION")

selected_anomaly = (
    training_report[
        "selected_anomaly_model"
    ]
)

selected_fault = (
    training_report[
        "selected_fault_model"
    ]
)


validation_anomaly_f1 = (
    training_report[
        "anomaly_candidates"
    ][
        selected_anomaly
    ][
        "validation"
    ][
        "f1"
    ]
)

validation_fault_macro_f1 = (
    training_report[
        "fault_candidates"
    ][
        selected_fault
    ][
        "validation"
    ][
        "macro_f1"
    ]
)


anomaly_drop = (
    validation_anomaly_f1
    - anomaly_f1
)

fault_drop = (
    validation_fault_macro_f1
    - fault_macro_f1
)


print(
    "Validation anomaly F1:",
    round(
        validation_anomaly_f1,
        6,
    ),
)

print(
    "Test anomaly F1      :",
    round(
        anomaly_f1,
        6,
    ),
)

print(
    "Anomaly F1 drop      :",
    round(
        anomaly_drop,
        6,
    ),
)


print()
print(
    "Validation fault macro-F1:",
    round(
        validation_fault_macro_f1,
        6,
    ),
)

print(
    "Test fault macro-F1      :",
    round(
        fault_macro_f1,
        6,
    ),
)

print(
    "Fault macro-F1 drop      :",
    round(
        fault_drop,
        6,
    ),
)


print("\n[D9] PRE-DECLARED ACCEPTANCE CRITERIA")

criteria = {
    "anomaly_f1":
        anomaly_f1
        >= ANOMALY_MIN_F1,

    "anomaly_balanced_accuracy":
        anomaly_balanced
        >= ANOMALY_MIN_BALANCED_ACCURACY,

    "anomaly_false_positive_rate":
        false_positive_rate
        <= ANOMALY_MAX_FALSE_POSITIVE_RATE,

    "anomaly_false_negative_rate":
        false_negative_rate
        <= ANOMALY_MAX_FALSE_NEGATIVE_RATE,

    "fault_macro_f1":
        fault_macro_f1
        >= FAULT_MIN_MACRO_F1,

    "fault_balanced_accuracy":
        fault_balanced
        >= FAULT_MIN_BALANCED_ACCURACY,

    "anomaly_generalization_drop":
        anomaly_drop
        <= MAX_ANOMALY_VALIDATION_DROP,

    "fault_generalization_drop":
        fault_drop
        <= MAX_FAULT_VALIDATION_DROP,
}


for criterion, passed in (
    criteria.items()
):

    print(
        f"{criterion:<42}",
        "PASS"
        if passed
        else "FAIL",
    )


print("\n[D10] EVALUATION PREDICTION EXPORT")


PREDICTIONS_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)


with PREDICTIONS_PATH.open(
    "w",
    encoding="utf-8",
    newline="",
) as handle:

    fieldnames = [
        "dataset_mission_id",
        "sample_index",

        "actual_anomaly",
        "predicted_anomaly",

        "actual_fault",
        "predicted_fault",

        "anomaly_probability",
        "fault_confidence",

        "evaluation_only",
    ]


    writer = csv.DictWriter(
        handle,
        fieldnames=
            fieldnames,
    )

    writer.writeheader()


    for index in range(
        len(
            rows
        )
    ):

        writer.writerow(
            {
                "dataset_mission_id":
                    missions[
                        index
                    ],

                "sample_index":
                    int(
                        sample_indices[
                            index
                        ]
                    ),

                "actual_anomaly":
                    int(
                        y_anomaly[
                            index
                        ]
                    ),

                "predicted_anomaly":
                    int(
                        anomaly_prediction[
                            index
                        ]
                    ),

                "actual_fault":
                    y_fault[
                        index
                    ],

                "predicted_fault":
                    fault_prediction[
                        index
                    ],

                "anomaly_probability":
                    (
                        float(
                            anomaly_probability[
                                index
                            ]
                        )
                        if anomaly_probability
                        is not None
                        else ""
                    ),

                "fault_confidence":
                    (
                        float(
                            fault_confidence[
                                index
                            ]
                        )
                        if fault_confidence
                        is not None
                        else ""
                    ),

                "evaluation_only":
                    1,
            }
        )


print(
    "Predictions:",
    PREDICTIONS_PATH,
)


report = {
    "project":
        "PRATIRUP",

    "stage":
        "ML-D",

    "evaluation_type":
        "COMPLETELY_UNSEEN_MISSION_HOLDOUT",

    "synthetic":
        True,

    "real_operational_validation":
        False,

    "test_rows":
        len(
            rows
        ),

    "test_missions":
        len(
            unique_missions
        ),

    "feature_count":
        len(
            FEATURES
        ),

    "test_artifact_sha256":
        current_test_hash,

    "anomaly_model_sha256":
        anomaly_model_hash,

    "fault_model_sha256":
        fault_model_hash,

    "model_fitting":
        False,

    "threshold_tuning":
        False,

    "algorithm_selection":
        False,

    "anomaly": {
        "accuracy":
            anomaly_accuracy,

        "balanced_accuracy":
            anomaly_balanced,

        "precision":
            anomaly_precision,

        "recall":
            anomaly_recall,

        "f1":
            anomaly_f1,

        "false_positive_rate":
            false_positive_rate,

        "false_negative_rate":
            false_negative_rate,

        "roc_auc":
            anomaly_auc,

        "confusion_matrix":
            anomaly_matrix,
    },

    "fault": {
        "accuracy":
            fault_accuracy,

        "balanced_accuracy":
            fault_balanced,

        "macro_precision":
            fault_macro_precision,

        "macro_recall":
            fault_macro_recall,

        "macro_f1":
            fault_macro_f1,

        "weighted_f1":
            fault_weighted_f1,

        "confusion_matrix":
            fault_matrix,

        "classification_report":
            fault_report,
    },

    "generalization": {
        "validation_anomaly_f1":
            validation_anomaly_f1,

        "test_anomaly_f1":
            anomaly_f1,

        "anomaly_f1_drop":
            anomaly_drop,

        "validation_fault_macro_f1":
            validation_fault_macro_f1,

        "test_fault_macro_f1":
            fault_macro_f1,

        "fault_macro_f1_drop":
            fault_drop,
    },

    "mission_results":
        mission_results,

    "acceptance_thresholds": {
        "anomaly_min_f1":
            ANOMALY_MIN_F1,

        "anomaly_min_balanced_accuracy":
            ANOMALY_MIN_BALANCED_ACCURACY,

        "anomaly_max_false_positive_rate":
            ANOMALY_MAX_FALSE_POSITIVE_RATE,

        "anomaly_max_false_negative_rate":
            ANOMALY_MAX_FALSE_NEGATIVE_RATE,

        "fault_min_macro_f1":
            FAULT_MIN_MACRO_F1,

        "fault_min_balanced_accuracy":
            FAULT_MIN_BALANCED_ACCURACY,

        "max_anomaly_validation_drop":
            MAX_ANOMALY_VALIDATION_DROP,

        "max_fault_validation_drop":
            MAX_FAULT_VALIDATION_DROP,
    },

    "acceptance":
        criteria,

    "all_acceptance_criteria_passed":
        all(
            criteria.values()
        ),

    "safety": {
        "flight_authorization":
            False,

        "certified":
            False,

        "database_writes":
            False,

        "digital_twin_modified":
            False,

        "real_drdo_vrde_accuracy_claim":
            False,
    },
}


with OUTPUT_REPORT_PATH.open(
    "w",
    encoding="utf-8",
) as handle:

    json.dump(
        json_safe(
            report
        ),
        handle,
        indent=2,
    )


print()
print("=" * 92)
print("PRATIRUP ML-D HOLDOUT RESULT")
print("=" * 92)

print(
    "TEST MISSIONS:",
    len(
        unique_missions
    ),
)

print(
    "TEST SAMPLES :",
    len(
        rows
    ),
)

print()
print(
    "ANOMALY F1       :",
    round(
        anomaly_f1,
        6,
    ),
)

print(
    "FAULT MACRO-F1   :",
    round(
        fault_macro_f1,
        6,
    ),
)

print()
print(
    "ALL CRITERIA PASS:",
    all(
        criteria.values()
    ),
)

print()
print(
    "MODEL FITTING       : 0"
)

print(
    "THRESHOLD TUNING    : 0"
)

print(
    "ALGORITHM SELECTION : 0"
)

print(
    "DATABASE WRITES     : 0"
)

print(
    "DIGITAL TWIN CHANGES: 0"
)

print(
    "FLIGHT AUTHORIZATION: FALSE"
)

print()

if all(
    criteria.values()
):

    print(
        "ML-D STATUS: HOLDOUT EVALUATION PASS / READY FOR ACCEPTANCE"
    )

else:

    print(
        "ML-D STATUS: HOLDOUT RESULTS REQUIRE REVIEW"
    )

print()
print(
    "REPORT:",
    OUTPUT_REPORT_PATH,
)

print("=" * 92)
