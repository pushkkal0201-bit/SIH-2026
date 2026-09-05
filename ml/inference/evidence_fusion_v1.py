from __future__ import annotations

from collections.abc import Mapping
from typing import Any


VERSION = "1.0.0"


ML_NORMAL_CLASS = "NORMAL"


def _family_from_paths(
    paths: list[str],
) -> set[str]:

    families: set[str] = set()

    normalized = [
        str(path).lower()
        for path
        in paths
    ]

    if any(
        path.startswith(
            "oil."
        )
        for path
        in normalized
    ):

        families.add(
            "OIL_PRESSURE_LOSS"
        )


    if any(
        path.startswith(
            "fuel."
        )
        for path
        in normalized
    ):

        families.add(
            "FUEL_PRESSURE_LOSS"
        )


    if any(
        path.startswith(
            "egt."
        )
        for path
        in normalized
    ):

        families.add(
            "EGT_IMBALANCE"
        )


    if any(
        path.startswith(
            "cht."
        )
        for path
        in normalized
    ):

        families.add(
            "COOLING_DEGRADATION"
        )


    if any(
        path.startswith(
            "vibration."
        )
        for path
        in normalized
    ):

        families.add(
            "VIBRATION_INCREASE"
        )


    return families


def normalize_physics_anomaly(
    anomaly: Mapping[str, Any] | None,
) -> dict[str, Any]:

    if not isinstance(
        anomaly,
        Mapping,
    ):

        return {
            "available":
                False,

            "alert":
                None,

            "state":
                None,

            "severity":
                None,

            "score":
                None,

            "confidence":
                None,
        }


    state = str(
        anomaly.get(
            "overall_state",
            "",
        )
    ).upper()


    alert = (
        state
        in {
            "DETECTED",
            "ALERT",
            "ANOMALOUS",
            "ABNORMAL",
        }
    )


    return {
        "available":
            True,

        "alert":
            alert,

        "state":
            anomaly.get(
                "overall_state"
            ),

        "severity":
            anomaly.get(
                "overall_severity"
            ),

        "score":
            anomaly.get(
                "overall_score"
            ),

        "confidence":
            anomaly.get(
                "overall_confidence"
            ),

        "anomaly_count":
            anomaly.get(
                "anomaly_count"
            ),
    }


def normalize_ml_anomaly(
    ml: Mapping[str, Any] | None,
) -> dict[str, Any]:

    if not isinstance(
        ml,
        Mapping,
    ):

        return {
            "available":
                False,

            "alert":
                None,

            "prediction":
                None,

            "probability":
                None,
        }


    anomaly = ml.get(
        "anomaly"
    )

    if not isinstance(
        anomaly,
        Mapping,
    ):

        return {
            "available":
                False,

            "alert":
                None,

            "prediction":
                None,

            "probability":
                None,
        }


    prediction = anomaly.get(
        "prediction"
    )


    if prediction not in (
        0,
        1,
    ):

        return {
            "available":
                False,

            "alert":
                None,

            "prediction":
                prediction,

            "probability":
                anomaly.get(
                    "probability"
                ),
        }


    return {
        "available":
            True,

        "alert":
            prediction == 1,

        "prediction":
            prediction,

        "state":
            anomaly.get(
                "state"
            ),

        "probability":
            anomaly.get(
                "probability"
            ),
    }


def normalize_physics_fault(
    fault: Mapping[str, Any] | None,
) -> dict[str, Any]:

    if not isinstance(
        fault,
        Mapping,
    ):

        return {
            "available":
                False,

            "detected":
                None,

            "families":
                [],

            "unmapped_faults":
                [],
        }


    active = fault.get(
        "active_faults"
    )

    if not isinstance(
        active,
        list,
    ):

        active = []


    families: set[str] = set()

    unmapped_faults = []


    for candidate in active:

        if not isinstance(
            candidate,
            Mapping,
        ):

            continue


        paths = candidate.get(
            "affected_paths"
        )

        if not isinstance(
            paths,
            list,
        ):

            paths = []


        candidate_families = (
            _family_from_paths(
                paths
            )
        )


        if candidate_families:

            families.update(
                candidate_families
            )

        else:

            unmapped_faults.append(
                {
                    "fault_id":
                        candidate.get(
                            "fault_id"
                        ),

                    "name":
                        candidate.get(
                            "name"
                        ),

                    "category":
                        candidate.get(
                            "category"
                        ),

                    "confidence":
                        candidate.get(
                            "confidence"
                        ),

                    "affected_paths":
                        paths,
                }
            )


    state = str(
        fault.get(
            "overall_state",
            "",
        )
    ).upper()


    detected = (
        state == "DETECTED"
        or len(
            active
        ) > 0
    )


    return {
        "available":
            True,

        "detected":
            detected,

        "state":
            fault.get(
                "overall_state"
            ),

        "severity":
            fault.get(
                "overall_severity"
            ),

        "score":
            fault.get(
                "overall_fault_score"
            ),

        "confidence":
            fault.get(
                "overall_confidence"
            ),

        "families":
            sorted(
                families
            ),

        "active_fault_count":
            len(
                active
            ),

        "unmapped_faults":
            unmapped_faults,

        "data_quality_issue_count":
            fault.get(
                "data_quality_issue_count",
                0,
            ),

        "sensor_coverage":
            fault.get(
                "sensor_coverage"
            ),

        "residual_coverage":
            fault.get(
                "residual_coverage"
            ),
    }


