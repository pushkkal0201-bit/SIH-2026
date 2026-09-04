from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Optional

from fastapi import APIRouter, HTTPException

from backend.models.schemas import TelemetryFrame
from backend.ingestion.telemetry_validator import validate_telemetry
from backend.core.state_estimator import (
    estimate_state,
    get_state_estimator_status,
)
from backend.core.digital_twin import (
    set_observed_state,
    get_latest_twin_state_dict,
    get_digital_twin_status,
    reset_digital_twin,
)
from backend.core.model_orchestrator import (
    run_for_observed_state,
    get_latest_orchestration_dict,
    get_model_orchestrator_status,
    reset_model_orchestrator,
)
from backend.core.residual_engine import get_residual_engine_status
from backend.diagnostics.sensor_validation import (
    validate_sensor_state,
    get_latest_sensor_validation,
    get_sensor_validation_status,
    reset_sensor_validation,
)
from backend.diagnostics.anomaly_detection import (
    detect_anomalies,
    get_latest_anomaly_detection,
    get_anomaly_detection_status,
    reset_anomaly_detection,
)
from backend.diagnostics.fault_detection import (
    detect_faults,
    get_latest_fault_detection,
    get_fault_detection_status,
    reset_fault_detection,
)
from backend.prognostics.degradation import (
    track_degradation,
    get_latest_degradation,
    get_degradation_status,
    reset_degradation,
)
from backend.prognostics.rul import (
    estimate_rul,
    get_latest_rul,
    get_rul_status,
    reset_rul,
)
from backend.prognostics.maintenance import (
    recommend_maintenance,
    get_latest_maintenance,
    get_maintenance_status,
    reset_maintenance,
)
from backend.mission.readiness import (
    assess_mission_readiness,
    get_latest_readiness,
    get_readiness_status,
    reset_readiness,
)
from backend.services.websocket_manager import websocket_manager
from backend.mission.readiness_adapter import build_operator_readiness
from backend.database.persistence_context import get_active_mission_id
from backend.database.persistence_service import telemetry_persistence_service
from backend.services.hybrid_integration import (
    integrate_hybrid_evidence,
    get_hybrid_integration_status,
    get_latest_hybrid_integration,
    reset_hybrid_integration,
)

router = APIRouter(
    prefix="/api/telemetry",
    tags=["telemetry"],
)

TELEMETRY_API_VERSION = "3.0.0-D7"

MAX_HISTORY = 1000

_telemetry_history: Deque[
    Dict[str, Any]
] = deque(
    maxlen=MAX_HISTORY
)

_latest_telemetry: Optional[
    Dict[str, Any]
] = None

_received_frames = 0
_accepted_frames = 0
_rejected_frames = 0

_pipeline_successful_runs = 0
_pipeline_failed_runs = 0

_latest_pipeline_result: Optional[
    Dict[str, Any]
] = None


def _utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


def _model_dump(
    model: Any,
) -> Dict[str, Any]:

    if hasattr(
        model,
        "model_dump",
    ):
        return model.model_dump(
            mode="json"
        )

    if hasattr(
        model,
        "dict",
    ):
        return model.dict()

    raise TypeError(
        "Unsupported telemetry model type."
    )


def _parse_timestamp(
    value: Any,
) -> Optional[datetime]:

    if isinstance(
        value,
        datetime,
    ):

        if value.tzinfo is None:
            return value.replace(
                tzinfo=timezone.utc
            )

        return value

    if isinstance(
        value,
        str,
    ):

        try:

            parsed = datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00",
                )
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            return parsed

        except ValueError:
            return None

    return None


def validate_frame(
    telemetry: TelemetryFrame,
) -> Dict[str, Any]:

    telemetry_payload = _model_dump(
        telemetry
    )

    result = validate_telemetry(
        telemetry_payload
    )

    if hasattr(
        result,
        "to_dict",
    ):
        result_dict = result.to_dict()

    elif isinstance(
        result,
        dict,
    ):
        result_dict = result

    else:
        raise TypeError(
            "Telemetry validator returned unsupported result."
        )

    valid = result_dict.get(
        "valid",
        result_dict.get(
            "accepted",
            False,
        ),
    )

    if valid is False:

        errors = result_dict.get(
            "errors"
        )

        if isinstance(
            errors,
            list,
        ):
            error_message = "; ".join(
                str(error)
                for error in errors
            )

        elif errors:
            error_message = str(
                errors
            )

        else:
            error_message = (
                result_dict.get(
                    "error"
                )
                or
                "Telemetry engineering validation failed."
            )

        raise ValueError(
            error_message
        )

    return result_dict


