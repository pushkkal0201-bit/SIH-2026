(function () {

    "use strict";

    const VERSION =
        "1.4.0";

    const SERVICE_NAME =
        "telemetry_websocket_bridge";

    const CONFIG = {

        host:
            "127.0.0.1",

        port:
            8000,

        path:
            "/ws",

        secure:
            false,

        reconnectEnabled:
            true,

        reconnectBaseDelayMs:
            1000,

        reconnectMaximumDelayMs:
            10000,

        connectionTimeoutMs:
            8000,

        staleAfterMs:
            5000,

        maximumReconnectAttempts:
            Infinity,

        disableLegacyBackendSocket:
            true,

        verbose:
            false
    };

    const CONNECTION_STATE =
        Object.freeze({

            IDLE:
                "IDLE",

            CONNECTING:
                "CONNECTING",

            CONNECTED:
                "CONNECTED",

            RECONNECTING:
                "RECONNECTING",

            DISCONNECTED:
                "DISCONNECTED",

            ERROR:
                "ERROR"
        });

    const state = {

        initialized:
            false,

        disposed:
            false,

        socket:
            null,

        connection:
            CONNECTION_STATE.IDLE,

        manuallyDisconnected:
            false,

        reconnectTimer:
            null,

        connectionTimer:
            null,

        reconnectAttempts:
            0,

        totalConnections:
            0,

        totalDisconnections:
            0,

        totalErrors:
            0,

        totalMessages:
            0,

        telemetryMessages:
            0,

        replayTelemetryMessages:
            0,

        lastReplayTelemetryAt:
            null,

        pipelineMessages:
            0,

        ignoredMessages:
            0,

        invalidTelemetryCandidates:
            0,

        lastConnectedAt:
            null,

        lastDisconnectedAt:
            null,

        lastMessageAt:
            null,

        lastTelemetryAt:
            null,

        lastPipelineAt:
            null,

        lastError:
            null,

        lastTelemetry:
            null,

        lastPipeline:
            null,

        legacySocketDisabled:
            false
    };

    function isObject(value) {

        return (
            value !== null &&
            typeof value === "object" &&
            !Array.isArray(value)
        );
    }

    function isFiniteNumber(value) {

        return (
            typeof value === "number" &&
            Number.isFinite(value)
        );
    }

    function clone(value) {

        if (value === undefined) {

            return undefined;
        }

        if (value === null) {

            return null;
        }

        try {

            if (
                typeof structuredClone ===
                "function"
            ) {

                return structuredClone(value);
            }

        } catch (error) {

        }

        try {

            return JSON.parse(
                JSON.stringify(value)
            );

        } catch (error) {

            return value;
        }
    }

    function nowISO() {

        return new Date().toISOString();
    }

    function log(...args) {

        if (!CONFIG.verbose) {

            return;
        }

        console.log(
            "[PRATIRUP WS]",
            ...args
        );
    }

    function warn(...args) {

        console.warn(
            "[PRATIRUP WS]",
            ...args
        );
    }

    function errorLog(...args) {

        console.error(
            "[PRATIRUP WS]",
            ...args
        );
    }

    function buildWebSocketURL() {

        const protocol =
            CONFIG.secure
                ? "wss"
                : "ws";

        let path =
            String(
                CONFIG.path || "/ws"
            ).trim();

        if (!path.startsWith("/")) {

            path =
                "/" + path;
        }

        return (
            protocol +
            "://" +
            CONFIG.host +
            ":" +
            CONFIG.port +
            path
        );
    }

    function dispatch(
        eventName,
        detail
    ) {

        try {

            window.dispatchEvent(
                new CustomEvent(
                    eventName,
                    {
                        detail:
                            clone(detail)
                    }
                )
            );

        } catch (error) {

            errorLog(
                "Unable to dispatch event:",
                eventName,
                error
            );
        }
    }

    function isCanonicalTelemetryFrame(
        value
    ) {

        if (!isObject(value)) {

            return false;
        }

        const requiredSections = [

            "meta",
            "engine",
            "cht",
            "egt",
            "oil",
            "fuel",
            "vibration",
            "electrical"
        ];

        for (
            const section of
            requiredSections
        ) {

            if (
                !isObject(
                    value[section]
                )
            ) {

                return false;
            }
        }

        const pipelineFields = [

            "telemetry",
            "observed_state",
            "expected_state",
            "sensor_validation",
            "residual_state",
            "fault_detection",
            "anomaly_detection",
            "degradation",
            "rul",
            "maintenance",
            "readiness",
            "digital_twin_state",
            "ml",
            "hybrid_evidence",
            "hybrid_integration",
            "pipeline_status"
        ];

        for (
            const field of
            pipelineFields
        ) {

            if (
                value[field] !==
                undefined
            ) {

                return false;
            }
        }

        return true;
    }

    function looksLikePipeline(
        value
    ) {

        if (!isObject(value)) {

            return false;
        }

        return (

            value.observed_state !==
                undefined ||

            value.sensor_validation !==
                undefined ||

            value.expected_state !==
                undefined ||

            value.residual_state !==
                undefined ||

            value.residual !==
                undefined ||

            value.residuals !==
                undefined ||

            value.fault_detection !==
                undefined ||

            value.faults !==
                undefined ||

            value.anomaly_detection !==
                undefined ||

            value.anomaly !==
                undefined ||

            value.degradation !==
                undefined ||

            value.rul !==
                undefined ||

            value.maintenance !==
                undefined ||

            value.readiness !==
                undefined ||

            value.digital_twin_state !==
                undefined ||

            value.digital_twin !==
                undefined ||

            value.twin !==
                undefined ||

            value.ml !==
                undefined ||

            value.hybrid_evidence !==
                undefined ||

            value.hybrid_integration !==
                undefined ||

            value.pipeline_status !==
                undefined
        );
    }

    function extractTelemetryDetail(
        message
    ) {

        if (!isObject(message)) {

            return null;
        }

        if (
            isCanonicalTelemetryFrame(
                message
            )
        ) {

            return message;
        }

        if (
            isObject(
                message.telemetry
            )
        ) {

            if (
                isCanonicalTelemetryFrame(
                    message.telemetry
                )
            ) {

                return message.telemetry;
            }

            state.invalidTelemetryCandidates +=
                1;
        }

        if (
            isObject(
                message.data
            )
        ) {

            if (
                isCanonicalTelemetryFrame(
                    message.data
                )
            ) {

                return message.data;
            }

            if (
                isObject(
                    message.data.telemetry
                )
            ) {

                if (
                    isCanonicalTelemetryFrame(
                        message.data.telemetry
                    )
                ) {

                    return message.data.telemetry;
                }

                state.invalidTelemetryCandidates +=
                    1;
            }
        }

        if (
            isObject(
                message.payload
            )
        ) {

            if (
                isCanonicalTelemetryFrame(
                    message.payload
                )
            ) {

                return message.payload;
            }

            if (
                isObject(
                    message.payload.telemetry
                )
            ) {

                if (
                    isCanonicalTelemetryFrame(
                        message.payload.telemetry
                    )
                ) {

                    return message.payload.telemetry;
                }

                state.invalidTelemetryCandidates +=
                    1;
            }
        }

        return null;
    }

    function extractPipelineDetail(
        message
    ) {

        if (!isObject(message)) {

            return null;
        }

        if (
            looksLikePipeline(
                message
            )
        ) {

            return message;
        }

        if (
            isObject(
                message.data
            ) &&
            looksLikePipeline(
                message.data
            )
        ) {

            return message.data;
        }

        if (
            isObject(
                message.payload
            ) &&
            looksLikePipeline(
                message.payload
            )
        ) {

            return message.payload;
        }

        return null;
    }

    function routeTelemetry(
        telemetry,
        envelope = null
    ) {

        if (
            !isCanonicalTelemetryFrame(
                telemetry
            )
        ) {

            return false;
        }

        state.lastTelemetry =
            clone(telemetry);

        state.lastTelemetryAt =
            Date.now();

        state.telemetryMessages +=
            1;

        const replayEnvelope =
            isObject(envelope) &&
            envelope.type === "replay_telemetry";

        if (replayEnvelope) {

            const meta =
                isObject(telemetry.meta)
                    ? telemetry.meta
                    : {};

            const replayTagged =
                String(meta.source || "").toUpperCase() === "REPLAY" &&
                meta.replay === true;

            if (!replayTagged) {

                state.invalidTelemetryCandidates += 1;

                warn(
                    "Rejected malformed replay telemetry envelope.",
                    envelope
                );

                return false;
            }

            state.replayTelemetryMessages += 1;
            state.lastReplayTelemetryAt = Date.now();

            dispatch(
                "pratirup:replay-telemetry",
                telemetry
            );

            dispatch(
                "pratirup:telemetry-source-change",
                {
                    source: "replay",
                    original_source: meta.original_source || null,
                    sequence: meta.sequence ?? null,
                    received_at: nowISO()
                }
            );

        } else {

            dispatch(
                "pratirup:backend-telemetry",
                telemetry
            );
        }

        dispatch(
            "pratirup:backend-telemetry-received",
            {
                telemetry:
                    telemetry,

                envelope_type:
                    isObject(envelope)
                        ? envelope.type || null
                        : null,

                received_at:
                    nowISO()
            }
        );

        return true;
    }

    function routePipeline(
        pipeline
    ) {

        if (
            !isObject(
                pipeline
            )
        ) {

            return false;
        }

        state.lastPipeline =
            clone(pipeline);

        state.lastPipelineAt =
            Date.now();

        state.pipelineMessages +=
            1;

        dispatch(
            "pratirup:pipeline",
            pipeline
        );

        if (
            pipeline.sensor_validation !==
            undefined
        ) {

            dispatch(
                "pratirup:sensor-validation",
                pipeline.sensor_validation
            );
        }

        if (
            pipeline.observed_state !==
            undefined
        ) {

            dispatch(
                "pratirup:observed-state",
                pipeline.observed_state
            );
        }

        if (
            pipeline.expected_state !==
            undefined
        ) {

            dispatch(
                "pratirup:expected-state",
                pipeline.expected_state
            );
        }

        const residual =
            pipeline.residual_state !==
                undefined
                ? pipeline.residual_state

                : pipeline.residual !==
                    undefined
                    ? pipeline.residual

                    : pipeline.residuals;

        if (
            residual !==
            undefined
        ) {

            dispatch(
                "pratirup:residual-state",
                residual
            );
        }

        const faults =
            pipeline.fault_detection !==
                undefined
                ? pipeline.fault_detection
                : pipeline.faults;

        if (
            faults !==
            undefined
        ) {

            dispatch(
                "pratirup:fault-detection",
                faults
            );
        }

        const anomaly =
            pipeline.anomaly_detection !==
                undefined
                ? pipeline.anomaly_detection
                : pipeline.anomaly;

        if (
            anomaly !==
            undefined
        ) {

            dispatch(
                "pratirup:anomaly-detection",
                anomaly
            );
        }

        if (
            pipeline.degradation !==
            undefined
        ) {

            dispatch(
                "pratirup:degradation",
                pipeline.degradation
            );
        }

        if (
            pipeline.rul !==
            undefined
        ) {

            dispatch(
                "pratirup:rul",
                pipeline.rul
            );
        }

        if (
            pipeline.maintenance !==
            undefined
        ) {

            dispatch(
                "pratirup:maintenance",
                pipeline.maintenance
            );
        }

        if (
            pipeline.readiness !==
            undefined
        ) {

            dispatch(
                "pratirup:readiness",
                pipeline.readiness
            );
        }

        if (
            pipeline.ml !==
            undefined
        ) {

            dispatch(
                "pratirup:ml-inference",
                pipeline.ml
            );
        }

        if (
            pipeline.hybrid_evidence !==
            undefined
        ) {

            dispatch(
                "pratirup:hybrid-evidence",
                pipeline.hybrid_evidence
            );
        }

        if (
            pipeline.hybrid_integration !==
            undefined
        ) {

            dispatch(
                "pratirup:hybrid-integration",
                pipeline.hybrid_integration
            );
        }

        const digitalTwin =
            pipeline.digital_twin_state !==
                undefined
                ? pipeline.digital_twin_state

                : pipeline.digital_twin !==
                    undefined
                    ? pipeline.digital_twin

                    : pipeline.twin;

        if (
            digitalTwin !==
            undefined
        ) {

            dispatch(
                "pratirup:digital-twin-state",
                digitalTwin
            );
        }

        if (
            pipeline.pipeline_status !==
            undefined
        ) {

            dispatch(
                "pratirup:pipeline-status",
                pipeline.pipeline_status
            );
        }

        return true;
    }

    function processMessage(
        message
    ) {

        if (
            !isObject(
                message
            )
        ) {

            state.ignoredMessages +=
                1;

            return false;
        }

        let processed =
            false;

        const telemetry =
            extractTelemetryDetail(
                message
            );

        if (telemetry) {

            routeTelemetry(
                telemetry,
                message
            );

            processed =
                true;
        }

        const pipeline =
            extractPipelineDetail(
                message
            );

        if (pipeline) {

            routePipeline(
                pipeline
            );

            processed =
                true;
        }

        if (!processed) {

            state.ignoredMessages +=
                1;

            log(
                "Ignored WebSocket message:",
                message
            );
        }

        return processed;
    }

    function handleMessage(
        event
    ) {

        state.totalMessages +=
            1;

        state.lastMessageAt =
            Date.now();

        let message;

        try {

            message =
                JSON.parse(
                    event.data
                );

        } catch (error) {

            state.ignoredMessages +=
                1;

            state.lastError = {

                time:
                    nowISO(),

                message:
                    "Unable to parse WebSocket JSON.",

                detail:
                    String(error)
            };

            warn(
                "Invalid WebSocket JSON:",
                error
            );

            return;
        }

        processMessage(
            message
        );
    }

    function disableLegacySocket() {

        if (
            !CONFIG.disableLegacyBackendSocket
        ) {

            return false;
        }

        try {

            if (
                window.PratirupBackend &&
                typeof window.PratirupBackend.disconnect ===
                    "function"
            ) {

                window.PratirupBackend.disconnect();

                state.legacySocketDisabled =
                    true;

                log(
                    "Legacy backend-client WebSocket disabled."
                );

                return true;
            }

        } catch (error) {

            warn(
                "Unable to disable legacy backend socket:",
                error
            );
        }

        return false;
    }

    function clearReconnectTimer() {

        if (
            state.reconnectTimer !==
            null
        ) {

            clearTimeout(
                state.reconnectTimer
            );

            state.reconnectTimer =
                null;
        }
    }

    function clearConnectionTimer() {

        if (
            state.connectionTimer !==
            null
        ) {

            clearTimeout(
                state.connectionTimer
            );

            state.connectionTimer =
                null;
        }
    }

    function calculateReconnectDelay() {

        const attempt =
            Math.max(
                0,
                state.reconnectAttempts
            );

        const exponential =
            CONFIG.reconnectBaseDelayMs *
            Math.pow(
                1.7,
                Math.min(
                    attempt,
                    8
                )
            );

        return Math.min(
            CONFIG.reconnectMaximumDelayMs,
            Math.round(exponential)
        );
    }

    function scheduleReconnect() {

        if (
            state.disposed ||
            state.manuallyDisconnected ||
            !CONFIG.reconnectEnabled
        ) {

            return;
        }

        if (
            state.reconnectAttempts >=
            CONFIG.maximumReconnectAttempts
        ) {

            state.connection =
                CONNECTION_STATE.ERROR;

            return;
        }

        clearReconnectTimer();

        state.connection =
            CONNECTION_STATE.RECONNECTING;

        const delay =
            calculateReconnectDelay();

        dispatch(
            "pratirup:telemetry-reconnecting",
            {
                attempt:
                    state.reconnectAttempts + 1,

                delay_ms:
                    delay,

                websocket_url:
                    buildWebSocketURL()
            }
        );

        state.reconnectTimer =
            setTimeout(
                function () {

                    state.reconnectTimer =
                        null;

                    state.reconnectAttempts +=
                        1;

                    connect();

                },
                delay
            );
    }

    function handleOpen() {

        clearConnectionTimer();

        state.connection =
            CONNECTION_STATE.CONNECTED;

        state.reconnectAttempts =
            0;

        state.totalConnections +=
            1;

        state.lastConnectedAt =
            Date.now();

        state.lastError =
            null;

        console.log(
            "[PRATIRUP WS] Connected:",
            buildWebSocketURL()
        );

        dispatch(
            "pratirup:telemetry-connected",
            {
                service:
                    SERVICE_NAME,

                version:
                    VERSION,

                websocket_url:
                    buildWebSocketURL(),

                connected_at:
                    nowISO()
            }
        );
    }

    function handleError(
        event
    ) {

        state.totalErrors +=
            1;

        state.lastError = {

            time:
                nowISO(),

            message:
                "WebSocket error.",

            websocket_url:
                buildWebSocketURL()
        };

        log(
            "WebSocket error:",
            event
        );

        dispatch(
            "pratirup:telemetry-error",
            {
                service:
                    SERVICE_NAME,

                websocket_url:
                    buildWebSocketURL(),

                time:
                    nowISO()
            }
        );
    }

    function handleClose(
        event
    ) {

        clearConnectionTimer();

        state.totalDisconnections +=
            1;

        state.lastDisconnectedAt =
            Date.now();

        state.socket =
            null;

        if (
            state.manuallyDisconnected ||
            state.disposed
        ) {

            state.connection =
                CONNECTION_STATE.DISCONNECTED;

            dispatch(
                "pratirup:telemetry-disconnected",
                {
                    manual:
                        true,

                    code:
                        event.code,

                    reason:
                        event.reason || null
                }
            );

            return;
        }

        state.connection =
            CONNECTION_STATE.RECONNECTING;

        dispatch(
            "pratirup:telemetry-disconnected",
            {
                manual:
                    false,

                code:
                    event.code,

                reason:
                    event.reason || null
            }
        );

        scheduleReconnect();
    }

    function connect() {

        if (state.disposed) {

            return false;
        }

        if (
            state.socket &&
            (
                state.socket.readyState ===
                    WebSocket.OPEN ||

                state.socket.readyState ===
                    WebSocket.CONNECTING
            )
        ) {

            return true;
        }

        clearReconnectTimer();

        clearConnectionTimer();

        state.manuallyDisconnected =
            false;

        state.connection =
            state.reconnectAttempts > 0
                ? CONNECTION_STATE.RECONNECTING
                : CONNECTION_STATE.CONNECTING;

        const url =
            buildWebSocketURL();

        log(
            "Connecting:",
            url
        );

        try {

            state.socket =
                new WebSocket(url);

        } catch (error) {

            state.totalErrors +=
                1;

            state.lastError = {

                time:
                    nowISO(),

                message:
                    String(error),

                websocket_url:
                    url
            };

            state.socket =
                null;

            scheduleReconnect();

            return false;
        }

        state.socket.onopen =
            handleOpen;

        state.socket.onmessage =
            handleMessage;

        state.socket.onerror =
            handleError;

        state.socket.onclose =
            handleClose;

        state.connectionTimer =
            setTimeout(
                function () {

                    state.connectionTimer =
                        null;

                    if (
                        state.socket &&
                        state.socket.readyState ===
                            WebSocket.CONNECTING
                    ) {

                        warn(
                            "WebSocket connection timeout."
                        );

                        try {

                            state.socket.close();

                        } catch (error) {

                        }
                    }

                },
                CONFIG.connectionTimeoutMs
            );

        return true;
    }

    function disconnect() {

        state.manuallyDisconnected =
            true;

        clearReconnectTimer();

        clearConnectionTimer();

        if (state.socket) {

            try {

                state.socket.close(
                    1000,
                    "PRATIRUP frontend disconnect"
                );

            } catch (error) {

            }
        }

        state.socket =
            null;

        state.connection =
            CONNECTION_STATE.DISCONNECTED;

        return true;
    }

    function reconnect() {

        clearReconnectTimer();

        clearConnectionTimer();

        state.manuallyDisconnected =
            false;

        if (state.socket) {

            try {

                state.socket.onopen =
                    null;

                state.socket.onmessage =
                    null;

                state.socket.onerror =
                    null;

                state.socket.onclose =
                    null;

                state.socket.close();

            } catch (error) {

            }
        }

        state.socket =
            null;

        state.reconnectAttempts =
            0;

        return connect();
    }

    function configure(
        options = {}
    ) {

        if (!isObject(options)) {

            return getStatus();
        }

        if (
            typeof options.host ===
                "string" &&
            options.host.trim()
        ) {

            CONFIG.host =
                options.host.trim();
        }

        if (
            isFiniteNumber(
                options.port
            ) &&
            options.port > 0
        ) {

            CONFIG.port =
                Math.round(
                    options.port
                );
        }

        if (
            typeof options.path ===
                "string" &&
            options.path.trim()
        ) {

            CONFIG.path =
                options.path.trim();
        }

        if (
            typeof options.secure ===
                "boolean"
        ) {

            CONFIG.secure =
                options.secure;
        }

        if (
            typeof options.verbose ===
                "boolean"
        ) {

            CONFIG.verbose =
                options.verbose;
        }

        if (
            typeof options.reconnectEnabled ===
                "boolean"
        ) {

            CONFIG.reconnectEnabled =
                options.reconnectEnabled;
        }

        return getStatus();
    }

    function getTelemetryAgeMs() {

        if (
            state.lastTelemetryAt ===
            null
        ) {

            return null;
        }

        return (
            Date.now() -
            state.lastTelemetryAt
        );
    }

    function isTelemetryStale() {

        const age =
            getTelemetryAgeMs();

        if (age === null) {

            return true;
        }

        return (
            age >
            CONFIG.staleAfterMs
        );
    }

    function getStatus() {

        const socketReadyState =
            state.socket
                ? state.socket.readyState
                : null;

        const readyStateName =
            socketReadyState ===
                WebSocket.CONNECTING
                ? "CONNECTING"

                : socketReadyState ===
                    WebSocket.OPEN
                    ? "OPEN"

                    : socketReadyState ===
                        WebSocket.CLOSING
                        ? "CLOSING"

                        : socketReadyState ===
                            WebSocket.CLOSED
                            ? "CLOSED"

                            : null;

        return {

            service:
                SERVICE_NAME,

            version:
                VERSION,

            initialized:
                state.initialized,

            connection:
                state.connection,

            websocket_url:
                buildWebSocketURL(),

            connected:
                Boolean(
                    state.socket &&
                    state.socket.readyState ===
                        WebSocket.OPEN
                ),

            socket_ready_state:
                readyStateName,

            reconnect_attempts:
                state.reconnectAttempts,

            total_connections:
                state.totalConnections,

            total_disconnections:
                state.totalDisconnections,

            total_errors:
                state.totalErrors,

            total_messages:
                state.totalMessages,

            telemetry_messages:
                state.telemetryMessages,

            replay_telemetry_messages:
                state.replayTelemetryMessages,

            last_replay_telemetry_at:
                state.lastReplayTelemetryAt !== null
                    ? new Date(
                        state.lastReplayTelemetryAt
                    ).toISOString()
                    : null,

            pipeline_messages:
                state.pipelineMessages,

            ignored_messages:
                state.ignoredMessages,

            invalid_telemetry_candidates:
                state.invalidTelemetryCandidates,

            telemetry_age_ms:
                getTelemetryAgeMs(),

            telemetry_stale:
                isTelemetryStale(),

            last_connected_at:
                state.lastConnectedAt !==
                null
                    ? new Date(
                        state.lastConnectedAt
                    ).toISOString()
                    : null,

            last_disconnected_at:
                state.lastDisconnectedAt !==
                null
                    ? new Date(
                        state.lastDisconnectedAt
                    ).toISOString()
                    : null,

            last_message_at:
                state.lastMessageAt !==
                null
                    ? new Date(
                        state.lastMessageAt
                    ).toISOString()
                    : null,

            last_telemetry_at:
                state.lastTelemetryAt !==
                null
                    ? new Date(
                        state.lastTelemetryAt
                    ).toISOString()
                    : null,

            last_pipeline_at:
                state.lastPipelineAt !==
                null
                    ? new Date(
                        state.lastPipelineAt
                    ).toISOString()
                    : null,

            legacy_socket_disabled:
                state.legacySocketDisabled,

            last_error:
                clone(
                    state.lastError
                )
        };
    }

    function getLastTelemetry() {

        return clone(
            state.lastTelemetry
        );
    }

    function getLastPipeline() {

        return clone(
            state.lastPipeline
        );
    }

    function injectTestMessage(
        message
    ) {

        processMessage(
            clone(message)
        );

        return getStatus();
    }

    function initialize() {

        if (
            state.initialized ||
            state.disposed
        ) {

            return getStatus();
        }

        state.initialized =
            true;

        disableLegacySocket();

        connect();

        console.log(
            "[PRATIRUP WS]",
            "Telemetry WebSocket Bridge",
            VERSION,
            "initialized."
        );

        return getStatus();
    }

    function dispose() {

        if (state.disposed) {

            return;
        }

        state.disposed =
            true;

        state.manuallyDisconnected =
            true;

        clearReconnectTimer();

        clearConnectionTimer();

        if (state.socket) {

            try {

                state.socket.onopen =
                    null;

                state.socket.onmessage =
                    null;

                state.socket.onerror =
                    null;

                state.socket.onclose =
                    null;

                state.socket.close();

            } catch (error) {

            }
        }

        state.socket =
            null;

        state.connection =
            CONNECTION_STATE.DISCONNECTED;

        console.log(
            "[PRATIRUP WS]",
            "Telemetry WebSocket Bridge disposed."
        );
    }

    window.PRATIRUPTelemetryWebSocket = {

        VERSION,

        initialize,

        connect,

        disconnect,

        reconnect,

        configure,

        getStatus,

        getLastTelemetry,

        getLastPipeline,

        injectTestMessage,

        isCanonicalTelemetryFrame,

        dispose
    };

    if (
        document.readyState ===
        "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            function () {

                initialize();
            },
            {
                once:
                    true
            }
        );

    } else {

        initialize();
    }

})();
