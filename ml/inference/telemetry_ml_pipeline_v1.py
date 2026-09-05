from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ml.inference.live_feature_builder_v1 import (
    FEATURES,
    RAW_FEATURES,
    PRATIRUPLiveFeatureBuilder,
)

from ml.inference.runtime_inference_v1 import (
    PRATIRUPRuntimeInference,
)


VERSION = "1.0.1"


class TelemetryMLPipelineError(RuntimeError):
    pass


def as_mapping(
    payload: Any,
) -> Mapping[str, Any]:

    if isinstance(
        payload,
        Mapping,
    ):
        return payload

    if hasattr(
        payload,
        "model_dump",
    ):
        result = payload.model_dump()

        if isinstance(
            result,
            Mapping,
        ):
            return result

    if hasattr(
        payload,
        "dict",
    ):
        result = payload.dict()

        if isinstance(
            result,
            Mapping,
        ):
            return result

    raise TelemetryMLPipelineError(
        "Canonical telemetry must be a mapping "
        "or a supported schema object."
    )


def nested_value(
    payload: Mapping[str, Any],
    section: str,
    field: str,
) -> Any:

    section_value = payload.get(
        section
    )

    if not isinstance(
        section_value,
        Mapping,
    ):
        raise TelemetryMLPipelineError(
            f"Missing canonical telemetry section: {section}"
        )

    if field not in section_value:
        raise TelemetryMLPipelineError(
            f"Missing canonical telemetry field: "
            f"{section}.{field}"
        )

    value = section_value[
        field
    ]

    if value is None:
        raise TelemetryMLPipelineError(
            f"Canonical telemetry field unavailable: "
            f"{section}.{field}"
        )

    return value


def canonical_feature_value(
    payload: Mapping[str, Any],
    feature: str,
) -> Any:

    if feature == "fuel.flow_kg_s":

        fuel = payload.get(
            "fuel"
        )

        if not isinstance(
            fuel,
            Mapping,
        ):
            raise TelemetryMLPipelineError(
                "Missing canonical telemetry section: fuel"
            )

        found_field = False

        for field in (
            "flow_kg_s",
            "flow_kg_per_second",
        ):

            if field in fuel:

                found_field = True

                value = fuel[
                    field
                ]

                if value is not None:
                    return value

        if found_field:
            raise TelemetryMLPipelineError(
                "Canonical telemetry fuel flow is unavailable."
            )

        raise TelemetryMLPipelineError(
            "Missing canonical telemetry fuel-flow field. "
            "Accepted fields: fuel.flow_kg_s or "
            "fuel.flow_kg_per_second"
        )

    parts = feature.split(
        ".",
        1,
    )

    if len(
        parts
    ) != 2:
        raise TelemetryMLPipelineError(
            f"Unsupported raw feature path: {feature}"
        )

    section, field = parts

    return nested_value(
        payload,
        section,
        field,
    )


