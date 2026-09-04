"use strict";


(function () {

    const VERSION =
        "2.1.0";


    const CONFIG = {

        apiBaseURL:
            "http://localhost:8000",

        websocketURL:
            "ws://localhost:8000/ws",

        healthEndpoint:
            "/health",

        telemetryEndpoint:
            "/api/telemetry",

        missionEndpoint:
            "/api/missions",

        predictionEndpoint:
            "/api/predictions",

        reportEndpoint:
            "/api/reports",

        systemEndpoint:
            "/api/system",

        requestTimeoutMs:
            10000,

        reconnectDelayMs:
            3000,

        maximumReconnectAttempts:
            20,

        autoHealthCheck:
            true,

        autoConnectWebSocket:
            false,

        verbose:
            false

    };

    const state = {

        backend:
            "OFFLINE",

        websocket:
            "DISCONNECTED",

        database:
            "UNKNOWN",

        aiService:
            "UNKNOWN",

        telemetryService:
            "UNKNOWN",

        canService:
            "UNKNOWN",

        connectedAt:
            null,

        lastHealthCheck:
            null,

        lastMessage:
            null,

        lastTelemetrySent:
            null,

        lastTelemetryReceived:
            null,

        telemetrySent:
            0,

        telemetryAccepted:
            0,

        telemetryFailed:
            0,

        reconnectAttempts:
            0,

        reconnectTimer:
            null,

        websocketObject:
            null,

        manuallyDisconnected:
            false,

        lastError:
            null

    };

    function clone(value) {

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
                JSON.stringify(value)
            );

        }

        catch (_) {

            return value;

        }

    }


    function isObject(value) {

        return (

            value !== null &&

            typeof value ===
                "object" &&

            !Array.isArray(value)

        );

    }


    function isFiniteNumber(value) {

        return (

            typeof value ===
                "number" &&

            Number.isFinite(value)

        );

    }


    function toNullableNumber(value) {


        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {

            return null;

        }


        if (
            isFiniteNumber(value)
        ) {

            return value;

        }


        const number =
            Number(value);


        return Number.isFinite(number)
            ? number
            : null;

    }


    function normalizeBaseURL(url) {

        if (!url) {

            return "";

        }


        return String(url)
            .replace(/\/+$/, "");

    }


    function normalizeWebSocketURL(url) {

        if (!url) {

            return "";

        }


        return String(url)
            .replace(/\/+$/, "");

    }


    function dispatch(
        name,
        detail
    ) {

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


    function publishState() {

        dispatch(
            "pratirup:backend-state",
            getState()
        );

    }


 
    function setText(
        selector,
        value
    ) {

        const element =
            document.querySelector(
                selector
            );


        if (!element) {

            return;

        }


        element.textContent =
            value ?? "—";

    }


    function setDatasetStatus(
        selector,
        value
    ) {

        const element =
            document.querySelector(
                selector
            );


        if (!element) {

            return;

        }


        element.dataset.status =
            String(
                value ??
                "UNKNOWN"
            ).toLowerCase();

    }


    function updateDashboard() {

        setText(
            "[data-backend-status]",
            state.backend
        );


        setText(
            "[data-websocket-status]",
            state.websocket
        );


        setText(
            "[data-database-status]",
            state.database
        );


        setText(
            "[data-ai-status]",
            state.aiService
        );


        setText(
            "[data-telemetry-status]",
            state.telemetryService
        );


        setText(
            "[data-can-status]",
            state.canService
        );


        setDatasetStatus(
            "[data-backend-status]",
            state.backend
        );


        setDatasetStatus(
            "[data-websocket-status]",
            state.websocket
        );


        setDatasetStatus(
            "[data-database-status]",
            state.database
        );


        setDatasetStatus(
            "[data-ai-status]",
            state.aiService
        );


        setDatasetStatus(
            "[data-telemetry-status]",
            state.telemetryService
        );


        setDatasetStatus(
            "[data-can-status]",
            state.canService
        );

    }


    function buildURL(path) {

        if (!path) {

            return normalizeBaseURL(
                CONFIG.apiBaseURL
            );

        }


        if (
            /^https?:\/\//i.test(path)
        ) {

            return path;

        }


        const base =
            normalizeBaseURL(
                CONFIG.apiBaseURL
            );


        const cleanPath =
            String(path).startsWith("/")
                ? String(path)
                : `/${path}`;


        return (
            base +
            cleanPath
        );

    }

    async function request(
        path,
        options = {}
    ) {

        const url =
            buildURL(path);


        const controller =
            new AbortController();


        const timeout =

            window.setTimeout(
                () => {

                    controller.abort();

                },
                CONFIG.requestTimeoutMs
            );


        const requestOptions = {

            method:
                options.method ??
                "GET",

            headers: {

                "Accept":
                    "application/json",

                ...(
                    options.body !==
                    undefined
                        ? {
                            "Content-Type":
                                "application/json"
                        }
                        : {}
                ),

                ...(
                    options.headers ??
                    {}
                )

            },

            signal:
                controller.signal

        };


        if (
            options.body !==
            undefined
        ) {

            requestOptions.body =

                typeof options.body ===
                    "string"

                    ? options.body

                    : JSON.stringify(
                        options.body
                    );

        }


        try {

            const response =
                await fetch(
                    url,
                    requestOptions
                );


            let data =
                null;


            const contentType =

                response.headers
                    .get(
                        "content-type"
                    ) ?? "";


            if (
                contentType.includes(
                    "application/json"
                )
            ) {

                try {

                    data =
                        await response.json();

                }

                catch (_) {

                    data =
                        null;

                }

            }

            else {

                try {

                    const text =
                        await response.text();


                    data =
                        text || null;

                }

                catch (_) {

                    data =
                        null;

                }

            }


            if (
                !response.ok
            ) {

                const errorMessage =

                    isObject(data)
                        ? (
                            data.detail ??
                            data.error ??
                            data.message ??
                            `HTTP ${response.status}`
                        )
                        : (
                            data ??
                            `HTTP ${response.status}`
                        );


                return {

                    ok:
                        false,

                    status:
                        response.status,

                    data,

                    error:
                        String(
                            errorMessage
                        )

                };

            }


            return {

                ok:
                    true,

                status:
                    response.status,

                data,

                error:
                    null

            };

        }

        catch (error) {

            const message =

                error?.name ===
                "AbortError"

                    ? "Request timeout."

                    : (
                        error?.message ??
                        String(error)
                    );


            state.lastError =
                message;


            return {

                ok:
                    false,

                status:
                    0,

                data:
                    null,

                error:
                    message

            };

        }

        finally {

            window.clearTimeout(
                timeout
            );

        }

    }

    function get(
        path,
        options = {}
    ) {

        return request(
            path,
            {
                ...options,
                method:
                    "GET"
            }
        );

    }


    function post(
        path,
        body,
        options = {}
    ) {

        return request(
            path,
            {
                ...options,

                method:
                    "POST",

                body
            }
        );

    }


    function put(
        path,
        body,
        options = {}
    ) {

        return request(
            path,
            {
                ...options,

                method:
                    "PUT",

                body
            }
        );

    }


    function remove(
        path,
        options = {}
    ) {

        return request(
            path,
            {
                ...options,

                method:
                    "DELETE"
            }
        );

    }


    function normalizeTelemetry(
        telemetry
    ) {

        if (
            !isObject(telemetry)
        ) {

            return null;

        }

        const schema =
            window
                .PRATIRUP_TELEMETRY_SCHEMA;


        if (
            schema &&
            typeof schema.normalize ===
                "function"
        ) {

            try {

                return schema.normalize(
                    telemetry
                );

            }

            catch (error) {

                if (
                    CONFIG.verbose
                ) {

                    console.warn(
                        "[PRATIRUP Backend] Schema normalization failed.",
                        error
                    );

                }

            }

        }

        return clone(
            telemetry
        );

    }

    async function checkHealth() {

        const result =
            await get(
                CONFIG.healthEndpoint
            );


        state.lastHealthCheck =
            Date.now();


        if (
            !result.ok
        ) {

            state.backend =
                "OFFLINE";


            state.telemetryService =
                "UNKNOWN";


            state.lastError =
                result.error;


            publishState();
            updateDashboard();


            dispatch(
                "pratirup:backend-health",
                {
                    online:
                        false,

                    result:
                        clone(result)
                }
            );


            return result;

        }


        state.backend =
            "ONLINE";


        if (
            state.connectedAt ===
            null
        ) {

            state.connectedAt =
                Date.now();

        }


        const data =
            isObject(result.data)
                ? result.data
                : {};


        const services =
            isObject(data.services)
                ? data.services
                : {};


        state.database =

            services.database ??
            data.database ??
            state.database ??
            "UNKNOWN";


        state.aiService =

            services.ai ??
            data.ai ??
            state.aiService ??
            "UNKNOWN";


        state.telemetryService =

            services.telemetry ??
            data.telemetry ??
            state.telemetryService ??
            "UNKNOWN";


        state.canService =

            services.can ??
            data.can ??
            state.canService ??
            "UNKNOWN";


        state.lastError =
            null;


        publishState();
        updateDashboard();


        dispatch(
            "pratirup:backend-health",
            {
                online:
                    true,

                result:
                    clone(result)
            }
        );


        return result;

    }


    function connectWebSocket() {


        console.warn(
            "[PRATIRUP Backend] Legacy WebSocket disabled. " +
            "Live telemetry is owned by telemetry-websocket-bridge.js."
        );


        state.websocket =
            "DISCONNECTED";


        state.manuallyDisconnected =
            true;


        publishState();
        updateDashboard();


        return false;

    }

    function connectLegacyWebSocketInternal() {

        if (
            !CONFIG.autoConnectWebSocket
        ) {

            return false;

        }


        if (
            state.websocketObject &&
            (
                state.websocketObject.readyState ===
                    WebSocket.OPEN ||

                state.websocketObject.readyState ===
                    WebSocket.CONNECTING
            )
        ) {

            return true;

        }


        state.manuallyDisconnected =
            false;


        state.websocket =
            "CONNECTING";


        publishState();
        updateDashboard();


        let socket;


        try {

            socket =
                new WebSocket(
                    normalizeWebSocketURL(
                        CONFIG.websocketURL
                    )
                );

        }

        catch (error) {

            state.websocket =
                "ERROR";


            state.lastError =
                error?.message ??
                String(error);


            publishState();
            updateDashboard();


            return false;

        }


        state.websocketObject =
            socket;


        socket.addEventListener(
            "open",
            handleSocketOpen
        );


        socket.addEventListener(
            "message",
            handleSocketMessage
        );


        socket.addEventListener(
            "error",
            handleSocketError
        );


        socket.addEventListener(
            "close",
            handleSocketClose
        );


        return true;

    }

    function handleSocketOpen() {

        state.websocket =
            "CONNECTED";


        state.connectedAt =
            state.connectedAt ??
            Date.now();


        state.reconnectAttempts =
            0;


        state.lastError =
            null;


        publishState();
        updateDashboard();


        dispatch(
            "pratirup:backend-websocket-open",
            {
                timestamp:
                    Date.now(),

                legacy:
                    true
            }
        );

        sendSocketMessage(
            {
                type:
                    "hello",

                client:
                    "PRATIRUP_DASHBOARD",

                version:
                    VERSION,

                timestamp:
                    Date.now()
            }
        );

    }

    function handleSocketMessage(
        event
    ) {

        let payload;


        try {

            payload =
                JSON.parse(
                    event.data
                );

        }

        catch (_) {

            console.warn(
                "[PRATIRUP Backend] Non-JSON WebSocket message ignored."
            );


            return;

        }


        state.lastMessage =
            Date.now();


        routeMessage(
            payload
        );

    }


    function routeMessage(
        payload
    ) {

        if (!payload) {

            return;

        }


        switch (
            payload.type
        ) {

      
            case "telemetry":

                state.lastTelemetryReceived =
                    Date.now();


                dispatch(
                    "pratirup:backend-telemetry",
                    payload.data
                );


                break;

            case "prediction":

                dispatch(
                    "pratirup:backend-prediction",
                    payload.data
                );


                break;


            case "anomaly":

                dispatch(
                    "pratirup:backend-anomaly",
                    payload.data
                );


                break;


            /* ---------------------------------------------
               RUL
            --------------------------------------------- */

            case "rul":

                dispatch(
                    "pratirup:backend-rul",
                    payload.data
                );


                break;

            case "maintenance":

                dispatch(
                    "pratirup:backend-maintenance",
                    payload.data
                );


                break;

            case "can_status":

                state.canService =

                    payload.status ??
                    "UNKNOWN";


                publishState();
                updateDashboard();


                dispatch(
                    "pratirup:backend-can-status",
                    payload
                );


                break;

            case "system_status":

                if (
                    payload.backend
                ) {

                    state.backend =
                        payload.backend;

                }


                if (
                    payload.database
                ) {

                    state.database =
                        payload.database;

                }


                if (
                    payload.ai
                ) {

                    state.aiService =
                        payload.ai;

                }


                if (
                    payload.telemetry
                ) {

                    state.telemetryService =
                        payload.telemetry;

                }


                if (
                    payload.can
                ) {

                    state.canService =
                        payload.can;

                }


                publishState();
                updateDashboard();


                dispatch(
                    "pratirup:backend-system-status",
                    payload
                );


                break;


            case "ping":

                sendSocketMessage(
                    {
                        type:
                            "pong",

                        timestamp:
                            Date.now()
                    }
                );


                break;

            default:

                dispatch(
                    "pratirup:backend-message",
                    payload
                );


                break;

        }

    }

    function handleSocketError(
        event
    ) {

        state.websocket =
            "ERROR";


        state.lastError =
            "Legacy WebSocket error.";


        publishState();
        updateDashboard();


        dispatch(
            "pratirup:backend-websocket-error",
            {
                timestamp:
                    Date.now(),

                event
            }
        );

    }

    function handleSocketClose(
        event
    ) {

        state.websocketObject =
            null;


        state.websocket =
            "DISCONNECTED";


        publishState();
        updateDashboard();


        dispatch(
            "pratirup:backend-websocket-close",
            {
                timestamp:
                    Date.now(),

                code:
                    event?.code ??
                    null,

                reason:
                    event?.reason ??
                    null
            }
        );

        if (
            CONFIG.autoConnectWebSocket &&
            !state.manuallyDisconnected
        ) {

            scheduleReconnect();

        }

    }

    function scheduleReconnect() {

        if (
            !CONFIG.autoConnectWebSocket
        ) {

            return;

        }


        if (
            state.reconnectTimer
        ) {

            return;

        }


        if (
            state.reconnectAttempts >=
            CONFIG.maximumReconnectAttempts
        ) {

            console.warn(
                "[PRATIRUP Backend] Maximum legacy reconnect attempts reached."
            );


            return;

        }


        state.reconnectAttempts++;


        state.reconnectTimer =

            window.setTimeout(
                () => {

                    state.reconnectTimer =
                        null;


                    connectLegacyWebSocketInternal();

                },
                CONFIG.reconnectDelayMs
            );

    }

    function disconnectWebSocket() {

        state.manuallyDisconnected =
            true;


        if (
            state.reconnectTimer
        ) {

            window.clearTimeout(
                state.reconnectTimer
            );


            state.reconnectTimer =
                null;

        }


        if (
            state.websocketObject
        ) {

            try {

                state.websocketObject
                    .close();

            }

            catch (_) {

              

            }

        }


        state.websocketObject =
            null;


        state.websocket =
            "DISCONNECTED";


        publishState();
        updateDashboard();


        return true;

    }



    function sendSocketMessage(
        payload
    ) {

        const socket =
            state.websocketObject;


        if (
            !socket ||
            socket.readyState !==
                WebSocket.OPEN
        ) {

            return false;

        }


        try {

            socket.send(
                JSON.stringify(
                    payload
                )
            );


            return true;

        }

        catch (error) {

            console.warn(
                "[PRATIRUP Backend] Unable to send legacy WebSocket message.",
                error
            );


            return false;

        }

    }


  
    function getLatestTelemetry() {

        return get(
            `${CONFIG.telemetryEndpoint}/latest`
        );

    }


    async function sendTelemetry(
        telemetry
    ) {

        const normalized =
            normalizeTelemetry(
                telemetry
            );


        if (!normalized) {

            state.telemetryFailed++;


            return {

                ok:
                    false,

                status:
                    0,

                error:
                    "Invalid telemetry object."

            };

        }


        state.telemetrySent++;


        state.lastTelemetrySent =
            Date.now();


        const result =
            await post(
                CONFIG.telemetryEndpoint,
                normalized
            );


        if (
            result.ok
        ) {

            state.telemetryAccepted++;


            if (
                CONFIG.verbose
            ) {

                console.info(
                    "[PRATIRUP Backend] Telemetry accepted.",
                    normalized
                );

            }

        }

        else {

            state.telemetryFailed++;


            console.warn(
                "[PRATIRUP Backend] Telemetry rejected:",
                result.error
            );

        }


        publishState();


        return result;

    }



    function getTelemetryHistory(
        limit = 100
    ) {

        const safeLimit =

            Number.isFinite(
                Number(limit)
            )

                ? Math.max(
                    1,
                    Math.floor(
                        Number(limit)
                    )
                )

                : 100;


        return get(

            `${CONFIG.telemetryEndpoint}/history?limit=${encodeURIComponent(
                safeLimit
            )}`

        );

    }



    function getTelemetryStatus() {

        return get(
            `${CONFIG.telemetryEndpoint}/status`
        );

    }


    function getMissions() {

        return get(
            CONFIG.missionEndpoint
        );

    }


    function getMission(
        missionId
    ) {

        if (
            missionId === null ||
            missionId === undefined ||
            missionId === ""
        ) {

            return Promise.resolve(
                {
                    ok:
                        false,

                    status:
                        0,

                    data:
                        null,

                    error:
                        "Mission ID is required."
                }
            );

        }


        return get(

            `${CONFIG.missionEndpoint}/${encodeURIComponent(
                missionId
            )}`

        );

    }


    function saveMission(
        mission
    ) {

        if (
            !isObject(mission)
        ) {

            return Promise.resolve(
                {
                    ok:
                        false,

                    status:
                        0,

                    data:
                        null,

                    error:
                        "Mission object is required."
                }
            );

        }


        return post(
            CONFIG.missionEndpoint,
            mission
        );

    }


 
    function requestPrediction(
        telemetry
    ) {

        const normalized =
            normalizeTelemetry(
                telemetry
            );


        if (!normalized) {

            return Promise.resolve(
                {
                    ok:
                        false,

                    status:
                        0,

                    data:
                        null,

                    error:
                        "Invalid telemetry object."
                }
            );

        }


        return post(
            CONFIG.predictionEndpoint,
            normalized
        );

    }



    function saveReport(
        report
    ) {

        if (
            !isObject(report)
        ) {

            return Promise.resolve(
                {
                    ok:
                        false,

                    status:
                        0,

                    data:
                        null,

                    error:
                        "Report object is required."
                }
            );

        }


        return post(
            CONFIG.reportEndpoint,
            report
        );

    }


    function getReports() {

        return get(
            CONFIG.reportEndpoint
        );

    }



    function getSystemStatus() {

        return get(
            CONFIG.systemEndpoint
        );

    }


 
    function getState() {

        return {

            version:
                VERSION,

            backend:
                state.backend,

            websocket:
                state.websocket,

            database:
                state.database,

            aiService:
                state.aiService,

            telemetryService:
                state.telemetryService,

            canService:
                state.canService,

            connectedAt:
                state.connectedAt,

            lastHealthCheck:
                state.lastHealthCheck,

            lastMessage:
                state.lastMessage,

            lastTelemetrySent:
                state.lastTelemetrySent,

            lastTelemetryReceived:
                state.lastTelemetryReceived,

            telemetrySent:
                state.telemetrySent,

            telemetryAccepted:
                state.telemetryAccepted,

            telemetryFailed:
                state.telemetryFailed,

            reconnectAttempts:
                state.reconnectAttempts,

            lastError:
                state.lastError,


    
            websocketOwnership: {

                owner:
                    "telemetry-websocket-bridge.js",

                legacyClientEnabled:
                    false,

                automaticConnection:
                    false

            }

        };

    }


    function configure(
        options = {}
    ) {

        if (
            !isObject(options)
        ) {

            return {
                ...CONFIG
            };

        }


        if (
            options.apiBaseURL !==
            undefined
        ) {

            CONFIG.apiBaseURL =
                normalizeBaseURL(
                    options.apiBaseURL
                );

        }


        if (
            options.websocketURL !==
            undefined
        ) {

            CONFIG.websocketURL =
                normalizeWebSocketURL(
                    options.websocketURL
                );

        }


        if (
            options.requestTimeoutMs !==
            undefined
        ) {

            const timeout =
                Number(
                    options.requestTimeoutMs
                );


            if (
                Number.isFinite(timeout) &&
                timeout > 0
            ) {

                CONFIG.requestTimeoutMs =
                    timeout;

            }

        }


        if (
            options.reconnectDelayMs !==
            undefined
        ) {

            const delay =
                Number(
                    options.reconnectDelayMs
                );


            if (
                Number.isFinite(delay) &&
                delay >= 0
            ) {

                CONFIG.reconnectDelayMs =
                    delay;

            }

        }


        if (
            options.maximumReconnectAttempts !==
            undefined
        ) {

            const attempts =
                Number(
                    options.maximumReconnectAttempts
                );


            if (
                Number.isFinite(attempts) &&
                attempts >= 0
            ) {

                CONFIG.maximumReconnectAttempts =
                    Math.floor(
                        attempts
                    );

            }

        }


        if (
            options.autoHealthCheck !==
            undefined
        ) {

            CONFIG.autoHealthCheck =
                Boolean(
                    options.autoHealthCheck
                );

        }

        if (
            options.autoConnectWebSocket ===
            true
        ) {

            console.warn(
                "[PRATIRUP Backend] autoConnectWebSocket=true ignored. " +
                "WebSocket ownership belongs to telemetry-websocket-bridge.js."
            );

        }


        CONFIG.autoConnectWebSocket =
            false;


        if (
            options.verbose !==
            undefined
        ) {

            CONFIG.verbose =
                Boolean(
                    options.verbose
                );

        }


        return {
            ...CONFIG
        };

    }

    window.PratirupBackend = {

        version:
            VERSION,

        VERSION,

        request,

        get,

        post,

        put,

        delete:
            remove,

        checkHealth,

        connect:
            connectWebSocket,

        disconnect:
            disconnectWebSocket,

        send:
            sendSocketMessage,

        normalizeTelemetry,

        getLatestTelemetry,

        getTelemetryHistory,

        getTelemetryStatus,

        sendTelemetry,

        getMissions,

        getMission,

        saveMission,

        requestPrediction,

        saveReport,

        getReports,

        getSystemStatus,

        getState,

        configure,

        config:
            CONFIG

    };

    async function initialize() {

        updateDashboard();


        console.info(
            `[PRATIRUP] Backend Client ${VERSION} ready.`
        );


        console.info(
            "[PRATIRUP Backend] REST/API mode enabled."
        );


        console.info(
            "[PRATIRUP Backend] Live WebSocket ownership: telemetry-websocket-bridge.js"
        );

        disconnectWebSocket();


        let backendAvailable =
            true;


        if (
            CONFIG.autoHealthCheck
        ) {

            const health =
                await checkHealth();


            backendAvailable =
                Boolean(
                    health?.ok
                );


            if (
                backendAvailable
            ) {

                console.info(
                    "[PRATIRUP] FastAPI backend online."
                );

            }

            else {

                console.warn(
                    "[PRATIRUP] FastAPI backend unavailable."
                );

            }

        }


        dispatch(
            "pratirup:backend-client-ready",
            {
                version:
                    VERSION,

                backendAvailable,

                websocketOwner:
                    "telemetry-websocket-bridge.js",

                legacyWebSocket:
                    false,

                timestamp:
                    Date.now()
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
        `[PRATIRUP] Backend Client ${VERSION} loaded.`
    );

})();