def run_state_estimator(
    telemetry: TelemetryFrame,
) -> Dict[str, Any]:

    estimated = estimate_state(
        telemetry
    )

    if hasattr(
        estimated,
        "to_dict",
    ):
        estimated_dict = (
            estimated.to_dict()
        )

    elif isinstance(
        estimated,
        dict,
    ):
        estimated_dict = estimated

    else:
        raise TypeError(
            "State estimator returned unsupported result."
        )

    if (
        "state" not in estimated_dict
        or
        not isinstance(
            estimated_dict["state"],
            dict,
        )
    ):
        raise ValueError(
            "State estimator result does not contain a valid state."
        )

    return estimated_dict


def run_sensor_validation(
    estimated_state: Dict[str, Any],
) -> Dict[str, Any]:

    observed_state = (
        estimated_state["state"]
    )

    timestamp = _parse_timestamp(
        estimated_state.get(
            "timestamp"
        )
    )

    report = validate_sensor_state(
        observed_state,
        timestamp=timestamp,
    )

    if hasattr(
        report,
        "to_dict",
    ):
        return report.to_dict()

    if isinstance(
        report,
        dict,
    ):
        return report

    raise TypeError(
        "Sensor validation returned unsupported result."
    )


def run_anomaly_detection(
    *,
    estimated_state: Dict[str, Any],
    sensor_validation: Dict[str, Any],
    residual_state: Optional[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    observed_state = (
        estimated_state["state"]
    )

    timestamp = _parse_timestamp(
        estimated_state.get(
            "timestamp"
        )
    )

    report = detect_anomalies(
        observed_state=observed_state,
        residual_state=residual_state,
        sensor_validation=sensor_validation,
        timestamp=timestamp,
    )

    if hasattr(
        report,
        "to_dict",
    ):
        return report.to_dict()

    if isinstance(
        report,
        dict,
    ):
        return report

    raise TypeError(
        "Anomaly detector returned unsupported result."
    )


def run_fault_detection(
    *,
    estimated_state: Dict[str, Any],
    sensor_validation: Dict[str, Any],
    expected_state: Optional[
        Dict[str, Any]
    ],
    residual_state: Optional[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    observed_state = (
        estimated_state["state"]
    )

    timestamp = _parse_timestamp(
        estimated_state.get(
            "timestamp"
        )
    )

    report = detect_faults(
        observed_state=observed_state,
        expected_state=expected_state,
        sensor_validation=sensor_validation,
        residual_state=residual_state,
        timestamp=timestamp,
    )

    if hasattr(
        report,
        "to_dict",
    ):
        return report.to_dict()

    if isinstance(
        report,
        dict,
    ):
        return report

    raise TypeError(
        "Fault detector returned unsupported result."
    )


def run_degradation_tracking(
    *,
    estimated_state: Dict[str, Any],
    sensor_validation: Dict[str, Any],
    residual_state: Optional[
        Dict[str, Any]
    ],
    anomaly_detection: Optional[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    timestamp = _parse_timestamp(
        estimated_state.get(
            "timestamp"
        )
    )

    report = track_degradation(
        residual_state=residual_state,
        anomaly_detection=anomaly_detection,
        sensor_validation=sensor_validation,
        timestamp=timestamp,
    )

    if hasattr(
        report,
        "to_dict",
    ):
        return report.to_dict()

    if isinstance(
        report,
        dict,
    ):
        return report

    raise TypeError(
        "Degradation tracker returned unsupported result."
    )


def run_rul_estimation(
    *,
    estimated_state: Dict[str, Any],
    degradation: Optional[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    timestamp = _parse_timestamp(
        estimated_state.get(
            "timestamp"
        )
    )

    report = estimate_rul(
        degradation_report=degradation,
        timestamp=timestamp,
    )

    if hasattr(
        report,
        "to_dict",
    ):
        return report.to_dict()

    if isinstance(
        report,
        dict,
    ):
        return report

    raise TypeError(
        "RUL estimator returned unsupported result."
    )


def run_maintenance_recommendation(
    *,
    estimated_state: Dict[str, Any],
    fault_detection: Optional[
        Dict[str, Any]
    ],
    degradation: Optional[
        Dict[str, Any]
    ],
    rul: Optional[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    timestamp = _parse_timestamp(
        estimated_state.get(
            "timestamp"
        )
    )

    report = recommend_maintenance(
        fault_detection=fault_detection,
        degradation=degradation,
        rul=rul,
        timestamp=timestamp,
    )

    if hasattr(
        report,
        "to_dict",
    ):
        return report.to_dict()

    if isinstance(
        report,
        dict,
    ):
        return report

    raise TypeError(
        "Maintenance recommendation returned unsupported result."
    )


def _serialize_operator_readiness(
    operator_result: Any,
) -> Dict[str, Any]:

    if hasattr(
        operator_result,
        "model_dump",
    ):
        operator = operator_result.model_dump(
            mode="json"
        )

    elif hasattr(
        operator_result,
        "dict",
    ):
        operator = operator_result.dict()

    elif isinstance(
        operator_result,
        dict,
    ):
        operator = dict(
            operator_result
        )

    else:
        raise TypeError(
            "Operator readiness adapter returned unsupported result."
        )

    if not isinstance(
        operator,
        dict,
    ):
        raise TypeError(
            "Operator readiness result must serialize to a dictionary."
        )

    operator[
        "flight_authorization"
    ] = False

    return operator


def _build_operator_from_report(
    report: Any,
) -> Dict[str, Any]:

    return _serialize_operator_readiness(
        build_operator_readiness(
            report
        )
    )


def run_mission_readiness(
    *,
    estimated_state: Dict[str, Any],
    sensor_validation: Optional[
        Dict[str, Any]
    ],
    fault_detection: Optional[
        Dict[str, Any]
    ],
    degradation: Optional[
        Dict[str, Any]
    ],
    rul: Optional[
        Dict[str, Any]
    ],
    maintenance: Optional[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    timestamp = _parse_timestamp(
        estimated_state.get(
            "timestamp"
        )
    )

    report = assess_mission_readiness(
        sensor_validation=sensor_validation,
        fault_detection=fault_detection,
        degradation=degradation,
        rul=rul,
        maintenance=maintenance,
        timestamp=timestamp,
    )

    if not hasattr(
        report,
        "to_dict",
    ):
        raise TypeError(
            "Mission readiness returned unsupported result. "
            "Expected MissionReadinessReport with to_dict()."
        )

    engineering = report.to_dict()

    if not isinstance(
        engineering,
        dict,
    ):
        raise TypeError(
            "MissionReadinessReport.to_dict() "
            "must return a dictionary."
        )

    engineering[
        "operator"
    ] = _build_operator_from_report(
        report
    )

    return engineering


async def process_digital_twin_pipeline(
    telemetry: TelemetryFrame,
) -> Dict[str, Any]:

    global _pipeline_successful_runs
    global _pipeline_failed_runs
    global _latest_pipeline_result

    started_at = _utc_now()

    try:

        estimated_state = run_state_estimator(
            telemetry
        )

        observed_state = estimated_state[
            "state"
        ]

        sensor_validation = (
            run_sensor_validation(
                estimated_state
            )
        )

        set_observed_state(
            estimated_state
        )

        orchestration = (
            await run_for_observed_state(
                observed_state
            )
        )

        if hasattr(
            orchestration,
            "to_dict",
        ):
            orchestration_dict = (
                orchestration.to_dict()
            )

        elif isinstance(
            orchestration,
            dict,
        ):
            orchestration_dict = (
                orchestration
            )

        else:
            raise TypeError(
                "Model orchestrator returned unsupported result."
            )

        expected_state = (
            orchestration_dict.get(
                "expected_state"
            )
        )

        residual_state = (
            orchestration_dict.get(
                "residual_result"
            )
        )

        if residual_state is None:
            residual_state = (
                orchestration_dict.get(
                    "residual_state"
                )
            )

        anomaly_detection = (
            run_anomaly_detection(
                estimated_state=
                    estimated_state,
                sensor_validation=
                    sensor_validation,
                residual_state=
                    residual_state,
            )
        )

        degradation = (
            run_degradation_tracking(
                estimated_state=
                    estimated_state,
                sensor_validation=
                    sensor_validation,
                residual_state=
                    residual_state,
                anomaly_detection=
                    anomaly_detection,
            )
        )

        rul = run_rul_estimation(
            estimated_state=
                estimated_state,
            degradation=
                degradation,
        )

        fault_detection = (
            run_fault_detection(
                estimated_state=
                    estimated_state,
                sensor_validation=
                    sensor_validation,
                expected_state=
                    expected_state,
                residual_state=
                    residual_state,
            )
        )

        maintenance = (
            run_maintenance_recommendation(
                estimated_state=
                    estimated_state,
                fault_detection=
                    fault_detection,
                degradation=
                    degradation,
                rul=
                    rul,
            )
        )

        readiness = (
            run_mission_readiness(
                estimated_state=
                    estimated_state,
                sensor_validation=
                    sensor_validation,
                fault_detection=
                    fault_detection,
                degradation=
                    degradation,
                rul=
                    rul,
                maintenance=
                    maintenance,
            )
        )

        digital_twin = (
            get_latest_twin_state_dict()
        )

        completed_at = _utc_now()

        result = {
            "success":
                True,

            "status":
                "READY",

            "version":
                TELEMETRY_API_VERSION,

            "estimated_state":
                estimated_state,

            "observed_state":
                observed_state,

            "sensor_validation":
                sensor_validation,

            "expected_state":
                expected_state,

            "expected_state_available":
                expected_state
                is not None,

            "residual_state":
                residual_state,

            "residual_calculated":
                residual_state
                is not None,

            "anomaly_detection":
                anomaly_detection,

            "anomaly_detection_available":
                anomaly_detection
                is not None,

            "degradation":
                degradation,

            "degradation_available":
                degradation
                is not None,

            "rul":
                rul,

            "rul_available":
                rul
                is not None,

            "fault_detection":
                fault_detection,

            "fault_detection_available":
                fault_detection
                is not None,

            "maintenance":
                maintenance,

            "maintenance_available":
                maintenance
                is not None,

            "readiness":
                readiness,

            "readiness_available":
                readiness
                is not None,

            "orchestration":
                orchestration_dict,

            "digital_twin":
                digital_twin,

            "processing": {
                "started_at":
                    started_at.isoformat(),

                "completed_at":
                    completed_at.isoformat(),

                "duration_ms":
                    (
                        completed_at
                        - started_at
                    ).total_seconds()
                    * 1000.0,
            },
        }

        _pipeline_successful_runs += 1

        _latest_pipeline_result = result

        return result

    except Exception as exc:

        _pipeline_failed_runs += 1

        completed_at = _utc_now()

        failure = {
            "success":
                False,

            "status":
                "ERROR",

            "version":
                TELEMETRY_API_VERSION,

            "error":
                str(exc),

            "processing": {
                "started_at":
                    started_at.isoformat(),

                "completed_at":
                    completed_at.isoformat(),

                "duration_ms":
                    (
                        completed_at
                        - started_at
                    ).total_seconds()
                    * 1000.0,
            },
        }

        _latest_pipeline_result = failure

        raise


async def ingest_telemetry(
    telemetry: TelemetryFrame,
) -> Dict[str, Any]:

    return await process_telemetry(
        telemetry
    )


async def process_telemetry(
    telemetry: TelemetryFrame,
) -> Dict[str, Any]:

    global _latest_telemetry
    global _received_frames
    global _accepted_frames
    global _rejected_frames

    _received_frames += 1

    try:

        validation = validate_frame(
            telemetry
        )

        telemetry_dict = _model_dump(
            telemetry
        )

        pipeline = (
            await process_digital_twin_pipeline(
                telemetry
            )
        )

        try:

            hybrid_integration = (
                integrate_hybrid_evidence(
                    telemetry=
                        telemetry,
                    digital_twin_result=
                        pipeline,
                )
            )

        except Exception as exc:

            hybrid_integration = {
                "success":
                    False,

                "available":
                    False,

                "status":
                    "DEGRADED",

                "version":
                    "1.0.0",

                "reason":
                    "HYBRID_INTEGRATION_EXCEPTION",

                "error":
                    str(exc),

                "ml":
                    None,

                "hybrid_evidence":
                    None,

                "readiness":
                    pipeline.get(
                        "readiness"
                    ),

                "safety": {
                    "existing_core_continues":
                        True,

                    "readiness_modified":
                        False,

                    "wrapper_database_writes":
                        False,

                    "flight_authorization":
                        False,

                    "decision_support_only":
                        True,
                },
            }

        accepted_at = (
            _utc_now().isoformat()
        )

        record = {
            "telemetry":
                telemetry_dict,

            "validation":
                validation,

            "pipeline":
                pipeline,

            "ml":
                hybrid_integration.get(
                    "ml"
                ),

            "hybrid_evidence":
                hybrid_integration.get(
                    "hybrid_evidence"
                ),

            "hybrid_integration":
                hybrid_integration,

            "accepted_at":
                accepted_at,
        }

        _latest_telemetry = record

        _telemetry_history.append(
            record
        )

        _accepted_frames += 1

        try:

            mission_id = (
                get_active_mission_id()
            )

            if mission_id is not None:
                telemetry_persistence_service.enqueue(
                    mission_id=
                        mission_id,
                    telemetry=
                        telemetry_dict,
                )

        except Exception:
            pass

        websocket_payload = {
            "type":
                "telemetry",

            "timestamp":
                accepted_at,

            "telemetry":
                telemetry_dict,

            "observed_state":
                pipeline.get(
                    "observed_state"
                ),

            "sensor_validation":
                pipeline.get(
                    "sensor_validation"
                ),

            "expected_state":
                pipeline.get(
                    "expected_state"
                ),

            "residual_state":
                pipeline.get(
                    "residual_state"
                ),

            "anomaly_detection":
                pipeline.get(
                    "anomaly_detection"
                ),

            "degradation":
                pipeline.get(
                    "degradation"
                ),

            "rul":
                pipeline.get(
                    "rul"
                ),

            "fault_detection":
                pipeline.get(
                    "fault_detection"
                ),

            "maintenance":
                pipeline.get(
                    "maintenance"
                ),

            "readiness":
                pipeline.get(
                    "readiness"
                ),

            "digital_twin_state":
                pipeline.get(
                    "digital_twin"
                ),

            "ml":
                hybrid_integration.get(
                    "ml"
                ),

            "hybrid_evidence":
                hybrid_integration.get(
                    "hybrid_evidence"
                ),

            "hybrid_integration": {
                "available":
                    hybrid_integration.get(
                        "available",
                        False,
                    ),

                "status":
                    hybrid_integration.get(
                        "status"
                    ),

                "version":
                    hybrid_integration.get(
                        "version"
                    ),

                "source":
                    hybrid_integration.get(
                        "source"
                    ),

                "feature_count":
                    hybrid_integration.get(
                        "feature_count"
                    ),

                "decision_support_only":
                    hybrid_integration.get(
                        "safety",
                        {},
                    ).get(
                        "decision_support_only",
                        True,
                    ),
            },

            "pipeline_status": {
                "success":
                    pipeline.get(
                        "success"
                    ),

                "status":
                    pipeline.get(
                        "status"
                    ),

                "version":
                    TELEMETRY_API_VERSION,
            },
        }

        try:
            await websocket_manager.broadcast(
                websocket_payload
            )

        except Exception:
            pass

        return record

    except Exception:

        _rejected_frames += 1

        raise


@router.post("")
async def post_telemetry(
    telemetry: TelemetryFrame,
) -> Dict[str, Any]:

    try:
        return await process_telemetry(
            telemetry
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.get("/latest")
async def get_latest_telemetry(
) -> Dict[str, Any]:

    return {
        "available":
            _latest_telemetry
            is not None,

        "latest":
            _latest_telemetry,

        "timestamp":
            _utc_now().isoformat(),
    }


@router.get("/history")
async def get_telemetry_history(
) -> Dict[str, Any]:

    return {
        "count":
            len(
                _telemetry_history
            ),

        "max_history":
            MAX_HISTORY,

        "frames":
            list(
                _telemetry_history
            ),

        "timestamp":
            _utc_now().isoformat(),
    }


@router.get("/status")
async def get_telemetry_status(
) -> Dict[str, Any]:

    return {
        "service":
            "telemetry",

        "status":
            "READY",

        "version":
            TELEMETRY_API_VERSION,

        "received_frames":
            _received_frames,

        "accepted_frames":
            _accepted_frames,

        "rejected_frames":
            _rejected_frames,

        "history_size":
            len(
                _telemetry_history
            ),

        "latest_available":
            _latest_telemetry
            is not None,

        "pipeline_successful_runs":
            _pipeline_successful_runs,

        "pipeline_failed_runs":
            _pipeline_failed_runs,

        "sensor_validation":
            get_sensor_validation_status(),

        "anomaly_detection":
            get_anomaly_detection_status(),

        "degradation":
            get_degradation_status(),

        "rul":
            get_rul_status(),

        "fault_detection":
            get_fault_detection_status(),

        "maintenance":
            get_maintenance_status(),

        "readiness":
            get_readiness_status(),

        "hybrid_integration":
            get_hybrid_integration_status(),

        "timestamp":
            _utc_now().isoformat(),
    }


@router.get("/validation")
async def get_validation_status(
) -> Dict[str, Any]:

    return {
        "available":
            _latest_telemetry
            is not None,

        "validation":
            (
                _latest_telemetry.get(
                    "validation"
                )
                if _latest_telemetry
                else None
            ),

        "timestamp":
            _utc_now().isoformat(),
    }


@router.get("/state-estimator")
async def get_state_estimator_api_status(
) -> Dict[str, Any]:

    return get_state_estimator_status()


@router.get("/sensor-validation")
async def get_sensor_validation_api_status(
) -> Dict[str, Any]:

    return {
        "status":
            get_sensor_validation_status(),

        "latest":
            get_latest_sensor_validation(),

        "timestamp":
            _utc_now().isoformat(),
    }


@router.get("/anomalies")
async def get_anomaly_detection_api_status(
) -> Dict[str, Any]:

    return {
        "status":
            get_anomaly_detection_status(),

        "latest":
            get_latest_anomaly_detection(),

        "timestamp":
            _utc_now().isoformat(),
    }


@router.get("/degradation")
async def get_degradation_api_status(
) -> Dict[str, Any]:

    return {
        "status":
            get_degradation_status(),

        "latest":
            get_latest_degradation(),

        "timestamp":
            _utc_now().isoformat(),
    }


@router.get("/rul")
async def get_rul_api_status(
) -> Dict[str, Any]:

    return {
        "status":
            get_rul_status(),

        "latest":
            get_latest_rul(),

        "timestamp":
            _utc_now().isoformat(),
    }


@router.get("/maintenance")
async def get_maintenance_api_status(
) -> Dict[str, Any]:

    return {
        "status":
            get_maintenance_status(),

        "latest":
            get_latest_maintenance(),

        "timestamp":
            _utc_now().isoformat(),
    }


@router.get("/readiness")
async def get_readiness_api_status(
) -> Dict[str, Any]:

    latest_report = (
        get_latest_readiness()
    )

    latest_engineering: Optional[
        Dict[str, Any]
    ] = None

    operator: Optional[
        Dict[str, Any]
    ] = None

    if latest_report is not None:

        if hasattr(
            latest_report,
            "to_dict",
        ):
            latest_engineering = (
                latest_report.to_dict()
            )

            operator = (
                _build_operator_from_report(
                    latest_report
                )
            )

        elif isinstance(
            latest_report,
            dict,
        ):

            latest_engineering = dict(
                latest_report
            )

            if (
                _latest_pipeline_result
                and
                isinstance(
                    _latest_pipeline_result,
                    dict,
                )
            ):

                latest_pipeline_readiness = (
                    _latest_pipeline_result.get(
                        "readiness"
                    )
                )

                if isinstance(
                    latest_pipeline_readiness,
                    dict,
                ):

                    pipeline_operator = (
                        latest_pipeline_readiness.get(
                            "operator"
                        )
                    )

                    if isinstance(
                        pipeline_operator,
                        dict,
                    ):
                        operator = dict(
                            pipeline_operator
                        )

    if operator is not None:
        operator[
            "flight_authorization"
        ] = False

    return {
        "status":
            get_readiness_status(),

        "latest":
            latest_engineering,

        "operator":
            operator,

        "operator_available":
            operator
            is not None,

        "decision_support_only":
            True,

        "automatic_flight_authorization":
            False,

        "mapping": {
            "READY":
                "GO",

            "READY_WITH_CAUTION":
                "CAUTION",

            "NOT_READY":
                "NO-GO",

            "INSUFFICIENT_DATA":
                "UNKNOWN",
        },

        "timestamp":
            _utc_now().isoformat(),
    }


@router.get("/faults")
async def get_fault_detection_api_status(
) -> Dict[str, Any]:

    return {
        "status":
            get_fault_detection_status(),

        "latest":
            get_latest_fault_detection(),

        "timestamp":
            _utc_now().isoformat(),
    }


@router.get("/models")
async def get_models_status(
) -> Dict[str, Any]:

    return {
        "status":
            get_model_orchestrator_status(),

        "latest":
            get_latest_orchestration_dict(),

        "timestamp":
            _utc_now().isoformat(),
    }


@router.get("/residuals")
async def get_residuals_status(
) -> Dict[str, Any]:

    return get_residual_engine_status()


@router.get("/digital-twin")
async def get_digital_twin_api_status(
) -> Dict[str, Any]:

    return {
        "status":
            get_digital_twin_status(),

        "latest":
            get_latest_twin_state_dict(),

        "timestamp":
            _utc_now().isoformat(),
    }


@router.get("/pipeline")
async def get_pipeline_status(
) -> Dict[str, Any]:

    return {
        "available":
            _latest_pipeline_result
            is not None,

        "version":
            TELEMETRY_API_VERSION,

        "successful_runs":
            _pipeline_successful_runs,

        "failed_runs":
            _pipeline_failed_runs,

        "latest":
            _latest_pipeline_result,

        "timestamp":
            _utc_now().isoformat(),
    }


@router.get("/hybrid")
async def get_hybrid_integration_api_status(
) -> Dict[str, Any]:

    return {
        "status":
            get_hybrid_integration_status(),

        "latest":
            get_latest_hybrid_integration(),

        "timestamp":
            _utc_now().isoformat(),
    }


@router.delete("/history")
async def clear_telemetry_history(
) -> Dict[str, Any]:

    global _latest_telemetry
    global _received_frames
    global _accepted_frames
    global _rejected_frames
    global _pipeline_successful_runs
    global _pipeline_failed_runs
    global _latest_pipeline_result

    _telemetry_history.clear()

    _latest_telemetry = None

    _received_frames = 0
    _accepted_frames = 0
    _rejected_frames = 0

    _pipeline_successful_runs = 0
    _pipeline_failed_runs = 0

    _latest_pipeline_result = None

    reset_sensor_validation()

    reset_anomaly_detection()

    reset_degradation()

    reset_rul()

    reset_maintenance()

    reset_readiness()

    reset_fault_detection()

    reset_digital_twin()

    reset_model_orchestrator(
        clear_models=False
    )

    reset_hybrid_integration()

    return {
        "success":
            True,

        "message":
            (
                "Telemetry and diagnostic runtime state "
                "cleared."
            ),

        "models_preserved":
            True,

        "sensor_validation_reset":
            True,

        "anomaly_detection_reset":
            True,

        "degradation_reset":
            True,

        "rul_reset":
            True,

        "maintenance_reset":
            True,

        "readiness_reset":
            True,

        "fault_detection_reset":
            True,

        "digital_twin_reset":
            True,

        "hybrid_integration_reset":
            True,

        "timestamp":
            _utc_now().isoformat(),
    }
