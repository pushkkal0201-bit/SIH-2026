"use strict";
const DIGITAL_TWIN_CORE_VERSION =
    "1.4.0";

const CORE_CONFIG = Object.freeze({

    telemetryTimeoutMs:
        2500,

    freshnessCheckIntervalMs:
        250,

    historyLimit:
        300,

    validateFrames:
        true,

    normalizeFrames:
        true,

    debug:
        false,


    residualNormalization: {

        rpm:
            250,

        torqueNm:
            50,

        powerKw:
            15,

        chtC:
            25,

        egtC:
            60,

        oilPressureKPa:
            80,

        oilTemperatureC:
            20,

        fuelFlowKgPerSecond:
            0.002,

        vibrationG:
            0.5

    }

});

const REQUIRED_TELEMETRY_SECTIONS =
    Object.freeze([

        "meta",

        "engine",

        "cht",

        "egt",

        "oil",

        "fuel",

        "vibration",

        "electrical"

    ]);

const twinState = {

    initialized:
        false,

    synchronized:
        false,

    synchronizationStatus:
        "WAITING_FOR_TELEMETRY",

    activeSource:
        null,

    latestFrame:
        null,

    observedState:
        null,

    expectedState:
        null,

    residualState:
        null,

    receivedFrames:
        0,

    acceptedFrames:
        0,

    rejectedFrames:
        0,

    ignoredEvents:
        0,

    normalizationFailures:
        0,

    lastSequence:
        null,

    droppedSequenceCount:
        0,

    duplicateSequenceCount:
        0,

    outOfOrderSequenceCount:
        0,

    lastFrameTimestamp:
        null,

    lastReceiveTime:
        null,

    telemetryAgeMs:
        null,
    history:
        []

};

let freshnessTimer =
    null;

function getSchema() {

    return window
        .PRATIRUP_TELEMETRY_SCHEMA;

}

function debugLog(...args) {

    if (
        CORE_CONFIG.debug
    ) {

        console.log(
            "[PRATIRUP TWIN]",
            ...args
        );

    }

}

