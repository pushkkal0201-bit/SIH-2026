from __future__ import annotations

import hashlib
import json
import math

from pathlib import Path
from typing import Any, Mapping

import joblib
import numpy as np


VERSION = "1.0.0"


MODEL_MANIFEST_PATH = Path(
    "ml/artifacts/pratirup_ml_model_manifest_v1.json"
)

ANOMALY_MODEL_PATH = Path(
    "ml/artifacts/pratirup_anomaly_model_v1.joblib"
)

FAULT_MODEL_PATH = Path(
    "ml/artifacts/pratirup_fault_model_v1.joblib"
)


class RuntimeInferenceError(RuntimeError):
    pass


def file_sha256(path: Path) -> str:

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


def finite_float(
    value: Any,
    *,
    feature: str,
) -> float:

    try:

        converted = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ) as exc:

        raise RuntimeInferenceError(
            f"Feature {feature!r} is not numeric."
        ) from exc

    if not math.isfinite(
        converted
    ):

        raise RuntimeInferenceError(
            f"Feature {feature!r} is not finite."
        )

    return converted


class PRATIRUPRuntimeInference:

    def __init__(
        self,
        *,
        manifest_path: Path = MODEL_MANIFEST_PATH,
        anomaly_model_path: Path = ANOMALY_MODEL_PATH,
        fault_model_path: Path = FAULT_MODEL_PATH,
    ) -> None:

        self.manifest_path = Path(
            manifest_path
        )

        self.anomaly_model_path = Path(
            anomaly_model_path
        )

        self.fault_model_path = Path(
            fault_model_path
        )

        self._validate_files()

        with self.manifest_path.open(
            "r",
            encoding="utf-8",
        ) as handle:

            self.manifest = json.load(
                handle
            )

        self.features = list(
            self.manifest[
                "features"
            ]
        )

        if len(
            self.features
        ) != 60:

            raise RuntimeInferenceError(
                "Frozen runtime feature contract "
                "must contain exactly 60 features."
            )

        if len(
            set(
                self.features
            )
        ) != 60:

            raise RuntimeInferenceError(
                "Frozen feature contract contains "
                "duplicate feature names."
            )

        self.anomaly_model = joblib.load(
            self.anomaly_model_path
        )

        self.fault_model = joblib.load(
            self.fault_model_path
        )

        self.anomaly_model_sha256 = file_sha256(
            self.anomaly_model_path
        )

        self.fault_model_sha256 = file_sha256(
            self.fault_model_path
        )

        self.ready = True


    def _validate_files(
        self,
    ) -> None:

        for path in (
            self.manifest_path,
            self.anomaly_model_path,
            self.fault_model_path,
        ):

            if (
                not path.exists()
                or not path.is_file()
                or path.stat().st_size <= 0
            ):

                raise RuntimeInferenceError(
                    f"Required ML artifact missing: {path}"
                )


    def get_status(
        self,
    ) -> dict[str, Any]:

        return {
            "service":
                "pratirup_runtime_ml",

            "version":
                VERSION,

            "status":
                "READY"
                if self.ready
                else "NOT_READY",

            "feature_count":
                len(
                    self.features
                ),

            "anomaly_algorithm":
                self.manifest[
                    "anomaly_model"
                ][
                    "algorithm"
                ],

            "fault_algorithm":
                self.manifest[
                    "fault_model"
                ][
                    "algorithm"
                ],

            "training_data":
                self.manifest.get(
                    "training_data"
                ),

            "real_operational_validation":
                self.manifest.get(
                    "real_operational_validation",
                    False,
                ),

            "certified":
                False,

            "flight_authorization":
                False,

            "database_writes":
                False,

            "digital_twin_modification":
                False,
        }


    def build_vector(
        self,
        row: Mapping[str, Any],
    ) -> np.ndarray:

        missing = [
            feature
            for feature
            in self.features
            if feature
            not in row
        ]

        if missing:

            raise RuntimeInferenceError(
                "Missing runtime feature(s): "
                + ", ".join(
                    missing
                )
            )

        vector = np.empty(
            (
                1,
                len(
                    self.features
                ),
            ),
            dtype=np.float64,
        )

        for index, feature in enumerate(
            self.features
        ):

            vector[
                0,
                index,
            ] = finite_float(
                row[
                    feature
                ],
                feature=
                    feature,
            )

        return vector


    def _anomaly_probability(
        self,
        vector: np.ndarray,
    ) -> float | None:

        if not hasattr(
            self.anomaly_model,
            "predict_proba",
        ):

            return None

        probabilities = (
            self.anomaly_model
            .predict_proba(
                vector
            )
        )

        classes = list(
            self.anomaly_model.classes_
        )

        if 1 not in classes:

            return None

        positive_index = (
            classes.index(
                1
            )
        )

        return float(
            probabilities[
                0,
                positive_index,
            ]
        )


    def _fault_confidence(
        self,
        vector: np.ndarray,
        predicted_fault: str,
    ) -> float | None:

        if not hasattr(
            self.fault_model,
            "predict_proba",
        ):

            return None

        probabilities = (
            self.fault_model
            .predict_proba(
                vector
            )
        )

        classes = list(
            self.fault_model.classes_
        )

        if predicted_fault not in classes:

            return None

        class_index = (
            classes.index(
                predicted_fault
            )
        )

        return float(
            probabilities[
                0,
                class_index,
            ]
        )


    def predict(
        self,
        row: Mapping[str, Any],
    ) -> dict[str, Any]:

        vector = self.build_vector(
            row
        )

        anomaly_prediction = int(
            self.anomaly_model.predict(
                vector
            )[
                0
            ]
        )

        fault_prediction = str(
            self.fault_model.predict(
                vector
            )[
                0
            ]
        )

        anomaly_probability = (
            self._anomaly_probability(
                vector
            )
        )

        fault_confidence = (
            self._fault_confidence(
                vector,
                fault_prediction,
            )
        )

        return {
            "success":
                True,

            "status":
                "READY",

            "inference_version":
                VERSION,

            "feature_contract_version":
                self.manifest.get(
                    "version"
                ),

            "feature_count":
                len(
                    self.features
                ),

            "anomaly": {
                "prediction":
                    anomaly_prediction,

                "state":
                    (
                        "ABNORMAL"
                        if anomaly_prediction
                        == 1
                        else "NORMAL"
                    ),

                "probability":
                    anomaly_probability,
            },

            "fault": {
                "prediction":
                    fault_prediction,

                "confidence":
                    fault_confidence,
            },

            "model": {
                "anomaly_algorithm":
                    self.manifest[
                        "anomaly_model"
                    ][
                        "algorithm"
                    ],

                "fault_algorithm":
                    self.manifest[
                        "fault_model"
                    ][
                        "algorithm"
                    ],

                "anomaly_sha256":
                    self.anomaly_model_sha256,

                "fault_sha256":
                    self.fault_model_sha256,
            },

            "provenance": {
                "training_data":
                    "synthetic",

                "real_operational_validation":
                    False,

                "official_drdo_vrde_model":
                    False,

                "certified":
                    False,
            },

            "safety": {
                "flight_authorization":
                    False,

                "database_writes":
                    False,

                "digital_twin_modification":
                    False,

                "decision_support_only":
                    True,
            },
        }


_default_runtime = None


def get_runtime_inference() -> PRATIRUPRuntimeInference:

    global _default_runtime

    if _default_runtime is None:

        _default_runtime = (
            PRATIRUPRuntimeInference()
        )

    return _default_runtime


def predict_feature_row(
    row: Mapping[str, Any],
) -> dict[str, Any]:

    return (
        get_runtime_inference()
        .predict(
            row
        )
    )
