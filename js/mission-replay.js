(function () {
    "use strict";

    const VERSION = "2.0.0";

    const CONFIG = Object.freeze({
        apiBase: "http://127.0.0.1:8000/api/replay",
        defaultReplaySpeed: 1,
        allowedReplaySpeeds: Object.freeze([0.5, 1, 2, 5]),
        statusPollIntervalMs: 1000,
        requestTimeoutMs: 10000
    });

    const STATE = {
        initialized: false,
        loadedMissionId: null,
        status: null,
        frame: null,
        speed: CONFIG.defaultReplaySpeed,
        replayOwnership: false,
        pollTimer: null,
        requestInFlight: false,
        lastError: null,
        lastStatusAt: null,
        lastFrameAt: null,
        replayTelemetryFrames: 0
    };

    function clone(value) {
        if (value === null || value === undefined) return value;

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

    function finiteNumber(value, fallback = null) {
        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {
            return fallback;
        }

        const result = Number(value);

        return Number.isFinite(result)
            ? result
            : fallback;
    }

    function normalizeState(value) {
        return String(
            value ?? "EMPTY"
        )
            .trim()
            .toUpperCase();
    }

    function isReplayActiveState(value) {
        return [
            "LOADED",
            "PLAYING",
            "PAUSED",
            "COMPLETED",
            "STOPPED"
        ].includes(
            normalizeState(value)
        );
    }

    function isPlayingState(value) {
        return normalizeState(value) === "PLAYING";
    }

    function getBridge() {
        return window.PRATIRUP_BRIDGE || null;
    }

    function setReplayOwnership(enabled) {
        const bridge = getBridge();

        if (
            !bridge ||
            typeof bridge.setSourceMode !== "function"
        ) {
            STATE.replayOwnership = false;

            console.warn(
                "[PRATIRUP Replay] Telemetry Bridge v2.2+ source arbitration is unavailable."
            );

            return false;
        }

        try {
            bridge.setSourceMode(
                enabled
                    ? "replay"
                    : "auto"
            );

            STATE.replayOwnership =
                Boolean(enabled);

            publish(
                "pratirup:mission-replay-source-mode",
                {
                    mode:
                        enabled
                            ? "replay"
                            : "auto",

                    replayActive:
                        Boolean(enabled)
                }
            );

            return true;
        }

        catch (error) {
            STATE.lastError =
                serializeError(error);

            console.error(
                "[PRATIRUP Replay] Unable to change source ownership:",
                error
            );

            return false;
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

            status:
                finiteNumber(
                    error.status,
                    null
                ),

            at:
                Date.now()
        };
    }

    function publish(
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

    function unwrapPayload(payload) {
        if (
            !payload ||
            typeof payload !== "object"
        ) {
            return payload;
        }

        if (
            payload.data &&
            typeof payload.data === "object"
        ) {
            return payload.data;
        }

        if (
            payload.result &&
            typeof payload.result === "object"
        ) {
            return payload.result;
        }

        return payload;
    }

    function extractReplayState(payload) {
        const data =
            unwrapPayload(payload) || {};

        return normalizeState(
            data.state ??
            data.status ??
            data.replay_state ??
            data.replayStatus ??
            STATE.status?.state ??
            "EMPTY"
        );
    }

    function extractMissionId(payload) {
        const data =
            unwrapPayload(payload) || {};

        return (
            data.mission_id ??
            data.missionId ??
            data.mission?.id ??
            data.mission?.mission_id ??
            STATE.loadedMissionId ??
            null
        );
    }

    function extractSpeed(payload) {
        const data =
            unwrapPayload(payload) || {};

        return finiteNumber(
            data.speed ??
            data.replay_speed ??
            data.replaySpeed,
            STATE.speed
        );
    }

    function extractIndex(payload) {
        const data =
            unwrapPayload(payload) || {};

        return finiteNumber(
            data.index ??
            data.current_index ??
            data.replay_index ??
            data.frame_index,
            null
        );
    }

    function extractTotal(payload) {
        const data =
            unwrapPayload(payload) || {};

        return finiteNumber(
            data.total ??
            data.total_frames ??
            data.frame_count ??
            data.sample_count ??
            data.samples,
            null
        );
    }

    function calculateProgress(payload) {
        const data =
            unwrapPayload(payload) || {};

        const direct =
            finiteNumber(
                data.progress ??
                data.progress_pct ??
                data.progress_percent,
                null
            );

        if (direct !== null) {
            return Math.max(
                0,
                Math.min(
                    100,
                    direct
                )
            );
        }

        const index =
            extractIndex(data);

        const total =
            extractTotal(data);

        if (
            index !== null &&
            total !== null &&
            total > 1
        ) {
            return Math.max(
                0,
                Math.min(
                    100,
                    (
                        index /
                        (total - 1)
                    ) * 100
                )
            );
        }

        return 0;
    }

    async function request(
        path,
        options = {}
    ) {
        const controller =
            new AbortController();

        const timeout =
            setTimeout(
                () =>
                    controller.abort(),
                CONFIG.requestTimeoutMs
            );

        try {
            const response =
                await fetch(
                    `${CONFIG.apiBase}${path}`,
                    {
                        method:
                            options.method ||
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
                                options.headers ||
                                {}
                            )
                        },

                        body:
                            options.body !==
                            undefined
                                ? JSON.stringify(
                                    options.body
                                )
                                : undefined,

                        signal:
                            controller.signal,

                        cache:
                            "no-store"
                    }
                );

            const text =
                await response.text();

            let payload = null;

            if (text) {
                try {
                    payload =
                        JSON.parse(text);
                }

                catch (_) {
                    payload = {
                        message:
                            text
                    };
                }
            }

            if (!response.ok) {
                const error =
                    new Error(
                        payload?.detail ??
                        payload?.message ??
                        `Replay API request failed (${response.status}).`
                    );

                error.status =
                    response.status;

                error.payload =
                    payload;

                throw error;
            }

            STATE.lastError = null;

            return payload;
        }

        finally {
            clearTimeout(timeout);
        }
    }

    function applyStatus(
        payload,
        reason = "status"
    ) {
        const data =
            unwrapPayload(payload) || {};

        const state =
            extractReplayState(data);

        const missionId =
            extractMissionId(data);

        const speed =
            extractSpeed(data);

        STATE.status = {
            ...clone(data),

            state,

            mission_id:
                missionId,

            speed,

            progress:
                calculateProgress(data)
        };

        STATE.loadedMissionId =
            missionId;

        STATE.speed =
            speed;

        STATE.lastStatusAt =
            Date.now();

        publish(
            "pratirup:mission-replay-state",
            {
                ...clone(
                    STATE.status
                ),

                reason,

                replaying:
                    state ===
                    "PLAYING",

                paused:
                    state ===
                    "PAUSED",

                loaded:
                    Boolean(
                        missionId
                    ),

                replayOwnership:
                    STATE.replayOwnership,

                controllerVersion:
                    VERSION
            }
        );

        updateLegacyDOM();

        return clone(
            STATE.status
        );
    }

    function applyFrame(
        payload,
        reason = "frame"
    ) {
        const data =
            unwrapPayload(payload);

        if (
            !data ||
            typeof data !== "object"
        ) {
            return null;
        }

        STATE.frame =
            clone(data);

        STATE.lastFrameAt =
            Date.now();

        publish(
            "pratirup:mission-replay-frame",
            {
                ...clone(data),

                reason,

                controllerVersion:
                    VERSION
            }
        );

        updateLegacyDOM();

        return clone(
            STATE.frame
        );
    }

    async function getStatus(
        options = {}
    ) {
        try {
            const payload =
                await request(
                    "/status"
                );

            return applyStatus(
                payload,
                options.reason ||
                "poll"
            );
        }

        catch (error) {
            STATE.lastError =
                serializeError(error);

            if (!options.silent) {
                console.error(
                    "[PRATIRUP Replay] Status request failed:",
                    error
                );
            }

            publish(
                "pratirup:mission-replay-error",
                STATE.lastError
            );

            return null;
        }
    }

    async function getFrame(
        options = {}
    ) {
        try {
            const payload =
                await request(
                    "/frame"
                );

            return applyFrame(
                payload,
                options.reason ||
                "request"
            );
        }

        catch (error) {
            STATE.lastError =
                serializeError(error);

            if (!options.silent) {
                console.error(
                    "[PRATIRUP Replay] Frame request failed:",
                    error
                );
            }

            return null;
        }
    }

    async function command(
        path,
        {
            releaseOnSuccess = false,
            acquireBefore = true,
            reason = "command"
        } = {}
    ) {
        if (
            STATE.requestInFlight
        ) {
            console.warn(
                "[PRATIRUP Replay] A replay command is already in progress."
            );
        }

        STATE.requestInFlight =
            true;

        if (acquireBefore) {
            setReplayOwnership(
                true
            );
        }

        try {
            const payload =
                await request(
                    path,
                    {
                        method:
                            "POST"
                    }
                );

            applyStatus(
                payload,
                reason
            );

            if (
                releaseOnSuccess
            ) {
                setReplayOwnership(
                    false
                );
            }

            return clone(
                unwrapPayload(
                    payload
                )
            );
        }

        catch (error) {
            STATE.lastError =
                serializeError(error);

            publish(
                "pratirup:mission-replay-error",
                STATE.lastError
            );

            console.error(
                `[PRATIRUP Replay] ${reason} failed:`,
                error
            );

            throw error;
        }

        finally {
            STATE.requestInFlight =
                false;
        }
    }

    async function loadMission(
        missionId
    ) {
        const id =
            String(
                missionId ?? ""
            ).trim();

        if (!id) {
            throw new Error(
                "A historical mission ID is required."
            );
        }

        setReplayOwnership(
            true
        );

        try {
            const payload =
                await request(
                    `/load/${encodeURIComponent(id)}`,
                    {
                        method:
                            "POST"
                    }
                );

            STATE.loadedMissionId =
                extractMissionId(
                    payload
                ) || id;

            const status =
                applyStatus(
                    payload,
                    "load"
                );

            await getFrame({
                silent: true,
                reason: "load"
            });

            publish(
                "pratirup:mission-replay-loaded",
                {
                    missionId:
                        STATE.loadedMissionId,

                    status,

                    controllerVersion:
                        VERSION
                }
            );

            return status;
        }

        catch (error) {
            STATE.lastError =
                serializeError(error);

            setReplayOwnership(
                false
            );

            publish(
                "pratirup:mission-replay-error",
                STATE.lastError
            );

            console.error(
                "[PRATIRUP Replay] Mission load failed:",
                error
            );

            throw error;
        }
    }

    async function play() {
        return command(
            "/play",
            {
                reason:
                    "play"
            }
        );
    }

    async function pause() {
        return command(
            "/pause",
            {
                reason:
                    "pause"
            }
        );
    }

    async function resume() {
        return command(
            "/resume",
            {
                reason:
                    "resume"
            }
        );
    }

    async function stop(
        options = {}
    ) {
        const release =
            options.release !==
            false;

        const result =
            await command(
                "/stop",
                {
                    reason:
                        "stop",

                    releaseOnSuccess:
                        release,

                    acquireBefore:
                        !STATE.replayOwnership
                }
            );

        publish(
            "pratirup:mission-replay-stopped",
            {
                missionId:
                    STATE.loadedMissionId,

                controllerVersion:
                    VERSION
            }
        );

        return result;
    }

    async function reset() {
        const result =
            await command(
                "/reset",
                {
                    reason:
                        "reset"
                }
            );

        await getFrame({
            silent: true,
            reason: "reset"
        });

        return result;
    }

    async function seekToIndex(
        index
    ) {
        const target =
            finiteNumber(
                index,
                null
            );

        if (
            target === null ||
            target < 0
        ) {
            throw new Error(
                "Replay index must be a non-negative number."
            );
        }

        const result =
            await command(
                `/seek?index=${encodeURIComponent(
                    Math.round(target)
                )}`,
                {
                    reason:
                        "seek-index"
                }
            );

        await getFrame({
            silent: true,
            reason:
                "seek-index"
        });

        return result;
    }

    async function seekPercent(
        percent
    ) {
        const target =
            finiteNumber(
                percent,
                null
            );

        if (
            target === null
        ) {
            throw new Error(
                "Replay percentage must be numeric."
            );
        }

        const bounded =
            Math.max(
                0,
                Math.min(
                    100,
                    target
                )
            );

        const result =
            await command(
                `/seek-percent?percent=${encodeURIComponent(
                    bounded
                )}`,
                {
                    reason:
                        "seek-percent"
                }
            );

        await getFrame({
            silent: true,
            reason:
                "seek-percent"
        });

        return result;
    }

    function nearestAllowedSpeed(
        speed
    ) {
        const requested =
            finiteNumber(
                speed,
                CONFIG.defaultReplaySpeed
            );

        return CONFIG
            .allowedReplaySpeeds
            .reduce(
                (
                    nearest,
                    candidate
                ) => (
                    Math.abs(
                        candidate -
                        requested
                    ) <
                    Math.abs(
                        nearest -
                        requested
                    )
                        ? candidate
                        : nearest
                ),
                CONFIG.allowedReplaySpeeds[0]
            );
    }

    async function setReplaySpeed(
        speed
    ) {
        const selected =
            nearestAllowedSpeed(
                speed
            );

        const result =
            await command(
                `/speed?speed=${encodeURIComponent(
                    selected
                )}`,
                {
                    reason:
                        "speed"
                }
            );

        STATE.speed =
            extractSpeed(
                result
            ) ?? selected;

        updateLegacyDOM();

        return STATE.speed;
    }

    async function exitReplay(
        options = {}
    ) {
        const stopBackend =
            options.stopBackend !==
            false;

        try {
            if (
                stopBackend &&
                STATE.loadedMissionId
            ) {
                try {
                    await command(
                        "/stop",
                        {
                            reason:
                                "exit",

                            releaseOnSuccess:
                                false,

                            acquireBefore:
                                false
                        }
                    );
                }

                catch (_) {}
            }
        }

        finally {
            setReplayOwnership(
                false
            );

            publish(
                "pratirup:mission-replay-exit",
                {
                    missionId:
                        STATE.loadedMissionId,

                    controllerVersion:
                        VERSION
                }
            );
        }

        return true;
    }

    function onReplayTelemetry(
        event
    ) {
        const detail =
            event?.detail;

        if (
            !detail ||
            typeof detail !==
            "object"
        ) {
            return;
        }

        const telemetry =
            detail.telemetry ??
            detail.data ??
            detail;

        const meta =
            telemetry?.meta ??
            detail?.meta ??
            {};

        const source =
            String(
                meta.source ??
                telemetry?.source ??
                ""
            ).toUpperCase();

        const replay =
            meta.replay ??
            telemetry?.replay ??
            detail?.replay;

        if (
            source &&
            source !== "REPLAY"
        ) {
            return;
        }

        if (
            replay !== true &&
            source !== "REPLAY"
        ) {
            return;
        }

        STATE.replayTelemetryFrames +=
            1;

        STATE.lastFrameAt =
            Date.now();

        publish(
            "pratirup:mission-replay-frame-received",
            {
                missionId:
                    STATE.loadedMissionId,

                sequence:
                    meta.sequence ??
                    telemetry?.sequence ??
                    telemetry?.meta?.sequence ??
                    null,

                phase:
                    telemetry?.mission?.phase ??
                    telemetry?.meta?.phase ??
                    null,

                receivedAt:
                    STATE.lastFrameAt,

                count:
                    STATE.replayTelemetryFrames,

                controllerVersion:
                    VERSION
            }
        );

        updateLegacyDOM(
            telemetry
        );
    }

    function startStatusPolling() {
        stopStatusPolling();

        STATE.pollTimer =
            window.setInterval(
                () => {
                    getStatus({
                        silent: true,
                        reason: "poll"
                    });
                },
                CONFIG.statusPollIntervalMs
            );

        return true;
    }

    function stopStatusPolling() {
        if (
            STATE.pollTimer !==
            null
        ) {
            clearInterval(
                STATE.pollTimer
            );

            STATE.pollTimer =
                null;
        }
    }

    function setText(
        id,
        value
    ) {
        const element =
            document.getElementById(
                id
            );

        if (element) {
            element.textContent =
                value;
        }
    }

    function setValue(
        id,
        value
    ) {
        const element =
            document.getElementById(
                id
            );

        if (element) {
            element.value =
                value;
        }
    }

    function updateLegacyDOM(
        telemetry = null
    ) {
        const status =
            STATE.status || {};

        const state =
            normalizeState(
                status.state
            );

        const progress =
            finiteNumber(
                status.progress,
                0
            );

        const index =
            extractIndex(
                status
            );

        const total =
            extractTotal(
                status
            );

        setText(
            "replayRecordingStatus",
            "BACKEND"
        );

        setText(
            "replayMissionId",
            STATE.loadedMissionId ||
            "--"
        );

        setText(
            "replaySnapshotCount",
            total ?? "--"
        );

        setText(
            "replaySpeed",
            `${STATE.speed}x`
        );

        setValue(
            "replayTimeline",
            progress
        );

        if (
            index !== null &&
            total !== null
        ) {
            setText(
                "replayFrame",
                `${Math.min(
                    index + 1,
                    total
                )} / ${total}`
            );
        }

        else {
            setText(
                "replayFrame",
                "0 / 0"
            );
        }

        const elapsed =
            finiteNumber(
                status.elapsed_seconds,
                null
            ) ??
            finiteNumber(
                status.elapsed_s,
                null
            ) ??
            finiteNumber(
                telemetry
                    ?.mission
                    ?.elapsed_s,
                null
            );

        setText(
            "replayTime",
            elapsed !== null
                ? `${elapsed.toFixed(1)} s`
                : "--"
        );

        setText(
            "replayReadiness",

            telemetry
                ?.readiness
                ?.status ??

            telemetry
                ?.mission_intelligence
                ?.readiness ??

            telemetry
                ?.missionIntelligence
                ?.readiness ??

            (
                state === "EMPTY"
                    ? "--"
                    : state
            )
        );

        const rul =
            finiteNumber(
                telemetry
                    ?.rul
                    ?.overall_rul_hours,
                null
            ) ??
            finiteNumber(
                telemetry
                    ?.rul
                    ?.overallRULHours,
                null
            );

        setText(
            "replayRul",
            rul !== null
                ? `${rul.toFixed(1)} h`
                : "--"
        );

        const anomaly =
            finiteNumber(
                telemetry
                    ?.anomaly
                    ?.score,
                null
            ) ??
            finiteNumber(
                telemetry
                    ?.anomaly
                    ?.anomaly_score,
                null
            ) ??
            finiteNumber(
                telemetry
                    ?.anomaly
                    ?.anomalyScore,
                null
            );

        setText(
            "replayAnomaly",
            anomaly !== null
                ? `${anomaly.toFixed(1)}%`
                : "--"
        );
    }

    function getControllerState() {
        return {
            version:
                VERSION,

            initialized:
                STATE.initialized,

            loadedMissionId:
                STATE.loadedMissionId,

            status:
                clone(
                    STATE.status
                ),

            frame:
                clone(
                    STATE.frame
                ),

            speed:
                STATE.speed,

            replayOwnership:
                STATE.replayOwnership,

            requestInFlight:
                STATE.requestInFlight,

            replayTelemetryFrames:
                STATE.replayTelemetryFrames,

            lastStatusAt:
                STATE.lastStatusAt,

            lastFrameAt:
                STATE.lastFrameAt,

            lastError:
                clone(
                    STATE.lastError
                )
        };
    }

    function retiredRecordingMethod(
        name
    ) {
        return function () {
            console.warn(
                `[PRATIRUP Replay] ${name}() is retired in v${VERSION}. ` +
                "Historical missions are now backend/database authoritative."
            );

            return false;
        };
    }

    function retiredDataMethod(
        name,
        fallback = null
    ) {
        return function () {
            console.warn(
                `[PRATIRUP Replay] ${name}() is retired in v${VERSION}.`
            );

            return clone(
                fallback
            );
        };
    }

    async function initialize() {
        if (
            STATE.initialized
        ) {
            return getControllerState();
        }

        STATE.initialized =
            true;

        window.addEventListener(
            "pratirup:replay-telemetry",
            onReplayTelemetry
        );

        startStatusPolling();

        const initialStatus =
            await getStatus({
                silent: true,
                reason:
                    "initialize"
            });

        if (
            initialStatus &&
            isReplayActiveState(
                initialStatus.state
            )
        ) {
            if (
                [
                    "PLAYING",
                    "PAUSED"
                ].includes(
                    normalizeState(
                        initialStatus.state
                    )
                )
            ) {
                setReplayOwnership(
                    true
                );
            }
        }

        console.info(
            `[PRATIRUP] Backend Mission Replay Controller ${VERSION} ready.`
        );

        publish(
            "pratirup:mission-replay-controller-ready",
            {
                version:
                    VERSION,

                status:
                    clone(
                        initialStatus
                    )
            }
        );

        return getControllerState();
    }

    function destroy() {
        stopStatusPolling();

        window.removeEventListener(
            "pratirup:replay-telemetry",
            onReplayTelemetry
        );

        if (
            STATE.replayOwnership
        ) {
            setReplayOwnership(
                false
            );
        }

        STATE.initialized =
            false;

        return true;
    }

    window.PratirupMissionReplay = {
        version:
            VERSION,

        config:
            CONFIG,

        initialize,

        destroy,

        loadMission,

        load:
            loadMission,

        play,

        startReplay:
            play,

        pause,

        pauseReplay:
            pause,

        resume,

        resumeReplay:
            resume,

        stop,

        stopReplay:
            stop,

        reset,

        resetReplay:
            reset,

        seekToIndex,

        seekPercent,

        setReplaySpeed,

        getStatus,

        getFrame,

        getState:
            getControllerState,

        exitReplay,

        isReplaying() {
            return isPlayingState(
                STATE.status?.state
            );
        },

        isPaused() {
            return (
                normalizeState(
                    STATE.status?.state
                ) ===
                "PAUSED"
            );
        },

        getReplayIndex() {
            return extractIndex(
                STATE.status
            );
        },

        getReplaySpeed() {
            return STATE.speed;
        },

        getMission() {
            return STATE.loadedMissionId
                ? {
                    id:
                        STATE.loadedMissionId,

                    status:
                        clone(
                            STATE.status
                        )
                }
                : null;
        },

        getSnapshots:
            retiredDataMethod(
                "getSnapshots",
                []
            ),

        getSnapshot:
            retiredDataMethod(
                "getSnapshot",
                null
            ),

        getSummary:
            retiredDataMethod(
                "getSummary",
                null
            ),

        startRecording:
            retiredRecordingMethod(
                "startRecording"
            ),

        stopRecording:
            retiredRecordingMethod(
                "stopRecording"
            ),

        pauseRecording:
            retiredRecordingMethod(
                "pauseRecording"
            ),

        resumeRecording:
            retiredRecordingMethod(
                "resumeRecording"
            ),

        capture:
            retiredRecordingMethod(
                "capture"
            ),

        isRecording() {
            return false;
        },

        exportMission:
            retiredDataMethod(
                "exportMission",
                null
            ),

        downloadMission:
            retiredRecordingMethod(
                "downloadMission"
            ),

        importMission:
            retiredDataMethod(
                "importMission",
                null
            ),

        async clearMission() {
            try {
                await exitReplay({
                    stopBackend:
                        true
                });
            }

            finally {
                STATE.loadedMissionId =
                    null;

                STATE.status =
                    null;

                STATE.frame =
                    null;

                STATE.speed =
                    CONFIG.defaultReplaySpeed;

                updateLegacyDOM();
            }

            return true;
        }
    };

    if (
        document.readyState ===
        "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            () =>
                initialize(),
            {
                once:
                    true
            }
        );
    }

    else {
        initialize();
    }

})();
