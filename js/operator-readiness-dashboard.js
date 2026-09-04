(function () {

    "use strict";

    const VERSION = "1.1.0";

    function byId(id) {
        return document.getElementById(id);
    }

    function setText(id, value, fallback = "--") {

        const element = byId(id);

        if (!element) {
            return;
        }

        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {
            element.textContent = fallback;
            return;
        }

        element.textContent = String(value);
    }

    function safeNumber(value) {

        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {
            return null;
        }

        const parsed = Number(value);

        return Number.isFinite(parsed)
            ? parsed
            : null;
    }

    function percentFromFraction(value) {

        const parsed = safeNumber(value);

        if (parsed === null) {
            return "--";
        }

        return (parsed * 100).toFixed(1) + " %";
    }

    function percentFrom100(value) {

        const parsed = safeNumber(value);

        if (parsed === null) {
            return "--";
        }

        return parsed.toFixed(1) + " %";
    }

    function formatState(value) {

        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {
            return "--";
        }

        return String(value)
            .replaceAll("_", " ");
    }

    function setDecision(decision) {

        const element =
            byId("operatorDecision");

        if (!element) {
            return;
        }

        const state =
            decision || "UNKNOWN";

        element.textContent = state;

        element.dataset.state = state;
    }

    function renderReasons(
        operator,
        engineering
    ) {

        const list =
            byId("operatorReasons");

        if (!list) {
            return;
        }

        list.innerHTML = "";

        let reasons = [];

        if (
            operator &&
            Array.isArray(operator.reasons)
        ) {
            reasons = operator.reasons;
        }

        if (
            reasons.length === 0 &&
            engineering &&
            Array.isArray(engineering.warnings)
        ) {
            reasons = engineering.warnings;
        }

        if (reasons.length === 0) {
            reasons = [
                "No active readiness warning reported."
            ];
        }

        reasons
            .slice(0, 12)
            .forEach(function (reason) {

                const item =
                    document.createElement("li");

                if (
                    reason &&
                    typeof reason === "object"
                ) {

                    item.textContent =
                        reason.message ||
                        reason.reason ||
                        reason.code ||
                        JSON.stringify(reason);
                }

                else {

                    item.textContent =
                        String(reason);
                }

                list.appendChild(item);
            });
    }

    function renderWarnings(engineering) {

        const element =
            byId("operatorWarnings");

        if (!element) {
            return;
        }

        element.innerHTML = "";

        const warnings =
            engineering &&
            Array.isArray(engineering.warnings)
                ? engineering.warnings
                : [];

        if (warnings.length === 0) {

            const item =
                document.createElement("li");

            item.textContent =
                "No readiness warning reported.";

            element.appendChild(item);

            return;
        }

        warnings.forEach(function (warning) {

            const item =
                document.createElement("li");

            item.textContent =
                typeof warning === "string"
                    ? warning
                    : (
                        warning.message ||
                        warning.code ||
                        JSON.stringify(warning)
                    );

            element.appendChild(item);
        });
    }

    function renderFactors(engineering) {

        const container =
            byId("operatorFactors");

        if (!container) {
            return;
        }

        container.innerHTML = "";

        const factors =
            engineering &&
            Array.isArray(engineering.factors)
                ? engineering.factors
                : [];

        if (factors.length === 0) {

            const empty =
                document.createElement("div");

            empty.className =
                "operator-factor-empty";

            empty.textContent =
                "No readiness factors available.";

            container.appendChild(empty);

            return;
        }

        factors.forEach(function (factor) {

            const card =
                document.createElement("div");

            card.className =
                "operator-factor-card";

            const title =
                document.createElement("strong");

            title.textContent =
                factor?.name ||
                factor?.factor ||
                factor?.source ||
                factor?.category ||
                "Readiness Factor";

            const details =
                document.createElement("span");

            details.textContent =
                factor?.message ||
                factor?.reason ||
                factor?.description ||
                factor?.state ||
                factor?.severity ||
                "Backend readiness evidence";

            card.appendChild(title);
            card.appendChild(details);

            container.appendChild(card);
        });
    }

    function syncExistingHealthPreview(
        engineering,
        operator
    ) {

        const healthState =
            byId("healthState");

        if (healthState) {

            healthState.textContent =
                formatState(
                    engineering?.faultState
                );
        }

        const healthIndex =
            byId("healthIndex");

        if (healthIndex) {

            healthIndex.textContent =
                engineering
                    ? percentFrom100(
                        engineering.readinessScorePercent
                    )
                    : "--";
        }

        const activeFaultCount =
            byId("activeFaultCount");

        if (activeFaultCount) {

            activeFaultCount.textContent =
                engineering?.faultState === "DETECTED"
                    ? "Detected"
                    : (
                        engineering?.faultState
                            ? formatState(
                                engineering.faultState
                            )
                            : "--"
                    );
        }

        const estimatedRul =
            byId("estimatedRul");

        if (estimatedRul) {

            estimatedRul.textContent =
                formatState(
                    engineering?.rulState
                );
        }
    }

    function render(payload) {

        if (!payload) {
            return;
        }

        const engineering =
            payload.engineering || null;

        const operator =
            payload.operator || null;

        const decision =
            operator?.readiness ||
            "UNKNOWN";

        setDecision(decision);

        setText(
            "operatorEngineeringState",
            formatState(
                engineering?.state ||
                "INSUFFICIENT_DATA"
            )
        );

        setText(
            "operatorSeverity",
            formatState(
                engineering?.severity
            )
        );

        setText(
            "operatorReadinessScore",
            percentFrom100(
                engineering?.readinessScorePercent
            )
        );

        setText(
            "operatorConfidence",
            percentFromFraction(
                engineering?.confidence
            )
        );

        setText(
            "operatorSensorCoverage",
            percentFromFraction(
                engineering?.sensorCoverage
            )
        );

        setText(
            "operatorFaultState",
            formatState(
                engineering?.faultState
            )
        );

        setText(
            "operatorDegradationState",
            formatState(
                engineering?.degradationState
            )
        );

        setText(
            "operatorRulState",
            formatState(
                engineering?.rulState
            )
        );

        setText(
            "operatorMaintenanceState",
            formatState(
                engineering?.maintenanceState
            )
        );

        setText(
            "operatorFactorCount",
            engineering?.factorCount
        );

        setText(
            "operatorBlockingFactorCount",
            engineering?.blockingFactorCount
        );

        setText(
            "operatorMissionRisk",
            percentFrom100(
                operator?.missionRisk
            )
        );

        setText(
            "operatorPropulsionRisk",
            percentFrom100(
                operator?.propulsionHealthRisk
            )
        );

        setText(
            "operatorEnvironmentalRisk",
            percentFrom100(
                operator?.environmentalRisk
            )
        );

        setText(
            "operatorRecommendation",
            operator?.recommendation,
            "No engineering recommendation available."
        );

        renderReasons(
            operator,
            engineering
        );

        renderWarnings(
            engineering
        );

        renderFactors(
            engineering
        );

        syncExistingHealthPreview(
            engineering,
            operator
        );
    }

    function getInfo() {

        return {
            service:
                "PRATIRUP Operator Readiness Dashboard",

            version: VERSION,

            architecture:
                "BACKEND_AUTHORITATIVE_PRESENTATION_ONLY",

            readinessCalculation: false,

            faultDetection: false,

            degradationCalculation: false,

            rulCalculation: false,

            maintenanceCalculation: false,

            telemetryMutation: false,

            databaseWrites: false,

            automaticFlightAuthorization: false
        };
    }

    function initialize() {

        window.addEventListener(
            "pratirup:readiness",
            function (event) {

                render(
                    event.detail
                );
            }
        );

        if (
            window.PRATIRUPReadinessAPI &&
            typeof window.PRATIRUPReadinessAPI.getLatest ===
                "function"
        ) {

            const latest =
                window
                    .PRATIRUPReadinessAPI
                    .getLatest();

            if (latest) {
                render(latest);
            }
        }
    }

    window.PRATIRUPOperatorReadinessDashboard =
        Object.freeze({
            version: VERSION,
            render: render,
            getInfo: getInfo
        });

    if (
        document.readyState === "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            initialize,
            { once: true }
        );
    }

    else {
        initialize();
    }

})();
