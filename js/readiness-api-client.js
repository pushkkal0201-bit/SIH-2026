(function () {

    "use strict";

    const VERSION = "1.0.0";

    const SERVICE_NAME =
        "PRATIRUP Readiness API Client";

    const DEFAULT_API_BASE =
        "http://127.0.0.1:8000";

    const READINESS_ENDPOINT =
        "/api/telemetry/readiness";

    const DEFAULT_POLL_INTERVAL_MS =
        1500;

    const REQUEST_TIMEOUT_MS =
        5000;

    const ENGINEERING_STATES = new Set([
        "READY",
        "READY_WITH_CAUTION",
        "NOT_READY",
        "INSUFFICIENT_DATA"
    ]);

    const OPERATOR_STATES = new Set([
        "GO",
        "CAUTION",
        "NO-GO",
        "UNKNOWN"
    ]);

    const EXPECTED_MAPPING = Object.freeze({

        READY:
            "GO",

        READY_WITH_CAUTION:
            "CAUTION",

        NOT_READY:
            "NO-GO",

        INSUFFICIENT_DATA:
            "UNKNOWN"

    });

    const state = {

        apiBase:
            DEFAULT_API_BASE,

        endpoint:
            READINESS_ENDPOINT,

        pollIntervalMs:
            DEFAULT_POLL_INTERVAL_MS,

        running:
            false,

        polling:
            false,

        timer:
            null,

        requestController:
            null,

        requestCount:
            0,

        successCount:
            0,

        failureCount:
            0,

        lastRequestAt:
            null,

        lastSuccessAt:
            null,

        lastFailureAt:
            null,

        lastError:
            null,

        latest:
            null

    };

    function nowIso() {

        return new Date().toISOString();

    }

    function isObject(value) {

        return (
            value !== null &&
            typeof value === "object" &&
            !Array.isArray(value)
        );

    }

    function hasOwn(object, key) {

        return (
            isObject(object) &&
            Object.prototype.hasOwnProperty.call(
                object,
                key
            )
        );

    }

    function clone(value) {

        if (value === undefined) {

            return undefined;

        }

        if (
            typeof structuredClone ===
            "function"
        ) {

            try {

                return structuredClone(value);

            }

            catch (_) {

            }

        }

        try {

            return JSON.parse(
                JSON.stringify(value)
            );

        }

        catch (_) {

            return value;

        }

    }

    function normalizeBaseUrl(value) {

        const raw =
            typeof value === "string"
                ? value.trim()
                : "";

        if (!raw) {

            return DEFAULT_API_BASE;

        }

        return raw.replace(
            /\/+$/,
            ""
        );

    }

    function normalizePollInterval(value) {

        const number =
            Number(value);

        if (
            !Number.isFinite(number) ||
            number < 500
        ) {

            return DEFAULT_POLL_INTERVAL_MS;

        }

        return Math.round(number);

    }

    function safeNumber(value) {

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

    function safeString(value) {

        if (
            value === null ||
            value === undefined
        ) {

            return null;

        }

        const text =
            String(value).trim();

        return text
            ? text
            : null;

    }

    function clamp(value, minimum, maximum) {

        const number =
            safeNumber(value);

        if (number === null) {

            return null;

        }

        return Math.min(
            maximum,
            Math.max(
                minimum,
                number
            )
        );

    }

    function emit(name, detail) {

        try {

            window.dispatchEvent(
                new CustomEvent(
                    name,
                    {
                        detail:
                            clone(detail)
                    }
                )
            );

        }

        catch (error) {

            console.warn(
                "[PRATIRUP D8-B] Event dispatch failed:",
                name,
                error
            );

        }

    }

    function emitReadiness(payload) {

        emit(
            "pratirup:readiness",
            payload
        );

    }

    function emitConnection(payload) {

        emit(
            "pratirup:readiness-connection",
            payload
        );

    }

    function emitError(payload) {

        emit(
            "pratirup:readiness-error",
            payload
        );

    }

    function normalizeEngineeringState(value) {

        const normalized =
            safeString(value);

        if (!normalized) {

            return null;

        }

        const stateName =
            normalized.toUpperCase();

        return ENGINEERING_STATES.has(
            stateName
        )
            ? stateName
            : null;

    }

    function normalizeOperatorState(value) {

        const normalized =
            safeString(value);

        if (!normalized) {

            return null;

        }

        const stateName =
            normalized.toUpperCase();

        return OPERATOR_STATES.has(
            stateName
        )
            ? stateName
            : null;

    }

    function normalizeEngineeringReport(raw) {

        if (!isObject(raw)) {

            return null;

        }

        return {

            state:
                normalizeEngineeringState(
                    raw.state
                ),

            severity:
                safeString(
                    raw.severity
                ),

            confidence:
                safeNumber(
                    raw.confidence
                ),

            confidenceLevel:
                safeString(
                    raw.confidence_level
                ),

            readinessScore:
                safeNumber(
                    raw.readiness_score
                ),

            readinessScorePercent:
                safeNumber(
                    raw.readiness_score_percent
                ),

            sensorCoverage:
                safeNumber(
                    raw.sensor_coverage
                ),

            factorCount:
                safeNumber(
                    raw.factor_count
                ),

            blockingFactorCount:
                safeNumber(
                    raw.blocking_factor_count
                ),

            maintenanceState:
                safeString(
                    raw.maintenance_state
                ),

            rulState:
                safeString(
                    raw.rul_state
                ),

            degradationState:
                safeString(
                    raw.degradation_state
                ),

            faultState:
                safeString(
                    raw.fault_state
                ),

            factors:
                Array.isArray(raw.factors)
                    ? clone(raw.factors)
                    : [],

            warnings:
                Array.isArray(raw.warnings)
                    ? clone(raw.warnings)
                    : [],

            timestamp:
                safeString(
                    raw.timestamp
                ),

            version:
                safeString(
                    raw.version
                ),

            raw:
                clone(raw)

        };

    }

    function normalizeOperatorReport(raw) {

        if (!isObject(raw)) {

            return null;

        }

        return {

            readiness:
                normalizeOperatorState(
                    raw.readiness
                ),

            missionRisk:
                clamp(
                    raw.mission_risk,
                    0,
                    100
                ),

            propulsionHealthRisk:
                clamp(
                    raw.propulsion_health_risk,
                    0,
                    100
                ),

            environmentalRisk:
                clamp(
                    raw.environmental_risk,
                    0,
                    100
                ),

            reasons:
                Array.isArray(raw.reasons)
                    ? clone(raw.reasons)
                    : [],

            recommendation:
                safeString(
                    raw.recommendation
                ),

            flightAuthorization:
                false,

            raw:
                clone(raw)

        };

    }

    function normalizeStatus(raw) {

        if (!isObject(raw)) {

            return null;

        }

        return {

            service:
                safeString(
                    raw.service
                ),

            status:
                safeString(
                    raw.status
                ),

            version:
                safeString(
                    raw.version
                ),

            assessmentCount:
                safeNumber(
                    raw.assessment_count
                ),

            failedAssessmentCount:
                safeNumber(
                    raw.failed_assessment_count
                ),

            latestResultAvailable:
                raw.latest_result_available === true,

            latestState:
                normalizeEngineeringState(
                    raw.latest_state
                ),

            latestSeverity:
                safeString(
                    raw.latest_severity
                ),

            latestConfidence:
                safeNumber(
                    raw.latest_confidence
                ),

            timestamp:
                safeString(
                    raw.timestamp
                ),

            raw:
                clone(raw)

        };

    }

    function validateMapping(
        engineering,
        operator
    ) {

        if (
            !engineering ||
            !operator
        ) {

            return null;

        }

        const engineeringState =
            engineering.state;

        const operatorState =
            operator.readiness;

        if (
            !engineeringState ||
            !operatorState
        ) {

            return null;

        }

        return (
            EXPECTED_MAPPING[
                engineeringState
            ] === operatorState
        );

    }

    function normalizePayload(raw) {

        const data =
            isObject(raw)
                ? raw
                : {};

        const engineering =
            normalizeEngineeringReport(
                data.latest
            );

        const operator =
            normalizeOperatorReport(
                data.operator
            );

        const status =
            normalizeStatus(
                data.status
            );

        const operatorAvailable =
            (
                data.operator_available === true &&
                operator !== null
            );

        const decisionSupportOnly =
            data.decision_support_only !== false;

        const automaticFlightAuthorization =
            false;

        const mappingValid =
            validateMapping(
                engineering,
                operator
            );

        return {

            service:
                SERVICE_NAME,

            clientVersion:
                VERSION,

            receivedAt:
                nowIso(),

            backendTimestamp:
                safeString(
                    data.timestamp
                ),

            status,

            engineering,

            operator,

            operatorAvailable,

            mappingValid,

            decisionSupportOnly,

            automaticFlightAuthorization,

            expectedMapping:
                clone(
                    EXPECTED_MAPPING
                ),

            raw:
                clone(data)

        };

    }

    async function fetchReadiness() {

        if (state.polling) {

            return state.latest;

        }

        state.polling =
            true;

        state.requestCount +=
            1;

        state.lastRequestAt =
            nowIso();

        const controller =
            new AbortController();

        state.requestController =
            controller;

        const timeoutId =
            window.setTimeout(
                function () {

                    controller.abort();

                },
                REQUEST_TIMEOUT_MS
            );

        const url =
            state.apiBase +
            state.endpoint;

        try {

            const response =
                await fetch(
                    url,
                    {

                        method:
                            "GET",

                        headers: {

                            "Accept":
                                "application/json"

                        },

                        cache:
                            "no-store",

                        signal:
                            controller.signal

                    }
                );

            if (!response.ok) {

                throw new Error(
                    "Readiness API returned HTTP " +
                    response.status
                );

            }

            const raw =
                await response.json();

            const normalized =
                normalizePayload(raw);

            state.latest =
                normalized;

            state.successCount +=
                1;

            state.lastSuccessAt =
                nowIso();

            state.lastError =
                null;

            emitReadiness(
                normalized
            );

            emitConnection({

                connected:
                    true,

                timestamp:
                    state.lastSuccessAt,

                requestCount:
                    state.requestCount,

                successCount:
                    state.successCount,

                failureCount:
                    state.failureCount

            });

            return normalized;

        }

        catch (error) {

            state.failureCount +=
                1;

            state.lastFailureAt =
                nowIso();

            const message =
                error &&
                error.name === "AbortError"
                    ? "Readiness API request timed out"
                    : (
                        error &&
                        error.message
                            ? error.message
                            : String(error)
                    );

            state.lastError =
                message;

            emitConnection({

                connected:
                    false,

                timestamp:
                    state.lastFailureAt,

                error:
                    message,

                requestCount:
                    state.requestCount,

                successCount:
                    state.successCount,

                failureCount:
                    state.failureCount

            });

            emitError({

                timestamp:
                    state.lastFailureAt,

                error:
                    message

            });

            return null;

        }

        finally {

            window.clearTimeout(
                timeoutId
            );

            if (
                state.requestController ===
                controller
            ) {

                state.requestController =
                    null;

            }

            state.polling =
                false;

        }

    }

    function scheduleNext() {

        if (!state.running) {

            return;

        }

        if (state.timer !== null) {

            window.clearTimeout(
                state.timer
            );

        }

        state.timer =
            window.setTimeout(
                async function () {

                    state.timer =
                        null;

                    if (!state.running) {

                        return;

                    }

                    await fetchReadiness();

                    scheduleNext();

                },
                state.pollIntervalMs
            );

    }

    async function start() {

        if (state.running) {

            return state.latest;

        }

        state.running =
            true;

        const result =
            await fetchReadiness();

        scheduleNext();

        return result;

    }

    function stop() {

        state.running =
            false;

        if (state.timer !== null) {

            window.clearTimeout(
                state.timer
            );

            state.timer =
                null;

        }

        if (state.requestController) {

            try {

                state.requestController.abort();

            }

            catch (_) {

            }

            state.requestController =
                null;

        }

    }

    async function refresh() {

        return fetchReadiness();

    }

    function configure(options) {

        const config =
            isObject(options)
                ? options
                : {};

        const wasRunning =
            state.running;

        if (wasRunning) {

            stop();

        }

        if (
            hasOwn(
                config,
                "apiBase"
            )
        ) {

            state.apiBase =
                normalizeBaseUrl(
                    config.apiBase
                );

        }

        if (
            hasOwn(
                config,
                "pollIntervalMs"
            )
        ) {

            state.pollIntervalMs =
                normalizePollInterval(
                    config.pollIntervalMs
                );

        }

        if (
            wasRunning
        ) {

            start();

        }

        return getInfo();

    }

    function getLatest() {

        return clone(
            state.latest
        );

    }

    function getInfo() {

        return {

            service:
                SERVICE_NAME,

            version:
                VERSION,

            architecture:
                "BACKEND_AUTHORITATIVE_READ_ONLY",

            apiBase:
                state.apiBase,

            endpoint:
                state.endpoint,

            running:
                state.running,

            requestInProgress:
                state.polling,

            pollIntervalMs:
                state.pollIntervalMs,

            requestCount:
                state.requestCount,

            successCount:
                state.successCount,

            failureCount:
                state.failureCount,

            lastRequestAt:
                state.lastRequestAt,

            lastSuccessAt:
                state.lastSuccessAt,

            lastFailureAt:
                state.lastFailureAt,

            lastError:
                state.lastError,

            latestAvailable:
                state.latest !== null,

            websocketOwner:
                false,

            databaseWrites:
                false,

            telemetryMutation:
                false,

            readinessCalculation:
                false,

            modelReprocessing:
                false,

            decisionSupportOnly:
                true,

            automaticFlightAuthorization:
                false,

            mapping:
                clone(
                    EXPECTED_MAPPING
                )

        };

    }

    function handleVisibilityChange() {

        if (
            document.visibilityState ===
            "visible" &&
            state.running
        ) {

            refresh();

        }

    }

    document.addEventListener(
        "visibilitychange",
        handleVisibilityChange
    );

    const api = Object.freeze({

        version:
            VERSION,

        start,

        stop,

        refresh,

        configure,

        getLatest,

        getInfo,

        normalize:
            normalizePayload,

        expectedMapping:
            clone(
                EXPECTED_MAPPING
            )

    });

    window.PRATIRUPReadinessAPI =
        api;

    emit(
        "pratirup:readiness-client-ready",
        getInfo()
    );

    function initialize() {

        start().catch(
            function (error) {

                console.warn(
                    "[PRATIRUP D8-B] Initialization failed:",
                    error
                );

            }
        );

    }

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

    }

    else {

        initialize();

    }

    console.info(
        "[PRATIRUP D8-B]",
        SERVICE_NAME,
        "v" + VERSION,
        "loaded"
    );

})();
