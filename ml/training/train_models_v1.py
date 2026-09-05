from __future__ import annotations
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
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
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

VERSION = "1.0.0"
RANDOM_STATE = 26054

TRAIN_PATH = Path(
    "data/processed/"
    "pratirup_train_features_v1.csv"
)

VALIDATION_PATH = Path(
    "data/processed/"
    "pratirup_validation_features_v1.csv"
)

TEST_PATH = Path(
    "data/processed/"
    "pratirup_test_features_v1.csv"
)

ARTIFACT_DIR = Path(
    "ml/artifacts"
)

REPORT_DIR = Path(
    "reports/ml"
)

ANOMALY_MODEL_PATH = (
    ARTIFACT_DIR
    / "pratirup_anomaly_model_v1.joblib"
)

FAULT_MODEL_PATH = (
    ARTIFACT_DIR
    / "pratirup_fault_model_v1.joblib"
)

TRAINING_REPORT_PATH = (
    REPORT_DIR
    / "pratirup_ml_c_training_report_v1.json"
)

MODEL_MANIFEST_PATH = (
    ARTIFACT_DIR
    / "pratirup_ml_model_manifest_v1.json"
)

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

FAULT_CLASSES = [
    "NORMAL",
    "OIL_PRESSURE_LOSS",
    "COOLING_DEGRADATION",
    "EGT_IMBALANCE",
    "FUEL_PRESSURE_LOSS",
    "VIBRATION_INCREASE",
]

FORBIDDEN_FEATURES = {
    "sample_label",
    "anomaly_target",
    "mission_fault_type",
    "fault_active",
    "fault_requested_severity",
    "fault_effective_severity",
    "dataset_mission_id",
    "mission_index",
    "sample_index",
    "split",
}


def file_sha256(
    path: Path,
) -> str:

    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:

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


def load_dataset(
    path: Path,
):

    with path.open(
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
            "Missing ML-B features: "
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

    anomaly = np.empty(
        len(rows),
        dtype=np.int8,
    )

    fault = np.empty(
        len(rows),
        dtype=object,
    )

    missions = np.empty(
        len(rows),
        dtype=object,
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
                    "Non-finite feature "
                    f"{feature} at row "
                    f"{row_index}."
                )

            X[
                row_index,
                feature_index,
            ] = value

        anomaly[
            row_index
        ] = int(
            row[
                "anomaly_target"
            ]
        )

        fault[
            row_index
        ] = row[
            "sample_label"
        ]

        missions[
            row_index
        ] = row[
            "dataset_mission_id"
        ]

    return (
        X,
        anomaly,
        fault,
        missions,
        columns,
    )


def json_safe(
    value: Any,
):

    if isinstance(
        value,
        dict,
    ):

        return {
            str(key):
                json_safe(
                    item
                )
            for key, item
            in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):

        return [
            json_safe(
                item
            )
            for item
            in value
        ]

    if isinstance(
        value,
        np.ndarray,
    ):

        return value.tolist()

    if isinstance(
        value,
        np.integer,
    ):

        return int(
            value
        )

    if isinstance(
        value,
        np.floating,
    ):

        return float(
            value
        )

    return value


def make_logistic():

    return Pipeline(
        [
            (
                "scaler",
                StandardScaler(),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=3000,
                    class_weight="balanced",
                    random_state=
                        RANDOM_STATE,
                ),
            ),
        ]
    )


def make_random_forest():

    return RandomForestClassifier(
        n_estimators=160,
        max_depth=16,
        min_samples_leaf=2,
        class_weight=
            "balanced_subsample",
        random_state=
            RANDOM_STATE,
        n_jobs=-1,
    )


def binary_metrics(
    model,
    X,
    y,
):

    prediction = (
        model.predict(
            X
        )
    )

    matrix = confusion_matrix(
        y,
        prediction,
        labels=[
            0,
            1,
        ],
    )

    tn, fp, fn, tp = (
        matrix.ravel()
    )

    false_positive_rate = (
        fp
        / (
            fp
            + tn
        )
        if (
            fp
            + tn
        ) > 0
        else 0.0
    )

    false_negative_rate = (
        fn
        / (
            fn
            + tp
        )
        if (
            fn
            + tp
        ) > 0
        else 0.0
    )

    result = {
        "accuracy":
            accuracy_score(
                y,
                prediction,
            ),

        "balanced_accuracy":
            balanced_accuracy_score(
                y,
                prediction,
            ),

        "precision":
            precision_score(
                y,
                prediction,
                zero_division=0,
            ),

        "recall":
            recall_score(
                y,
                prediction,
                zero_division=0,
            ),

        "f1":
            f1_score(
                y,
                prediction,
                zero_division=0,
            ),

        "false_positive_rate":
            false_positive_rate,

        "false_negative_rate":
            false_negative_rate,

        "confusion_matrix":
            matrix,
    }

    if hasattr(
        model,
        "predict_proba",
    ):

        probabilities = (
            model.predict_proba(
                X
            )
        )

        if probabilities.shape[
            1
        ] >= 2:

            result[
                "roc_auc"
            ] = roc_auc_score(
                y,
                probabilities[
                    :,
                    1,
                ],
            )

    return result


