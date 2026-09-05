from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ml.inference.telemetry_ml_pipeline_v1 import (
    PRATIRUPTelemetryMLPipeline,
)

from ml.inference.evidence_fusion_v1 import (
    PRATIRUPEvidenceFusion,
)


VERSION = "1.0.0"
PHASE = "ML-E-E"

SERVICE_NAME = (
    "pratirup_backend_hybrid_integration"
)


_ml_pipeline = (
    PRATIRUPTelemetryMLPipeline()
)

_fusion = (
    PRATIRUPEvidenceFusion()
)


_requests = 0

_successful_integrations = 0

_degraded_integrations = 0

_replay_skips = 0


_latest_result: dict[str, Any] | None = None


def _frame_to_mapping(
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

    raise TypeError(
        "Unsupported telemetry frame representation."
    )


def _telemetry_source(
    canonical: Mapping[str, Any],
) -> str:

    meta = canonical.get(
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
    ).strip().lower()


def _base_safety() -> dict[str, Any]:

    return {
        "digital_twin_rerun":
            False,

        "physics_rerun":
            False,

        "residual_rerun":
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

        "existing_telemetry_persistence":
            "UNCHANGED",

        "replay_model_reprocessing":
            False,

        "flight_authorization":
            False,

        "decision_support_only":
            True,
    }


def get_hybrid_integration_status(
) -> dict[str, Any]:

    ml_status = (
        _ml_pipeline.get_status()
    )

    fusion_status = (
        _fusion.get_status()
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
        "success":
            True,

        "status":
            (
                "READY"
                if ready
                else "DEGRADED"
            ),

        "service":
            SERVICE_NAME,

        "phase":
            PHASE,

        "version":
            VERSION,

        "integration_mode":
            "POST_DIGITAL_TWIN_ADVISORY",

        "ml_pipeline": {
            "status":
                ml_status.get(
                    "status"
                ),

            "version":
                ml_status.get(
                    "version"
                ),

            "feature_count":
                ml_status.get(
                    "feature_count"
                ),
        },

        "fusion": {
            "status":
                fusion_status.get(
                    "status"
                ),

            "version":
                fusion_status.get(
                    "version"
                ),

            "mode":
                fusion_status.get(
                    "mode"
                ),
        },

        "requests":
            _requests,

        "successful_integrations":
            _successful_integrations,

        "degraded_integrations":
            _degraded_integrations,

        "replay_skips":
            _replay_skips,

        "latest_available":
            _latest_result
            is not None,

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

        "safety":
            _base_safety(),
    }


def get_latest_hybrid_integration(
) -> dict[str, Any] | None:

    return _latest_result


def reset_hybrid_integration(
) -> None:

    global _requests
    global _successful_integrations
    global _degraded_integrations
    global _replay_skips
    global _latest_result


    _ml_pipeline.reset()


    _requests = 0

    _successful_integrations = 0

    _degraded_integrations = 0

    _replay_skips = 0

    _latest_result = None


def integrate_hybrid_evidence(
    *,
    telemetry: Any,
    digital_twin_result: Mapping[str, Any],
) -> dict[str, Any]:

    global _requests
    global _successful_integrations
    global _degraded_integrations
    global _replay_skips
    global _latest_result


    _requests += 1


    readiness = (
        digital_twin_result.get(
            "readiness"
        )
        if isinstance(
            digital_twin_result,
            Mapping,
        )
        else None
    )


    try:

        canonical = (
            _frame_to_mapping(
                telemetry
            )
        )

    except Exception as exc:

        _degraded_integrations += 1

        result = {
            "success":
                False,

            "available":
                False,

            "status":
                "DEGRADED",

            "service":
                SERVICE_NAME,

            "phase":
                PHASE,

            "version":
                VERSION,

            "reason":
                "CANONICAL_CONVERSION_FAILED",

            "error":
                str(exc),

            "ml":
                None,

            "hybrid_evidence":
                None,

            "readiness":
                readiness,

            "safety":
                _base_safety(),
        }

        _latest_result = result

        return result


    source = (
        _telemetry_source(
            canonical
        )
    )


    if source == "replay":

        _replay_skips += 1

        result = {
            "success":
                True,

            "available":
                False,

            "status":
                "SKIPPED_REPLAY",

            "service":
                SERVICE_NAME,

            "phase":
                PHASE,

            "version":
                VERSION,

            "source":
                source,

            "reason":
                "HISTORICAL_REPLAY_MODEL_REPROCESSING_DISABLED",

            "ml":
                None,

            "hybrid_evidence":
                None,

            "readiness":
                readiness,

            "authority": {
                "readiness":
                    "EXISTING_CORE",

                "ml":
                    "NOT_REPROCESSED",

                "hybrid_evidence":
                    "NOT_REPROCESSED",
            },

            "safety":
                _base_safety(),
        }

        _latest_result = result

        return result


    if not isinstance(
        digital_twin_result,
        Mapping,
    ):

        _degraded_integrations += 1

        result = {
            "success":
                False,

            "available":
                False,

            "status":
                "DEGRADED",

            "service":
                SERVICE_NAME,

            "phase":
                PHASE,

            "version":
                VERSION,

            "source":
                source,

            "reason":
                "INVALID_DIGITAL_TWIN_RESULT",

            "ml":
                None,

            "hybrid_evidence":
                None,

            "readiness":
                readiness,

            "safety":
                _base_safety(),
        }

        _latest_result = result

        return result


    try:

        ml_result = (
            _ml_pipeline.process(
                canonical
            )
        )

    except Exception as exc:

        _degraded_integrations += 1

        result = {
            "success":
                False,

            "available":
                False,

            "status":
                "DEGRADED",

            "service":
                SERVICE_NAME,

            "phase":
                PHASE,

            "version":
                VERSION,

            "source":
                source,

            "reason":
                "ML_INFERENCE_UNAVAILABLE",

            "error":
                str(exc),

            "ml":
                None,

            "hybrid_evidence":
                None,

            "readiness":
                readiness,

            "authority": {
                "digital_twin":
                    "EXISTING_CORE",

                "readiness":
                    "EXISTING_CORE",

                "ml":
                    "UNAVAILABLE",

                "hybrid_evidence":
                    "UNAVAILABLE",
            },

            "safety":
                _base_safety(),
        }

        _latest_result = result

        return result


    ml_evidence = (
        ml_result.get(
            "ml"
        )
    )


    if not isinstance(
        ml_evidence,
        Mapping,
    ):

        _degraded_integrations += 1

        result = {
            "success":
                False,

            "available":
                False,

            "status":
                "DEGRADED",

            "service":
                SERVICE_NAME,

            "phase":
                PHASE,

            "version":
                VERSION,

            "source":
                source,

            "reason":
                "INVALID_ML_EVIDENCE",

            "ml":
                ml_result,

            "hybrid_evidence":
                None,

            "readiness":
                readiness,

            "safety":
                _base_safety(),
        }

        _latest_result = result

        return result


    try:

        hybrid_evidence = (
            _fusion.fuse(
                anomaly_detection=
                    digital_twin_result.get(
                        "anomaly_detection"
                    ),

                fault_detection=
                    digital_twin_result.get(
                        "fault_detection"
                    ),

                ml_result=
                    ml_evidence,
            )
        )

    except Exception as exc:

        _degraded_integrations += 1

        result = {
            "success":
                False,

            "available":
                False,

            "status":
                "DEGRADED",

            "service":
                SERVICE_NAME,

            "phase":
                PHASE,

            "version":
                VERSION,

            "source":
                source,

            "reason":
                "EVIDENCE_FUSION_UNAVAILABLE",

            "error":
                str(exc),

            "ml":
                ml_result,

            "hybrid_evidence":
                None,

            "readiness":
                readiness,

            "safety":
                _base_safety(),
        }

        _latest_result = result

        return result


    _successful_integrations += 1


    result = {
        "success":
            True,

        "available":
            True,

        "status":
            "READY",

        "service":
            SERVICE_NAME,

        "phase":
            PHASE,

        "version":
            VERSION,

        "source":
            source,

        "feature_count":
            ml_result.get(
                "feature_count"
            ),

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

        "safety":
            _base_safety(),
    }


    _latest_result = result

    return result
