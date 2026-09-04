(() => {
    "use strict";

    const VERSION = "1.0.0";

    const CONFIG = {
        apiBase:
            "http://127.0.0.1:8000/api/missions",

        statusIntervalMs:
            1000,

        requestTimeoutMs:
            8000,

        supportedSpeeds:
            [0.5, 1, 2, 5]
    };

    const state = {
        connected: false,

        polling: false,

        pollTimer: null,

        lastStatus: null,

        lastError: null,

        requestCount: 0,

        successCount: 0,

        failureCount: 0,

        updatedAt: null
    };

    const EVENTS = {
        STATUS:
            "pratirup:mission-status",

        STATE:
            "pratirup:mission-state",

        PHASE:
            "pratirup:mission-phase",

        FAULT:
            "pratirup:mission-fault",

        ERROR:
            "pratirup:mission-error",

        CONNECTED:
            "pratirup:mission-connected",

        DISCONNECTED:
            "pratirup:mission-disconnected"
    };

    function emit(name, detail = {}) {
        window.dispatchEvent(
            new CustomEvent(
                name,
                {
                    detail
                }
            )
        );
    }

    function safeNumber(value) {
        if (
            value === null ||
            value === undefined ||
            typeof value === "boolean"
        ) {
            return null;
        }

        const number =
            Number(value);

        if (
            !Number.isFinite(number)
        ) {
            return null;
        }

        return number;
    }

    function clamp(
        value,
        minimum,
        maximum
    ) {
        return Math.min(
            maximum,
            Math.max(
                minimum,
                value
            )
        );
    }

    function normalizeFaultName(value) {
        return String(
            value || ""
        )
            .trim()
            .toUpperCase();
    }

    async function apiRequest(
        path = "",
        options = {}
    ) {
        state.requestCount++;

        const controller =
            new AbortController();

        const timeout =
            setTimeout(
                () => {
                    controller.abort();
                },
                CONFIG.requestTimeoutMs
            );

        try {
            const response =
                await fetch(
                    `${CONFIG.apiBase}${path}`,
                    {
                        ...options,

                        headers: {
                            "Content-Type":
                                "application/json",

                            ...(options.headers || {})
                        },

                        signal:
                            controller.signal
                    }
                );

            const text =
                await response.text();

            let body = null;

            if (text) {
                try {
                    body =
                        JSON.parse(text);
                } catch {
                    body = text;
                }
            }

            if (!response.ok) {
                throw new Error(
                    (
                        body &&
                        typeof body === "object"
                    )
                        ? JSON.stringify(
                            body.detail ??
                            body
                        )
                        : (
                            body ||
                            `HTTP ${response.status}`
                        )
                );
            }

            state.successCount++;

            state.lastError =
                null;

            return body;

        } catch (error) {
            state.failureCount++;

            state.lastError =
                error?.message ||
                String(error);

            emit(
                EVENTS.ERROR,
                {
                    message:
                        state.lastError,

                    path
                }
            );

            throw error;

        } finally {
            clearTimeout(
                timeout
            );
        }
    }

    async function getStatus() {
        const previous =
            state.lastStatus;

        try {
            const status =
                await apiRequest(
                    "/status"
                );

            state.lastStatus =
                status;

            state.updatedAt =
                new Date().toISOString();

            if (!state.connected) {
                state.connected =
                    true;

                emit(
                    EVENTS.CONNECTED,
                    {
                        status
                    }
                );
            }

            emit(
                EVENTS.STATUS,
                status
            );

            const previousPlayer =
                previous
                    ?.simulation_player;

            const player =
                status
                    ?.simulation_player;

            if (
                player &&
                player.state !==
                    previousPlayer?.state
            ) {
                emit(
                    EVENTS.STATE,
                    {
                        state:
                            player.state,

                        previousState:
                            previousPlayer
                                ?.state ??
                            null,

                        player
                    }
                );
            }

            if (
                player &&
                player.phase !==
                    previousPlayer?.phase
            ) {
                emit(
                    EVENTS.PHASE,
                    {
                        phase:
                            player.phase,

                        previousPhase:
                            previousPlayer
                                ?.phase ??
                            null,

                        player
                    }
                );
            }

            return status;

        } catch (error) {
            if (state.connected) {
                state.connected =
                    false;

                emit(
                    EVENTS.DISCONNECTED,
                    {
                        error:
                            error?.message ||
                            String(error)
                    }
                );
            }

            throw error;
        }
    }

    async function play() {
        return apiRequest(
            "/play",
            {
                method:
                    "POST"
            }
        );
    }

    async function pause() {
        return apiRequest(
            "/pause",
            {
                method:
                    "POST"
            }
        );
    }

    async function resume() {
        return apiRequest(
            "/resume",
            {
                method:
                    "POST"
            }
        );
    }

    async function stop() {
        return apiRequest(
            "/stop",
            {
                method:
                    "POST"
            }
        );
    }

    async function reset() {
        return apiRequest(
            "/reset",
            {
                method:
                    "POST"
            }
        );
    }

    async function restart() {
        return apiRequest(
            "/restart",
            {
                method:
                    "POST"
            }
        );
    }

    async function setSpeed(value) {
        const speed =
            safeNumber(value);

        if (
            speed === null ||
            !CONFIG
                .supportedSpeeds
                .includes(speed)
        ) {
            throw new Error(
                "Unsupported simulation speed. " +
                "Use 0.5, 1, 2 or 5."
            );
        }

        return apiRequest(
            "/speed",
            {
                method:
                    "POST",

                body:
                    JSON.stringify(
                        {
                            speed
                        }
                    )
            }
        );
    }

    async function seek(
        elapsedTimeSec
    ) {
        const elapsed =
            safeNumber(
                elapsedTimeSec
            );

        if (
            elapsed === null ||
            elapsed < 0
        ) {
            throw new Error(
                "Mission seek time must be >= 0."
            );
        }

        return apiRequest(
            "/seek",
            {
                method:
                    "POST",

                body:
                    JSON.stringify(
                        {
                            elapsed_time_sec:
                                elapsed
                        }
                    )
            }
        );
    }

    async function tick(
        deltaRealSec = 1
    ) {
        const delta =
            safeNumber(
                deltaRealSec
            );

        if (
            delta === null ||
            delta <= 0
        ) {
            throw new Error(
                "Tick delta must be > 0."
            );
        }

        return apiRequest(
            "/tick",
            {
                method:
                    "POST",

                body:
                    JSON.stringify(
                        {
                            delta_real_sec:
                                delta
                        }
                    )
            }
        );
    }

    async function getFaults() {
        return apiRequest(
            "/faults"
        );
    }

    async function injectFault(
        faultType,
        severity = 1,
        rampSec = 0
    ) {
        const fault =
            normalizeFaultName(
                faultType
            );

        const normalizedSeverity =
            safeNumber(
                severity
            );

        const normalizedRamp =
            safeNumber(
                rampSec
            );

        if (!fault) {
            throw new Error(
                "Fault type is required."
            );
        }

        if (
            normalizedSeverity ===
                null ||
            normalizedSeverity < 0 ||
            normalizedSeverity > 1
        ) {
            throw new Error(
                "Fault severity must be between 0 and 1."
            );
        }

        if (
            normalizedRamp ===
                null ||
            normalizedRamp < 0
        ) {
            throw new Error(
                "Fault ramp must be >= 0."
            );
        }

        const response =
            await apiRequest(
                "/faults",
                {
                    method:
                        "POST",

                    body:
                        JSON.stringify(
                            {
                                fault_type:
                                    fault,

                                severity:
                                    clamp(
                                        normalizedSeverity,
                                        0,
                                        1
                                    ),

                                ramp_sec:
                                    normalizedRamp
                            }
                        )
                }
            );

        emit(
            EVENTS.FAULT,
            {
                action:
                    "INJECTED",

                fault,

                severity:
                    normalizedSeverity,

                rampSec:
                    normalizedRamp,

                response
            }
        );

        return response;
    }

    async function clearFault(
        faultType
    ) {
        const fault =
            normalizeFaultName(
                faultType
            );

        if (!fault) {
            throw new Error(
                "Fault type is required."
            );
        }

        const response =
            await apiRequest(
                `/faults/${encodeURIComponent(
                    fault
                )}`,
                {
                    method:
                        "DELETE"
                }
            );

        emit(
            EVENTS.FAULT,
            {
                action:
                    "CLEARED",

                fault,

                response
            }
        );

        return response;
    }

    async function clearAllFaults() {
        const response =
            await apiRequest(
                "/faults",
                {
                    method:
                        "DELETE"
                }
            );

        emit(
            EVENTS.FAULT,
            {
                action:
                    "CLEARED_ALL",

                response
            }
        );

        return response;
    }

    async function poll() {
        if (!state.polling) {
            return;
        }

        try {
            await getStatus();
        } catch {
        }

        if (
            state.polling
        ) {
            state.pollTimer =
                setTimeout(
                    poll,
                    CONFIG
                        .statusIntervalMs
                );
        }
    }

    function startPolling(
        intervalMs =
            CONFIG.statusIntervalMs
    ) {
        const interval =
            safeNumber(
                intervalMs
            );

        if (
            interval !== null &&
            interval >= 250
        ) {
            CONFIG.statusIntervalMs =
                interval;
        }

        if (state.polling) {
            return;
        }

        state.polling =
            true;

        poll();
    }

    function stopPolling() {
        state.polling =
            false;

        if (
            state.pollTimer
        ) {
            clearTimeout(
                state.pollTimer
            );

            state.pollTimer =
                null;
        }
    }

    function bindButton(
        selector,
        handler
    ) {
        const element =
            document.querySelector(
                selector
            );

        if (!element) {
            return;
        }

        element.addEventListener(
            "click",
            async () => {
                element.disabled =
                    true;

                try {
                    await handler();

                    await getStatus();

                } catch (error) {
                    console.error(
                        "[PRATIRUP Mission Control]",
                        error
                    );

                } finally {
                    element.disabled =
                        false;
                }
            }
        );
    }

    function bindDefaultControls() {
        bindButton(
            "[data-mission-action='play']",
            play
        );

        bindButton(
            "[data-mission-action='pause']",
            pause
        );

        bindButton(
            "[data-mission-action='resume']",
            resume
        );

        bindButton(
            "[data-mission-action='stop']",
            stop
        );

        bindButton(
            "[data-mission-action='restart']",
            restart
        );

        bindButton(
            "[data-mission-action='reset']",
            reset
        );

        document
            .querySelectorAll(
                "[data-mission-speed]"
            )
            .forEach(
                element => {
                    element
                        .addEventListener(
                            "click",
                            async () => {
                                const speed =
                                    safeNumber(
                                        element.dataset
                                            .missionSpeed
                                    );

                                if (
                                    speed === null
                                ) {
                                    return;
                                }

                                try {
                                    await setSpeed(
                                        speed
                                    );

                                    await getStatus();

                                } catch (error) {
                                    console.error(
                                        "[PRATIRUP Speed]",
                                        error
                                    );
                                }
                            }
                        );
                }
            );

        const seekInput =
            document.querySelector(
                "[data-mission-seek]"
            );

        if (seekInput) {
            seekInput.addEventListener(
                "change",
                async () => {
                    try {
                        await seek(
                            seekInput.value
                        );

                        await getStatus();

                    } catch (error) {
                        console.error(
                            "[PRATIRUP Seek]",
                            error
                        );
                    }
                }
            );
        }

        const faultButton =
            document.querySelector(
                "[data-mission-inject-fault]"
            );

        if (faultButton) {
            faultButton.addEventListener(
                "click",
                async () => {
                    const faultSelect =
                        document.querySelector(
                            "[data-mission-fault-type]"
                        );

                    const severityInput =
                        document.querySelector(
                            "[data-mission-fault-severity]"
                        );

                    const rampInput =
                        document.querySelector(
                            "[data-mission-fault-ramp]"
                        );

                    try {
                        await injectFault(
                            faultSelect?.value,

                            severityInput
                                ?.value ??
                            1,

                            rampInput
                                ?.value ??
                            0
                        );

                        await getStatus();

                    } catch (error) {
                        console.error(
                            "[PRATIRUP Fault]",
                            error
                        );
                    }
                }
            );
        }

        bindButton(
            "[data-mission-clear-faults]",
            clearAllFaults
        );
    }

    function bindStatusDisplay() {
        window.addEventListener(
            EVENTS.STATUS,
            event => {
                const status =
                    event.detail;

                const player =
                    status
                        ?.simulation_player;

                if (!player) {
                    return;
                }

                const mappings = {
                    "[data-mission-state]":
                        player.state,

                    "[data-mission-phase]":
                        player.phase,

                    "[data-mission-speed-value]":
                        player.speed ??
                        player.scenario
                            ?.simulation_speed ??
                        1,

                    "[data-mission-elapsed]":
                        player.elapsed_time_sec,

                    "[data-mission-progress]":
                        (
                            safeNumber(
                                player.progress
                            ) ?? 0
                        ) * 100,

                    "[data-mission-ticks]":
                        player.ticks,

                    "[data-mission-successful-ticks]":
                        player.successful_ticks,

                    "[data-mission-failed-ticks]":
                        player.failed_ticks
                };

                Object.entries(
                    mappings
                ).forEach(
                    ([
                        selector,
                        value
                    ]) => {
                        const element =
                            document.querySelector(
                                selector
                            );

                        if (
                            element &&
                            value !==
                                undefined &&
                            value !== null
                        ) {
                            element.textContent =
                                String(value);
                        }
                    }
                );

                const progress =
                    document.querySelector(
                        "[data-mission-progress-bar]"
                    );

                if (progress) {
                    const value =
                        clamp(
                            (
                                safeNumber(
                                    player.progress
                                ) ?? 0
                            ) * 100,
                            0,
                            100
                        );

                    progress.style.width =
                        `${value}%`;

                    progress.setAttribute(
                        "aria-valuenow",
                        String(value)
                    );
                }

                const connection =
                    document.querySelector(
                        "[data-mission-connection]"
                    );

                if (connection) {
                    connection.textContent =
                        "CONNECTED";
                }
            }
        );

        window.addEventListener(
            EVENTS.DISCONNECTED,
            () => {
                const connection =
                    document.querySelector(
                        "[data-mission-connection]"
                    );

                if (connection) {
                    connection.textContent =
                        "OFFLINE";
                }
            }
        );
    }

    function getRuntimeState() {
        return {
            version:
                VERSION,

            connected:
                state.connected,

            polling:
                state.polling,

            requestCount:
                state.requestCount,

            successCount:
                state.successCount,

            failureCount:
                state.failureCount,

            lastError:
                state.lastError,

            updatedAt:
                state.updatedAt,

            lastStatus:
                state.lastStatus
        };
    }

    window.PRATIRUPMissionControl = {
        VERSION,

        EVENTS,

        CONFIG,

        getStatus,

        play,

        pause,

        resume,

        stop,

        reset,

        restart,

        setSpeed,

        seek,

        tick,

        getFaults,

        injectFault,

        clearFault,

        clearAllFaults,

        startPolling,

        stopPolling,

        bindDefaultControls,

        bindStatusDisplay,

        getRuntimeState
    };

    document.addEventListener(
        "DOMContentLoaded",
        () => {
            bindDefaultControls();

            bindStatusDisplay();

            startPolling();

            console.log(
                `[PRATIRUP] Mission Control v${VERSION} ready.`
            );
        }
    );

})();
