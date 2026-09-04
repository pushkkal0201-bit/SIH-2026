(function () {

    "use strict";

    const VERSION =
        "1.0.1";

    const EVENT_NAME =
        "pratirup:hybrid-dashboard-state";

    const runtime = {

        initialized:
            false,

        listenerAttached:
            false,

        renderCount:
            0,

        eventCount:
            0,

        lastSnapshot:
            null,

        lastRenderedAt:
            null,

        lastError:
            null

    };

    function el(id) {

        return document.getElementById(id);

    }

    function clone(value) {

        if (
            value === null ||
            value === undefined
        ) {

            return value;

        }

        try {

            return JSON.parse(
                JSON.stringify(value)
            );

        } catch (_) {

            return value;

        }

    }

    function setText(
        id,
        value,
        fallback = "--"
    ) {

        const node =
            el(id);

        if (!node) {

            return;

        }

        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {

            node.textContent =
                fallback;

            return;

        }

        node.textContent =
            String(value);

    }

    function setTone(
        id,
        tone = "neutral"
    ) {

        const node =
            el(id);

        if (node) {

            node.dataset.tone =
                tone;

        }

    }

    function setBar(
        id,
        value
    ) {

        const node =
            el(id);

        if (!node) {

            return;

        }

        const number =
            Number(value);

        const percent =
            Number.isFinite(number)
                ? Math.max(
                    0,
                    Math.min(
                        100,
                        number
                    )
                )
                : 0;

        node.style.width =
            `${percent}%`;

    }

    function numberOrNull(value) {

        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {

            return null;

        }

        const number =
            Number(value);

        return Number.isFinite(number)
            ? number
            : null;

    }

    function validText(
        value
    ) {

        if (
            value === null ||
            value === undefined
        ) {

            return null;

        }

        const text =
            String(value)
                .trim();

        if (
            !text ||
            text === "--"
        ) {

            return null;

        }

        return text;

    }

    function formatPercent(
        value
    ) {

        const number =
            numberOrNull(value);

        if (
            number === null
        ) {

            return "--";

        }

        return `${number.toFixed(1)}%`;

    }

    function getH2() {

        return (
            window
                .PRATIRUPHybridDashboard
            ||
            null
        );

    }

    function getSnapshot() {

        const h2 =
            getH2();

        if (
            !h2 ||
            typeof h2.getSnapshot !==
                "function"
        ) {

            return null;

        }

        try {

            return clone(
                h2.getSnapshot()
            );

        } catch (error) {

            runtime.lastError = {

                stage:
                    "H2_GET_SNAPSHOT",

                message:
                    String(error)

            };

            return null;

        }

    }

    function integrationTone(
        value
    ) {

        const text =
            String(
                value || ""
            )
            .toUpperCase();

        if (
            text.includes("SUCCESS") ||
            text.includes("READY") ||
            text.includes("ACTIVE")
        ) {

            return "success";

        }

        if (
            text.includes("DEGRADED") ||
            text.includes("CAUTION") ||
            text.includes("SKIPPED")
        ) {

            return "warning";

        }

        if (
            text.includes("FAIL") ||
            text.includes("ERROR")
        ) {

            return "danger";

        }

        return "neutral";

    }

    function readinessTone(
        value
    ) {

        const text =
            String(
                value || ""
            )
            .toUpperCase();

        if (
            text === "READY" ||
            text === "GO"
        ) {

            return "success";

        }

        if (
            text.includes("CAUTION")
        ) {

            return "warning";

        }

        if (
            text === "NOT_READY" ||
            text === "NO-GO" ||
            text === "NO_GO"
        ) {

            return "danger";

        }

        return "neutral";

    }

    function evidenceTone(
        value
    ) {

        const text =
            String(
                value || ""
            )
            .toUpperCase();

        if (
            text.includes("DISAGREEMENT") ||
            text.includes("PHYSICS_ONLY") ||
            text.includes("ML_ONLY") ||
            text.includes("REVIEW")
        ) {

            return "warning";

        }

        if (
            text.includes("FAULT") ||
            text.includes("ALERT") ||
            text.includes("ABNORMAL") ||
            text.includes("DETECTED")
        ) {

            return "danger";

        }

        if (
            text.includes("NORMAL") ||
            text.includes("AGREEMENT") ||
            text.includes("NO REVIEW")
        ) {

            return "success";

        }

        return "neutral";

    }

    function renderAuthority() {

        setText(
            "hybridTwinAuthority",
            "EXISTING CORE"
        );

        setText(
            "hybridPhysicsAuthority",
            "EXISTING CORE"
        );

        setText(
            "hybridMLAuthority",
            "ADVISORY ONLY"
        );

        setText(
            "hybridFusionAuthority",
            "ADVISORY ONLY"
        );

        setText(
            "hybridFlightAuthorization",
            "FALSE"
        );

        setTone(
            "hybridFlightAuthorization",
            "danger"
        );

    }

    function normalize(
        snapshot
    ) {

        const ml =
            snapshot?.ml
            ||
            {};

        const hybrid =
            snapshot?.hybrid
            ||
            {};

        const integration =
            snapshot?.integration
            ||
            {};

        const readiness =
            snapshot?.readiness
            ||
            {};

        const authority =
            snapshot?.authority
            ||
            {};

        const mlAvailable =
            ml.available ===
            true;

        const mlAnomaly =
            validText(
                ml.anomaly_state
            )
            ||
            "--";

        const mlAnomalyConfidence =
            numberOrNull(
                ml
                    .anomaly_confidence_percent
            );

        const mlFault =
            validText(
                ml.fault_prediction
            )
            ||
            "--";

        const mlFaultConfidence =
            numberOrNull(
                ml
                    .fault_confidence_percent
            );

        const hybridAvailable =
            hybrid.available ===
            true;

        const anomalyFusion =
            validText(
                hybrid.anomaly_state
            )
            ||
            "--";

        const faultFusion =
            validText(
                hybrid.fault_state
            )
            ||
            "--";

        const reviewRequired =
            hybrid
                .engineering_review_required ===
            true;

        let reviewState =
            "--";

        let reviewReason =
            "Waiting for backend hybrid evidence.";

        if (
            hybridAvailable
        ) {

            reviewState =
                reviewRequired
                    ? "REVIEW REQUIRED"
                    : "NO REVIEW REQUIRED";

            const backendReason =
                validText(
                    hybrid
                        .engineering_review_reason
                );

            if (
                backendReason
            ) {

                reviewReason =
                    backendReason;

            } else if (
                reviewRequired
            ) {

                reviewReason =
                    "Physics and ML evidence requires engineering review.";

            } else {

                reviewReason =
                    "Current physics and advisory ML evidence does not require additional engineering review.";

            }

        }

        const integrationAvailable =
            integration.available ===
            true;

        const integrationStatus =
            validText(
                integration.status
            )
            ||
            (
                integrationAvailable
                    ? "AVAILABLE"
                    : "--"
            );

        const integrationSource =
            validText(
                integration.source
            )
            ||
            "--";

        const backendFeatureCount =
            numberOrNull(
                integration.feature_count
            );

        const featureCount =
            backendFeatureCount !==
            null
                ? backendFeatureCount
                : 60;

        const readinessState =
            validText(
                readiness.state
            )
            ||
            "--";

        const operatorState =
            validText(
                readiness.operator_state
            )
            ||
            "--";

        return {

            mlAvailable,

            mlAnomaly,

            mlAnomalyConfidence,

            mlFault,

            mlFaultConfidence,

            hybridAvailable,

            anomalyFusion,

            faultFusion,

            reviewRequired,

            reviewState,

            reviewReason,

            integrationAvailable,

            integrationStatus,

            integrationSource,

            featureCount,

            readinessState,

            operatorState,

            authority,

            flightAuthorization:
                readiness
                    .flight_authorization ===
                false

        };

    }

    function render(
        suppliedSnapshot
    ) {

        try {

            renderAuthority();

            const snapshot =
                suppliedSnapshot &&
                typeof suppliedSnapshot ===
                    "object"
                    ? clone(
                        suppliedSnapshot
                    )
                    : getSnapshot();

            if (
                !snapshot
            ) {

                return false;

            }

            const view =
                normalize(
                    snapshot
                );

            setText(
                "hybridIntegrationStatus",
                view.integrationStatus
            );

            setTone(
                "hybridIntegrationBadge",
                integrationTone(
                    view.integrationStatus
                )
            );

            setText(
                "hybridSource",
                view.integrationSource
            );

            setText(
                "hybridFeatureCount",
                view.featureCount
            );

            setText(
                "hybridReadinessState",
                view.readinessState
            );

            setTone(
                "hybridReadinessState",
                readinessTone(
                    view.readinessState
                )
            );

            setText(
                "hybridOperatorState",
                view.operatorState
            );

            setTone(
                "hybridOperatorState",
                readinessTone(
                    view.operatorState
                )
            );

            setText(
                "hybridMLAnomalyState",
                view.mlAnomaly
            );

            setText(
                "hybridMLAnomalyChip",
                view.mlAvailable
                    ? view.mlAnomaly
                    : "WAITING"
            );

            setTone(
                "hybridMLAnomalyChip",
                evidenceTone(
                    view.mlAnomaly
                )
            );

            setText(
                "hybridMLAnomalyConfidence",
                formatPercent(
                    view.mlAnomalyConfidence
                )
            );

            setBar(
                "hybridMLAnomalyConfidenceBar",
                view.mlAnomalyConfidence
            );

            setText(
                "hybridMLFaultState",
                view.mlFault
            );

            setText(
                "hybridMLFaultChip",
                view.mlAvailable
                    ? view.mlFault
                    : "WAITING"
            );

            setTone(
                "hybridMLFaultChip",
                evidenceTone(
                    view.mlFault
                )
            );

            setText(
                "hybridMLFaultConfidence",
                formatPercent(
                    view.mlFaultConfidence
                )
            );

            setBar(
                "hybridMLFaultConfidenceBar",
                view.mlFaultConfidence
            );

            setText(
                "hybridAnomalyFusionState",
                view.anomalyFusion
            );

            setTone(
                "hybridAnomalyFusionState",
                evidenceTone(
                    view.anomalyFusion
                )
            );

            setText(
                "hybridFaultFusionState",
                view.faultFusion
            );

            setTone(
                "hybridFaultFusionState",
                evidenceTone(
                    view.faultFusion
                )
            );

            setText(
                "hybridFusionChip",
                view.hybridAvailable
                    ? "EVIDENCE"
                    : "WAITING"
            );

            setText(
                "hybridEngineeringReviewState",
                view.reviewState
            );

            setText(
                "hybridEngineeringReviewBadge",
                view.hybridAvailable
                    ? view.reviewState
                    : "WAITING"
            );

            setText(
                "hybridEngineeringReviewReason",
                view.reviewReason
            );

            const reviewTone =
                view.reviewRequired
                    ? "warning"
                    : (
                        view.hybridAvailable
                            ? "success"
                            : "neutral"
                    );

            setTone(
                "hybridEngineeringReviewCard",
                reviewTone
            );

            setTone(
                "hybridEngineeringReviewBadge",
                reviewTone
            );

            renderAuthority();

            const timestamp =
                validText(
                    snapshot.updated_at
                );

            const displayTime =
                timestamp
                    ? new Date(
                        timestamp
                    )
                    : new Date();

            setText(
                "hybridLastUpdate",
                `Updated ${displayTime.toLocaleTimeString()}`
            );

            runtime
                .renderCount +=
                1;

            runtime
                .lastSnapshot =
                clone(
                    snapshot
                );

            runtime
                .lastRenderedAt =
                new Date()
                    .toISOString();

            runtime
                .lastError =
                null;

            return true;

        } catch (error) {

            runtime.lastError = {

                stage:
                    "RENDER",

                message:
                    String(error)

            };

            console.error(
                "[PRATIRUP H3] render failed:",
                error
            );

            return false;

        }

    }

    function onHybridDashboardState(
        event
    ) {

        runtime
            .eventCount +=
            1;

        const detail =
            event?.detail;

        const snapshot =
            detail?.snapshot
            ||
            detail?.state
            ||
            detail?.data
            ||
            detail;

        render(
            snapshot
        );

    }

    function initialize() {

        if (
            !runtime
                .listenerAttached
        ) {

            window.addEventListener(
                EVENT_NAME,
                onHybridDashboardState
            );

            runtime
                .listenerAttached =
                true;

        }

        runtime
            .initialized =
            true;

        renderAuthority();

        render();

        return getStatus();

    }

    function getStatus() {

        const h2 =
            getH2();

        return {

            service:
                "hybrid_intelligence_ui",

            version:
                VERSION,

            initialized:
                runtime.initialized,

            listener_attached:
                runtime.listenerAttached,

            h2_available:
                Boolean(h2),

            h2_version:
                h2?.VERSION
                ??
                null,

            render_count:
                runtime.renderCount,

            event_count:
                runtime.eventCount,

            has_snapshot:
                Boolean(
                    runtime.lastSnapshot
                ),

            last_rendered_at:
                runtime.lastRenderedAt,

            last_error:
                clone(
                    runtime.lastError
                ),

            authority: {

                digital_twin:
                    "EXISTING_CORE",

                physics:
                    "EXISTING_CORE",

                diagnostics:
                    "EXISTING_CORE",

                readiness:
                    "EXISTING_CORE",

                ml:
                    "ADVISORY_ONLY",

                hybrid_fusion:
                    "ADVISORY_ONLY",

                flight_authorization:
                    false

            }

        };

    }

    window.PRATIRUPHybridIntelligenceUI = {

        VERSION,

        initialize,

        render,

        getStatus

    };

    if (
        document.readyState ===
        "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            initialize,
            {
                once:
                    true
            }
        );

    } else {

        initialize();

    }

    console.info(
        `[PRATIRUP H3] Hybrid Intelligence UI v${VERSION} loaded.`
    );

})();