def mission_identifier(
    payload: Mapping[str, Any],
) -> str:

    mission = payload.get(
        "mission"
    )

    if not isinstance(
        mission,
        Mapping,
    ):
        raise TelemetryMLPipelineError(
            "Canonical mission section is required."
        )

    for key in (
        "missionId",
        "mission_id",
        "id",
    ):

        value = mission.get(
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

    raise TelemetryMLPipelineError(
        "Canonical mission identifier is unavailable."
    )


def mission_phase(
    payload: Mapping[str, Any],
) -> str:

    mission = payload.get(
        "mission"
    )

    if not isinstance(
        mission,
        Mapping,
    ):
        raise TelemetryMLPipelineError(
            "Canonical mission section is required."
        )

    phase = mission.get(
        "phase"
    )

    if (
        phase is None
        or not str(
            phase
        ).strip()
    ):
        raise TelemetryMLPipelineError(
            "Canonical mission.phase is unavailable."
        )

    return str(
        phase
    )


def telemetry_source(
    payload: Mapping[str, Any],
) -> str:

    meta = payload.get(
        "meta"
    )

    if not isinstance(
        meta,
        Mapping,
    ):
        return "unknown"

    source = meta.get(
        "source"
    )

    if source is None:
        return "unknown"

    return str(
        source
    )


def canonical_to_feature_input(
    telemetry: Any,
) -> dict[str, Any]:

    payload = as_mapping(
        telemetry
    )

    flattened: dict[
        str,
        Any
    ] = {}

    for feature in RAW_FEATURES:

        flattened[
            feature
        ] = canonical_feature_value(
            payload,
            feature,
        )

    flattened[
        "mission.missionId"
    ] = mission_identifier(
        payload
    )

    flattened[
        "mission.phase"
    ] = mission_phase(
        payload
    )

    return flattened


class PRATIRUPTelemetryMLPipeline:

    def __init__(
        self,
        *,
        feature_builder: (
            PRATIRUPLiveFeatureBuilder
            | None
        ) = None,
        runtime: (
            PRATIRUPRuntimeInference
            | None
        ) = None,
    ) -> None:

        self.feature_builder = (
            feature_builder
            if feature_builder
            is not None
            else PRATIRUPLiveFeatureBuilder()
        )

        self.runtime = (
            runtime
            if runtime
            is not None
            else PRATIRUPRuntimeInference()
        )

        if (
            self.runtime.features
            != FEATURES
        ):
            raise TelemetryMLPipelineError(
                "ML-E-A and ML-E-B feature "
                "contracts do not match."
            )

        self.samples_processed = 0


    def reset(
        self,
        *,
        mission_id: str | None = None,
    ) -> None:

        self.feature_builder.reset(
            mission_id=
                mission_id
        )

        self.samples_processed = 0


    def get_status(
        self,
    ) -> dict[str, Any]:

        builder_status = (
            self.feature_builder
            .get_status()
        )

        runtime_status = (
            self.runtime
            .get_status()
        )

        ready = (
            builder_status[
                "status"
            ] == "READY"
            and runtime_status[
                "status"
            ] == "READY"
        )

        return {
            "service":
                "pratirup_telemetry_ml_pipeline",

            "version":
                VERSION,

            "status":
                (
                    "READY"
                    if ready
                    else "NOT_READY"
                ),

            "input":
                "canonical_telemetry",

            "feature_count":
                len(
                    FEATURES
                ),

            "causal":
                True,

            "future_information":
                False,

            "model_fitting":
                False,

            "threshold_tuning":
                False,

            "database_writes":
                False,

            "digital_twin_modification":
                False,

            "flight_authorization":
                False,

            "decision_support_only":
                True,

            "fuel_flow_compatibility": {
                "backend_canonical":
                    "fuel.flow_kg_per_second",

                "frozen_ml_feature":
                    "fuel.flow_kg_s",

                "raw_simulator_supported":
                    True,

                "backend_schema_supported":
                    True,

                "model_contract_changed":
                    False,
            },

            "feature_builder":
                builder_status,

            "runtime":
                runtime_status,
        }


    def prepare_features(
        self,
        telemetry: Any,
    ) -> dict[str, float]:

        flattened = (
            canonical_to_feature_input(
                telemetry
            )
        )

        features = (
            self.feature_builder
            .build(
                flattened
            )
        )

        if len(
            features
        ) != 60:
            raise TelemetryMLPipelineError(
                "Runtime feature count must be 60."
            )

        if set(
            features.keys()
        ) != set(
            FEATURES
        ):
            raise TelemetryMLPipelineError(
                "Generated ML feature names do not match "
                "the frozen ML-B contract."
            )

        return features


    def process(
        self,
        telemetry: Any,
        *,
        include_features: bool = False,
    ) -> dict[str, Any]:

        payload = as_mapping(
            telemetry
        )

        features = (
            self.prepare_features(
                payload
            )
        )

        inference = (
            self.runtime.predict(
                features
            )
        )

        self.samples_processed += 1

        result = {
            "success":
                True,

            "status":
                "READY",

            "pipeline_version":
                VERSION,

            "source":
                telemetry_source(
                    payload
                ),

            "mission_id":
                mission_identifier(
                    payload
                ),

            "mission_phase":
                mission_phase(
                    payload
                ),

            "feature_count":
                len(
                    features
                ),

            "ml":
                inference,

            "compatibility": {
                "fuel_flow": {
                    "backend_canonical":
                        "fuel.flow_kg_per_second",

                    "ml_feature":
                        "fuel.flow_kg_s",

                    "normalized":
                        True,
                },

                "feature_contract_changed":
                    False,

                "model_retraining_required":
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

                "replaces_existing_diagnostics":
                    False,

                "replaces_readiness":
                    False,

                "replaces_fadec":
                    False,
            },
        }

        if include_features:

            result[
                "features"
            ] = features

        return result
