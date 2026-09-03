"use strict";
const SIMULATION_ADAPTER_VERSION =
    "2.0.0";

const SIMULATION_ADAPTER_MODES =
    Object.freeze({

        BACKEND_AUTHORITATIVE:
            "BACKEND_AUTHORITATIVE",

        LOCAL_DEMO:
            "LOCAL_DEMO"
    });

const UPDATE_RATE_HZ =
    10;


const UPDATE_INTERVAL_MS =
    1000 / UPDATE_RATE_HZ;


/*
 * CRITICAL:
 * ----------------------
 * Backend is the default authority.
 * This prevents the old browser simulator from starting
 * automatically and competing with backend mission,
 * replay, CAN or future FADEC telemetry.
 */

const DEFAULT_SOURCE_MODE =
    SIMULATION_ADAPTER_MODES
        .BACKEND_AUTHORITATIVE;

const adapterState = {

    initialized:
        false,

    sourceMode:
        DEFAULT_SOURCE_MODE,

    /*
     * running describes the LOCAL visual/simulation
     * engine state.
     * It does NOT mean that the adapter is publishing.
     */

    running:
        false,

    publishing:
        false,

    sequence:
        0,

    timer:
        null,

    rpm:
        2200,

    throttlePercent:
        null,

    loadPercent:
        null,

    operatingMode:
        "idle",

    missionId:
        null,

    missionPhase:
        null,

    missionStartTime:
        null,

    altitudeM:
        null,

    ambientTemperatureC:
        null,

    ambientPressurePa:
        null,

    airDensityKgM3:
        null,

    publishedFrames:
        0,

    blockedPublishes:
        0,

    lastPublishedAt:
        null,

    lastModeChangeAt:
        null
};


/* =========================================================
   GET REQUIRED MODULES
========================================================= */

function getSchema() {

    return window
        .PRATIRUP_TELEMETRY_SCHEMA;
}


function getBridge() {

    return window
        .PRATIRUP_BRIDGE;
}

function isBackendAuthoritative() {

    return (
        adapterState.sourceMode ===
        SIMULATION_ADAPTER_MODES
            .BACKEND_AUTHORITATIVE
    );
}


function isLocalDemoMode() {

    return (
        adapterState.sourceMode ===
        SIMULATION_ADAPTER_MODES
            .LOCAL_DEMO
    );
}

function clearPublishingTimer() {

    if (
        adapterState.timer !==
        null
    ) {

        window.clearInterval(
            adapterState.timer
        );

        adapterState.timer =
            null;
    }


    adapterState.publishing =
        false;
}

function initializeSimulationAdapter() {

    if (
        adapterState.initialized
    ) {

        return getAdapterState();
    }


    const schema =
        getSchema();


    const bridge =
        getBridge();


    if (!schema) {

        console.error(
            "[PRATIRUP SIM ADAPTER] Telemetry schema missing."
        );

        return null;
    }


    if (!bridge) {

        console.error(
            "[PRATIRUP SIM ADAPTER] Telemetry bridge missing."
        );

        return null;
    }


    /*
     * Preserve existing visual state if available.
     * This is LOCAL state only.
     * It is NOT automatically transmitted when operating
     * in BACKEND_AUTHORITATIVE mode.
     */

    const visualState =
        bridge.getState?.();


    if (visualState) {

        const visualRPM =
            Number(
                visualState.rpm
            );


        if (
            Number.isFinite(
                visualRPM
            )
        ) {

            adapterState.rpm =
                visualRPM;
        }


        adapterState.running =
            Boolean(
                visualState.running
            );
    }


    adapterState.initialized =
        true;

    clearPublishingTimer();


    console.log(
        `[PRATIRUP] Simulation Adapter ${SIMULATION_ADAPTER_VERSION} ready.`
    );


    console.log(
        `[PRATIRUP] Source ownership: ${adapterState.sourceMode}`
    );


    console.log(
        "[PRATIRUP] Local periodic telemetry publishing: DISABLED"
    );


    return getAdapterState();
}