def normalize_ml_fault(
    ml: Mapping[str, Any] | None,
) -> dict[str, Any]:

    if not isinstance(
        ml,
        Mapping,
    ):

        return {
            "available":
                False,

            "detected":
                None,

            "prediction":
                None,

            "confidence":
                None,
        }


    fault = ml.get(
        "fault"
    )

    if not isinstance(
        fault,
        Mapping,
    ):

        return {
            "available":
                False,

            "detected":
                None,

            "prediction":
                None,

            "confidence":
                None,
        }


    prediction = fault.get(
        "prediction"
    )


    if prediction is None:

        return {
            "available":
                False,

            "detected":
                None,

            "prediction":
                None,

            "confidence":
                fault.get(
                    "confidence"
                ),
        }


    prediction = str(
        prediction
    )


    return {
        "available":
            True,

        "detected":
            prediction
            != ML_NORMAL_CLASS,

        "prediction":
            prediction,

        "confidence":
            fault.get(
                "confidence"
            ),
    }


def fuse_anomaly(
    physics: dict[str, Any],
    ml: dict[str, Any],
) -> dict[str, Any]:

    if (
        not physics[
            "available"
        ]
        and not ml[
            "available"
        ]
    ):

        state = (
            "INSUFFICIENT_EVIDENCE"
        )

        agreement = None


    elif not physics[
        "available"
    ]:

        state = (
            "ML_ONLY_EVIDENCE"
        )

        agreement = None


    elif not ml[
        "available"
    ]:

        state = (
            "PHYSICS_ONLY_EVIDENCE"
        )

        agreement = None


    elif (
        physics[
            "alert"
        ]
        and ml[
            "alert"
        ]
    ):

        state = (
            "AGREEMENT_ALERT"
        )

        agreement = True


    elif (
        not physics[
            "alert"
        ]
        and not ml[
            "alert"
        ]
    ):

        state = (
            "AGREEMENT_NORMAL"
        )

        agreement = True


    elif physics[
        "alert"
    ]:

        state = (
            "PHYSICS_ONLY_ALERT"
        )

        agreement = False


    else:

        state = (
            "ML_ONLY_ALERT"
        )

        agreement = False


    return {
        "state":
            state,

        "agreement":
            agreement,

        "physics_alert":
            physics.get(
                "alert"
            ),

        "ml_alert":
            ml.get(
                "alert"
            ),

        "physics_score":
            physics.get(
                "score"
            ),

        "physics_confidence":
            physics.get(
                "confidence"
            ),

        "ml_probability":
            ml.get(
                "probability"
            ),
    }


