from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.api.telemetry import (
    process_digital_twin_pipeline,
)

from ml.inference.telemetry_ml_pipeline_v1 import (
    PRATIRUPTelemetryMLPipeline,
)

from ml.inference.evidence_fusion_v1 import (
    PRATIRUPEvidenceFusion,
)


VERSION = "1.0.0"

SERVICE_NAME = "pratirup_hybrid_runtime"

MODE = "DIGITAL_TWIN_PLUS_ML_ADVISORY_FUSION"


class HybridRuntimeError(RuntimeError):
    pass


def frame_to_mapping(
    frame: Any,
) -> dict[str, Any]:

    if isinstance(
        frame,
        Mapping,
    ):
        return dict(frame)

    if hasattr(
        frame,
        "model_dump",
    ):
        return frame.model_dump(
            mode="python"
        )

    if hasattr(
        frame,
        "dict",
    ):
        return frame.dict()

    raise HybridRuntimeError(
        "Unsupported canonical telemetry frame representation."
    )


class PRATIRUPHybridRuntime:

    def __init__(
        self,
        *,
        ml_pipeline: PRATIRUPTelemetryMLPipeline | None = None,
        fusion: PRATIRUPEvidenceFusion | None = None,
    ) -> None:

        self.ml_pipeline = (
            ml_pipeline
            if ml_pipeline is not None
            else PRATIRUPTelemetryMLPipeline()
        )

        self.fusion = (
            fusion
            if fusion is not None
            else PRATIRUPEvidenceFusion()
        )

        self._validate_components()


    def _validate_components(
        self,
    ) -> None:

        ml_status = (
            self.ml_pipeline.get_status()
        )

        fusion_status = (
            self.fusion.get_status()
        )

        if (
            ml_status.get(
                "status"
            )
            != "READY"
        ):
            raise HybridRuntimeError(
                "ML-E-C telemetry ML pipeline is not READY."
            )

        if (
            ml_status.get(
                "feature_count"
            )
            != 60
        ):
            raise HybridRuntimeError(
                "ML-E-C feature contract mismatch. "
                "Expected exactly 60 features."
            )

        if (
            fusion_status.get(
                "status"
            )
            != "READY"
        ):
            raise HybridRuntimeError(
                "ML-E-D1 evidence fusion service is not READY."
            )

        if (
            fusion_status.get(
                "mode"
            )
            != "ADVISORY_EVIDENCE_COMPARISON"
        ):
            raise HybridRuntimeError(
                "Unexpected ML-E-D1 fusion mode."
            )


    def reset(
        self,
        mission_id: str | None = None,
    ) -> None:

        reset_method = getattr(
            self.ml_pipeline,
            "reset",
            None,
        )

        if reset_method is None:
            raise HybridRuntimeError(
                "ML-E-C reset interface is unavailable."
            )

        if mission_id is None:
            reset_method()

        else:
            try:
                reset_method(
                    mission_id
                )

            except TypeError:
                reset_method()


    def get_status(
        self,
    ) -> dict[str, Any]:

        ml_status = (
            self.ml_pipeline.get_status()
        )

        fusion_status = (
            self.fusion.get_status()
        )

        ready = (
            ml_status.get(
                "status"
            )
            == "READY"
            and
            ml_status.get(
                "feature_count"
            )
            == 60
            and
            fusion_status.get(
                "status"
            )
            == "READY"
        )

        return {
            "success": True,

            "status":
                "READY"
                if ready
                else "DEGRADED",

            "service":
                SERVICE_NAME,

            "version":
                VERSION,

            "mode":
                MODE,

            "components": {
                "digital_twin": {
                    "authority":
                        "EXISTING_CORE",

                    "modified":
                        False,

                    "persistence":
                        "UNCHANGED",
                },

                "ml_pipeline": {
                    "status":
                        ml_status.get(
                            "status"
                        ),

                    "feature_count":
                        ml_status.get(
                            "feature_count"
                        ),

                    "version":
                        ml_status.get(
                            "version"
                        ),
                },

                "evidence_fusion": {
                    "status":
                        fusion_status.get(
                            "status"
                        ),

                    "mode":
                        fusion_status.get(
                            "mode"
                        ),

                    "version":
                        fusion_status.get(
                            "version"
                        ),
                },
            },

            "authority": {
                "physics":
                    "EXISTING_CORE",

                "anomaly_detection":
                    "EXISTING_CORE",

                "fault_detection":
                    "EXISTING_CORE",

                "readiness":
                    "EXISTING_CORE",

                "ml":
                    "ADVISORY_ONLY",

                "hybrid_evidence":
                    "ADVISORY_ONLY",
            },

            "safety": {
                "model_fitting":
                    False,

                "threshold_tuning":
                    False,

                "physics_modified":
                    False,

                "existing_diagnostics_modified":
                    False,

                "readiness_modified":
                    False,

                "ml_overrides_physics":
                    False,

                "ml_overrides_existing_diagnostics":
                    False,

                "ml_overrides_readiness":
                    False,

                "wrapper_database_writes":
                    False,

                "digital_twin_persistence":
                    "UNCHANGED",

                "flight_authorization":
                    False,

                "decision_support_only":
                    True,
            },
        }


    async def process(
        self,
        frame: Any,
    ) -> dict[str, Any]:

        try:
            canonical = frame_to_mapping(
                frame
            )

        except Exception as exc:
            raise HybridRuntimeError(
                "HYBRID_CANONICAL_CONVERSION_FAILED: "
                f"{exc}"
            ) from exc


        try:
            digital_twin_result = (
                await process_digital_twin_pipeline(
                    frame
                )
            )

        except Exception as exc:
            raise HybridRuntimeError(
                "HYBRID_DIGITAL_TWIN_FAILED: "
                f"{exc}"
            ) from exc


        if not isinstance(
            digital_twin_result,
            Mapping,
        ):
            raise HybridRuntimeError(
                "Digital Twin result is not a mapping."
            )


        try:
            ml_result = (
                self.ml_pipeline.process(
                    canonical
                )
            )

        except Exception as exc:
            raise HybridRuntimeError(
                "HYBRID_ML_INFERENCE_FAILED: "
                f"{exc}"
            ) from exc


        if not isinstance(
            ml_result,
            Mapping,
        ):
            raise HybridRuntimeError(
                "ML-E-C result is not a mapping."
            )


        ml_evidence = (
            ml_result.get(
                "ml"
            )
        )


        if not isinstance(
            ml_evidence,
            Mapping,
        ):
            raise HybridRuntimeError(
                "ML-E-C did not return valid ML evidence."
            )


        anomaly_detection = (
            digital_twin_result.get(
                "anomaly_detection"
            )
        )

        fault_detection = (
            digital_twin_result.get(
                "fault_detection"
            )
        )

        readiness = (
            digital_twin_result.get(
                "readiness"
            )
        )


        try:
            hybrid_evidence = (
                self.fusion.fuse(
                    anomaly_detection=
                        anomaly_detection,

                    fault_detection=
                        fault_detection,

                    ml_result=
                        ml_evidence,
                )
            )

        except Exception as exc:
            raise HybridRuntimeError(
                "HYBRID_EVIDENCE_FUSION_FAILED: "
                f"{exc}"
            ) from exc


        if not isinstance(
            hybrid_evidence,
            Mapping,
        ):
            raise HybridRuntimeError(
                "ML-E-D1 fusion result is not a mapping."
            )


        dt_success = (
            digital_twin_result.get(
                "success"
            )
            is True
        )

        ml_success = (
            ml_result.get(
                "success"
            )
            is True
        )

        fusion_success = (
            hybrid_evidence.get(
                "success"
            )
            is True
        )

        overall_success = (
            dt_success
            and
            ml_success
            and
            fusion_success
        )


        return {
            "success":
                overall_success,

            "status":
                "READY"
                if overall_success
                else "DEGRADED",

            "service":
                SERVICE_NAME,

            "version":
                VERSION,

            "mode":
                MODE,

            "source": {
                "telemetry":
                    ml_result.get(
                        "source"
                    ),

                "mission_id":
                    ml_result.get(
                        "mission_id"
                    ),

                "mission_phase":
                    ml_result.get(
                        "mission_phase"
                    ),
            },

            "digital_twin":
                digital_twin_result,

            "ml":
                ml_result,

            "hybrid_evidence":
                hybrid_evidence,

            "readiness":
                readiness,

            "authority": {
                "digital_twin":
                    "EXISTING_CORE",

                "physics":
                    "EXISTING_CORE",

                "anomaly_detection":
                    "EXISTING_CORE",

                "fault_detection":
                    "EXISTING_CORE",

                "readiness":
                    "EXISTING_CORE",

                "ml":
                    "ADVISORY_ONLY",

                "hybrid_evidence":
                    "ADVISORY_ONLY",
            },

            "processing": {
                "digital_twin_success":
                    dt_success,

                "ml_success":
                    ml_success,

                "fusion_success":
                    fusion_success,

                "feature_count":
                    ml_result.get(
                        "feature_count"
                    ),
            },

            "safety": {
                "model_fitting":
                    False,

                "threshold_tuning":
                    False,

                "physics_modified":
                    False,

                "existing_diagnostics_modified":
                    False,

                "readiness_modified":
                    False,

                "ml_overrides_physics":
                    False,

                "ml_overrides_existing_diagnostics":
                    False,

                "ml_overrides_readiness":
                    False,

                "wrapper_database_writes":
                    False,

                "digital_twin_persistence":
                    "UNCHANGED",

                "flight_authorization":
                    False,

                "decision_support_only":
                    True,
            },
        }


_RUNTIME: PRATIRUPHybridRuntime | None = None


def get_hybrid_runtime() -> PRATIRUPHybridRuntime:

    global _RUNTIME

    if _RUNTIME is None:
        _RUNTIME = (
            PRATIRUPHybridRuntime()
        )

    return _RUNTIME


async def process_hybrid_frame(
    frame: Any,
) -> dict[str, Any]:

    runtime = (
        get_hybrid_runtime()
    )

    return await runtime.process(
        frame
    )