def multiclass_metrics(
    model,
    X,
    y,
):

    prediction = (
        model.predict(
            X
        )
    )

    return {
        "accuracy":
            accuracy_score(
                y,
                prediction,
            ),

        "balanced_accuracy":
            balanced_accuracy_score(
                y,
                prediction,
            ),

        "macro_precision":
            precision_score(
                y,
                prediction,
                average="macro",
                zero_division=0,
            ),

        "macro_recall":
            recall_score(
                y,
                prediction,
                average="macro",
                zero_division=0,
            ),

        "macro_f1":
            f1_score(
                y,
                prediction,
                average="macro",
                zero_division=0,
            ),

        "weighted_f1":
            f1_score(
                y,
                prediction,
                average="weighted",
                zero_division=0,
            ),

        "confusion_matrix":
            confusion_matrix(
                y,
                prediction,
                labels=
                    FAULT_CLASSES,
            ),

        "classification_report":
            classification_report(
                y,
                prediction,
                labels=
                    FAULT_CLASSES,
                output_dict=True,
                zero_division=0,
            ),
    }


def binary_mission_scores(
    model,
    X,
    y,
    missions,
):

    scores = {}

    for mission_id in sorted(
        set(
            missions.tolist()
        )
    ):

        mask = (
            missions
            == mission_id
        )

        prediction = (
            model.predict(
                X[
                    mask
                ]
            )
        )

        scores[
            mission_id
        ] = f1_score(
            y[
                mask
            ],
            prediction,
            zero_division=0,
        )

    values = list(
        scores.values()
    )

    return {
        "per_mission":
            scores,

        "mean_f1":
            float(
                np.mean(
                    values
                )
            ),

        "minimum_f1":
            float(
                np.min(
                    values
                )
            ),
    }


def multiclass_mission_scores(
    model,
    X,
    y,
    missions,
):

    scores = {}

    for mission_id in sorted(
        set(
            missions.tolist()
        )
    ):

        mask = (
            missions
            == mission_id
        )

        prediction = (
            model.predict(
                X[
                    mask
                ]
            )
        )

        scores[
            mission_id
        ] = f1_score(
            y[
                mask
            ],
            prediction,
            average="macro",
            zero_division=0,
        )

    values = list(
        scores.values()
    )

    return {
        "per_mission":
            scores,

        "mean_macro_f1":
            float(
                np.mean(
                    values
                )
            ),

        "minimum_macro_f1":
            float(
                np.min(
                    values
                )
            ),
    }


def extract_feature_importance(
    model,
):

    importance = None

    if hasattr(
        model,
        "feature_importances_",
    ):

        importance = (
            model
            .feature_importances_
        )

    elif isinstance(
        model,
        Pipeline,
    ):

        classifier = (
            model.named_steps[
                "classifier"
            ]
        )

        if hasattr(
            classifier,
            "coef_",
        ):

            coefficients = np.abs(
                classifier.coef_
            )

            importance = (
                coefficients
                .mean(
                    axis=0
                )
            )

    if importance is None:
        return []

    pairs = list(
        zip(
            FEATURES,
            importance.tolist(),
        )
    )

    pairs.sort(
        key=lambda item:
            item[
                1
            ],
        reverse=True,
    )

    return [
        {
            "feature":
                feature,

            "importance":
                score,
        }

        for feature, score
        in pairs
    ]