function buildTelemetryFrame() {

    const schema =
        getSchema();


    if (!schema) {

        return null;
    }


    const frame =
        schema.create(
            schema.DATA_SOURCES
                .SIMULATION
        );


    frame.meta.sequence =
        adapterState.sequence;


    frame.meta.timestamp =
        Date.now();


    frame.meta.source =
        schema.DATA_SOURCES
            .SIMULATION;


    frame.meta.valid =
        true;

    frame.engine.rpm =
        adapterState.running
            ? adapterState.rpm
            : 0;


    frame.engine.throttlePercent =
        adapterState
            .throttlePercent;


    frame.engine.loadPercent =
        adapterState
            .loadPercent;


    frame.engine.operatingMode =
        adapterState.running
            ? adapterState.operatingMode
            : "idle";


    frame.environment.altitudeM =
        adapterState.altitudeM;


    frame.environment.ambientTemperatureC =
        adapterState
            .ambientTemperatureC;


    frame.environment.ambientPressurePa =
        adapterState
            .ambientPressurePa;


    frame.environment.airDensityKgM3 =
        adapterState
            .airDensityKgM3;

    frame.mission.missionId =
        adapterState.missionId;


    frame.mission.phase =
        adapterState.missionPhase;


    if (
        adapterState.missionStartTime !==
        null
    ) {

        frame.mission.elapsedTimeSec =

            (
                Date.now() -
                adapterState
                    .missionStartTime
            ) /
            1000;
    }

    else {

        frame.mission.elapsedTimeSec =
            null;
    }


    /*
     * All unsupported quantities remain exactly as created
     * by telemetry-schema.js.
     * Missing sensor values must remain null.
     */


    return frame;
}
function validateLocalFrame(
    frame
) {

    const schema =
        getSchema();


    if (
        !schema ||
        !frame
    ) {

        return {
            valid:
                false,

            errors: [
                "Telemetry schema or frame unavailable."
            ]
        };
    }


    if (
        typeof schema.validate !==
        "function"
    ) {

        return {
            valid:
                true,

            errors:
                []
        };
    }


    return schema.validate(
        frame
    );
}

function publishTelemetry(
    options = {}
) {

    if (
        !adapterState.initialized
    ) {

        return false;
    }


    /*
     * v2.0.0 SAFETY:
     * Backend authoritative mode refuses local publishing.
     * This is the permanent fix for the old competing
     * 2200-RPM browser stream.
     */

    if (
        !isLocalDemoMode()
    ) {

        adapterState.blockedPublishes++;


        if (
            options.silent !==
            true
        ) {

            console.warn(
                "[PRATIRUP SIM ADAPTER] Local telemetry publish blocked. Source authority is BACKEND_AUTHORITATIVE."
            );
        }


        return false;
    }


    const bridge =
        getBridge();


    if (
        !bridge ||
        typeof bridge.updateTelemetry !==
            "function"
    ) {

        console.error(
            "[PRATIRUP SIM ADAPTER] Telemetry bridge unavailable."
        );

        return false;
    }


    const frame =
        buildTelemetryFrame();


    if (!frame) {

        return false;
    }


    const validation =
        validateLocalFrame(
            frame
        );


    if (
        !validation.valid
    ) {

        console.error(
            "[PRATIRUP SIM ADAPTER] Invalid local telemetry frame:",
            validation.errors
        );

        return false;
    }


    /*
     * Increment only when an actual local frame is about
     * to be published.
     */

    adapterState.sequence++;


    bridge.updateTelemetry(
        frame
    );


    adapterState.publishedFrames++;


    adapterState.lastPublishedAt =
        Date.now();


    return true;
}


function startPublishing() {

    if (
        !adapterState.initialized
    ) {

        return false;
    }


    if (
        !isLocalDemoMode()
    ) {

        clearPublishingTimer();


        console.warn(
            "[PRATIRUP SIM ADAPTER] start() blocked because backend is authoritative. Use enableLocalDemo() explicitly for browser telemetry."
        );


        return false;
    }


    if (
        adapterState.timer !==
        null
    ) {

        adapterState.publishing =
            true;

        return true;
    }


    /*
     * Publish immediately.
     */

    publishTelemetry({
        silent:
            true
    });


    adapterState.timer =
        window.setInterval(
            function () {

                publishTelemetry({
                    silent:
                        true
                });

            },
            UPDATE_INTERVAL_MS
        );


    adapterState.publishing =
        true;


    console.log(
        `[PRATIRUP SIM ADAPTER] LOCAL_DEMO publishing started at ${UPDATE_RATE_HZ} Hz.`
    );


    return true;
}

function stopPublishing() {

    clearPublishingTimer();


    console.log(
        "[PRATIRUP SIM ADAPTER] Local telemetry publishing stopped."
    );


    return true;
}
function setSourceMode(
    mode
) {

    if (
        !Object.values(
            SIMULATION_ADAPTER_MODES
        ).includes(
            mode
        )
    ) {

        console.warn(
            "[PRATIRUP SIM ADAPTER] Invalid source mode:",
            mode
        );


        return false;
    }


    /*
     * Moving to backend authority MUST immediately stop
     * local publishing before changing ownership.
     */

    if (
        mode ===
        SIMULATION_ADAPTER_MODES
            .BACKEND_AUTHORITATIVE
    ) {

        clearPublishingTimer();
    }


    adapterState.sourceMode =
        mode;


    adapterState.lastModeChangeAt =
        Date.now();


    window.dispatchEvent(

        new CustomEvent(
            "pratirup:simulation-source-mode",
            {
                detail: {

                    mode:
                        adapterState
                            .sourceMode,

                    backendAuthoritative:
                        isBackendAuthoritative(),

                    localDemo:
                        isLocalDemoMode(),

                    timestamp:
                        Date.now()
                }
            }
        )
    );


    console.log(
        `[PRATIRUP SIM ADAPTER] Source mode: ${adapterState.sourceMode}`
    );


    return true;
}