def fuse_fault(
    physics: dict[str, Any],
    ml: dict[str, Any],
) -> dict[str, Any]:

    if (
        not physics[
            "available"
        ]
        and not ml[
            "available"
        ]
    ):

        state = (
            "INSUFFICIENT_EVIDENCE"
        )

        agreement = None


    elif not physics[
        "available"
    ]:

        state = (
            "ML_ONLY_EVIDENCE"
        )

        agreement = None


    elif not ml[
        "available"
    ]:

        state = (
            "PHYSICS_ONLY_EVIDENCE"
        )

        agreement = None


    elif (
        not physics[
            "detected"
        ]
        and not ml[
            "detected"
        ]
    ):

        state = (
            "AGREEMENT_NORMAL"
        )

        agreement = True


    elif (
        physics[
            "detected"
        ]
        and not ml[
            "detected"
        ]
    ):

        state = (
            "PHYSICS_ONLY_FAULT"
        )

        agreement = False


    elif (
        not physics[
            "detected"
        ]
        and ml[
            "detected"
        ]
    ):

        state = (
            "ML_ONLY_FAULT"
        )

        agreement = False


    else:

        ml_family = ml[
            "prediction"
        ]

        physics_families = set(
            physics[
                "families"
            ]
        )


        if (
            ml_family
            in physics_families
        ):

            state = (
                "AGREEMENT_FAULT"
            )

            agreement = True


        elif (
            not physics_families
            and physics[
                "unmapped_faults"
            ]
        ):

            state = (
                "TAXONOMY_UNRESOLVED"
            )

            agreement = None


        else:

            state = (
                "FAULT_DISAGREEMENT"
            )

            agreement = False


    return {
        "state":
            state,

        "agreement":
            agreement,

        "physics_detected":
            physics.get(
                "detected"
            ),

        "physics_families":
            physics.get(
                "families",
                [],
            ),

        "physics_unmapped_faults":
            physics.get(
                "unmapped_faults",
                [],
            ),

        "ml_detected":
            ml.get(
                "detected"
            ),

        "ml_prediction":
            ml.get(
                "prediction"
            ),

        "physics_confidence":
            physics.get(
                "confidence"
            ),

        "ml_confidence":
            ml.get(
                "confidence"
            ),
    }


class PRATIRUPEvidenceFusion:

    def get_status(
        self,
    ) -> dict[str, Any]:

        return {
            "service":
                "pratirup_evidence_fusion",

            "version":
                VERSION,

            "status":
                "READY",

            "mode":
                "ADVISORY_EVIDENCE_COMPARISON",

            "physics_authority_preserved":
                True,

            "ml_overrides_physics":
                False,

            "ml_overrides_readiness":
                False,

            "readiness_modified":
                False,

            "database_writes":
                False,

            "flight_authorization":
                False,

            "decision_support_only":
                True,
        }


    def fuse(
        self,
        *,
        anomaly_detection:
            Mapping[str, Any]
            | None,

        fault_detection:
            Mapping[str, Any]
            | None,

        ml_result:
            Mapping[str, Any]
            | None,

    ) -> dict[str, Any]:

        physics_anomaly = (
            normalize_physics_anomaly(
                anomaly_detection
            )
        )

        ml_anomaly = (
            normalize_ml_anomaly(
                ml_result
            )
        )

        physics_fault = (
            normalize_physics_fault(
                fault_detection
            )
        )

        ml_fault = (
            normalize_ml_fault(
                ml_result
            )
        )


        anomaly_fusion = (
            fuse_anomaly(
                physics_anomaly,
                ml_anomaly,
            )
        )


        fault_fusion = (
            fuse_fault(
                physics_fault,
                ml_fault,
            )
        )


        review_reasons = []


        if (
            anomaly_fusion[
                "agreement"
            ]
            is False
        ):

            review_reasons.append(
                "ANOMALY_EVIDENCE_DISAGREEMENT"
            )


        if (
            fault_fusion[
                "agreement"
            ]
            is False
        ):

            review_reasons.append(
                "FAULT_EVIDENCE_DISAGREEMENT"
            )


        if (
            fault_fusion[
                "state"
            ]
            == "TAXONOMY_UNRESOLVED"
        ):

            review_reasons.append(
                "FAULT_TAXONOMY_UNRESOLVED"
            )


        data_quality_issues = (
            physics_fault.get(
                "data_quality_issue_count",
                0,
            )
            or 0
        )


        if data_quality_issues > 0:

            review_reasons.append(
                "PHYSICS_DATA_QUALITY_ISSUES_PRESENT"
            )


        review_required = (
            len(
                review_reasons
            )
            > 0
        )


        return {
            "success":
                True,

            "status":
                "READY",

            "version":
                VERSION,

            "mode":
                "ADVISORY_EVIDENCE_COMPARISON",

            "anomaly":
                anomaly_fusion,

            "fault":
                fault_fusion,

            "source_evidence": {
                "physics_anomaly":
                    physics_anomaly,

                "ml_anomaly":
                    ml_anomaly,

                "physics_fault":
                    physics_fault,

                "ml_fault":
                    ml_fault,
            },

            "engineering_review": {
                "required":
                    review_required,

                "reasons":
                    review_reasons,
            },

            "safety": {
                "ml_overrides_physics":
                    False,

                "ml_overrides_existing_diagnostics":
                    False,

                "ml_overrides_readiness":
                    False,

                "readiness_modified":
                    False,

                "database_writes":
                    False,

                "flight_authorization":
                    False,

                "decision_support_only":
                    True,
            },
        }