def main():

    print(
        "=" * 88
    )

    print(
        "PRATIRUP ML-C MODEL TRAINING"
    )

    print(
        "=" * 88
    )

    ARTIFACT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "\n[C1] FEATURE SAFETY"
    )

    leaking = (
        set(
            FEATURES
        )
        &
        FORBIDDEN_FEATURES
    )

    print(
        "Features:",
        len(
            FEATURES
        ),
    )

    print(
        "Forbidden feature leakage:",
        sorted(
            leaking
        ),
    )

    if leaking:

        raise RuntimeError(
            "Ground-truth leakage detected."
        )

    print(
        "\n[C2] DATA LOADING"
    )

    (
        X_train,
        anomaly_train,
        fault_train,
        mission_train,
        _,
    ) = load_dataset(
        TRAIN_PATH
    )

    (
        X_validation,
        anomaly_validation,
        fault_validation,
        mission_validation,
        _,
    ) = load_dataset(
        VALIDATION_PATH
    )

    print(
        "Train rows      :",
        len(
            X_train
        ),
    )

    print(
        "Validation rows :",
        len(
            X_validation
        ),
    )

    print(
        "Train missions  :",
        len(
            set(
                mission_train.tolist()
            )
        ),
    )

    print(
        "Validation missions:",
        len(
            set(
                mission_validation.tolist()
            )
        ),
    )

    print(
        "Test dataset used:",
        False,
    )

    test_hash = (
        file_sha256(
            TEST_PATH
        )
        if TEST_PATH.exists()
        else None
    )

    print(
        "\n[C3] BINARY ANOMALY MODEL COMPARISON"
    )

    anomaly_candidates = {
        "logistic_regression":
            make_logistic(),

        "random_forest":
            make_random_forest(),
    }

    anomaly_results = {}

    anomaly_models = {}

    for name, model in (
        anomaly_candidates.items()
    ):

        print(
            "\nTraining anomaly:",
            name,
        )

        model.fit(
            X_train,
            anomaly_train,
        )

        metrics = (
            binary_metrics(
                model,
                X_validation,
                anomaly_validation,
            )
        )

        mission_metrics = (
            binary_mission_scores(
                model,
                X_validation,
                anomaly_validation,
                mission_validation,
            )
        )

        anomaly_results[
            name
        ] = {
            "validation":
                metrics,

            "mission_validation":
                mission_metrics,
        }

        anomaly_models[
            name
        ] = model

        print(
            "Validation F1:",
            round(
                metrics[
                    "f1"
                ],
                6,
            ),
        )

        print(
            "Balanced accuracy:",
            round(
                metrics[
                    "balanced_accuracy"
                ],
                6,
            ),
        )

        print(
            "False positive rate:",
            round(
                metrics[
                    "false_positive_rate"
                ],
                6,
            ),
        )

        print(
            "False negative rate:",
            round(
                metrics[
                    "false_negative_rate"
                ],
                6,
            ),
        )

    best_anomaly_name = max(
        anomaly_results,
        key=lambda name: (
            anomaly_results[
                name
            ][
                "validation"
            ][
                "f1"
            ],
            anomaly_results[
                name
            ][
                "validation"
            ][
                "balanced_accuracy"
            ],
        ),
    )

    best_anomaly_model = (
        anomaly_models[
            best_anomaly_name
        ]
    )

    print(
        "\n[C4] MULTICLASS FAULT MODEL COMPARISON"
    )

    fault_candidates = {
        "logistic_regression":
            make_logistic(),

        "random_forest":
            make_random_forest(),
    }

    fault_results = {}

    fault_models = {}

    for name, model in (
        fault_candidates.items()
    ):

        print(
            "\nTraining fault classifier:",
            name,
        )

        model.fit(
            X_train,
            fault_train,
        )

        metrics = (
            multiclass_metrics(
                model,
                X_validation,
                fault_validation,
            )
        )

        mission_metrics = (
            multiclass_mission_scores(
                model,
                X_validation,
                fault_validation,
                mission_validation,
            )
        )

        fault_results[
            name
        ] = {
            "validation":
                metrics,

            "mission_validation":
                mission_metrics,
        }

        fault_models[
            name
        ] = model

        print(
            "Validation macro F1:",
            round(
                metrics[
                    "macro_f1"
                ],
                6,
            ),
        )

        print(
            "Balanced accuracy:",
            round(
                metrics[
                    "balanced_accuracy"
                ],
                6,
            ),
        )

        print(
            "Weighted F1:",
            round(
                metrics[
                    "weighted_f1"
                ],
                6,
            ),
        )

    best_fault_name = max(
        fault_results,
        key=lambda name: (
            fault_results[
                name
            ][
                "validation"
            ][
                "macro_f1"
            ],
            fault_results[
                name
            ][
                "validation"
            ][
                "balanced_accuracy"
            ],
        ),
    )

    best_fault_model = (
        fault_models[
            best_fault_name
        ]
    )

    print(
        "\n[C5] MODEL FREEZE CANDIDATES"
    )

    joblib.dump(
        best_anomaly_model,
        ANOMALY_MODEL_PATH,
    )

    joblib.dump(
        best_fault_model,
        FAULT_MODEL_PATH,
    )

    print(
        "Selected anomaly model:",
        best_anomaly_name,
    )

    print(
        "Selected fault model:",
        best_fault_name,
    )

    print(
        "Anomaly artifact:",
        ANOMALY_MODEL_PATH,
    )

    print(
        "Fault artifact:",
        FAULT_MODEL_PATH,
    )

    anomaly_importance = (
        extract_feature_importance(
            best_anomaly_model
        )
    )

    fault_importance = (
        extract_feature_importance(
            best_fault_model
        )
    )

    print(
        "\n[C6] TOP ANOMALY FEATURES"
    )

    for item in (
        anomaly_importance[
            :10
        ]
    ):

        print(
            f"{item['feature']:<38}",
            round(
                item[
                    "importance"
                ],
                6,
            ),
        )

    print(
        "\n[C7] TOP FAULT FEATURES"
    )

    for item in (
        fault_importance[
            :10
        ]
    ):

        print(
            f"{item['feature']:<38}",
            round(
                item[
                    "importance"
                ],
                6,
            ),
        )

    report = {
        "project":
            "PRATIRUP",

        "stage":
            "ML-C",

        "version":
            VERSION,

        "problem_statement_id":
            26054,

        "data_origin":
            "PRATIRUP synthetic simulator",

        "synthetic_training":
            True,

        "real_drdo_vrde_training_data":
            False,

        "classified_data":
            False,

        "feature_count":
            len(
                FEATURES
            ),

        "training_rows":
            len(
                X_train
            ),

        "validation_rows":
            len(
                X_validation
            ),

        "training_missions":
            len(
                set(
                    mission_train.tolist()
                )
            ),

        "validation_missions":
            len(
                set(
                    mission_validation.tolist()
                )
            ),

        "test_dataset_parsed":
            False,

        "test_dataset_used_for_training":
            False,

        "test_dataset_used_for_model_selection":
            False,

        "test_file_sha256":
            test_hash,

        "selection_policy": {
            "anomaly":
                (
                    "Highest validation F1; "
                    "balanced accuracy used "
                    "as tie-breaker."
                ),

            "fault":
                (
                    "Highest validation macro F1; "
                    "balanced accuracy used "
                    "as tie-breaker."
                ),
        },

        "anomaly_candidates":
            anomaly_results,

        "fault_candidates":
            fault_results,

        "selected_anomaly_model":
            best_anomaly_name,

        "selected_fault_model":
            best_fault_name,

        "anomaly_feature_importance":
            anomaly_importance,

        "fault_feature_importance":
            fault_importance,

        "feature_names":
            FEATURES,

        "safety": {
            "flight_authorization":
                False,

            "certified_prediction":
                False,

            "operational_drdo_model":
                False,

            "database_writes":
                False,

            "digital_twin_core_modified":
                False,
        },
    }

    with TRAINING_REPORT_PATH.open(
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

    manifest = {
        "version":
            VERSION,

        "features":
            FEATURES,

        "feature_count":
            len(
                FEATURES
            ),

        "anomaly_model": {
            "algorithm":
                best_anomaly_name,

            "artifact":
                str(
                    ANOMALY_MODEL_PATH
                ),

            "target":
                "anomaly_target",

            "classes": [
                0,
                1,
            ],
        },

        "fault_model": {
            "algorithm":
                best_fault_name,

            "artifact":
                str(
                    FAULT_MODEL_PATH
                ),

            "target":
                "sample_label",

            "classes":
                FAULT_CLASSES,
        },

        "training_data":
            "synthetic",

        "real_operational_validation":
            False,

        "certified":
            False,

        "flight_authorization":
            False,

        "test_holdout_reserved":
            True,
    }

    with MODEL_MANIFEST_PATH.open(
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
        "=" * 88
    )

    print(
        "ML-C TRAINING COMPLETE"
    )

    print(
        "=" * 88
    )

    print(
        "Anomaly model:",
        best_anomaly_name,
    )

    print(
        "Validation anomaly F1:",
        round(
            anomaly_results[
                best_anomaly_name
            ][
                "validation"
            ][
                "f1"
            ],
            6,
        ),
    )

    print(
        "Fault model:",
        best_fault_name,
    )

    print(
        "Validation fault macro F1:",
        round(
            fault_results[
                best_fault_name
            ][
                "validation"
            ][
                "macro_f1"
            ],
            6,
        ),
    )

    print()
    print(
        "TRAIN MISSIONS      : 30"
    )

    print(
        "VALIDATION MISSIONS : 10"
    )

    print(
        "TEST MISSIONS USED  : 0"
    )

    print(
        "MODEL INPUT FEATURES:",
        len(
            FEATURES
        ),
    )

    print()
    print(
        "DATABASE WRITES          : 0"
    )

    print(
        "DIGITAL TWIN MODIFICATIONS: 0"
    )

    print(
        "REAL / CLASSIFIED DATA   : 0"
    )

    print(
        "FLIGHT AUTHORIZATION     : FALSE"
    )

    print()
    print(
        "ML-C STATUS: TRAINED / READY FOR ACCEPTANCE"
    )

    print(
        "NEXT: ML-D UNSEEN TEST-MISSION EVALUATION"
    )

    print(
        "=" * 88
    )


if __name__ == "__main__":
    main()
