(function () {

    "use strict";

    const VERSION = "1.0.2";

    const SERVICE =
        "historical_replay_dashboard";

    const REPLAY_STATES = Object.freeze({

        EMPTY:
            "EMPTY",

        LOADED:
            "LOADED",

        PLAYING:
            "PLAYING",

        PAUSED:
            "PAUSED",

        COMPLETED:
            "COMPLETED",

        STOPPED:
            "STOPPED"

    });

    const VALID_SPEEDS =
        Object.freeze([

            0.5,

            1,

            2,

            5

        ]);

    const state = {

        initialized:
            false,

        backendAvailable:
            false,

        websocketConnected:
            false,

        replayActive:
            false,

        replayState:
            REPLAY_STATES.EMPTY,

        missionId:
            null,

        missionCode:
            null,

        frameCount:
            0,

        currentIndex:
            0,

        currentSequence:
            null,

        currentPhase:
            null,

        currentSpeed:
            1,

        currentProgress:
            0,

        originalSource:
            null,

        lastFrame:
            null,

        lastStatus:
            null,

        lastError:
            null,

        busy:
            false,

        seeking:
            false,

        statusPollTimer:
            null,

        statusPollMs:
            1000,

        replayFramesReceived:
            0,

        lastAppliedReplayIdentity:
            null,

        updatedAt:
            null

    };

    const dom = {};

    function cacheDOM() {

        dom.panel =
            document.getElementById(
                "historicalReplayPanel"
            );

        dom.missionInput =
            document.querySelector(
                "[data-replay-mission-id-input]"
            );

        dom.badge =
            document.querySelector(
                "[data-replay-ui-badge]"
            );

        dom.backendStatus =
            document.querySelector(
                "[data-replay-backend-status]"
            );

        dom.websocketStatus =
            document.querySelector(
                "[data-replay-websocket-status]"
            );

        dom.sourceMode =
            document.querySelector(
                "[data-replay-source-mode]"
            );

        dom.replayState =
            document.querySelector(
                "[data-replay-state]"
            );

        dom.missionCode =
            document.querySelector(
                "[data-replay-mission-code]"
            );

        dom.phase =
            document.querySelector(
                "[data-replay-phase]"
            );

        dom.sequence =
            document.querySelector(
                "[data-replay-sequence-display]"
            );

        dom.originalSource =
            document.querySelector(
                "[data-replay-original-source-display]"
            );

        dom.speedDisplay =
            document.querySelector(
                "[data-replay-speed-display]"
            );

        dom.progress =
            document.querySelector(
                "[data-replay-progress]"
            );

        dom.timeline =
            document.querySelector(
                "[data-replay-timeline]"
            );

        dom.frameIndex =
            document.querySelector(
                "[data-replay-frame-index]"
            );

        dom.frameCount =
            document.querySelector(
                "[data-replay-frame-count]"
            );

        dom.historicalTime =
            document.querySelector(
                "[data-replay-historical-time]"
            );

        dom.rpm =
            document.querySelector(
                "[data-replay-rpm]"
            );

        dom.power =
            document.querySelector(
                "[data-replay-power]"
            );

        dom.cht =
            document.querySelector(
                "[data-replay-cht]"
            );

        dom.egt =
            document.querySelector(
                "[data-replay-egt]"
            );

        dom.oilPressure =
            document.querySelector(
                "[data-replay-oil-pressure]"
            );

        dom.vibration =
            document.querySelector(
                "[data-replay-vibration]"
            );

        dom.altitude =
            document.querySelector(
                "[data-replay-altitude]"
            );

        dom.load =
            document.querySelector(
                "[data-replay-load]"
            );

        dom.isolationStatus =
            document.querySelector(
                "[data-replay-isolation-status]"
            );

        dom.databaseWrites =
            document.querySelector(
                "[data-replay-database-writes]"
            );

        dom.persistence =
            document.querySelector(
                "[data-replay-persistence]"
            );

        dom.liveIngestion =
            document.querySelector(
                "[data-replay-live-ingestion]"
            );

        dom.modelReprocessing =
            document.querySelector(
                "[data-replay-model-reprocessing]"
            );

        dom.actionButtons =
            Array.from(
                document.querySelectorAll(
                    "[data-replay-action]"
                )
            );

        dom.speedButtons =
            Array.from(
                document.querySelectorAll(
                    "[data-replay-speed]"
                )
            );

    }

    function getController() {

        return (
            window.PratirupMissionReplay ||
            null
        );

    }

    function getBridge() {

        return (
            window.PRATIRUP_BRIDGE ||
            null
        );

    }

    function getWebSocketBridge() {

        return (
            window.PRATIRUPTelemetryWebSocket ||
            null
        );

    }

    function isObject(
        value
    ) {

        return (
            value !== null &&
            typeof value ===
                "object" &&
            !Array.isArray(
                value
            )
        );

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

    function numberOrNull(
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

        return (
            Number.isFinite(
                numeric
            )
                ? numeric
                : null
        );

    }

    function clamp(
        value,
        min,
        max
    ) {

        return Math.min(
            max,
            Math.max(
                min,
                value
            )
        );

    }

    function normalizeState(
        value
    ) {

        if (
            value === null ||
            value === undefined
        ) {

            return REPLAY_STATES.EMPTY;

        }

        return String(
            value
        )
            .trim()
            .toUpperCase();

    }

    function normalizeSource(
        value
    ) {

        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {

            return null;

        }

        return String(
            value
        )
            .trim()
            .toUpperCase();

    }

    function formatNumber(
        value,
        decimals = 1
    ) {

        const numeric =
            numberOrNull(
                value
            );

        if (
            numeric === null
        ) {

            return "—";

        }

        return numeric.toFixed(
            decimals
        );

    }

    function formatInteger(
        value
    ) {

        const numeric =
            numberOrNull(
                value
            );

        if (
            numeric === null
        ) {

            return "—";

        }

        return String(
            Math.round(
                numeric
            )
        );

    }

    function setText(
        element,
        value
    ) {

        if (
            !element
        ) {

            return;

        }

        element.textContent =
            (
                value === null ||
                value === undefined ||
                value === ""
            )
                ? "—"
                : String(
                    value
                );

    }

    function setStatusClass(
        element,
        className
    ) {

        if (
            !element
        ) {

            return;

        }

        element.classList.remove(

            "is-good",

            "is-warning",

            "is-danger",

            "is-muted",

            "is-active",

            "is-selected"

        );

        if (
            className
        ) {

            element.classList.add(
                className
            );

        }

    }

    function getPath(
        object,
        path
    ) {

        if (
            !object ||
            !path
        ) {

            return undefined;

        }

        const parts =
            String(
                path
            )
                .split(
                    "."
                );

        let current =
            object;

        for (
            const part
            of parts
        ) {

            if (
                current === null ||
                current === undefined
            ) {

                return undefined;

            }

            current =
                current[
                    part
                ];

        }

        return current;

    }

    function firstPath(
        object,
        paths
    ) {

        for (
            const path
            of paths
        ) {

            const value =
                getPath(
                    object,
                    path
                );

            if (
                value !== undefined &&
                value !== null
            ) {

                return value;

            }

        }

        return null;

    }

    function averageAvailable(
        values
    ) {

        const available =
            values
                .map(
                    numberOrNull
                )
                .filter(
                    value =>
                        value !== null
                );

        if (
            available.length ===
                0
        ) {

            return null;

        }

        const total =
            available.reduce(
                (
                    sum,
                    value
                ) =>
                    sum + value,
                0
            );

        return (
            total /
            available.length
        );

    }

    function calculateProgress(
        currentIndex,
        frameCount
    ) {

        const index =
            numberOrNull(
                currentIndex
            );

        const count =
            numberOrNull(
                frameCount
            );

        if (
            index === null ||
            count === null ||
            count <= 0
        ) {

            return 0;

        }

        if (
            count ===
                1
        ) {

            return 100;

        }

        const safeIndex =
            clamp(
                index,
                0,
                count - 1
            );

        if (
            safeIndex >=
            count - 1
        ) {

            return 100;

        }

        return clamp(

            (
                safeIndex /
                (
                    count - 1
                )
            ) *

            100,

            0,

            100

        );

    }

    function unwrapTelemetry(
        candidate
    ) {

        if (
            !candidate
        ) {

            return null;

        }

        if (
            isObject(
                candidate.telemetry
            )
        ) {

            return candidate.telemetry;

        }

        if (
            isObject(
                candidate.data
            )
        ) {

            return candidate.data;

        }

        if (
            isObject(
                candidate.frame
            )
        ) {

            return candidate.frame;

        }

        return candidate;

    }

    function buildFrameModel(
        candidate
    ) {

        const telemetry =
            unwrapTelemetry(
                candidate
            );

        if (
            !isObject(
                telemetry
            )
        ) {

            return null;

        }

        const source =
            normalizeSource(
                firstPath(
                    telemetry,
                    [
                        "meta.source",
                        "source"
                    ]
                )
            );

        const replay =
            firstPath(
                telemetry,
                [
                    "meta.replay",
                    "replay"
                ]
            ) === true;

        const originalSource =
            normalizeSource(
                firstPath(
                    telemetry,
                    [
                        "meta.original_source",
                        "meta.originalSource",
                        "original_source",
                        "originalSource"
                    ]
                )
            );

        const sequence =
            firstPath(
                telemetry,
                [
                    "meta.sequence",
                    "sequence",
                    "sequence_number"
                ]
            );

        const missionId =
            firstPath(
                telemetry,
                [
                    "meta.mission_id",
                    "meta.missionId",
                    "mission.id",
                    "mission_id"
                ]
            );

        const phase =
            firstPath(
                telemetry,
                [
                    "mission.phase",
                    "mission_phase",
                    "phase"
                ]
            );

        const timestamp =
            firstPath(
                telemetry,
                [
                    "meta.timestamp",
                    "timestamp",
                    "recorded_at",
                    "created_at"
                ]
            );

        const rpm =
            firstPath(
                telemetry,
                [
                    "engine.rpm",
                    "rpm"
                ]
            );

        const power =
            firstPath(
                telemetry,
                [
                    "engine.power_kw",
                    "power_kw",
                    "performance.power_kw"
                ]
            );

        const load =
            firstPath(
                telemetry,
                [
                    "engine.load_pct",
                    "engine.engine_load_pct",
                    "engine.load_percent",
                    "load_pct",
                    "load_percent",
                    "engine_load_pct",
                    "mission.engine_load_pct"
                ]
            );

        const altitude =
            firstPath(
                telemetry,
                [
                    "environment.altitude_m",
                    "altitude_m",
                    "mission.altitude_m"
                ]
            );

        const oilPressure =
            firstPath(
                telemetry,
                [
                    "oil.pressure_kpa",
                    "oil_pressure_kpa",
                    "lubrication.pressure_kpa"
                ]
            );

        const vibration =
            firstPath(
                telemetry,
                [
                    "vibration.level",
                    "vibration.value",
                    "vibration.overall_g",
                    "vibration.rms_g",
                    "vibration",
                    "vibration_g",
                    "engine.vibration"
                ]
            );

        const cht =
            averageAvailable([

                firstPath(
                    telemetry,
                    [
                        "cht.cylinder1_c",
                        "cht.cylinder_1_c",
                        "cht.cyl1_c"
                    ]
                ),

                firstPath(
                    telemetry,
                    [
                        "cht.cylinder2_c",
                        "cht.cylinder_2_c",
                        "cht.cyl2_c"
                    ]
                ),

                firstPath(
                    telemetry,
                    [
                        "cht.cylinder3_c",
                        "cht.cylinder_3_c",
                        "cht.cyl3_c"
                    ]
                ),

                firstPath(
                    telemetry,
                    [
                        "cht.cylinder4_c",
                        "cht.cylinder_4_c",
                        "cht.cyl4_c"
                    ]
                )

            ]);

        const directCht =
            firstPath(
                telemetry,
                [
                    "cht.mean_c",
                    "cht.average_c",
                    "cht_c",
                    "engine.cht_c"
                ]
            );

        const egt =
            averageAvailable([

                firstPath(
                    telemetry,
                    [
                        "egt.cylinder1_c",
                        "egt.cylinder_1_c",
                        "egt.cyl1_c"
                    ]
                ),

                firstPath(
                    telemetry,
                    [
                        "egt.cylinder2_c",
                        "egt.cylinder_2_c",
                        "egt.cyl2_c"
                    ]
                ),

                firstPath(
                    telemetry,
                    [
                        "egt.cylinder3_c",
                        "egt.cylinder_3_c",
                        "egt.cyl3_c"
                    ]
                ),

                firstPath(
                    telemetry,
                    [
                        "egt.cylinder4_c",
                        "egt.cylinder_4_c",
                        "egt.cyl4_c"
                    ]
                )

            ]);

        const directEgt =
            firstPath(
                telemetry,
                [
                    "egt.mean_c",
                    "egt.average_c",
                    "egt_c",
                    "engine.egt_c"
                ]
            );

        return {

            telemetry,

            source,

            replay,

            originalSource,

            sequence,

            missionId,

            phase,

            timestamp,

            rpm:
                numberOrNull(
                    rpm
                ),

            power:
                numberOrNull(
                    power
                ),

            load:
                numberOrNull(
                    load
                ),

            altitude:
                numberOrNull(
                    altitude
                ),

            oilPressure:
                numberOrNull(
                    oilPressure
                ),

            vibration:
                numberOrNull(
                    vibration
                ),

            cht:
                numberOrNull(
                    firstDefined(
                        directCht,
                        cht
                    )
                ),

            egt:
                numberOrNull(
                    firstDefined(
                        directEgt,
                        egt
                    )
                )

        };

    }

    function buildReplayIdentity(
        candidate
    ) {

        const model =
            buildFrameModel(
                candidate
            );

        if (
            !model ||
            model.source !==
                "REPLAY" ||
            model.replay !==
                true
        ) {

            return null;

        }

        const missionId =
            firstDefined(

                model.missionId,

                state.missionId,

                ""

            );

        const sequence =
            firstDefined(

                model.sequence,

                ""

            );

        const timestamp =
            firstDefined(

                model.timestamp,

                ""

            );

        return [

            String(
                missionId
            ),

            String(
                sequence
            ),

            String(
                timestamp
            )

        ].join(
            "|"
        );

    }

    function unwrapStatus(
        result
    ) {

        if (
            !result
        ) {

            return null;

        }

        if (
            isObject(
                result.status
            )
        ) {

            return result.status;

        }

        if (
            isObject(
                result.data
            )
        ) {

            if (
                isObject(
                    result.data.status
                )
            ) {

                return result.data.status;

            }

            return result.data;

        }

        return result;

    }

    function applyStatus(
        result
    ) {

        const status =
            unwrapStatus(
                result
            );

        if (
            !isObject(
                status
            )
        ) {

            return false;

        }

        state.lastStatus =
            status;

        state.backendAvailable =
            true;

        const replayStatus =
            isObject(
                status.replay
            )
                ? status.replay
                : null;

        state.replayState =
            normalizeState(
                firstDefined(

                    status.state,

                    status.replay_state,

                    replayStatus?.state,

                    status.status,

                    state.replayState

                )
            );

        state.missionId =
            firstDefined(

                status.mission_id,

                status.missionId,

                status.mission?.id,

                replayStatus?.mission_id,

                replayStatus?.missionId,

                state.missionId

            );

        state.missionCode =
            firstDefined(

                status.mission_code,

                status.missionCode,

                status.mission?.code,

                replayStatus?.mission_code,

                replayStatus?.missionCode,

                state.missionCode

            );

        const frameCount =
            numberOrNull(
                firstDefined(

                    status.frame_count,

                    status.frameCount,

                    status.total_frames,

                    status.totalFrames,

                    replayStatus?.frame_count,

                    replayStatus?.frameCount,

                    replayStatus?.total_frames,

                    replayStatus?.totalFrames

                )
            );

        if (
            frameCount !==
                null
        ) {

            state.frameCount =
                Math.max(

                    0,

                    Math.round(
                        frameCount
                    )

                );

        }

        const currentIndex =
            numberOrNull(
                firstDefined(

                    status.current_index,

                    status.currentIndex,

                    status.index,

                    replayStatus?.current_index,

                    replayStatus?.currentIndex,

                    replayStatus?.index

                )
            );

        if (
            currentIndex !==
                null
        ) {

            state.currentIndex =
                Math.max(

                    0,

                    Math.round(
                        currentIndex
                    )

                );

        }

        state.currentSequence =
            firstDefined(

                status.current_sequence,

                status.currentSequence,

                status.sequence,

                replayStatus?.current_sequence,

                replayStatus?.currentSequence,

                replayStatus?.sequence,

                state.currentSequence

            );

        state.currentPhase =
            firstDefined(

                status.current_phase,

                status.currentPhase,

                status.phase,

                replayStatus?.current_phase,

                replayStatus?.currentPhase,

                replayStatus?.phase,

                state.currentPhase

            );

        const speed =
            numberOrNull(
                firstDefined(

                    status.speed,

                    status.playback_speed,

                    status.playbackSpeed,

                    replayStatus?.speed,

                    replayStatus?.playback_speed,

                    replayStatus?.playbackSpeed

                )
            );

        if (
            speed !==
                null
        ) {

            state.currentSpeed =
                speed;

        }

        state.originalSource =
            normalizeSource(
                firstDefined(

                    status.original_source,

                    status.originalSource,

                    replayStatus?.original_source,

                    replayStatus?.originalSource,

                    state.originalSource

                )
            );

        state.currentProgress =
            calculateProgress(

                state.currentIndex,

                state.frameCount

            );

        state.replayActive =
            (
                state.replayState ===
                    REPLAY_STATES.PLAYING ||

                state.replayState ===
                    REPLAY_STATES.PAUSED
            );

        state.updatedAt =
            new Date()
                .toISOString();

        return true;

    }

    function applyReplayFrame(
        candidate
    ) {

        const model =
            buildFrameModel(
                candidate
            );

        if (
            !model
        ) {

            return false;

        }

        if (
            model.source !==
                "REPLAY" ||

            model.replay !==
                true
        ) {

            return false;

        }

        const replayIdentity =
            buildReplayIdentity(
                candidate
            );

        if (
            replayIdentity &&

            replayIdentity ===
                state
                    .lastAppliedReplayIdentity
        ) {

            return false;

        }

        if (
            replayIdentity
        ) {

            state
                .lastAppliedReplayIdentity =
                replayIdentity;

        }

        state.lastFrame =
            model;

        state.replayFramesReceived +=
            1;

        if (
            model.missionId !==
                null
        ) {

            state.missionId =
                model.missionId;

        }

        if (
            model.sequence !==
                null
        ) {

            state.currentSequence =
                model.sequence;

        }

        if (
            model.phase !==
                null
        ) {

            state.currentPhase =
                model.phase;

        }

        if (
            model.originalSource !==
                null
        ) {

            state.originalSource =
                model.originalSource;

        }

        state.replayActive =
            true;

        state.updatedAt =
            new Date()
                .toISOString();

        render();

        return true;

    }

    function readBridgeStatus() {

        const bridge =
            getBridge();

        if (
            !bridge
        ) {

            return null;

        }

        try {

            if (
                typeof bridge
                    .getSourceArbitrationStatus ===
                "function"
            ) {

                const status =
                    bridge
                        .getSourceArbitrationStatus();

                if (
                    status
                ) {

                    state.replayActive =
                        status.replayActive ===
                        true;

                    return status;

                }

            }

            if (
                typeof bridge
                    .getSourceMode ===
                "function"
            ) {

                const mode =
                    bridge
                        .getSourceMode();

                state.replayActive =
                    String(
                        mode
                    )
                        .toLowerCase() ===
                    "replay";

                return {

                    mode,

                    replayActive:
                        state.replayActive

                };

            }

        }

        catch (
            error
        ) {

            console.warn(

                "[PRATIRUP D4] Unable to read source arbitration status.",

                error

            );

        }

        return null;

    }

    function readWebSocketStatus() {

        const websocket =
            getWebSocketBridge();

        if (
            !websocket ||
            typeof websocket.getStatus !==
                "function"
        ) {

            state.websocketConnected =
                false;

            return null;

        }

        try {

            const status =
                websocket
                    .getStatus();

            const connection =
                firstDefined(

                    status?.connection,

                    status?.state,

                    status?.connectionState,

                    status?.connection_state

                );

            state.websocketConnected =
                String(
                    connection
                )
                    .toUpperCase() ===
                "CONNECTED";

            return status;

        }

        catch (
            error
        ) {

            state.websocketConnected =
                false;

            return null;

        }

    }

    function renderConnections() {

        setText(

            dom.backendStatus,

            state.backendAvailable
                ? "ONLINE"
                : "OFFLINE"

        );

        setStatusClass(

            dom.backendStatus,

            state.backendAvailable
                ? "is-good"
                : "is-danger"

        );

        setText(

            dom.websocketStatus,

            state.websocketConnected
                ? "CONNECTED"
                : "DISCONNECTED"

        );

        setStatusClass(

            dom.websocketStatus,

            state.websocketConnected
                ? "is-good"
                : "is-danger"

        );

        const arbitration =
            readBridgeStatus();

        const sourceMode =
            firstDefined(

                arbitration?.mode,

                arbitration?.sourceMode,

                state.replayActive
                    ? "REPLAY"
                    : "AUTO"

            );

        setText(

            dom.sourceMode,

            String(
                sourceMode
            )
                .toUpperCase()

        );

        setStatusClass(

            dom.sourceMode,

            state.replayActive
                ? "is-active"
                : "is-muted"

        );

    }

    function renderReplayStatus() {

        setText(
            dom.replayState,
            state.replayState
        );

        setText(
            dom.missionCode,
            state.missionCode
        );

        setText(
            dom.phase,
            state.currentPhase
        );

        setText(
            dom.sequence,
            state.currentSequence
        );

        setText(
            dom.originalSource,
            state.originalSource
        );

        setText(

            dom.speedDisplay,

            formatNumber(
                state.currentSpeed,
                1
            )

        );

        if (
            dom.badge
        ) {

            if (
                state.replayActive
            ) {

                dom.badge.textContent =
                    "REPLAY";

                setStatusClass(
                    dom.badge,
                    "is-active"
                );

            }

            else {

                dom.badge.textContent =
                    state.replayState;

                setStatusClass(
                    dom.badge,
                    "is-muted"
                );

            }

        }

    }

    function renderTimeline() {

        const progress =
            calculateProgress(

                state.currentIndex,

                state.frameCount

            );

        state.currentProgress =
            progress;

        setText(

            dom.progress,

            progress.toFixed(
                1
            )

        );

        setText(

            dom.frameIndex,

            state.frameCount > 0
                ? state.currentIndex
                : 0

        );

        setText(

            dom.frameCount,

            state.frameCount

        );

        if (
            dom.timeline &&
            !state.seeking
        ) {

            dom.timeline.value =
                String(
                    progress
                );

        }

        if (
            dom.timeline
        ) {

            dom.timeline.disabled =
                (
                    state.busy ||
                    state.frameCount <=
                        0
                );

        }

        const timestamp =
            state.lastFrame
                ?.timestamp;

        if (
            timestamp
        ) {

            let formatted =
                timestamp;

            try {

                const date =
                    new Date(
                        timestamp
                    );

                if (
                    !Number.isNaN(
                        date.getTime()
                    )
                ) {

                    formatted =
                        date
                            .toLocaleString();

                }

            }

            catch (
                error
            ) {

            }

            setText(

                dom.historicalTime,

                formatted

            );

        }

        else {

            setText(

                dom.historicalTime,

                null

            );

        }

    }

    function renderTelemetry() {

        const frame =
            state.lastFrame;

        if (
            !frame
        ) {

            setText(
                dom.rpm,
                null
            );

            setText(
                dom.power,
                null
            );

            setText(
                dom.cht,
                null
            );

            setText(
                dom.egt,
                null
            );

            setText(
                dom.oilPressure,
                null
            );

            setText(
                dom.vibration,
                null
            );

            setText(
                dom.altitude,
                null
            );

            setText(
                dom.load,
                null
            );

            return;

        }

        setText(

            dom.rpm,

            frame.rpm ===
                null

                ? "—"

                : formatInteger(
                    frame.rpm
                )

        );

        setText(

            dom.power,

            frame.power ===
                null

                ? "—"

                : formatNumber(
                    frame.power,
                    1
                )

        );

        setText(

            dom.cht,

            frame.cht ===
                null

                ? "—"

                : formatNumber(
                    frame.cht,
                    1
                )

        );

        setText(

            dom.egt,

            frame.egt ===
                null

                ? "—"

                : formatNumber(
                    frame.egt,
                    1
                )

        );

        setText(

            dom.oilPressure,

            frame.oilPressure ===
                null

                ? "—"

                : formatNumber(
                    frame.oilPressure,
                    1
                )

        );

        setText(

            dom.vibration,

            frame.vibration ===
                null

                ? "—"

                : formatNumber(
                    frame.vibration,
                    3
                )

        );

        setText(

            dom.altitude,

            frame.altitude ===
                null

                ? "—"

                : formatNumber(
                    frame.altitude,
                    0
                )

        );

        setText(

            dom.load,

            frame.load ===
                null

                ? "—"

                : formatNumber(
                    frame.load,
                    1
                )

        );

    }

    function renderIsolation() {

        setText(
            dom.isolationStatus,
            "READ ONLY"
        );

        setStatusClass(
            dom.isolationStatus,
            "is-good"
        );

        setText(
            dom.databaseWrites,
            "DISABLED"
        );

        setStatusClass(
            dom.databaseWrites,
            "is-good"
        );

        setText(
            dom.persistence,
            "DISABLED"
        );

        setStatusClass(
            dom.persistence,
            "is-good"
        );

        setText(
            dom.liveIngestion,
            "ISOLATED"
        );

        setStatusClass(
            dom.liveIngestion,
            "is-good"
        );

        setText(
            dom.modelReprocessing,
            "DISABLED"
        );

        setStatusClass(
            dom.modelReprocessing,
            "is-good"
        );

    }

    function renderSpeedButtons() {

        for (
            const button
            of dom.speedButtons
        ) {

            const speed =
                numberOrNull(
                    button
                        .dataset
                        .replaySpeed
                );

            const active =
                (
                    speed !==
                        null &&

                    speed ===
                        state.currentSpeed
                );

            button.classList
                .toggle(
                    "is-selected",
                    active
                );

            button.disabled =
                state.busy;

        }

    }

    function renderActionButtons() {

        for (
            const button
            of dom.actionButtons
        ) {

            const action =
                String(
                    button
                        .dataset
                        .replayAction ||
                    ""
                )
                    .toLowerCase();

            let disabled =
                state.busy;

            switch (
                action
            ) {

                case "load":

                    break;

                case "play":

                    disabled =
                        disabled ||
                        ![
                            REPLAY_STATES.LOADED,
                            REPLAY_STATES.PAUSED,
                            REPLAY_STATES.STOPPED
                        ]
                        .includes(
                            state.replayState
                        );

                    break;

                case "pause":

                    disabled =
                        disabled ||
                        state.replayState !==
                            REPLAY_STATES.PLAYING;

                    break;

                case "resume":

                    disabled =
                        disabled ||
                        state.replayState !==
                            REPLAY_STATES.PAUSED;

                    break;

                case "reset":

                    disabled =
                        disabled ||
                        state.frameCount <=
                            0;

                    break;

                case "stop":

                    disabled =
                        disabled ||
                        ![
                            REPLAY_STATES.LOADED,
                            REPLAY_STATES.PLAYING,
                            REPLAY_STATES.PAUSED,
                            REPLAY_STATES.COMPLETED
                        ]
                        .includes(
                            state.replayState
                        );

                    break;

                default:

                    break;

            }

            button.disabled =
                disabled;

        }

    }

    function render() {

        readWebSocketStatus();

        renderConnections();

        renderReplayStatus();

        renderTimeline();

        renderTelemetry();

        renderIsolation();

        renderSpeedButtons();

        renderActionButtons();

    }

    function normalizeError(
        error
    ) {

        if (
            error === null ||
            error === undefined
        ) {

            return "Unknown error";

        }

        if (
            typeof error ===
            "string"
        ) {

            return error;

        }

        if (
            error instanceof
            Error
        ) {

            return (
                error.message ||
                String(
                    error
                )
            );

        }

        if (
            isObject(
                error
            )
        ) {

            const message =
                firstDefined(

                    error.message,

                    error.detail,

                    error.error,

                    error.reason

                );

            if (
                typeof message ===
                    "string"
            ) {

                return message;

            }

            try {

                return JSON.stringify(
                    error
                );

            }

            catch (
                serializationError
            ) {

                return String(
                    error
                );

            }

        }

        return String(
            error
        );

    }

    function setError(
        error
    ) {

        state.lastError =
            normalizeError(
                error
            );

        state.updatedAt =
            new Date()
                .toISOString();

        console.error(

            "[PRATIRUP D4]",

            state.lastError

        );

    }

    function clearError() {

        state.lastError =
            null;

    }

    async function refreshStatus() {

        const controller =
            getController();

        if (
            !controller ||
            typeof controller
                .getStatus !==
            "function"
        ) {

            state.backendAvailable =
                false;

            render();

            return {

                success:
                    false,

                reason:
                    "MISSION_REPLAY_CONTROLLER_UNAVAILABLE"

            };

        }

        try {

            const result =
                await controller
                    .getStatus();

            applyStatus(
                result
            );

            readWebSocketStatus();

            readBridgeStatus();

            render();

            return result;

        }

        catch (
            error
        ) {

            state.backendAvailable =
                false;

            setError(
                error
            );

            render();

            return {

                success:
                    false,

                error:
                    state.lastError

            };

        }

    }

    async function loadMission(
        missionId = null
    ) {

        const controller =
            getController();

        if (
            !controller ||
            typeof controller
                .loadMission !==
            "function"
        ) {

            setError(
                "Mission Replay controller is unavailable."
            );

            render();

            return {

                success:
                    false,

                error:
                    state.lastError

            };

        }

        const requestedMissionId =
            firstDefined(

                missionId,

                dom.missionInput
                    ?.value

            );

        if (
            requestedMissionId ===
                null ||

            String(
                requestedMissionId
            )
                .trim() ===
            ""
        ) {

            setError(
                "Historical mission ID is required."
            );

            render();

            return {

                success:
                    false,

                error:
                    state.lastError

            };

        }

        state.busy =
            true;

        clearError();

        state
            .lastAppliedReplayIdentity =
            null;

        state.replayFramesReceived =
            0;

        state.lastFrame =
            null;

        render();

        try {

            const result =
                await controller
                    .loadMission(
                        String(
                            requestedMissionId
                        )
                            .trim()
                    );

            applyStatus(
                result
            );

            state.missionId =
                firstDefined(

                    state.missionId,

                    String(
                        requestedMissionId
                    )
                        .trim()

                );

            state.currentIndex =
                0;

            state.currentProgress =
                calculateProgress(

                    state.currentIndex,

                    state.frameCount

                );

            state.busy =
                false;

            render();

            return result;

        }

        catch (
            error
        ) {

            state.busy =
                false;

            setError(
                error
            );

            render();

            return {

                success:
                    false,

                error:
                    state.lastError

            };

        }

    }

    async function callControllerAction(
        methodName,
        options = {}
    ) {

        const controller =
            getController();

        if (
            !controller ||
            typeof controller[
                methodName
            ] !==
            "function"
        ) {

            setError(
                `Mission Replay action unavailable: ${methodName}`
            );

            render();

            return {

                success:
                    false,

                error:
                    state.lastError

            };

        }

        state.busy =
            true;

        clearError();

        render();

        try {

            const result =
                await controller[
                    methodName
                ](
                    ...(
                        Array.isArray(
                            options.args
                        )
                            ? options.args
                            : []
                    )
                );

            applyStatus(
                result
            );

            if (
                options.releaseReplay ===
                true
            ) {

                state.replayActive =
                    false;

            }

            state.busy =
                false;

            render();

            return result;

        }

        catch (
            error
        ) {

            state.busy =
                false;

            setError(
                error
            );

            render();

            return {

                success:
                    false,

                error:
                    state.lastError

            };

        }

    }

    async function playReplay() {

        return callControllerAction(
            "play"
        );

    }

    async function pauseReplay() {

        return callControllerAction(
            "pause"
        );

    }

    async function resumeReplay() {

        return callControllerAction(
            "resume"
        );

    }

    async function stopReplay() {

        return callControllerAction(

            "stop",

            {

                releaseReplay:
                    true

            }

        );

    }

    async function resetReplay() {

        state
            .lastAppliedReplayIdentity =
            null;

        const result =
            await callControllerAction(
                "reset"
            );

        state.currentIndex =
            0;

        state.currentProgress =
            calculateProgress(

                state.currentIndex,

                state.frameCount

            );

        render();

        return result;

    }

    async function setReplaySpeed(
        requestedSpeed
    ) {

        const speed =
            numberOrNull(
                requestedSpeed
            );

        if (
            speed ===
                null ||

            !VALID_SPEEDS.includes(
                speed
            )
        ) {

            setError(
                `Unsupported replay speed: ${requestedSpeed}`
            );

            render();

            return {

                success:
                    false,

                error:
                    state.lastError

            };

        }

        const controller =
            getController();

        if (
            !controller
        ) {

            setError(
                "Mission Replay controller is unavailable."
            );

            render();

            return {

                success:
                    false,

                error:
                    state.lastError

            };

        }

        const method =
            (
                typeof controller
                    .setReplaySpeed ===
                "function"
            )

                ? "setReplaySpeed"

                : (
                    typeof controller
                        .setSpeed ===
                    "function"
                )

                    ? "setSpeed"

                    : (
                        typeof controller
                            .speed ===
                        "function"
                    )

                        ? "speed"

                        : null;

        if (
            !method
        ) {

            setError(
                "Mission Replay speed controller is unavailable."
            );

            render();

            return {

                success:
                    false,

                error:
                    state.lastError

            };

        }

        state.busy =
            true;

        clearError();

        render();

        try {

            const result =
                await controller[
                    method
                ](
                    speed
                );

            state.currentSpeed =
                speed;

            applyStatus(
                result
            );

            const authoritativeSpeed =
                numberOrNull(
                    firstDefined(

                        result?.speed,

                        result?.playback_speed,

                        result?.playbackSpeed,

                        result?.replay?.speed,

                        result?.replay
                            ?.playback_speed,

                        result?.replay
                            ?.playbackSpeed

                    )
                );

            if (
                authoritativeSpeed !==
                    null
            ) {

                state.currentSpeed =
                    authoritativeSpeed;

            }

            state.busy =
                false;

            state.updatedAt =
                new Date()
                    .toISOString();

            render();

            return result;

        }

        catch (
            error
        ) {

            state.busy =
                false;

            setError(
                error
            );

            render();

            return {

                success:
                    false,

                error:
                    state.lastError

            };

        }

    }

    async function seekPercent(
        requestedPercent
    ) {

        const percent =
            numberOrNull(
                requestedPercent
            );

        if (
            percent ===
                null
        ) {

            return {

                success:
                    false,

                error:
                    "Invalid seek percentage."

            };

        }

        const safePercent =
            clamp(

                percent,

                0,

                100

            );

        const controller =
            getController();

        if (
            !controller
        ) {

            setError(
                "Mission Replay controller is unavailable."
            );

            render();

            return {

                success:
                    false,

                error:
                    state.lastError

            };

        }

        const method =
            (
                typeof controller
                    .seekPercent ===
                "function"
            )

                ? "seekPercent"

                : (
                    typeof controller
                        .seekToPercent ===
                    "function"
                )

                    ? "seekToPercent"

                    : null;

        if (
            !method
        ) {

            setError(
                "Mission Replay percentage seek is unavailable."
            );

            render();

            return {

                success:
                    false,

                error:
                    state.lastError

            };

        }

        state.busy =
            true;

        clearError();

        render();

        try {

            const result =
                await controller[
                    method
                ](
                    safePercent
                );

            applyStatus(
                result
            );

            state.currentProgress =
                calculateProgress(

                    state.currentIndex,

                    state.frameCount

                );

            state.busy =
                false;

            render();

            return result;

        }

        catch (
            error
        ) {

            state.busy =
                false;

            setError(
                error
            );

            render();

            return {

                success:
                    false,

                error:
                    state.lastError

            };

        }

    }

    function stopStatusPolling() {

        if (
            state.statusPollTimer
        ) {

            clearInterval(
                state.statusPollTimer
            );

            state.statusPollTimer =
                null;

        }

    }

    function startStatusPolling() {

        stopStatusPolling();

        state.statusPollTimer =
            window.setInterval(

                function () {

                    refreshStatus();

                },

                state.statusPollMs

            );

    }

    function bindActionButtons() {

        for (
            const button
            of dom.actionButtons
        ) {

            button.addEventListener(

                "click",

                async function () {

                    const action =
                        String(

                            button
                                .dataset
                                .replayAction ||
                            ""

                        )
                            .toLowerCase();

                    switch (
                        action
                    ) {

                        case "load":

                            await loadMission();

                            break;

                        case "play":

                            await playReplay();

                            break;

                        case "pause":

                            await pauseReplay();

                            break;

                        case "resume":

                            await resumeReplay();

                            break;

                        case "reset":

                            await resetReplay();

                            break;

                        case "stop":

                            await stopReplay();

                            break;

                        default:

                            break;

                    }

                }

            );

        }

    }

    function bindSpeedButtons() {

        for (
            const button
            of dom.speedButtons
        ) {

            button.addEventListener(

                "click",

                async function () {

                    const speed =
                        numberOrNull(
                            button
                                .dataset
                                .replaySpeed
                        );

                    if (
                        speed ===
                            null
                    ) {

                        return;

                    }

                    await setReplaySpeed(
                        speed
                    );

                }

            );

        }

    }

    function bindTimeline() {

        if (
            !dom.timeline
        ) {

            return;

        }

        dom.timeline.addEventListener(

            "pointerdown",

            function () {

                state.seeking =
                    true;

            }

        );

        dom.timeline.addEventListener(

            "pointerup",

            async function () {

                const value =
                    numberOrNull(
                        dom.timeline
                            .value
                    );

                state.seeking =
                    false;

                if (
                    value ===
                        null
                ) {

                    render();

                    return;

                }

                await seekPercent(
                    value
                );

            }

        );

        dom.timeline.addEventListener(

            "change",

            async function () {

                const value =
                    numberOrNull(
                        dom.timeline
                            .value
                    );

                state.seeking =
                    false;

                if (
                    value ===
                        null
                ) {

                    render();

                    return;

                }

                await seekPercent(
                    value
                );

            }

        );

        dom.timeline.addEventListener(

            "input",

            function () {

                const value =
                    numberOrNull(
                        dom.timeline
                            .value
                    );

                if (
                    value ===
                        null
                ) {

                    return;

                }

                setText(

                    dom.progress,

                    clamp(
                        value,
                        0,
                        100
                    )
                        .toFixed(
                            1
                        )

                );

            }

        );

    }

    function handleReplayTelemetry(
        event
    ) {

        if (
            !event
        ) {

            return;

        }

        const detail =
            event.detail;

        applyReplayFrame(
            detail
        );

    }

    function handleReplayControllerFrame(
        event
    ) {

        if (
            !event
        ) {

            return;

        }

        applyReplayFrame(
            event.detail
        );

    }

    function handleCanonicalTelemetry(
        event
    ) {

        const candidate =
            event?.detail;

        if (
            !candidate
        ) {

            return;

        }

        const model =
            buildFrameModel(
                candidate
            );

        if (
            !model ||
            model.source !==
                "REPLAY" ||
            model.replay !==
                true
        ) {

            return;

        }

        applyReplayFrame(
            candidate
        );

    }

    function handleReplayState(
        event
    ) {

        const detail =
            event?.detail;

        if (
            detail
        ) {

            applyStatus(
                detail
            );

        }

        render();

    }

    function handleSourceMode(
        event
    ) {

        const detail =
            event?.detail;

        if (
            detail &&
            typeof detail ===
                "object"
        ) {

            const mode =
                normalizeSource(
                    firstDefined(
                        detail.mode,
                        detail.sourceMode
                    )
                );

            if (
                mode !==
                    null
            ) {

                state.replayActive =
                    mode ===
                    "REPLAY";

            }

        }

        render();

    }

    function handleReplayError(
        event
    ) {

        const detail =
            event?.detail;

        setError(
            detail ||
            "Historical replay error."
        );

        render();

    }

    function handleWebSocketStatus() {

        readWebSocketStatus();

        render();

    }

    function bindEvents() {

        window.addEventListener(

            "pratirup:replay-telemetry",

            handleReplayTelemetry

        );

        window.addEventListener(

            "pratirup:mission-replay-frame",

            handleReplayControllerFrame

        );

        window.addEventListener(

            "pratirup:telemetry",

            handleCanonicalTelemetry

        );

        window.addEventListener(

            "pratirup:mission-replay-state",

            handleReplayState

        );

        window.addEventListener(

            "pratirup:mission-replay-source-mode",

            handleSourceMode

        );

        window.addEventListener(

            "pratirup:mission-replay-error",

            handleReplayError

        );

        window.addEventListener(

            "pratirup:websocket-status",

            handleWebSocketStatus

        );

        window.addEventListener(

            "pratirup:telemetry-websocket-status",

            handleWebSocketStatus

        );

    }

    function unbindEvents() {

        window.removeEventListener(

            "pratirup:replay-telemetry",

            handleReplayTelemetry

        );

        window.removeEventListener(

            "pratirup:mission-replay-frame",

            handleReplayControllerFrame

        );

        window.removeEventListener(

            "pratirup:telemetry",

            handleCanonicalTelemetry

        );

        window.removeEventListener(

            "pratirup:mission-replay-state",

            handleReplayState

        );

        window.removeEventListener(

            "pratirup:mission-replay-source-mode",

            handleSourceMode

        );

        window.removeEventListener(

            "pratirup:mission-replay-error",

            handleReplayError

        );

        window.removeEventListener(

            "pratirup:websocket-status",

            handleWebSocketStatus

        );

        window.removeEventListener(

            "pratirup:telemetry-websocket-status",

            handleWebSocketStatus

        );

    }

    function getState() {

        return {

            service:
                SERVICE,

            version:
                VERSION,

            initialized:
                state.initialized,

            backendAvailable:
                state.backendAvailable,

            websocketConnected:
                state.websocketConnected,

            replayActive:
                state.replayActive,

            replayState:
                state.replayState,

            missionId:
                state.missionId,

            missionCode:
                state.missionCode,

            frameCount:
                state.frameCount,

            currentIndex:
                state.currentIndex,

            currentSequence:
                state.currentSequence,

            currentPhase:
                state.currentPhase,

            currentSpeed:
                state.currentSpeed,

            currentProgress:
                state.currentProgress,

            originalSource:
                state.originalSource,

            replayFramesReceived:
                state.replayFramesReceived,

            lastFrame:
                state.lastFrame
                    ? {
                        ...state.lastFrame
                    }
                    : null,

            lastStatus:
                state.lastStatus
                    ? {
                        ...state.lastStatus
                    }
                    : null,

            lastError:
                state.lastError,

            busy:
                state.busy,

            seeking:
                state.seeking,

            updatedAt:
                state.updatedAt

        };

    }

    async function initialize() {

        if (
            state.initialized
        ) {

            return getState();

        }

        cacheDOM();

        bindActionButtons();

        bindSpeedButtons();

        bindTimeline();

        bindEvents();

        state.initialized =
            true;

        clearError();

        readWebSocketStatus();

        readBridgeStatus();

        render();

        await refreshStatus();

        startStatusPolling();

        console.info(
            `[PRATIRUP] Historical Replay Dashboard ${VERSION} ready.`
        );

        window.dispatchEvent(

            new CustomEvent(
                "pratirup:historical-replay-dashboard-ready",
                {

                    detail: {

                        service:
                            SERVICE,

                        version:
                            VERSION

                    }

                }
            )

        );

        return getState();

    }

    function destroy() {

        stopStatusPolling();

        unbindEvents();

        state.initialized =
            false;

        return true;

    }

    window.PratirupHistoricalReplayDashboard = {

        version:
            VERSION,

        service:
            SERVICE,

        initialize,

        destroy,

        refreshStatus,

        loadMission,

        play:
            playReplay,

        pause:
            pauseReplay,

        resume:
            resumeReplay,

        stop:
            stopReplay,

        reset:
            resetReplay,

        setReplaySpeed,

        seekPercent,

        render,

        applyStatus,

        applyReplayFrame,

        getState

    };

    if (
        document.readyState ===
        "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            () => {
                initialize();
            },
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
