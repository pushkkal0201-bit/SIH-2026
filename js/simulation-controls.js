"use strict";


const SIMULATION_CONTROLS_VERSION =
    "1.0.0";

const simulationControlState = {

    throttlePercent:
        65,

    loadPercent:
        60,

    altitudeM:
        0,

    ambientTemperatureC:
        15,

    operatingMode:
        "idle",

    missionRunning:
        false,

    missionId:
        null

};

function safeNumber(
    value,
    fallback = 0
) {

    const number =
        Number(value);


    return Number.isFinite(number)
        ? number
        : fallback;

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

function getAdapter() {

    return window
        .PRATIRUP_SIMULATION_ADAPTER;

}

function setThrottle(
    value
) {

    const throttle =
        clamp(
            safeNumber(
                value,
                simulationControlState
                    .throttlePercent
            ),
            0,
            100
        );


    simulationControlState
        .throttlePercent =
        throttle;


    getAdapter()
        ?.setThrottle(
            throttle
        );


    updateValueDisplay(
        "simThrottleValue",
        `${Math.round(throttle)} %`
    );


    publishControlState();

}

function setLoad(
    value
) {

    const load =
        clamp(
            safeNumber(
                value,
                simulationControlState
                    .loadPercent
            ),
            0,
            100
        );


    simulationControlState
        .loadPercent =
        load;


    getAdapter()
        ?.setLoad(
            load
        );


    updateValueDisplay(
        "simLoadValue",
        `${Math.round(load)} %`
    );


    publishControlState();

}
function setAltitude(
    value
) {

    /*
       The baseline atmosphere model currently supports
       the ISA troposphere up to 11,000 m. We therefore constrain the UI to that range.
    */

    const altitude =
        clamp(
            safeNumber(
                value,
                simulationControlState
                    .altitudeM
            ),
            0,
            11000
        );


    simulationControlState
        .altitudeM =
        altitude;


    updateEnvironment();


    updateValueDisplay(
        "simAltitudeValue",
        `${Math.round(altitude)} m`
    );


    publishControlState();

}

function setAmbientTemperature(
    value
) {

    const temperature =
        clamp(
            safeNumber(
                value,
                simulationControlState
                    .ambientTemperatureC
            ),
            -40,
            60
        );


    simulationControlState
        .ambientTemperatureC =
        temperature;


    updateEnvironment();


    updateValueDisplay(
        "simTemperatureValue",
        `${temperature.toFixed(0)} °C`
    );


    publishControlState();

}

function updateEnvironment() {

    const adapter =
        getAdapter();


    if (
        !adapter
    ) {

        return;

    }


    /*
       We deliberately send only the environmental
       conditions directly controlled by the user.Pressure and density are NOT generated here.
       The physics model calculates those quantities.
    */

    adapter.setEnvironment({

        altitudeM:
            simulationControlState
                .altitudeM,

        ambientTemperatureC:
            simulationControlState
                .ambientTemperatureC,

        ambientPressurePa:
            null,

        airDensityKgM3:
            null

    });

}

function setOperatingMode(
    mode
) {

    const schema =
        window
            .PRATIRUP_TELEMETRY_SCHEMA;


    if (
        !schema
    ) {

        console.warn(
            "[PRATIRUP CONTROLS] Telemetry schema unavailable."
        );

        return false;

    }


    const allowedModes =
        Object.values(
            schema.OPERATING_MODES
        );


    if (
        !allowedModes.includes(
            mode
        )
    ) {

        console.warn(
            "[PRATIRUP CONTROLS] Unsupported operating mode:",
            mode
        );

        return false;

    }


    simulationControlState
        .operatingMode =
        mode;


    getAdapter()
        ?.setOperatingMode(
            mode
        );


    updateValueDisplay(
        "simMissionModeValue",
        mode.toUpperCase()
    );


    publishControlState();


    return true;

}

function startMission() {

    if (
        simulationControlState
            .missionRunning
    ) {

        return;

    }


    const missionId =
        `SIM-${Date.now()}`;


    simulationControlState
        .missionRunning =
        true;


    simulationControlState
        .missionId =
        missionId;


    const phase =
        simulationControlState
            .operatingMode ===
        "idle"

            ? "preflight"

            : simulationControlState
                .operatingMode;


    getAdapter()
        ?.startMission(
            missionId,
            phase
        );


    /*
       Start visual/mechanical engine.
    */

    window.dispatchEvent(

        new CustomEvent(
            "pratirup:run",
            {

                detail: {

                    value:
                        true

                }

            }
        )

    );


    updateMissionButton();


    publishControlState();


    console.log(
        "[PRATIRUP] Simulation mission started:",
        missionId
    );

}

function stopMission() {

    if (
        !simulationControlState
            .missionRunning
    ) {

        return;

    }


    getAdapter()
        ?.endMission();


    simulationControlState
        .missionRunning =
        false;


    /*
       Stop visual/mechanical engine.
    */

    window.dispatchEvent(

        new CustomEvent(
            "pratirup:run",
            {

                detail: {

                    value:
                        false

                }

            }
        )

    );


    updateMissionButton();


    publishControlState();


    console.log(
        "[PRATIRUP] Simulation mission stopped."
    );

}

function toggleMission() {

    if (
        simulationControlState
            .missionRunning
    ) {

        stopMission();

    }

    else {

        startMission();

    }

}

function resetControls() {

    simulationControlState
        .throttlePercent =
        65;


    simulationControlState
        .loadPercent =
        60;


    simulationControlState
        .altitudeM =
        0;


    simulationControlState
        .ambientTemperatureC =
        15;


    simulationControlState
        .operatingMode =
        "idle";


    applyStateToAdapter();

    applyStateToUI();

    publishControlState();

}

function applyStateToAdapter() {

    const adapter =
        getAdapter();


    if (
        !adapter
    ) {

        return;

    }


    adapter.setThrottle(
        simulationControlState
            .throttlePercent
    );


    adapter.setLoad(
        simulationControlState
            .loadPercent
    );


    adapter.setOperatingMode(
        simulationControlState
            .operatingMode
    );


    updateEnvironment();

}

function updateValueDisplay(
    elementId,
    value
) {

    const element =
        document.getElementById(
            elementId
        );


    if (
        element
    ) {

        element.textContent =
            value;

    }

}

function applyStateToUI() {

    const throttle =
        document.getElementById(
            "simThrottle"
        );


    const load =
        document.getElementById(
            "simLoad"
        );


    const altitude =
        document.getElementById(
            "simAltitude"
        );


    const temperature =
        document.getElementById(
            "simTemperature"
        );


    const missionMode =
        document.getElementById(
            "simMissionMode"
        );


    if (
        throttle
    ) {

        throttle.value =
            simulationControlState
                .throttlePercent;

    }


    if (
        load
    ) {

        load.value =
            simulationControlState
                .loadPercent;

    }


    if (
        altitude
    ) {

        altitude.value =
            simulationControlState
                .altitudeM;

    }


    if (
        temperature
    ) {

        temperature.value =
            simulationControlState
                .ambientTemperatureC;

    }


    if (
        missionMode
    ) {

        missionMode.value =
            simulationControlState
                .operatingMode;

    }


    updateValueDisplay(
        "simThrottleValue",
        `${simulationControlState.throttlePercent} %`
    );


    updateValueDisplay(
        "simLoadValue",
        `${simulationControlState.loadPercent} %`
    );


    updateValueDisplay(
        "simAltitudeValue",
        `${simulationControlState.altitudeM} m`
    );


    updateValueDisplay(
        "simTemperatureValue",
        `${simulationControlState.ambientTemperatureC} °C`
    );


    updateValueDisplay(
        "simMissionModeValue",
        simulationControlState
            .operatingMode
            .toUpperCase()
    );


    updateMissionButton();

}

function updateMissionButton() {

    const button =
        document.getElementById(
            "simMissionButton"
        );


    if (
        !button
    ) {

        return;

    }


    button.textContent =

        simulationControlState
            .missionRunning

            ? "STOP MISSION"

            : "START MISSION";


    button.classList.toggle(
        "active",
        simulationControlState
            .missionRunning
    );

}

function publishControlState() {

    window.dispatchEvent(

        new CustomEvent(
            "pratirup:simulation-controls",
            {

                detail:
                    getState()

            }
        )

    );

}

function getState() {

    return {

        version:
            SIMULATION_CONTROLS_VERSION,

        throttlePercent:
            simulationControlState
                .throttlePercent,

        loadPercent:
            simulationControlState
                .loadPercent,

        altitudeM:
            simulationControlState
                .altitudeM,

        ambientTemperatureC:
            simulationControlState
                .ambientTemperatureC,

        operatingMode:
            simulationControlState
                .operatingMode,

        missionRunning:
            simulationControlState
                .missionRunning,

        missionId:
            simulationControlState
                .missionId

    };

}

function connectControls() {

    const throttle =
        document.getElementById(
            "simThrottle"
        );


    const load =
        document.getElementById(
            "simLoad"
        );


    const altitude =
        document.getElementById(
            "simAltitude"
        );


    const temperature =
        document.getElementById(
            "simTemperature"
        );


    const missionMode =
        document.getElementById(
            "simMissionMode"
        );


    const missionButton =
        document.getElementById(
            "simMissionButton"
        );


    const resetButton =
        document.getElementById(
            "simResetButton"
        );

    throttle?.addEventListener(
        "input",
        event => {

            setThrottle(
                event.target.value
            );

        }
    );


    load?.addEventListener(
        "input",
        event => {

            setLoad(
                event.target.value
            );

        }
    );

    altitude?.addEventListener(
        "input",
        event => {

            setAltitude(
                event.target.value
            );

        }
    );

    temperature?.addEventListener(
        "input",
        event => {

            setAmbientTemperature(
                event.target.value
            );

        }
    );

    missionMode?.addEventListener(
        "change",
        event => {

            setOperatingMode(
                event.target.value
            );


            if (
                simulationControlState
                    .missionRunning
            ) {

                getAdapter()
                    ?.setMissionPhase(
                        event.target.value
                    );

            }

        }
    );

    missionButton?.addEventListener(
        "click",
        toggleMission
    );

    resetButton?.addEventListener(
        "click",
        resetControls
    );


    applyStateToAdapter();

    applyStateToUI();


    console.log(
        `[PRATIRUP] Simulation Controls ${SIMULATION_CONTROLS_VERSION} ready.`
    );

}

if (
    document.readyState ===
    "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        connectControls,
        {
            once: true
        }
    );

}

else {

    connectControls();

}

window.PRATIRUP_SIMULATION_CONTROLS = {

    version:
        SIMULATION_CONTROLS_VERSION,

    getState,

    setThrottle,

    setLoad,

    setAltitude,

    setAmbientTemperature,

    setOperatingMode,

    startMission,

    stopMission,

    reset:
        resetControls

};