function cloneValue(value) {

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

function isFiniteNumber(value) {

    return (

        typeof value === "number" &&

        Number.isFinite(value)

    );

}


function safeDifference(
    observed,
    expected
) {

    if (
        !isFiniteNumber(observed) ||
        !isFiniteNumber(expected)
    ) {

        return null;

    }


    return observed - expected;

}


function normalizeResidual(
    residual,
    normalizationLimit
) {

    if (
        !isFiniteNumber(residual) ||
        !isFiniteNumber(normalizationLimit) ||
        normalizationLimit <= 0
    ) {

        return null;

    }


    return (
        Math.abs(residual) /
        normalizationLimit
    );

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

function isTelemetryCandidate(frame) {

    if (
        !frame ||
        typeof frame !== "object" ||
        Array.isArray(frame)
    ) {

        return false;

    }


    let sectionCount =
        0;


    for (
        const section
        of REQUIRED_TELEMETRY_SECTIONS
    ) {

        if (
            frame[section] &&
            typeof frame[section] === "object"
        ) {

            sectionCount++;

        }

    }


    return sectionCount >= 3;

}

function initializeDigitalTwinCore() {

    if (
        twinState.initialized
    ) {

        return true;

    }


    const schema =
        getSchema();


    if (!schema) {

        console.error(
            "[PRATIRUP TWIN] telemetry-schema.js is not loaded."
        );

        return false;

    }


    if (
        typeof schema.validate !==
        "function"
    ) {

        console.error(
            "[PRATIRUP TWIN] Schema validate() unavailable."
        );

        return false;

    }


    if (
        typeof schema.normalize !==
        "function"
    ) {

        console.error(
            "[PRATIRUP TWIN] Schema normalize() unavailable."
        );

        return false;

    }


    window.addEventListener(

        "pratirup:telemetry",

        handleTelemetryFrame

    );


    freshnessTimer =

        window.setInterval(

            updateSynchronizationHealth,

            CORE_CONFIG
                .freshnessCheckIntervalMs

        );


    twinState.initialized =
        true;


    publishTwinState();


    window.dispatchEvent(

        new CustomEvent(

            "pratirup:twin-core-ready",

            {

                detail: {

                    version:
                        DIGITAL_TWIN_CORE_VERSION

                }

            }

        )

    );


    console.log(

        `[PRATIRUP] Digital Twin Core ${DIGITAL_TWIN_CORE_VERSION} ready.`

    );


    console.log(

        "[PRATIRUP TWIN] Canonical telemetry listener: pratirup:telemetry"

    );


    return true;

}

function handleTelemetryFrame(event) {

    const rawFrame =
        extractEventFrame(event);

    if (
        !isTelemetryCandidate(
            rawFrame
        )
    ) {

        twinState.ignoredEvents++;


        debugLog(
            "Ignored non-telemetry event.",
            rawFrame
        );


        return;

    }


    twinState.receivedFrames++;

    const validation =

        validateIncomingFrame(
            rawFrame
        );


    if (
        !validation.valid
    ) {

        twinState.rejectedFrames++;


        console.warn(

            "[PRATIRUP TWIN] Telemetry rejected:",

            validation.errors

        );


        publishTwinState();


        return;

    }

    const frame =

        normalizeIncomingFrame(
            rawFrame
        );


    if (!frame) {

        twinState
            .normalizationFailures++;


        twinState
            .rejectedFrames++;


        console.warn(
            "[PRATIRUP TWIN] Telemetry normalization failed."
        );


        publishTwinState();


        return;

    }

    twinState.acceptedFrames++;


    processAcceptedFrame(
        frame
    );

}

function extractEventFrame(event) {

    if (
        event === null ||
        event === undefined
    ) {

        return null;

    }

    if (
        typeof CustomEvent !== "undefined" &&
        event instanceof CustomEvent
    ) {

        return event.detail;

    }

    if (
        typeof event === "object" &&
        "detail" in event
    ) {

        return event.detail;

    }

    return event;

}

function validateIncomingFrame(frame) {

    if (
        !frame ||
        typeof frame !== "object"
    ) {

        return {

            valid:
                false,

            errors: [
                "Telemetry frame is not an object."
            ]

        };

    }


    if (
        !CORE_CONFIG.validateFrames
    ) {

        return {

            valid:
                true,

            errors:
                []

        };

    }


    const schema =
        getSchema();


    if (
        !schema ||
        typeof schema.validate !==
        "function"
    ) {

        return {

            valid:
                false,

            errors: [
                "Telemetry schema validator unavailable."
            ]

        };

    }


    try {

        const result =
            schema.validate(frame);


        if (
            result &&
            typeof result === "object"
        ) {

            return {

                valid:
                    result.valid === true,

                errors:
                    Array.isArray(
                        result.errors
                    )
                        ? result.errors
                        : []

            };

        }


        return {

            valid:
                false,

            errors: [
                "Telemetry validator returned an invalid result."
            ]

        };

    }

    catch (error) {

        return {

            valid:
                false,

            errors: [

                `Telemetry validation exception: ${
                    error?.message ??
                    String(error)
                }`

            ]

        };

    }

}

function normalizeIncomingFrame(frame) {

    if (
        !CORE_CONFIG.normalizeFrames
    ) {

        return cloneValue(frame);

    }


    const schema =
        getSchema();


    if (
        !schema ||
        typeof schema.normalize !==
        "function"
    ) {

        return null;

    }


    try {

        const normalized =
            schema.normalize(frame);


        if (
            !normalized ||
            typeof normalized !== "object"
        ) {

            return null;

        }


        return normalized;

    }

    catch (error) {

        console.error(

            "[PRATIRUP TWIN] Normalization exception:",

            error

        );


        return null;

    }

}

function processAcceptedFrame(frame) {

    trackSequence(frame);


    twinState.activeSource =

        frame.meta
            ?.source ??

        "unknown";


    twinState.latestFrame =
        cloneValue(frame);


    twinState.lastFrameTimestamp =

        frame.meta
            ?.timestamp ??

        Date.now();


    twinState.lastReceiveTime =
        Date.now();


    twinState.telemetryAgeMs =
        0;


    twinState.observedState =

        createObservedState(
            frame
        );


    pushHistory(frame);


    twinState.synchronized =
        true;


    twinState
        .synchronizationStatus =

        "SYNCHRONIZED";

    if (
        twinState.expectedState
    ) {

        twinState.residualState =

            calculateResidualState(

                twinState
                    .observedState,

                twinState
                    .expectedState

            );

    }

    publishObservedState(frame);

    publishTwinState();

}

function createObservedState(frame) {

    return {

        engine: {

            rpm:

                frame.engine
                    ?.rpm ??

                null,


            throttlePercent:

                frame.engine
                    ?.throttlePercent ??

                null,


            loadPercent:

                frame.engine
                    ?.loadPercent ??

                null,


            powerKw:

                frame.engine
                    ?.powerKw ??

                null,


            torqueNm:

                frame.engine
                    ?.torqueNm ??

                null,


            operatingMode:

                frame.engine
                    ?.operatingMode ??

                null

        },

        cht: {

            cylinder1C:

                frame.cht
                    ?.cylinder1C ??

                null,


            cylinder2C:

                frame.cht
                    ?.cylinder2C ??

                null,


            cylinder3C:

                frame.cht
                    ?.cylinder3C ??

                null,


            cylinder4C:

                frame.cht
                    ?.cylinder4C ??

                null,


            averageC:

                frame.cht
                    ?.averageC ??

                null,


            maximumC:

                frame.cht
                    ?.maximumC ??

                null

        },

        egt: {

            cylinder1C:

                frame.egt
                    ?.cylinder1C ??

                null,


            cylinder2C:

                frame.egt
                    ?.cylinder2C ??

                null,


            cylinder3C:

                frame.egt
                    ?.cylinder3C ??

                null,


            cylinder4C:

                frame.egt
                    ?.cylinder4C ??

                null,


            averageC:

                frame.egt
                    ?.averageC ??

                null,


            maximumC:

                frame.egt
                    ?.maximumC ??

                null

        },

        oil: {

            pressureKPa:

                frame.oil
                    ?.pressureKPa ??

                null,


            temperatureC:

                frame.oil
                    ?.temperatureC ??

                null

        },

        fuel: {

            flowKgPerSecond:

                frame.fuel
                    ?.flowKgPerSecond ??

                null,


            pressureKPa:

                frame.fuel
                    ?.pressureKPa ??

                null,


            injectionTimingDeg:

                frame.fuel
                    ?.injectionTimingDeg ??

                null

        },

        injection: {

            timingDeg:

                frame.fuel
                    ?.injectionTimingDeg ??

                null,


            injector1PulseMs:
                null,

            injector2PulseMs:
                null,

            injector3PulseMs:
                null,

            injector4PulseMs:
                null

        },

        vibration: {

            overallG:

                frame.vibration
                    ?.overallG ??

                null,


            xG:

                frame.vibration
                    ?.xG ??

                null,


            yG:

                frame.vibration
                    ?.yG ??

                null,


            zG:

                frame.vibration
                    ?.zG ??

                null

        },

        electrical: {

            batteryVoltageV:

                frame.electrical
                    ?.batteryVoltageV ??

                null,


            batteryCurrentA:

                frame.electrical
                    ?.batteryCurrentA ??

                null,


            alternatorVoltageV:

                frame.electrical
                    ?.alternatorVoltageV ??

                null,


            alternatorCurrentA:

                frame.electrical
                    ?.alternatorCurrentA ??

                null

        },

        environment: {

            altitudeM:

                frame.environment
                    ?.altitudeM ??

                null,


            ambientTemperatureC:

                frame.environment
                    ?.ambientTemperatureC ??

                null,


            ambientPressurePa:

                frame.environment
                    ?.ambientPressurePa ??

                null,


            airDensityKgM3:

                frame.environment
                    ?.airDensityKgM3 ??

                null

        },

        mission: {

            missionId:

                frame.mission
                    ?.missionId ??

                null,


            elapsedTimeSec:

                frame.mission
                    ?.elapsedTimeSec ??

                null,


            phase:

                frame.mission
                    ?.phase ??

                null

        }

    };

}

function publishObservedState(frame) {

    window.dispatchEvent(

        new CustomEvent(

            "pratirup:observed-state",

            {

                detail: {

                    observedState:

                        cloneValue(

                            twinState
                                .observedState

                        ),


                    source:

                        twinState
                            .activeSource,


                    timestamp:

                        frame.meta
                            ?.timestamp ??

                        Date.now(),


                    sequence:

                        frame.meta
                            ?.sequence ??

                        null

                }

            }

        )

    );

}
function trackSequence(frame) {

    const sequence =

        frame.meta
            ?.sequence;


    if (
        !Number.isInteger(sequence)
    ) {

        return;

    }


    const previous =

        twinState
            .lastSequence;


    if (
        Number.isInteger(previous)
    ) {

        if (
            sequence === previous
        ) {

            twinState
                .duplicateSequenceCount++;

        }


        else if (
            sequence < previous
        ) {

            twinState
                .outOfOrderSequenceCount++;

        }


        else if (
            sequence > previous + 1
        ) {

            twinState
                .droppedSequenceCount +=

                sequence -
                previous -
                1;

        }

    }
    if (
        !Number.isInteger(previous) ||
        sequence > previous
    ) {

        twinState.lastSequence =
            sequence;

    }

}
function pushHistory(frame) {

    twinState.history.push(

        cloneValue(frame)

    );


    while (

        twinState.history.length >

        CORE_CONFIG.historyLimit

    ) {

        twinState.history.shift();

    }

}
function updateSynchronizationHealth() {

    if (
        !twinState.lastReceiveTime
    ) {

        twinState.telemetryAgeMs =
            null;


        if (

            twinState
                .synchronizationStatus !==
            "WAITING_FOR_TELEMETRY"

        ) {

            twinState.synchronized =
                false;


            twinState
                .synchronizationStatus =

                "WAITING_FOR_TELEMETRY";


            publishTwinState();

        }


        return;

    }


    const age =

        Date.now() -

        twinState.lastReceiveTime;


    twinState.telemetryAgeMs =
        age;


    if (

        age >

        CORE_CONFIG
            .telemetryTimeoutMs

    ) {

        if (

            twinState
                .synchronizationStatus !==
            "TELEMETRY_STALE"

        ) {

            twinState.synchronized =
                false;


            twinState
                .synchronizationStatus =

                "TELEMETRY_STALE";


            publishTwinState();

        }


        return;

    }


    if (

        twinState
            .synchronizationStatus !==
        "SYNCHRONIZED"

    ) {

        twinState.synchronized =
            true;


        twinState
            .synchronizationStatus =

            "SYNCHRONIZED";


        publishTwinState();

    }

}
function calculateResidualState(
    observed,
    expected
) {

    if (
        !observed ||
        !expected
    ) {

        return null;

    }


    const residual = {

        timestamp:
            Date.now(),


        engine: {

            rpm:

                safeDifference(

                    observed.engine
                        ?.rpm,

                    expected.engine
                        ?.expectedRpm

                ),


            torqueNm:

                safeDifference(

                    observed.engine
                        ?.torqueNm,

                    expected.engine
                        ?.expectedTorqueNm

                ),


            powerKw:

                safeDifference(

                    observed.engine
                        ?.powerKw,

                    expected.engine
                        ?.expectedPowerKw

                )

        },


        cht: {

            cylinder1C:

                safeDifference(

                    observed.cht
                        ?.cylinder1C,

                    expected.cht
                        ?.cylinder1C

                ),


            cylinder2C:

                safeDifference(

                    observed.cht
                        ?.cylinder2C,

                    expected.cht
                        ?.cylinder2C

                ),


            cylinder3C:

                safeDifference(

                    observed.cht
                        ?.cylinder3C,

                    expected.cht
                        ?.cylinder3C

                ),


            cylinder4C:

                safeDifference(

                    observed.cht
                        ?.cylinder4C,

                    expected.cht
                        ?.cylinder4C

                )

        },


        egt: {

            cylinder1C:

                safeDifference(

                    observed.egt
                        ?.cylinder1C,

                    expected.egt
                        ?.cylinder1C

                ),


            cylinder2C:

                safeDifference(

                    observed.egt
                        ?.cylinder2C,

                    expected.egt
                        ?.cylinder2C

                ),


            cylinder3C:

                safeDifference(

                    observed.egt
                        ?.cylinder3C,

                    expected.egt
                        ?.cylinder3C

                ),


            cylinder4C:

                safeDifference(

                    observed.egt
                        ?.cylinder4C,

                    expected.egt
                        ?.cylinder4C

                )

        },


        oil: {

            pressureKPa:

                safeDifference(

                    observed.oil
                        ?.pressureKPa,

                    expected.oil
                        ?.pressureKPa

                ),


            temperatureC:

                safeDifference(

                    observed.oil
                        ?.temperatureC,

                    expected.oil
                        ?.temperatureC

                )

        },


        fuel: {

            flowKgPerSecond:

                safeDifference(

                    observed.fuel
                        ?.flowKgPerSecond,

                    expected.fuel
                        ?.flowKgPerSecond

                )

        },


        vibration: {

            overallG:

                safeDifference(

                    observed.vibration
                        ?.overallG,

                    expected.vibration
                        ?.overallG

                )

        }

    };

    residual.normalized = {

        engine: {

            rpm:

                normalizeResidual(

                    residual.engine.rpm,

                    CORE_CONFIG
                        .residualNormalization
                        .rpm

                ),


            torque:

                normalizeResidual(

                    residual.engine
                        .torqueNm,

                    CORE_CONFIG
                        .residualNormalization
                        .torqueNm

                ),


            power:

                normalizeResidual(

                    residual.engine
                        .powerKw,

                    CORE_CONFIG
                        .residualNormalization
                        .powerKw

                )

        },


        cht: {

            cylinder1:

                normalizeResidual(

                    residual.cht
                        .cylinder1C,

                    CORE_CONFIG
                        .residualNormalization
                        .chtC

                ),


            cylinder2:

                normalizeResidual(

                    residual.cht
                        .cylinder2C,

                    CORE_CONFIG
                        .residualNormalization
                        .chtC

                ),


            cylinder3:

                normalizeResidual(

                    residual.cht
                        .cylinder3C,

                    CORE_CONFIG
                        .residualNormalization
                        .chtC

                ),


            cylinder4:

                normalizeResidual(

                    residual.cht
                        .cylinder4C,

                    CORE_CONFIG
                        .residualNormalization
                        .chtC

                )

        },


        egt: {

            cylinder1:

                normalizeResidual(

                    residual.egt
                        .cylinder1C,

                    CORE_CONFIG
                        .residualNormalization
                        .egtC

                ),


            cylinder2:

                normalizeResidual(

                    residual.egt
                        .cylinder2C,

                    CORE_CONFIG
                        .residualNormalization
                        .egtC

                ),


            cylinder3:

                normalizeResidual(

                    residual.egt
                        .cylinder3C,

                    CORE_CONFIG
                        .residualNormalization
                        .egtC

                ),


            cylinder4:

                normalizeResidual(

                    residual.egt
                        .cylinder4C,

                    CORE_CONFIG
                        .residualNormalization
                        .egtC

                )

        },


        oil: {

            pressure:

                normalizeResidual(

                    residual.oil
                        .pressureKPa,

                    CORE_CONFIG
                        .residualNormalization
                        .oilPressureKPa

                ),


            temperature:

                normalizeResidual(

                    residual.oil
                        .temperatureC,

                    CORE_CONFIG
                        .residualNormalization
                        .oilTemperatureC

                )

        },


        fuel: {

            flow:

                normalizeResidual(

                    residual.fuel
                        .flowKgPerSecond,

                    CORE_CONFIG
                        .residualNormalization
                        .fuelFlowKgPerSecond

                )

        },


        vibration: {

            overall:

                normalizeResidual(

                    residual.vibration
                        .overallG,

                    CORE_CONFIG
                        .residualNormalization
                        .vibrationG

                )

        }

    };


    residual.summary =

        calculateResidualSummary(

            residual.normalized

        );


    return residual;

}
function collectNormalizedValues(
    object,
    output = []
) {

    if (
        object === null ||
        object === undefined
    ) {

        return output;

    }


    if (
        isFiniteNumber(object)
    ) {

        output.push(object);


        return output;

    }


    if (
        typeof object !== "object"
    ) {

        return output;

    }


    for (
        const value
        of Object.values(object)
    ) {

        collectNormalizedValues(

            value,

            output

        );

    }


    return output;

}

function calculateResidualSummary(
    normalizedResiduals
) {

    const values =

        collectNormalizedValues(

            normalizedResiduals

        );
    const possibleResidualCount =
        15;


    const availableResidualCount =
        values.length;


    const coverage =

        possibleResidualCount > 0

            ? clamp(

                availableResidualCount /
                possibleResidualCount,

                0,

                1

            )

            : 0;


    if (
        availableResidualCount === 0
    ) {

        return {

            availableResidualCount:
                0,

            possibleResidualCount,

            coverage:
                0,

            meanNormalizedResidual:
                null,

            maximumNormalizedResidual:
                null,

            residualScore:
                null,

            stateConfidence:
                0

        };

    }


    const total =

        values.reduce(

            (
                sum,
                value
            ) =>

                sum + value,

            0

        );


    const mean =
        total /
        availableResidualCount;


    const maximum =
        Math.max(...values);

    const residualScore =
        mean;


    const agreementConfidence =

        clamp(

            1 - mean,

            0,

            1

        );


    const stateConfidence =

        clamp(

            agreementConfidence *
            coverage,

            0,

            1

        );


    return {

        availableResidualCount,

        possibleResidualCount,

        coverage,

        meanNormalizedResidual:
            mean,

        maximumNormalizedResidual:
            maximum,

        residualScore,

        stateConfidence

    };

}
function setExpectedState(
    expectedState
) {

    twinState.expectedState =

        expectedState

            ? cloneValue(
                expectedState
            )

            : null;


    if (
        twinState.observedState &&
        twinState.expectedState
    ) {

        twinState.residualState =

            calculateResidualState(

                twinState
                    .observedState,

                twinState
                    .expectedState

            );

    }

    else {

        twinState.residualState =
            null;

    }


    publishExpectedState();


    publishResidualState();


    publishTwinState();

}
function publishExpectedState() {

    window.dispatchEvent(

        new CustomEvent(

            "pratirup:expected-state",

            {

                detail:

                    twinState.expectedState

                        ? cloneValue(

                            twinState
                                .expectedState

                        )

                        : null

            }

        )

    );

}
function publishResidualState() {

    window.dispatchEvent(

        new CustomEvent(

            "pratirup:residual-state",

            {

                detail:

                    twinState.residualState

                        ? cloneValue(

                            twinState
                                .residualState

                        )

                        : null

            }

        )

    );

}
function clearExpectedState() {

    twinState.expectedState =
        null;


    twinState.residualState =
        null;


    publishExpectedState();


    publishResidualState();


    publishTwinState();

}
function setActiveSource(source) {

    twinState.activeSource =

        source ?? null;


    publishTwinState();

}
function getHistory() {

    return twinState.history.map(

        frame =>
            cloneValue(frame)

    );

}


function clearHistory() {

    twinState.history.length =
        0;


    publishTwinState();

}
function getResidualState() {

    return twinState.residualState

        ? cloneValue(
            twinState.residualState
        )

        : null;

}
function getObservedState() {

    return twinState.observedState

        ? cloneValue(
            twinState.observedState
        )

        : null;

}

function getExpectedState() {

    return twinState.expectedState

        ? cloneValue(
            twinState.expectedState
        )

        : null;

}

function getLatestFrame() {

    return twinState.latestFrame

        ? cloneValue(
            twinState.latestFrame
        )

        : null;

}

function getTwinState() {

    const summary =

        twinState.residualState
            ?.summary ??

        null;


    return {

        version:
            DIGITAL_TWIN_CORE_VERSION,


        initialized:
            twinState.initialized,


        synchronized:
            twinState.synchronized,


        synchronizationStatus:

            twinState
                .synchronizationStatus,


        activeSource:

            twinState
                .activeSource,


        latestFrame:

            twinState.latestFrame

                ? cloneValue(
                    twinState.latestFrame
                )

                : null,


        observedState:

            twinState.observedState

                ? cloneValue(
                    twinState.observedState
                )

                : null,


        expectedState:

            twinState.expectedState

                ? cloneValue(
                    twinState.expectedState
                )

                : null,


        residualState:

            twinState.residualState

                ? cloneValue(
                    twinState.residualState
                )

                : null,


        residualScore:

            summary
                ?.residualScore ??

            null,


        residualCoverage:

            summary
                ?.coverage ??

            0,


        stateConfidence:

            summary
                ?.stateConfidence ??

            null,


        receivedFrames:

            twinState
                .receivedFrames,


        acceptedFrames:

            twinState
                .acceptedFrames,


        rejectedFrames:

            twinState
                .rejectedFrames,


        ignoredEvents:

            twinState
                .ignoredEvents,


        normalizationFailures:

            twinState
                .normalizationFailures,


        lastSequence:

            twinState
                .lastSequence,


        droppedSequenceCount:

            twinState
                .droppedSequenceCount,


        duplicateSequenceCount:

            twinState
                .duplicateSequenceCount,


        outOfOrderSequenceCount:

            twinState
                .outOfOrderSequenceCount,


        lastFrameTimestamp:

            twinState
                .lastFrameTimestamp,


        telemetryAgeMs:

            twinState
                .telemetryAgeMs,


        historySize:

            twinState
                .history
                .length

    };

}
function resetDigitalTwinCore() {

    twinState.synchronized =
        false;


    twinState
        .synchronizationStatus =

        "WAITING_FOR_TELEMETRY";


    twinState.activeSource =
        null;


    twinState.latestFrame =
        null;


    twinState.observedState =
        null;


    twinState.expectedState =
        null;


    twinState.residualState =
        null;


    twinState.receivedFrames =
        0;


    twinState.acceptedFrames =
        0;


    twinState.rejectedFrames =
        0;


    twinState.ignoredEvents =
        0;


    twinState.normalizationFailures =
        0;


    twinState.lastSequence =
        null;


    twinState.droppedSequenceCount =
        0;


    twinState.duplicateSequenceCount =
        0;


    twinState.outOfOrderSequenceCount =
        0;


    twinState.lastFrameTimestamp =
        null;


    twinState.lastReceiveTime =
        null;


    twinState.telemetryAgeMs =
        null;


    twinState.history.length =
        0;


    publishTwinState();

}

function ingest(frame) {

    handleTelemetryFrame(
        frame
    );


    return getTwinState();

}

function publishTwinState() {

    const state =
        getTwinState();


    window.dispatchEvent(

        new CustomEvent(

            "pratirup:twin-state",

            {

                detail:
                    state

            }

        )

    );


    window.dispatchEvent(

        new CustomEvent(

            "pratirup:twin-sync",

            {

                detail: {

                    synchronized:

                        state
                            .synchronized,


                    status:

                        state
                            .synchronizationStatus,


                    source:

                        state
                            .activeSource,


                    telemetryAgeMs:

                        state
                            .telemetryAgeMs,


                    residualScore:

                        state
                            .residualScore,


                    residualCoverage:

                        state
                            .residualCoverage,


                    stateConfidence:

                        state
                            .stateConfidence,


                    acceptedFrames:

                        state
                            .acceptedFrames,


                    rejectedFrames:

                        state
                            .rejectedFrames,


                    ignoredEvents:

                        state
                            .ignoredEvents

                }

            }

        )

    );

}
function disposeDigitalTwinCore() {

    window.removeEventListener(

        "pratirup:telemetry",

        handleTelemetryFrame

    );


    if (
        freshnessTimer !== null
    ) {

        window.clearInterval(
            freshnessTimer
        );


        freshnessTimer =
            null;

    }


    twinState.initialized =
        false;


    twinState.synchronized =
        false;


    twinState
        .synchronizationStatus =

        "DISPOSED";

}
window.PRATIRUP_TWIN = {

    version:
        DIGITAL_TWIN_CORE_VERSION,


    VERSION:
        DIGITAL_TWIN_CORE_VERSION,


    CONFIG:
        CORE_CONFIG,


    initialize:
        initializeDigitalTwinCore,


    ingest,


    getState:
        getTwinState,


    getObservedState,


    getExpectedState,


    getResidualState,


    getLatestFrame,


    getHistory,


    clearHistory,


    setExpectedState,


    clearExpectedState,


    setActiveSource,


    calculateResidualState,


    reset:
        resetDigitalTwinCore,


    dispose:
        disposeDigitalTwinCore

};
initializeDigitalTwinCore();
