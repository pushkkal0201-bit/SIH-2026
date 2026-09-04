(function () {
    "use strict";

    const VERSION = "1.1.0";

    const CONFIG = Object.freeze({
        defaultWebSocketURL: "ws://localhost:8000/ws/telemetry",
        reconnectDelayMs: 3000,
        maximumReconnectDelayMs: 30000,
        reconnectBackoffFactor: 1.6,
        reconnectJitterRatio: 0.15,
        telemetryTimeoutMs: 2500,
        maximumReconnectAttempts: 20,
        expectedFrameRateHz: 10
    });

    const state = {
        mode: "SIMULATION",
        connectionStatus: "DISCONNECTED",
        canStatus: "NOT_CONNECTED",
        socketCanStatus: "NOT_CONNECTED",
        fadecStatus: "NOT_CONNECTED",
        backendStatus: "NOT_CONNECTED",
        websocket: null,
        websocketURL: CONFIG.defaultWebSocketURL,
        reconnectAttempts: 0,
        reconnectTimer: null,
        manualDisconnect: false,
        lastFrameTimestamp: null,
        lastFrameReceiveTime: null,
        frameCount: 0,
        validFrames: 0,
        invalidFrames: 0,
        droppedFrames: 0,
        outOfOrderFrames: 0,
        sequenceResets: 0,
        previousSequence: null,
        frameRateHz: 0,
        packetQuality: 0,
        sensorFreshnessMs: null,
        lastFrame: null,
        connectedAt: null,
        lastError: null,
        canonicalFramesPublished: 0,
        canonicalFramesSuppressed: 0
    };

    let rateWindowStart = performance.now();
    let rateWindowFrames = 0;

    function clone(value) {
        if (value === null || value === undefined) {
            return value;
        }

        if (typeof structuredClone === "function") {
            try {
                return structuredClone(value);
            } catch (_) {}
        }

        try {
            return JSON.parse(JSON.stringify(value));
        } catch (_) {
            return value;
        }
    }

    function number(value, fallback = null) {
        if (value === null || value === undefined || value === "") {
            return fallback;
        }

        const n = Number(value);

        return Number.isFinite(n)
            ? n
            : fallback;
    }

    function clamp(value, min = 0, max = 100) {
        const n = number(value, min);

        return Math.max(
            min,
            Math.min(
                max,
                n
            )
        );
    }

    function normalizeStatus(value, fallback = null) {
        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {
            return fallback;
        }

        return String(value)
            .trim()
            .toUpperCase();
    }

    function setText(id, value) {
        const element =
            document.getElementById(id);

        if (element) {
            element.textContent =
                value === null ||
                value === undefined ||
                value === ""
                    ? "--"
                    : String(value);
        }
    }

    function serializeError(error) {
        if (!error) {
            return null;
        }

        return {
            name:
                error.name ||
                "Error",

            message:
                error.message ||
                String(error),

            at:
                Date.now()
        };
    }

    function publish(name, detail) {
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

    function getBridge() {
        return (
            window.PRATIRUP_BRIDGE ||
            null
        );
    }

    function setBridgeSourceMode(mode) {
        const bridge =
            getBridge();

        if (
            !bridge ||
            typeof bridge.setSourceMode !== "function"
        ) {
            return false;
        }

        try {
            bridge.setSourceMode(mode);

            return true;
        } catch (error) {
            state.lastError =
                serializeError(error);

            return false;
        }
    }

    function getBridgeArbitrationStatus() {
        const bridge =
            getBridge();

        if (!bridge) {
            return null;
        }

        try {
            if (
                typeof bridge.getSourceArbitrationStatus ===
                "function"
            ) {
                return bridge
                    .getSourceArbitrationStatus();
            }

            if (
                typeof bridge.getSourceMode ===
                "function"
            ) {
                return {
                    mode:
                        bridge.getSourceMode()
                };
            }
        } catch (_) {}

        return null;
    }

    function replayOwnsCanonicalPipeline() {
        const status =
            getBridgeArbitrationStatus();

        if (!status) {
            return false;
        }

        if (
            status.replayActive === true
        ) {
            return true;
        }

        const mode =
            normalizeStatus(
                status.mode ??
                status.sourceMode,
                ""
            );

        return mode === "REPLAY";
    }

    function validateFrame(frame) {
        if (
            !frame ||
            typeof frame !== "object" ||
            Array.isArray(frame)
        ) {
            return false;
        }

        const schema =
            window.PRATIRUP_TELEMETRY_SCHEMA;

        if (
            schema &&
            typeof schema.validate === "function"
        ) {
            try {
                return (
                    schema.validate(frame)
                        ?.valid === true
                );
            } catch (_) {
                return false;
            }
        }

        return Boolean(
            frame.meta ||
            frame.engine ||
            frame.telemetry
        );
    }

    function extractSequence(frame) {
        return number(
            frame?.meta?.sequence ??
            frame?.sequence ??
            frame?.sequence_number,
            null
        );
    }

    function trackSequence(frame) {
        const sequence =
            extractSequence(frame);

        if (sequence === null) {
            return;
        }

        if (
            state.previousSequence !== null
        ) {
            const difference =
                sequence -
                state.previousSequence;

            if (difference > 1) {
                state.droppedFrames +=
                    difference - 1;
            } else if (
                difference === 0
            ) {
                state.outOfOrderFrames += 1;
            } else if (
                difference < 0
            ) {
                state.sequenceResets += 1;
            }
        }

        state.previousSequence =
            sequence;
    }

    function updateFrameRate() {
        rateWindowFrames += 1;

        const now =
            performance.now();

        const elapsed =
            now -
            rateWindowStart;

        if (elapsed >= 1000) {
            state.frameRateHz =
                (
                    rateWindowFrames /
                    elapsed
                ) *
                1000;

            rateWindowFrames = 0;

            rateWindowStart =
                now;
        }
    }

    function calculatePacketQuality() {
        if (
            state.frameCount === 0
        ) {
            state.packetQuality = 0;

            return 0;
        }

        const validity =
            state.validFrames /
            state.frameCount;

        const sequenceTotal =
            state.validFrames +
            state.droppedFrames;

        const delivery =
            sequenceTotal > 0
                ? state.validFrames /
                  sequenceTotal
                : 1;

        const quality =
            validity * 0.60 +
            delivery * 0.40;

        state.packetQuality =
            clamp(
                quality *
                100
            );

        return state.packetQuality;
    }

    function normalizeBackendFrame(payload) {
        if (
            !payload ||
            typeof payload !== "object"
        ) {
            return payload;
        }

        if (
            payload.type === "telemetry" &&
            payload.data &&
            typeof payload.data === "object"
        ) {
            return payload.data;
        }

        if (
            payload.telemetry &&
            typeof payload.telemetry === "object"
        ) {
            return payload.telemetry;
        }

        if (
            payload.data &&
            payload.data.telemetry &&
            typeof payload.data.telemetry ===
                "object"
        ) {
            return payload
                .data
                .telemetry;
        }

        return payload;
    }

    function buildOutputFrame(frame) {
        const outputFrame =
            clone(frame) ||
            {};

        outputFrame.meta =
            outputFrame.meta &&
            typeof outputFrame.meta === "object"
                ? outputFrame.meta
                : {};

        outputFrame.meta.source =
            "CAN_FADEC";

        outputFrame.meta.transport =
            "WEBSOCKET";

        outputFrame.meta.receivedAt =
            Date.now();

        outputFrame.meta.live =
            true;

        outputFrame.meta.replay =
            false;

        return outputFrame;
    }

    function processTelemetry(payload) {
        const frame =
            normalizeBackendFrame(
                payload
            );

        state.frameCount += 1;

        if (
            !validateFrame(frame)
        ) {
            state.invalidFrames += 1;

            calculatePacketQuality();

            updateDashboard();

            publish(
                "pratirup:can-invalid-frame",
                {
                    frame,

                    receivedAt:
                        Date.now(),

                    version:
                        VERSION
                }
            );

            return false;
        }

        state.validFrames += 1;

        trackSequence(frame);

        updateFrameRate();

        state.lastFrame =
            clone(frame);

        state.lastFrameTimestamp =
            frame?.meta?.timestamp ??
            frame?.timestamp ??
            Date.now();

        state.lastFrameReceiveTime =
            Date.now();

        state.sensorFreshnessMs =
            0;

        if (
            state.canStatus ===
            "STALE_DATA"
        ) {
            state.canStatus =
                "CONNECTED";
        }

        calculatePacketQuality();

        const outputFrame =
            buildOutputFrame(
                frame
            );

        publish(
            "pratirup:can-telemetry",
            outputFrame
        );

        if (
            !replayOwnsCanonicalPipeline()
        ) {
            publish(
                "pratirup:telemetry",
                outputFrame
            );

            state
                .canonicalFramesPublished +=
                1;
        } else {
            state
                .canonicalFramesSuppressed +=
                1;

            publish(
                "pratirup:can-telemetry-suppressed",
                {
                    reason:
                        "REPLAY_SOURCE_OWNERSHIP",

                    sequence:
                        extractSequence(
                            outputFrame
                        ),

                    receivedAt:
                        outputFrame
                            .meta
                            .receivedAt,

                    version:
                        VERSION
                }
            );
        }

        updateDashboard();

        publishState();

        return true;
    }

    function processStatusMessage(payload) {
        const data =
            payload?.data &&
            typeof payload.data === "object"
                ? payload.data
                : payload ||
                  {};

        const canStatus =
            data.can_status ??
            data.canStatus;

        const socketCanStatus =
            data.socketcan_status ??
            data.socketCanStatus;

        const fadecStatus =
            data.fadec_status ??
            data.fadecStatus;

        const backendStatus =
            data.backend_status ??
            data.backendStatus;

        if (
            canStatus !== undefined &&
            canStatus !== null
        ) {
            state.canStatus =
                normalizeStatus(
                    canStatus,
                    state.canStatus
                );
        }

        if (
            socketCanStatus !== undefined &&
            socketCanStatus !== null
        ) {
            state.socketCanStatus =
                normalizeStatus(
                    socketCanStatus,
                    state.socketCanStatus
                );
        }

        if (
            fadecStatus !== undefined &&
            fadecStatus !== null
        ) {
            state.fadecStatus =
                normalizeStatus(
                    fadecStatus,
                    state.fadecStatus
                );
        }

        if (
            backendStatus !== undefined &&
            backendStatus !== null
        ) {
            state.backendStatus =
                normalizeStatus(
                    backendStatus,
                    state.backendStatus
                );
        }

        updateDashboard();

        publishState();
    }

    function handleMessage(event) {
        let payload;

        try {
            payload =
                typeof event.data ===
                "string"
                    ? JSON.parse(
                        event.data
                    )
                    : event.data;
        } catch (error) {
            state.invalidFrames += 1;

            state.lastError =
                serializeError(
                    error
                );

            calculatePacketQuality();

            updateDashboard();

            publish(
                "pratirup:can-message-error",
                state.lastError
            );

            return;
        }

        const type =
            normalizeStatus(
                payload?.type,
                ""
            );

        if (
            type === "STATUS"
        ) {
            processStatusMessage(
                payload
            );

            return;
        }

        if (
            type === "HEARTBEAT"
        ) {
            state.backendStatus =
                "CONNECTED";

            state.lastError =
                null;

            updateDashboard();

            publishState();

            return;
        }

        processTelemetry(
            payload
        );
    }

    function validateWebSocketURL(url) {
        if (
            typeof url !== "string" ||
            !url.trim()
        ) {
            return null;
        }

        try {
            const parsed =
                new URL(
                    url.trim(),
                    window.location.href
                );

            if (
                parsed.protocol !== "ws:" &&
                parsed.protocol !== "wss:"
            ) {
                return null;
            }

            return parsed.href;
        } catch (_) {
            return null;
        }
    }

    function connect(url = null) {
        if (
            url !== null &&
            url !== undefined
        ) {
            const validated =
                validateWebSocketURL(
                    url
                );

            if (!validated) {
                state.lastError = {
                    name:
                        "ConfigurationError",

                    message:
                        "WebSocket URL must use ws:// or wss://.",

                    at:
                        Date.now()
                };

                publish(
                    "pratirup:can-error",
                    state.lastError
                );

                return false;
            }

            state.websocketURL =
                validated;
        }

        if (
            state.websocket &&
            (
                state.websocket.readyState ===
                    WebSocket.OPEN ||
                state.websocket.readyState ===
                    WebSocket.CONNECTING
            )
        ) {
            return false;
        }

        state.manualDisconnect =
            false;

        state.connectionStatus =
            "CONNECTING";

        state.backendStatus =
            "CONNECTING";

        state.mode =
            "CAN_FADEC";

        state.lastError =
            null;

        setBridgeSourceMode(
            "live"
        );

        updateDashboard();

        publishState();

        try {
            const socket =
                new WebSocket(
                    state.websocketURL
                );

            state.websocket =
                socket;

            socket.addEventListener(
                "open",
                handleOpen
            );

            socket.addEventListener(
                "message",
                handleMessage
            );

            socket.addEventListener(
                "error",
                handleError
            );

            socket.addEventListener(
                "close",
                handleClose
            );

            return true;
        } catch (error) {
            state.connectionStatus =
                "ERROR";

            state.backendStatus =
                "ERROR";

            state.lastError =
                serializeError(
                    error
                );

            scheduleReconnect();

            updateDashboard();

            publishState();

            publish(
                "pratirup:can-error",
                state.lastError
            );

            return false;
        }
    }

    function handleOpen() {
        state.connectionStatus =
            "CONNECTED";

        state.backendStatus =
            "CONNECTED";

        state.connectedAt =
            Date.now();

        state.reconnectAttempts =
            0;

        state.lastError =
            null;

        setBridgeSourceMode(
            "live"
        );

        updateDashboard();

        publishState();

        publish(
            "pratirup:can-connected",
            getState()
        );
    }

    function handleError(error) {
        state.connectionStatus =
            "ERROR";

        state.lastError =
            serializeError(
                error
            );

        updateDashboard();

        publishState();

        publish(
            "pratirup:can-error",
            state.lastError
        );
    }

    function handleClose(event) {
        state.connectionStatus =
            "DISCONNECTED";

        state.backendStatus =
            "DISCONNECTED";

        state.websocket =
            null;

        updateDashboard();

        publishState();

        publish(
            "pratirup:can-disconnected",
            {
                code:
                    event?.code ??
                    null,

                reason:
                    event?.reason ??
                    null,

                clean:
                    event?.wasClean ??
                    null,

                version:
                    VERSION
            }
        );

        if (
            !state.manualDisconnect &&
            state.mode ===
                "CAN_FADEC"
        ) {
            scheduleReconnect();
        }
    }

    function calculateReconnectDelay() {
        const exponent =
            Math.max(
                0,
                state
                    .reconnectAttempts -
                1
            );

        const base =
            Math.min(
                CONFIG
                    .maximumReconnectDelayMs,

                CONFIG
                    .reconnectDelayMs *
                Math.pow(
                    CONFIG
                        .reconnectBackoffFactor,
                    exponent
                )
            );

        const jitter =
            base *
            CONFIG
                .reconnectJitterRatio *
            (
                Math.random() *
                2 -
                1
            );

        return Math.max(
            250,
            Math.round(
                base +
                jitter
            )
        );
    }

    function scheduleReconnect() {
        if (
            state.reconnectTimer ||
            state.manualDisconnect ||
            state.mode !==
                "CAN_FADEC"
        ) {
            return false;
        }

        if (
            state.reconnectAttempts >=
            CONFIG.maximumReconnectAttempts
        ) {
            state.connectionStatus =
                "RECONNECT_LIMIT";

            state.backendStatus =
                "DISCONNECTED";

            updateDashboard();

            publishState();

            publish(
                "pratirup:can-reconnect-exhausted",
                getState()
            );

            return false;
        }

        state.reconnectAttempts +=
            1;

        const delay =
            calculateReconnectDelay();

        state.reconnectTimer =
            window.setTimeout(
                () => {
                    state.reconnectTimer =
                        null;

                    connect();
                },
                delay
            );

        publish(
            "pratirup:can-reconnect-scheduled",
            {
                attempt:
                    state
                        .reconnectAttempts,

                delayMs:
                    delay,

                maximumAttempts:
                    CONFIG
                        .maximumReconnectAttempts,

                version:
                    VERSION
            }
        );

        return true;
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

    function disconnect(options = {}) {
        const switchToSimulation =
            options.switchToSimulation !==
            false;

        state.manualDisconnect =
            true;

        clearReconnectTimer();

        const socket =
            state.websocket;

        state.websocket =
            null;

        if (socket) {
            try {
                socket.removeEventListener(
                    "open",
                    handleOpen
                );

                socket.removeEventListener(
                    "message",
                    handleMessage
                );

                socket.removeEventListener(
                    "error",
                    handleError
                );

                socket.removeEventListener(
                    "close",
                    handleClose
                );

                socket.close(
                    1000,
                    "PRATIRUP CAN frontend disconnect"
                );
            } catch (_) {}
        }

        if (
            switchToSimulation
        ) {
            state.mode =
                "SIMULATION";

            setBridgeSourceMode(
                "auto"
            );
        }

        state.connectionStatus =
            "DISCONNECTED";

        state.backendStatus =
            "DISCONNECTED";

        state.canStatus =
            "NOT_CONNECTED";

        state.socketCanStatus =
            "NOT_CONNECTED";

        state.fadecStatus =
            "NOT_CONNECTED";

        state.sensorFreshnessMs =
            null;

        updateDashboard();

        publishState();

        return true;
    }

    function useSimulation() {
        disconnect({
            switchToSimulation:
                true
        });

        state.mode =
            "SIMULATION";

        setBridgeSourceMode(
            "auto"
        );

        publishState();

        updateDashboard();

        return true;
    }

    function useRealEngine(
        url = null
    ) {
        state.mode =
            "CAN_FADEC";

        state.manualDisconnect =
            false;

        setBridgeSourceMode(
            "live"
        );

        publishState();

        updateDashboard();

        return connect(
            url
        );
    }

    function updateFreshness() {
        if (
            !state.lastFrameReceiveTime
        ) {
            state.sensorFreshnessMs =
                null;

            updateDashboard();

            return;
        }

        state.sensorFreshnessMs =
            Date.now() -
            state.lastFrameReceiveTime;

        if (
            state.sensorFreshnessMs >
                CONFIG.telemetryTimeoutMs &&
            state.connectionStatus ===
                "CONNECTED"
        ) {
            state.canStatus =
                "STALE_DATA";
        }

        updateDashboard();
    }

    const freshnessTimer =
        window.setInterval(
            updateFreshness,
            500
        );

    function publishState() {
        publish(
            "pratirup:can-state",
            getState()
        );
    }

    function getState() {
        return {
            version:
                VERSION,

            mode:
                state.mode,

            connectionStatus:
                state.connectionStatus,

            backendStatus:
                state.backendStatus,

            canStatus:
                state.canStatus,

            socketCanStatus:
                state.socketCanStatus,

            fadecStatus:
                state.fadecStatus,

            websocketURL:
                state.websocketURL,

            connectedAt:
                state.connectedAt,

            reconnectAttempts:
                state.reconnectAttempts,

            frameCount:
                state.frameCount,

            validFrames:
                state.validFrames,

            invalidFrames:
                state.invalidFrames,

            droppedFrames:
                state.droppedFrames,

            outOfOrderFrames:
                state.outOfOrderFrames,

            sequenceResets:
                state.sequenceResets,

            frameRateHz:
                Number(
                    state
                        .frameRateHz
                        .toFixed(
                            1
                        )
                ),

            expectedFrameRateHz:
                CONFIG.expectedFrameRateHz,

            packetQuality:
                Number(
                    state
                        .packetQuality
                        .toFixed(
                            1
                        )
                ),

            sensorFreshnessMs:
                state.sensorFreshnessMs,

            lastFrameTimestamp:
                state.lastFrameTimestamp,

            canonicalFramesPublished:
                state
                    .canonicalFramesPublished,

            canonicalFramesSuppressed:
                state
                    .canonicalFramesSuppressed,

            replayOwnsCanonicalPipeline:
                replayOwnsCanonicalPipeline(),

            lastError:
                clone(
                    state.lastError
                ),

            lastFrame:
                state.lastFrame
                    ? clone(
                        state.lastFrame
                    )
                    : null
        };
    }

    function resetStatistics() {
        state.frameCount =
            0;

        state.validFrames =
            0;

        state.invalidFrames =
            0;

        state.droppedFrames =
            0;

        state.outOfOrderFrames =
            0;

        state.sequenceResets =
            0;

        state.previousSequence =
            null;

        state.frameRateHz =
            0;

        state.packetQuality =
            0;

        state.canonicalFramesPublished =
            0;

        state.canonicalFramesSuppressed =
            0;

        rateWindowFrames =
            0;

        rateWindowStart =
            performance.now();

        updateDashboard();

        publishState();

        return true;
    }

    function updateDashboard() {
        setText(
            "canStatus",
            state.canStatus
        );

        setText(
            "socketCanStatus",
            state.socketCanStatus
        );

        setText(
            "fadecStatus",
            state.fadecStatus
        );

        setText(
            "packetQuality",
            state.frameCount > 0
                ? `${state.packetQuality.toFixed(1)}%`
                : "--"
        );

        setText(
            "canFrameRate",
            state.frameRateHz > 0
                ? `${state.frameRateHz.toFixed(1)} Hz`
                : "--"
        );

        setText(
            "canDroppedFrames",
            String(
                state.droppedFrames
            )
        );

        setText(
            "sensorFreshness",
            state.sensorFreshnessMs !==
                null
                ? `${state.sensorFreshnessMs} ms`
                : "--"
        );

        setText(
            "sensorValidity",
            state.frameCount > 0
                ? `${(
                    state.validFrames /
                    state.frameCount *
                    100
                ).toFixed(1)}%`
                : "--"
        );

        setText(
            "twinSource",
            state.mode ===
                "CAN_FADEC"
                ? "CAN / FADEC INPUT"
                : "SIMULATION"
        );

        setText(
            "twinSourceDetail",
            state.mode ===
                "CAN_FADEC"
                ? (
                    replayOwnsCanonicalPipeline()
                        ? "CAN / FADEC • REPLAY HAS PRIORITY"
                        : "CAN / FADEC • LIVE"
                )
                : "SIMULATION"
        );

        setText(
            "canBackendStatus",
            state.backendStatus
        );

        setText(
            "canConnectionStatus",
            state.connectionStatus
        );
    }

    function bindDashboardButtons() {
        const connectButton =
            document.getElementById(
                "connectCanButton"
            );

        if (
            connectButton &&
            !connectButton
                .dataset
                .pratirupBound
        ) {
            connectButton
                .dataset
                .pratirupBound =
                "true";

            connectButton.addEventListener(
                "click",
                () => {
                    useRealEngine();
                }
            );
        }

        const disconnectButton =
            document.getElementById(
                "disconnectCanButton"
            );

        if (
            disconnectButton &&
            !disconnectButton
                .dataset
                .pratirupBound
        ) {
            disconnectButton
                .dataset
                .pratirupBound =
                "true";

            disconnectButton
                .addEventListener(
                    "click",
                    () => {
                        disconnect();
                    }
                );
        }

        const simulationButton =
            document.getElementById(
                "useSimulationButton"
            );

        if (
            simulationButton &&
            !simulationButton
                .dataset
                .pratirupBound
        ) {
            simulationButton
                .dataset
                .pratirupBound =
                "true";

            simulationButton
                .addEventListener(
                    "click",
                    () => {
                        useSimulation();
                    }
                );
        }
    }

    function setWebSocketURL(url) {
        const validated =
            validateWebSocketURL(
                url
            );

        if (!validated) {
            return false;
        }

        state.websocketURL =
            validated;

        return true;
    }

    function destroy() {
        disconnect({
            switchToSimulation:
                true
        });

        clearInterval(
            freshnessTimer
        );

        return true;
    }

    window.PratirupCANFADEC = {
        version:
            VERSION,

        connect,

        disconnect,

        useSimulation,

        useRealEngine,

        processTelemetry,

        processStatusMessage,

        getState,

        getLatestFrame() {
            return state.lastFrame
                ? clone(
                    state.lastFrame
                )
                : null;
        },

        getPacketQuality() {
            return state.packetQuality;
        },

        resetStatistics,

        setWebSocketURL,

        destroy,

        config:
            CONFIG
    };

    function initialize() {
        bindDashboardButtons();

        updateDashboard();

        publishState();

        console.info(
            `[PRATIRUP] CAN / FADEC Frontend Interface ${VERSION} ready.`
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
    } else {
        initialize();
    }
})();
