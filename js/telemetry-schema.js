"use strict";

const TELEMETRY_SCHEMA_VERSION = "2.0.0";
const DATA_SOURCES = Object.freeze({
    SIMULATION: "simulation",
    REAL_ENGINE: "real-engine",
    CAN: "can",
    FADEC: "fadec",
    REPLAY: "replay",
    UNKNOWN: "unknown"
});

const OPERATING_MODES = Object.freeze({
    IDLE: "idle",
    ENGINE_START: "engine_start",
    WARMUP: "warmup",
    TAKEOFF: "takeoff",
    CLIMB: "climb",
    CRUISE: "cruise",
    HIGH_ALTITUDE: "high_altitude",
    ENDURANCE: "endurance",
    DESCENT: "descent",
    LANDING: "landing",
    ENGINE_SHUTDOWN: "engine_shutdown",
    TEST: "test",
    UNKNOWN: "unknown"
});

function cloneValue(value) {

    if (
        value === null ||
        value === undefined
    ) {

        return value;

    }


    if (
        typeof structuredClone === "function"
    ) {

        return structuredClone(value);

    }


    return JSON.parse(
        JSON.stringify(value)
    );

}


function firstDefined(...values) {

    for (const value of values) {

        if (value !== undefined) {

            return value;

        }

    }


    return undefined;

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


function safeInteger(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {

        return null;

    }


    const number =
        Number(value);


    return Number.isInteger(number)
        ? number
        : null;

}


function safeBoolean(
    value,
    fallback = false
) {

    if (
        value === null ||
        value === undefined
    ) {

        return fallback;

    }


    return Boolean(value);

}


function safeString(
    value,
    fallback = null
) {

    if (
        value === null ||
        value === undefined
    ) {

        return fallback;

    }


    return String(value);

}


function safeArray(value) {

    return Array.isArray(value)
        ? cloneValue(value)
        : [];

}

function createTelemetryFrame(
    source = DATA_SOURCES.UNKNOWN
) {

    return {

    
        meta: {

            schemaVersion:
                TELEMETRY_SCHEMA_VERSION,

            timestamp:
                Date.now(),

            sequence:
                0,

            source,

            valid:
                true

        },

        engine: {

            rpm:
                null,

            throttlePercent:
                null,

            loadPercent:
                null,

            powerKw:
                null,

            torqueNm:
                null,

            operatingMode:
                OPERATING_MODES.UNKNOWN

        },

        cht: {

            cylinder1C:
                null,

            cylinder2C:
                null,

            cylinder3C:
                null,

            cylinder4C:
                null,

            averageC:
                null,

            maximumC:
                null

        },

        egt: {

            cylinder1C:
                null,

            cylinder2C:
                null,

            cylinder3C:
                null,

            cylinder4C:
                null,

            averageC:
                null,

            maximumC:
                null

        },

        oil: {

            pressureKPa:
                null,

            temperatureC:
                null

        },

        fuel: {

            flowKgPerSecond:
                null,

            pressureKPa:
                null,

            injectionTimingDeg:
                null

        },


        vibration: {

            overallG:
                null,

            xG:
                null,

            yG:
                null,

            zG:
                null

        },


        electrical: {

            batteryVoltageV:
                null,

            batteryCurrentA:
                null,

            alternatorVoltageV:
                null,

            alternatorCurrentA:
                null

        },

        environment: {

            altitudeM:
                null,

            ambientTemperatureC:
                null,

            ambientPressurePa:
                null,

            airDensityKgM3:
                null

        },

        mission: {

            missionId:
                null,

            elapsedTimeSec:
                null,

            phase:
                null

        },


        twin: {

            synchronized:
                false,

            stateConfidence:
                null,

            residualScore:
                null

        },

        health: {

            overallIndex:
                null,

            combustion:
                null,

            lubrication:
                null,

            cooling:
                null,

            fuelSystem:
                null,

            electrical:
                null,

            vibration:
                null

        },


       
        diagnostics: {

            anomalyDetected:
                false,

            anomalyScore:
                null,

            activeFaults:
                [],

            probableFaults:
                []

        },


        prediction: {

            degradationRate:
                null,

            rulHours:
                null,

            confidence:
                null,

            maintenanceRecommendation:
                null

        }

    };

}


function validateTelemetryFrame(frame) {

    const errors = [];


    if (
        !frame ||
        typeof frame !== "object"
    ) {

        return {

            valid:
                false,

            errors: [
                "Telemetry frame must be an object."
            ]

        };

    }


    const requiredSections = [

        [
            "meta",
            "meta"
        ],

        [
            "engine",
            "engine"
        ],

        [
            "cht",
            "CHT"
        ],

        [
            "egt",
            "EGT"
        ],

        [
            "oil",
            "oil"
        ],

        [
            "fuel",
            "fuel"
        ],

        [
            "vibration",
            "vibration"
        ],

        [
            "electrical",
            "electrical"
        ]

    ];


    for (
        const [
            key,
            label
        ]
        of requiredSections
    ) {

        if (
            !frame[key] ||
            typeof frame[key] !== "object"
        ) {

            errors.push(
                `Missing ${label} section.`
            );

        }

    }


    return {

        valid:
            errors.length === 0,

        errors

    };

}

function normalizeTelemetryFrame(frame) {

    if (
        !frame ||
        typeof frame !== "object"
    ) {

        return null;

    }


    const source =
        firstDefined(
            frame.meta?.source,
            DATA_SOURCES.UNKNOWN
        );


    const normalized =
        createTelemetryFrame(

            safeString(
                source,
                DATA_SOURCES.UNKNOWN
            )

        );

    normalized.meta.schemaVersion =

        safeString(

            firstDefined(
                frame.meta?.schemaVersion,
                frame.meta?.schema_version
            ),

            TELEMETRY_SCHEMA_VERSION

        );


    normalized.meta.timestamp =

        firstDefined(
            frame.meta?.timestamp,
            Date.now()
        );


    const sequence =

        safeInteger(

            firstDefined(
                frame.meta?.sequence,
                frame.sequence
            )

        );


    normalized.meta.sequence =
        sequence ?? 0;


    normalized.meta.source =

        safeString(

            firstDefined(
                frame.meta?.source,
                source
            ),

            DATA_SOURCES.UNKNOWN

        );


    normalized.meta.valid =

        safeBoolean(

            firstDefined(
                frame.meta?.valid,
                true
            ),

            true

        );

    normalized.engine.rpm =

        safeNumber(

            firstDefined(
                frame.engine?.rpm
            )

        );


    normalized.engine.throttlePercent =

        safeNumber(

            firstDefined(
                frame.engine?.throttlePercent,
                frame.engine?.throttle_percent
            )

        );


    normalized.engine.loadPercent =

        safeNumber(

            firstDefined(
                frame.engine?.loadPercent,
                frame.engine?.load_percent
            )

        );


    normalized.engine.powerKw =

        safeNumber(

            firstDefined(
                frame.engine?.powerKw,
                frame.engine?.power_kw
            )

        );


    normalized.engine.torqueNm =

        safeNumber(

            firstDefined(
                frame.engine?.torqueNm,
                frame.engine?.torque_nm
            )

        );


    normalized.engine.operatingMode =

        safeString(

            firstDefined(
                frame.engine?.operatingMode,
                frame.engine?.operating_mode
            ),

            OPERATING_MODES.UNKNOWN

        );

    normalized.cht.cylinder1C =

        safeNumber(

            firstDefined(
                frame.cht?.cylinder1C,
                frame.cht?.cylinder_1_c
            )

        );


    normalized.cht.cylinder2C =

        safeNumber(

            firstDefined(
                frame.cht?.cylinder2C,
                frame.cht?.cylinder_2_c
            )

        );


    normalized.cht.cylinder3C =

        safeNumber(

            firstDefined(
                frame.cht?.cylinder3C,
                frame.cht?.cylinder_3_c
            )

        );


    normalized.cht.cylinder4C =

        safeNumber(

            firstDefined(
                frame.cht?.cylinder4C,
                frame.cht?.cylinder_4_c
            )

        );


    normalized.cht.averageC =

        safeNumber(

            firstDefined(
                frame.cht?.averageC,
                frame.cht?.average_c
            )

        );


    normalized.cht.maximumC =

        safeNumber(

            firstDefined(
                frame.cht?.maximumC,
                frame.cht?.maximum_c,
                frame.cht?.max_c
            )

        );

    normalized.egt.cylinder1C =

        safeNumber(

            firstDefined(
                frame.egt?.cylinder1C,
                frame.egt?.cylinder_1_c
            )

        );


    normalized.egt.cylinder2C =

        safeNumber(

            firstDefined(
                frame.egt?.cylinder2C,
                frame.egt?.cylinder_2_c
            )

        );


    normalized.egt.cylinder3C =

        safeNumber(

            firstDefined(
                frame.egt?.cylinder3C,
                frame.egt?.cylinder_3_c
            )

        );


    normalized.egt.cylinder4C =

        safeNumber(

            firstDefined(
                frame.egt?.cylinder4C,
                frame.egt?.cylinder_4_c
            )

        );


    normalized.egt.averageC =

        safeNumber(

            firstDefined(
                frame.egt?.averageC,
                frame.egt?.average_c
            )

        );


    normalized.egt.maximumC =

        safeNumber(

            firstDefined(
                frame.egt?.maximumC,
                frame.egt?.maximum_c,
                frame.egt?.max_c
            )

        );

    normalized.oil.pressureKPa =

        safeNumber(

            firstDefined(
                frame.oil?.pressureKPa,
                frame.oil?.pressure_kpa
            )

        );


    normalized.oil.temperatureC =

        safeNumber(

            firstDefined(
                frame.oil?.temperatureC,
                frame.oil?.temperature_c
            )

        );

    normalized.fuel.flowKgPerSecond =

        safeNumber(

            firstDefined(
                frame.fuel?.flowKgPerSecond,
                frame.fuel?.flow_kg_per_second
            )

        );


    normalized.fuel.pressureKPa =

        safeNumber(

            firstDefined(
                frame.fuel?.pressureKPa,
                frame.fuel?.pressure_kpa
            )

        );

    normalized.fuel.injectionTimingDeg =

        safeNumber(

            firstDefined(

                frame.fuel
                    ?.injectionTimingDeg,

                frame.fuel
                    ?.injection_timing_deg,

                frame.injection
                    ?.timingDeg,

                frame.injection
                    ?.timing_deg

            )

        );

    normalized.vibration.overallG =

        safeNumber(

            firstDefined(
                frame.vibration?.overallG,
                frame.vibration?.overall_g
            )

        );


    normalized.vibration.xG =

        safeNumber(

            firstDefined(
                frame.vibration?.xG,
                frame.vibration?.x_g
            )

        );


    normalized.vibration.yG =

        safeNumber(

            firstDefined(
                frame.vibration?.yG,
                frame.vibration?.y_g
            )

        );


    normalized.vibration.zG =

        safeNumber(

            firstDefined(
                frame.vibration?.zG,
                frame.vibration?.z_g
            )

        );

    normalized.electrical.batteryVoltageV =

        safeNumber(

            firstDefined(
                frame.electrical
                    ?.batteryVoltageV,

                frame.electrical
                    ?.battery_voltage_v
            )

        );


    normalized.electrical.batteryCurrentA =

        safeNumber(

            firstDefined(
                frame.electrical
                    ?.batteryCurrentA,

                frame.electrical
                    ?.battery_current_a
            )

        );


    normalized.electrical.alternatorVoltageV =

        safeNumber(

            firstDefined(
                frame.electrical
                    ?.alternatorVoltageV,

                frame.electrical
                    ?.alternator_voltage_v
            )

        );


    normalized.electrical.alternatorCurrentA =

        safeNumber(

            firstDefined(
                frame.electrical
                    ?.alternatorCurrentA,

                frame.electrical
                    ?.alternator_current_a
            )

        );

    normalized.environment.altitudeM =

        safeNumber(

            firstDefined(
                frame.environment?.altitudeM,
                frame.environment?.altitude_m
            )

        );


    normalized.environment
        .ambientTemperatureC =

        safeNumber(

            firstDefined(
                frame.environment
                    ?.ambientTemperatureC,

                frame.environment
                    ?.ambient_temperature_c
            )

        );


    normalized.environment
        .ambientPressurePa =

        safeNumber(

            firstDefined(
                frame.environment
                    ?.ambientPressurePa,

                frame.environment
                    ?.ambient_pressure_pa
            )

        );


    normalized.environment
        .airDensityKgM3 =

        safeNumber(

            firstDefined(
                frame.environment
                    ?.airDensityKgM3,

                frame.environment
                    ?.air_density_kg_m3
            )

        );

    normalized.mission.missionId =

        firstDefined(
            frame.mission?.missionId,
            frame.mission?.mission_id,
            null
        );


    normalized.mission.elapsedTimeSec =

        safeNumber(

            firstDefined(
                frame.mission
                    ?.elapsedTimeSec,

                frame.mission
                    ?.elapsed_time_sec
            )

        );


    normalized.mission.phase =

        firstDefined(
            frame.mission?.phase,
            null
        );

    if (
        frame.twin &&
        typeof frame.twin === "object"
    ) {

        normalized.twin.synchronized =

            safeBoolean(

                firstDefined(
                    frame.twin?.synchronized,
                    normalized.twin
                        .synchronized
                ),

                false

            );


        normalized.twin.stateConfidence =

            safeNumber(

                firstDefined(
                    frame.twin
                        ?.stateConfidence,

                    frame.twin
                        ?.state_confidence
                )

            );


        normalized.twin.residualScore =

            safeNumber(

                firstDefined(
                    frame.twin
                        ?.residualScore,

                    frame.twin
                        ?.residual_score
                )

            );

    }

    if (
        frame.health &&
        typeof frame.health === "object"
    ) {

        normalized.health = {

            ...normalized.health,

            ...cloneValue(
                frame.health
            )

        };

    }

    if (
        frame.diagnostics &&
        typeof frame.diagnostics === "object"
    ) {

        normalized.diagnostics = {

            ...normalized.diagnostics,

            ...cloneValue(
                frame.diagnostics
            )

        };


        normalized.diagnostics.activeFaults =

            safeArray(

                firstDefined(
                    frame.diagnostics
                        ?.activeFaults,

                    frame.diagnostics
                        ?.active_faults
                )

            );


        normalized.diagnostics.probableFaults =

            safeArray(

                firstDefined(
                    frame.diagnostics
                        ?.probableFaults,

                    frame.diagnostics
                        ?.probable_faults
                )

            );

    }

    if (
        frame.prediction &&
        typeof frame.prediction === "object"
    ) {

        normalized.prediction = {

            ...normalized.prediction,

            ...cloneValue(
                frame.prediction
            )

        };

    }


    return normalized;

}

function stampTelemetryFrame(
    frame,
    sequence = null
) {

    if (!frame?.meta) {

        return frame;

    }


    frame.meta.timestamp =
        Date.now();


    if (
        Number.isInteger(sequence)
    ) {

        frame.meta.sequence =
            sequence;

    }


    return frame;

}

function cloneTelemetryFrame(frame) {

    return cloneValue(frame);

}

window.PRATIRUP_TELEMETRY_SCHEMA = {

    version:
        TELEMETRY_SCHEMA_VERSION,


    DATA_SOURCES,

    OPERATING_MODES,


    create:
        createTelemetryFrame,


    validate:
        validateTelemetryFrame,


    normalize:
        normalizeTelemetryFrame,


    stamp:
        stampTelemetryFrame,


    clone:
        cloneTelemetryFrame,


    safeNumber

};

window.dispatchEvent(

    new CustomEvent(

        "pratirup:telemetry-schema-ready",

        {

            detail: {

                version:
                    TELEMETRY_SCHEMA_VERSION

            }

        }

    )

);


console.log(
    `[PRATIRUP] Telemetry Schema ${TELEMETRY_SCHEMA_VERSION} ready.`
);


console.log(
    "[PRATIRUP] Backend snake_case + frontend camelCase normalization enabled."
);


console.log(
    "[PRATIRUP] Injection timing canonical location: fuel.injectionTimingDeg."
);