function enableBackendAuthority() {

    setSourceMode(
        SIMULATION_ADAPTER_MODES
            .BACKEND_AUTHORITATIVE
    );


    clearPublishingTimer();


    return getAdapterState();
}

function enableLocalDemo(
    autoStart = true
) {

    setSourceMode(
        SIMULATION_ADAPTER_MODES
            .LOCAL_DEMO
    );


    if (autoStart) {

        startPublishing();
    }


    return getAdapterState();
}

window.addEventListener(
    "pratirup:run",
    event => {

        adapterState.running =
            Boolean(
                event.detail?.value
            );
    }
);

window.addEventListener(
    "pratirup:rpm",
    event => {

        const rpm =
            Number(
                event.detail?.value
            );


        if (
            !Number.isFinite(
                rpm
            )
        ) {

            return;
        }


        adapterState.rpm =
            SAFE_CLAMP(
                rpm,
                0,
                4500
            );
    }
);

function SAFE_CLAMP(
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

function setOperatingMode(
    mode
) {

    const schema =
        getSchema();


    if (!schema) {

        return false;
    }


    const validModes =
        Object.values(
            schema.OPERATING_MODES
        );


    if (
        !validModes.includes(
            mode
        )
    ) {

        console.warn(
            "[PRATIRUP SIM ADAPTER] Invalid operating mode:",
            mode
        );


        return false;
    }


    adapterState.operatingMode =
        mode;


    return true;
}

function setRPM(
    value
) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {

        return false;
    }


    const rpm =
        Number(
            value
        );


    if (
        !Number.isFinite(
            rpm
        )
    ) {

        return false;
    }


    adapterState.rpm =
        SAFE_CLAMP(
            rpm,
            0,
            4500
        );


    return true;
}

function setRunning(
    value
) {

    adapterState.running =
        Boolean(
            value
        );


    return true;
}

function setThrottle(
    value
) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {

        adapterState.throttlePercent =
            null;


        return true;
    }


    const throttle =
        Number(
            value
        );


    if (
        !Number.isFinite(
            throttle
        )
    ) {

        return false;
    }


    adapterState.throttlePercent =
        SAFE_CLAMP(
            throttle,
            0,
            100
        );


    return true;
}

function setLoad(
    value
) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {

        adapterState.loadPercent =
            null;


        return true;
    }


    const load =
        Number(
            value
        );


    if (
        !Number.isFinite(
            load
        )
    ) {

        return false;
    }


    adapterState.loadPercent =
        SAFE_CLAMP(
            load,
            0,
            100
        );


    return true;
}

function setEnvironment(
    environment = {}
) {

    if (
        environment.altitudeM !==
        undefined
    ) {

        adapterState.altitudeM =
            safeNullableNumber(
                environment.altitudeM
            );
    }


    if (
        environment.ambientTemperatureC !==
        undefined
    ) {

        adapterState
            .ambientTemperatureC =
            safeNullableNumber(
                environment
                    .ambientTemperatureC
            );
    }


    if (
        environment.ambientPressurePa !==
        undefined
    ) {

        adapterState
            .ambientPressurePa =
            safeNullableNumber(
                environment
                    .ambientPressurePa
            );
    }


    if (
        environment.airDensityKgM3 !==
        undefined
    ) {

        adapterState
            .airDensityKgM3 =
            safeNullableNumber(
                environment
                    .airDensityKgM3
            );
    }


    return true;
}

function safeNullableNumber(
    value
) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {

        return null;
    }


    const number =
        Number(
            value
        );


    return Number.isFinite(
        number
    )
        ? number
        : null;
}

function startMission(
    missionId = null,
    phase = "preflight"
) {

    adapterState.missionId =
        missionId;


    adapterState.missionPhase =
        phase;


    adapterState.missionStartTime =
        Date.now();


    console.log(
        "[PRATIRUP SIM ADAPTER] Local mission context started:",
        missionId
    );


    return true;
}

function setMissionPhase(
    phase
) {

    adapterState.missionPhase =
        phase;


    return true;
}

