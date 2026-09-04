(function () {

    "use strict";

    const SERVICE =
        "hybrid_evidence_dashboard";

    const VERSION =
        "1.0.1";

    const EVENTS = Object.freeze({

        ML:
            "pratirup:ml-inference",

        HYBRID:
            "pratirup:hybrid-evidence",

        INTEGRATION:
            "pratirup:hybrid-integration",

        READINESS:
            "pratirup:readiness",

        DASHBOARD_STATE:
            "pratirup:hybrid-dashboard-state"

    });

    const AUTHORITY = Object.freeze({

        digital_twin:
            "EXISTING_CORE",

        physics:
            "EXISTING_CORE",

        anomaly:
            "EXISTING_CORE",

        fault:
            "EXISTING_CORE",

        readiness:
            "EXISTING_CORE",

        ml:
            "ADVISORY_ONLY",

        hybrid:
            "ADVISORY_ONLY",

        flight_authorization:
            false

    });

    function isObject(
        value
    ) {

        return (
            value !== null &&
            typeof value === "object" &&
            !Array.isArray(value)
        );
    }

    function clone(
        value
    ) {

        if (
            value === null ||
            value === undefined
        ) {

            return value;
        }

        if (
            typeof structuredClone ===
            "function"
        ) {

            try {

                return structuredClone(
                    value
                );
            }

            catch (_) {

            }
        }

        try {

            return JSON.parse(
                JSON.stringify(
                    value
                )
            );
        }

        catch (_) {

            return value;
        }
    }

    function firstDefined(
        ...values
    ) {

        for (
            const value
            of values
        ) {

            if (
                value !== undefined &&
                value !== null
            ) {

                return value;
            }
        }

        return null;
    }

    function firstObject(
        ...values
    ) {

        for (
            const value
            of values
        ) {

            if (
                isObject(
                    value
                )
            ) {

                return value;
            }
        }

        return {};
    }

    function finiteNumberOrNull(
        value
    ) {

        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {

            return null;
        }

        const numeric =
            Number(
                value
            );

        return Number.isFinite(
            numeric
        )
            ? numeric
            : null;
    }

    function normalizePercent(
        value
    ) {

        const numeric =
            finiteNumberOrNull(
                value
            );

        if (
            numeric === null
        ) {

            return null;
        }

        const percent =
            (
                numeric >= 0 &&
                numeric <= 1
            )
                ? numeric * 100
                : numeric;

        return Math.max(
            0,
            Math.min(
                100,
                percent
            )
        );
    }

    function normalizeText(
        value,
        fallback = "--"
    ) {

        if (
            value === null ||
            value === undefined
        ) {

            return fallback;
        }

        const text =
            String(
                value
            )
                .trim();

        return text.length > 0
            ? text
            : fallback;
    }

    function normalizeState(
        value,
        fallback = "--"
    ) {

        const text =
            normalizeText(
                value,
                fallback
            );

        if (
            text === fallback
        ) {

            return fallback;
        }

        return text
            .trim()
            .toUpperCase();
    }

    function booleanOrFallback(
        value,
        fallback = false
    ) {

        if (
            typeof value ===
            "boolean"
        ) {

            return value;
        }

        return fallback;
    }

    function utcNow() {

        return new Date()
            .toISOString();
    }

    function createInitialState() {

        return {

            service:
                SERVICE,

            version:
                VERSION,

            updated_at:
                null,

            ml: {

                available:
                    false,

                anomaly_state:
                    "--",

                anomaly_confidence_percent:
                    null,

                fault_prediction:
                    "--",

                fault_confidence_percent:
                    null

            },

            hybrid: {

                available:
                    false,

                anomaly_state:
                    "--",

                fault_state:
                    "--",

                engineering_review_required:
                    false,

                engineering_review_reason:
                    "--"

            },

            integration: {

                available:
                    false,

                status:
                    "--",

                version:
                    "--",

                source:
                    "--",

                feature_count:
                    null,

                decision_support_only:
                    true

            },

            readiness: {

                state:
                    "--",

                operator_state:
                    "--",

                flight_authorization:
                    false,

                authoritative_source:
                    "EXISTING_CORE"

            },

            authority: {

                digital_twin:
                    AUTHORITY.digital_twin,

                physics:
                    AUTHORITY.physics,

                anomaly:
                    AUTHORITY.anomaly,

                fault:
                    AUTHORITY.fault,

                readiness:
                    AUTHORITY.readiness,

                ml:
                    AUTHORITY.ml,

                hybrid:
                    AUTHORITY.hybrid,

                flight_authorization:
                    false

            },

            counters: {

                ml_messages:
                    0,

                hybrid_messages:
                    0,

                integration_messages:
                    0,

                readiness_messages:
                    0

            }

        };
    }

    let state =
        createInitialState();

    function getSnapshot() {

        return clone(
            state
        );
    }

    function publishSnapshot() {

        const snapshot =
            getSnapshot();

        window.dispatchEvent(
            new CustomEvent(
                EVENTS.DASHBOARD_STATE,
                {
                    detail:
                        snapshot
                }
            )
        );

        return snapshot;
    }

    function markUpdated() {

        state.updated_at =
            utcNow();
    }

    function extractMLRoot(
        payload
    ) {

        if (
            !isObject(
                payload
            )
        ) {

            return {};
        }

        return firstObject(

            payload.ml,

            payload.result,

            payload.latest,

            payload

        );
    }

    function extractMLAnomaly(
        root
    ) {

        return firstObject(

            root.anomaly,

            root.anomaly_detection,

            root.anomaly_result,

            root.predictions
                ?.anomaly

        );
    }

    function extractMLFault(
        root
    ) {

        return firstObject(

            root.fault,

            root.fault_detection,

            root.fault_prediction_result,

            root.predictions
                ?.fault

        );
    }

    function handleMLInferenceEvent(
        event
    ) {

        const payload =
            isObject(
                event?.detail
            )
                ? event.detail
                : {};

        const root =
            extractMLRoot(
                payload
            );

        const anomaly =
            extractMLAnomaly(
                root
            );

        const fault =
            extractMLFault(
                root
            );

        const anomalyState =
            firstDefined(

                anomaly.state,

                anomaly.prediction,

                anomaly.label,

                anomaly.classification,

                root.anomaly_state,

                root.anomaly_prediction,

                root.predicted_anomaly

            );

        const anomalyConfidence =
            firstDefined(

                anomaly.confidence_percent,

                anomaly.confidence,

                anomaly.probability_percent,

                anomaly.probability,

                root.anomaly_confidence_percent,

                root.anomaly_confidence

            );

        const faultPrediction =
            firstDefined(

                fault.prediction,

                fault.state,

                fault.label,

                fault.classification,

                fault.fault_type,

                root.fault_prediction,

                root.predicted_fault,

                root.fault_state

            );

        const faultConfidence =
            firstDefined(

                fault.confidence_percent,

                fault.confidence,

                fault.probability_percent,

                fault.probability,

                root.fault_confidence_percent,

                root.fault_confidence

            );

        state.ml.available =
            true;

        state.ml.anomaly_state =
            normalizeState(
                anomalyState
            );

        state.ml.anomaly_confidence_percent =
            normalizePercent(
                anomalyConfidence
            );

        state.ml.fault_prediction =
            normalizeState(
                faultPrediction
            );

        state.ml.fault_confidence_percent =
            normalizePercent(
                faultConfidence
            );

        state.counters.ml_messages +=
            1;

        markUpdated();

        publishSnapshot();

    }

    function extractHybridRoot(
        payload
    ) {

        if (
            !isObject(
                payload
            )
        ) {

            return {};
        }

        return firstObject(

            payload.hybrid_evidence,

            payload.hybrid,

            payload.fusion,

            payload.result,

            payload.latest,

            payload

        );
    }

    function handleHybridEvidenceEvent(
        event
    ) {

        const payload =
            isObject(
                event?.detail
            )
                ? event.detail
                : {};

        const root =
            extractHybridRoot(
                payload
            );

        const anomalySection =
            firstObject(

                root.anomaly,

                root.anomaly_fusion,

                root.fused_anomaly

            );

        const faultSection =
            firstObject(

                root.fault,

                root.fault_fusion,

                root.fused_fault

            );

        const anomalyState =
            firstDefined(

                anomalySection.state,

                anomalySection.fusion_state,

                anomalySection.result,

                root.anomaly_state,

                root.anomaly_fusion_state

            );

        const faultState =
            firstDefined(

                faultSection.state,

                faultSection.fusion_state,

                faultSection.result,

                root.fault_state,

                root.fault_fusion_state

            );

        const reviewRequired =
            booleanOrFallback(

                firstDefined(

                    root.engineering_review_required,

                    root.review_required,

                    root.requires_engineering_review,

                    root.engineering_review
                        ?.required

                ),

                false

            );

        const reviewReason =
            firstDefined(

                root.engineering_review_reason,

                root.review_reason,

                root.engineering_review
                    ?.reason,

                root.reason

            );

        state.hybrid.available =
            true;

        state.hybrid.anomaly_state =
            normalizeState(
                anomalyState
            );

        state.hybrid.fault_state =
            normalizeState(
                faultState
            );

        state.hybrid.engineering_review_required =
            reviewRequired;

        state.hybrid.engineering_review_reason =
            reviewRequired
                ? normalizeText(
                    reviewReason,
                    "Engineering review required."
                )
                : "--";

        state.counters.hybrid_messages +=
            1;

        markUpdated();

        publishSnapshot();

    }

    function extractIntegrationRoot(
        payload
    ) {

        if (
            !isObject(
                payload
            )
        ) {

            return {};
        }

        return firstObject(

            payload.hybrid_integration,

            payload.integration,

            payload.status_detail,

            payload.result,

            payload.latest,

            payload

        );
    }

    function handleHybridIntegrationEvent(
        event
    ) {

        const payload =
            isObject(
                event?.detail
            )
                ? event.detail
                : {};

        const root =
            extractIntegrationRoot(
                payload
            );

        const status =
            firstDefined(

                root.status,

                root.integration_status,

                root.state

            );

        const integrationVersion =
            firstDefined(

                root.version,

                root.integration_version,

                root.runtime_version

            );

        const source =
            firstDefined(

                root.source,

                root.telemetry_source,

                root.data_source,

                root.input_source

            );

        const featureCount =
            finiteNumberOrNull(

                firstDefined(

                    root.feature_count,

                    root.features_count,

                    root.ml_feature_count,

                    root.feature_vector_size

                )

            );

        const decisionSupportOnly =
            firstDefined(

                root.decision_support_only,

                root.decisionSupportOnly

            );

        state.integration.status =
            normalizeState(
                status
            );

        state.integration.version =
            normalizeText(
                integrationVersion
            );

        state.integration.source =
            normalizeText(
                source
            );

        state.integration.feature_count =
            featureCount;

        state.integration.decision_support_only =
            (
                typeof decisionSupportOnly ===
                "boolean"
            )
                ? decisionSupportOnly
                : true;

        state.integration.available =
            (
                state.integration.status ===
                "READY"
            );

        state.counters.integration_messages +=
            1;

        markUpdated();

        publishSnapshot();

    }

    function extractReadinessPayload(
        event
    ) {

        const payload =
            isObject(
                event?.detail
            )
                ? event.detail
                : {};

        const wrapped =
            firstObject(

                payload.readiness,

                payload.latest_readiness,

                payload.result

            );

        const effectivePayload =
            Object.keys(
                wrapped
            ).length > 0
                ? wrapped
                : payload;

        const engineering =
            firstObject(

                effectivePayload.engineering,

                effectivePayload.latest,

                payload.engineering,

                payload.latest,

                effectivePayload

            );

        const operator =
            firstObject(

                effectivePayload.operator,

                engineering.operator,

                payload.operator,

                payload.latest
                    ?.operator

            );

        return {

            payload,

            effectivePayload,

            engineering,

            operator

        };
    }

    function handleReadinessEvent(
        event
    ) {

        const {

            payload,

            effectivePayload,

            engineering,

            operator

        } =
            extractReadinessPayload(
                event
            );

        const engineeringState =
            firstDefined(

                engineering.state,

                engineering.readiness_state,

                engineering.engineering_state,

                effectivePayload.state,

                effectivePayload.readiness_state,

                effectivePayload.engineering_state,

                payload.state,

                payload.readiness_state,

                payload.engineering_state

            );

        const operatorState =
            firstDefined(

                operator.readiness,

                operator.operator_state,

                operator.state,

                effectivePayload.operator_state,

                effectivePayload.operator_readiness,

                payload.operator_state,

                payload.operator_readiness

            );

        state.readiness.state =
            normalizeState(
                engineeringState
            );

        state.readiness.operator_state =
            normalizeState(
                operatorState
            );

        state.readiness.flight_authorization =
            false;

        state.readiness.authoritative_source =
            "EXISTING_CORE";

        state.authority.readiness =
            "EXISTING_CORE";

        state.authority.flight_authorization =
            false;

        state.counters.readiness_messages +=
            1;

        markUpdated();

        publishSnapshot();

    }

    let initialized =
        false;

    function initialize() {

        if (
            initialized
        ) {

            return true;
        }

        window.addEventListener(
            EVENTS.ML,
            handleMLInferenceEvent
        );

        window.addEventListener(
            EVENTS.HYBRID,
            handleHybridEvidenceEvent
        );

        window.addEventListener(
            EVENTS.INTEGRATION,
            handleHybridIntegrationEvent
        );

        window.addEventListener(
            EVENTS.READINESS,
            handleReadinessEvent
        );

        initialized =
            true;

        return true;
    }

    function reset() {

        state =
            createInitialState();

        state.readiness
            .flight_authorization =
            false;

        state.authority
            .flight_authorization =
            false;

        publishSnapshot();

        return getSnapshot();
    }

    function validateAuthorityContract() {

        state.authority.digital_twin =
            "EXISTING_CORE";

        state.authority.physics =
            "EXISTING_CORE";

        state.authority.anomaly =
            "EXISTING_CORE";

        state.authority.fault =
            "EXISTING_CORE";

        state.authority.readiness =
            "EXISTING_CORE";

        state.authority.ml =
            "ADVISORY_ONLY";

        state.authority.hybrid =
            "ADVISORY_ONLY";

        state.authority.flight_authorization =
            false;

        state.readiness.authoritative_source =
            "EXISTING_CORE";

        state.readiness.flight_authorization =
            false;

        state.integration.decision_support_only =
            true;

    }

    const API = {

        VERSION,

        getSnapshot,

        publishSnapshot,

        reset

    };

    window.PRATIRUPHybridDashboard =
        API;

    validateAuthorityContract();

    initialize();

    publishSnapshot();

    console.log(
        "[PRATIRUP] Hybrid Evidence Dashboard Adapter v" +
        VERSION +
        " loaded."
    );

    console.log(
        "[PRATIRUP] Readiness compatibility: direct Core + D8 client envelope."
    );

    console.log(
        "[PRATIRUP] Authority: Core = authoritative, ML/Hybrid = advisory only."
    );

    console.log(
        "[PRATIRUP] Flight authorization: FALSE."
    );

})();