function endMission() {

    adapterState.missionPhase =
        "completed";


    /*
     * Only LOCAL_DEMO is allowed to publish a final frame.
     */

    if (
        isLocalDemoMode()
    ) {

        publishTelemetry({
            silent:
                true
        });
    }


    adapterState.missionStartTime =
        null;


    return true;
}

function resetAdapter() {

    /*
     * Reset must NEVER generate telemetry while backend
     * authority is active.
     */

    clearPublishingTimer();


    adapterState.running =
        false;


    adapterState.sequence =
        0;


    adapterState.rpm =
        2200;


    adapterState.throttlePercent =
        null;


    adapterState.loadPercent =
        null;


    adapterState.operatingMode =
        "idle";


    adapterState.missionId =
        null;


    adapterState.missionPhase =
        null;


    adapterState.missionStartTime =
        null;


    adapterState.altitudeM =
        null;


    adapterState.ambientTemperatureC =
        null;


    adapterState.ambientPressurePa =
        null;


    adapterState.airDensityKgM3 =
        null;


    adapterState.publishedFrames =
        0;


    adapterState.blockedPublishes =
        0;


    adapterState.lastPublishedAt =
        null;


    /*
     * Preserve source ownership.
     * reset() does NOT silently switch modes.
     */


    if (
        isLocalDemoMode()
    ) {

        publishTelemetry({
            silent:
                true
        });
    }


    return getAdapterState();
}

function getAdapterState() {

    return {

        version:
            SIMULATION_ADAPTER_VERSION,

        source:
            "simulation",

        sourceMode:
            adapterState.sourceMode,

        backendAuthoritative:
            isBackendAuthoritative(),

        localDemo:
            isLocalDemoMode(),

        updateRateHz:
            UPDATE_RATE_HZ,

        initialized:
            adapterState.initialized,

        running:
            adapterState.running,

        publishing:
            adapterState.publishing,

        sequence:
            adapterState.sequence,

        rpm:
            adapterState.rpm,

        throttlePercent:
            adapterState
                .throttlePercent,

        loadPercent:
            adapterState
                .loadPercent,

        operatingMode:
            adapterState
                .operatingMode,

        missionId:
            adapterState.missionId,

        missionPhase:
            adapterState
                .missionPhase,

        missionStartTime:
            adapterState
                .missionStartTime,

        altitudeM:
            adapterState.altitudeM,

        ambientTemperatureC:
            adapterState
                .ambientTemperatureC,

        ambientPressurePa:
            adapterState
                .ambientPressurePa,

        airDensityKgM3:
            adapterState
                .airDensityKgM3,

        publishedFrames:
            adapterState
                .publishedFrames,

        blockedPublishes:
            adapterState
                .blockedPublishes,

        lastPublishedAt:
            adapterState
                .lastPublishedAt,

        lastModeChangeAt:
            adapterState
                .lastModeChangeAt,

        timerActive:
            adapterState.timer !==
            null
    };
}

function getSourceMode() {

    return adapterState
        .sourceMode;
}

window.PRATIRUP_SIMULATION_ADAPTER = {

    version:
        SIMULATION_ADAPTER_VERSION,

    VERSION:
        SIMULATION_ADAPTER_VERSION,

    MODES:
        SIMULATION_ADAPTER_MODES,

    getState:
        getAdapterState,

    getFrame:
        buildTelemetryFrame,

    publish:
        publishTelemetry,

    start:
        startPublishing,

    stop:
        stopPublishing,

    reset:
        resetAdapter,

    setSourceMode,

    getSourceMode,

    enableBackendAuthority,

    enableLocalDemo,

    isBackendAuthoritative,

    isLocalDemoMode,

    setOperatingMode,

    setRPM,

    setRunning,

    setThrottle,

    setLoad,

    setEnvironment,

    startMission,

    setMissionPhase,

    endMission
};

initializeSimulationAdapter();

window.dispatchEvent(

    new CustomEvent(
        "pratirup:simulation-adapter-ready",
        {
            detail: {

                version:
                    SIMULATION_ADAPTER_VERSION,

                source:
                    "simulation",

                sourceMode:
                    adapterState
                        .sourceMode,

                backendAuthoritative:
                    isBackendAuthoritative(),

                localDemo:
                    isLocalDemoMode(),

                publishing:
                    adapterState
                        .publishing,

                updateRateHz:
                    UPDATE_RATE_HZ
            }
        }
    )
);

console.log(
    `[PRATIRUP] Simulation Adapter ${SIMULATION_ADAPTER_VERSION} loaded.`
);


console.log(
    "[PRATIRUP] Backend-authoritative telemetry ownership enabled."
);
