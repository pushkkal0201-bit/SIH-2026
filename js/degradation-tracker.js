(function () {

    "use strict";

    const VERSION = "1.0.0";

    const CONFIG = {

        historyLength: 300,

        minimumSamples: 15,

        trendWindow: 20,

        smoothingFactor: 0.20,

        recoveryFactor: 0.04,

        persistenceGain: 0.08,

        maximumDegradationRate: 5,

        levels: {

            healthy: 15,

            watch: 30,

            degraded: 50,

            severe: 75,

            critical: 90

        }

    };

    const history = [];

    const subsystemState = {

        thermal: createSubsystem(),

        lubrication: createSubsystem(),

        mechanical: createSubsystem(),

        combustion: createSubsystem(),

        fuelInjection: createSubsystem(),

        electrical: createSubsystem()

    };

    let latestResult = null;

    let running = true;

    let lastProcessedTime = 0;

    function createSubsystem() {

        return {

            degradation: 0,

            previousDegradation: 0,

            degradationRate: 0,

            persistence: 0,

            trend: "STABLE",

            level: "HEALTHY",

            samples: 0

        };

    }

    function number(
        value,
        fallback = 0
    ) {

        const result = Number(value);

        return Number.isFinite(result)
            ? result
            : fallback;

    }

    function clamp(
        value,
        minimum = 0,
        maximum = 100
    ) {

        return Math.max(
            minimum,
            Math.min(
                maximum,
                value
            )
        );

    }

    function average(values) {

        const valid = values
            .map(Number)
            .filter(Number.isFinite);

        if (!valid.length) {

            return 0;

        }

        return valid.reduce(
            (sum, value) =>
                sum + value,
            0
        ) / valid.length;

    }

    function spread(values) {

        const valid = values
            .map(Number)
            .filter(Number.isFinite);

        if (!valid.length) {

            return 0;

        }

        return (
            Math.max(...valid) -
            Math.min(...valid)
        );

    }

    function normalizedRisk(
        value,
        warning,
        critical
    ) {

        if (!Number.isFinite(value)) {

            return 0;

        }

        if (value <= warning) {

            return 0;

        }

        if (value >= critical) {

            return 100;

        }

        return clamp(

            (
                (value - warning) /
                (critical - warning)
            ) * 100

        );

    }

    function inverseRisk(
        value,
        warning,
        critical
    ) {

        if (!Number.isFinite(value)) {

            return 0;

        }

        if (value >= warning) {

            return 0;

        }

        if (value <= critical) {

            return 100;

        }

        return clamp(

            (
                (warning - value) /
                (warning - critical)
            ) * 100

        );

    }

    function degradationLevel(value) {

        if (
            value >=
            CONFIG.levels.critical
        ) {

            return "CRITICAL";

        }

        if (
            value >=
            CONFIG.levels.severe
        ) {

            return "SEVERE";

        }

        if (
            value >=
            CONFIG.levels.degraded
        ) {

            return "DEGRADED";

        }

        if (
            value >=
            CONFIG.levels.watch
        ) {

            return "CAUTION";

        }

        if (
            value >=
            CONFIG.levels.healthy
        ) {

            return "WATCH";

        }

        return "HEALTHY";

    }

    function classifyTrend(rate) {

        if (rate > 1.5) {

            return "RAPIDLY_WORSENING";

        }

        if (rate > 0.35) {

            return "WORSENING";

        }

        if (rate < -1.0) {

            return "RECOVERING";

        }

        if (rate < -0.25) {

            return "IMPROVING";

        }

        return "STABLE";

    }

    function normalizeTelemetry(input) {

        const source =

            input?.telemetry ||

            input?.observed ||

            input?.engine ||

            input ||

            {};

        function value(...keys) {

            for (const key of keys) {

                if (
                    source[key] !== undefined
                ) {

                    const result =
                        Number(
                            source[key]
                        );

                    if (
                        Number.isFinite(
                            result
                        )
                    ) {

                        return result;

                    }

                }

            }

            return 0;

        }

        function cylinders(prefix) {

            if (
                Array.isArray(
                    source[prefix]
                )
            ) {

                return source[prefix]
                    .map(Number)
                    .filter(
                        Number.isFinite
                    );

            }

            return [

                value(`${prefix}1`),

                value(`${prefix}2`),

                value(`${prefix}3`),

                value(`${prefix}4`)

            ];

        }

        return {

            timestamp:
                Date.now(),

            rpm:
                value(
                    "rpm",
                    "engineRPM",
                    "engineRpm"
                ),

            throttle:
                value(
                    "throttle",
                    "throttlePercent"
                ),

            load:
                value(
                    "load",
                    "engineLoad",
                    "loadPercent"
                ),

            power:
                value(
                    "power",
                    "powerKw",
                    "enginePower"
                ),

            cht:
                cylinders("cht"),

            egt:
                cylinders("egt"),

            oilPressure:
                value(
                    "oilPressure",
                    "oilPressureKpa"
                ),

            oilTemperature:
                value(
                    "oilTemperature",
                    "oilTemp"
                ),

            fuelFlow:
                value(
                    "fuelFlow",
                    "fuelFlowKgS"
                ),

            fuelPressure:
                value(
                    "fuelPressure",
                    "fuelPressureKpa"
                ),

            vibration:
                value(
                    "vibration",
                    "vibrationOverall",
                    "vibrationG"
                ),

            batteryVoltage:
                value(
                    "batteryVoltage",
                    "batteryV"
                ),

            alternatorVoltage:
                value(
                    "alternatorVoltage",
                    "alternatorV"
                ),

            injectionTiming:
                value(
                    "injectionTiming",
                    "injectionTimingDeg"
                )

        };

    }

    function getFaultAnalysis() {

        const engine =
            window.PratirupFaultDetection;

        if (
            !engine ||
            typeof engine.getLatest !==
            "function"
        ) {

            return null;

        }

        return engine.getLatest();

    }

    function getAnomalyAnalysis() {

        const engine =
            window.PratirupAnomalyDetection;

        if (
            !engine ||
            typeof engine.getLatest !==
            "function"
        ) {

            return null;

        }

        return engine.getLatest();

    }

    function getClassification() {

        const engine =
            window.PratirupFaultClassifier;

        if (
            !engine ||
            typeof engine.getLatest !==
            "function"
        ) {

            return null;

        }

        return engine.getLatest();

    }

    function faultRisk(
        faultAnalysis,
        faultIds
    ) {

        if (
            !faultAnalysis ||
            !Array.isArray(
                faultAnalysis.faults
            )
        ) {

            return 0;

        }

        let maximum = 0;

        faultAnalysis.faults.forEach(

            fault => {

                if (
                    faultIds.includes(
                        fault.id
                    )
                ) {

                    maximum =
                        Math.max(

                            maximum,

                            number(
                                fault.score
                            ) * 100

                        );

                }

            }

        );

        return maximum;

    }

    function thermalEvidence(
        sample,
        faultAnalysis
    ) {

        const averageCHT =
            average(sample.cht);

        const averageEGT =
            average(sample.egt);

        const chtRisk =
            normalizedRisk(
                averageCHT,
                210,
                255
            );

        const egtRisk =
            normalizedRisk(
                averageEGT,
                760,
                860
            );

        const chtImbalance =
            normalizedRisk(
                spread(sample.cht),
                20,
                50
            );

        const fault =
            faultRisk(

                faultAnalysis,

                [
                    "cooling",
                    "overheating"
                ]

            );

        return clamp(

            chtRisk * 0.30 +

            egtRisk * 0.20 +

            chtImbalance * 0.15 +

            fault * 0.35

        );

    }

    function lubricationEvidence(
        sample,
        faultAnalysis
    ) {

        const pressureRisk =
            inverseRisk(
                sample.oilPressure,
                190,
                110
            );

        const temperatureRisk =
            normalizedRisk(
                sample.oilTemperature,
                110,
                140
            );

        const fault =
            faultRisk(
                faultAnalysis,
                [
                    "lubrication"
                ]
            );

        return clamp(

            pressureRisk * 0.45 +

            temperatureRisk * 0.25 +

            fault * 0.30

        );

    }

    function mechanicalEvidence(
        sample,
        faultAnalysis
    ) {

        const vibrationRisk =
            normalizedRisk(
                sample.vibration,
                1.2,
                2.8
            );

        const fault =
            faultRisk(
                faultAnalysis,
                [
                    "vibration"
                ]
            );

        return clamp(

            vibrationRisk * 0.60 +

            fault * 0.40

        );

    }

    function combustionEvidence(
        sample,
        faultAnalysis
    ) {

        const egtImbalance =
            normalizedRisk(
                spread(sample.egt),
                40,
                100
            );

        const chtImbalance =
            normalizedRisk(
                spread(sample.cht),
                20,
                50
            );

        const fault =
            faultRisk(

                faultAnalysis,

                [
                    "misfire",
                    "combustion-instability"
                ]

            );

        return clamp(

            egtImbalance * 0.30 +

            chtImbalance * 0.20 +

            fault * 0.50

        );

    }

    function fuelInjectionEvidence(
        sample,
        faultAnalysis
    ) {

        const injectorFault =
            faultRisk(
                faultAnalysis,
                [
                    "injector"
                ]
            );

        const egtImbalance =
            normalizedRisk(
                spread(sample.egt),
                45,
                100
            );

        return clamp(

            injectorFault * 0.70 +

            egtImbalance * 0.30

        );

    }

    function electricalEvidence(
        sample,
        faultAnalysis
    ) {

        const batteryRisk =
            inverseRisk(
                sample.batteryVoltage,
                11.8,
                9.5
            );

        const alternatorRisk =
            inverseRisk(
                sample.alternatorVoltage,
                12.8,
                10.5
            );

        const fault =
            faultRisk(
                faultAnalysis,
                [
                    "electrical"
                ]
            );

        return clamp(

            Math.max(
                batteryRisk,
                alternatorRisk
            ) * 0.65 +

            fault * 0.35

        );

    }

    function updateSubsystem(
        name,
        evidence
    ) {

        const state =
            subsystemState[name];

        state.samples++;

        state.previousDegradation =
            state.degradation;

        if (evidence >= 30) {

            state.persistence =
                clamp(
                    state.persistence +
                    CONFIG.persistenceGain * 100
                );

        }

        else {

            state.persistence =
                clamp(
                    state.persistence -
                    CONFIG.recoveryFactor * 100
                );

        }

        const persistenceFactor =

            0.70 +

            (
                state.persistence /
                100
            ) * 0.30;

        const targetDegradation =

            evidence *
            persistenceFactor;

        state.degradation =

            state.degradation *

            (
                1 -
                CONFIG.smoothingFactor
            )

            +

            targetDegradation *

            CONFIG.smoothingFactor;

        state.degradation =
            clamp(
                state.degradation
            );

        let rate =

            state.degradation -
            state.previousDegradation;

        rate =
            Math.max(

                -CONFIG.maximumDegradationRate,

                Math.min(
                    CONFIG.maximumDegradationRate,
                    rate
                )

            );

        state.degradationRate =
            Number(
                rate.toFixed(3)
            );

        state.trend =
            classifyTrend(
                rate
            );

        state.level =
            degradationLevel(
                state.degradation
            );

        return {

            degradation:
                Number(
                    state.degradation
                        .toFixed(2)
                ),

            degradationRate:
                state.degradationRate,

            persistence:
                Number(
                    state.persistence
                        .toFixed(1)
                ),

            trend:
                state.trend,

            level:
                state.level,

            evidence:
                Number(
                    evidence.toFixed(2)
                ),

            samples:
                state.samples

        };

    }

    function calculateHealthIndex(
        degradation
    ) {

        return Number(

            clamp(
                100 -
                degradation
            ).toFixed(1)

        );

    }

    function calculateOverall(
        subsystems
    ) {

        const weights = {

            thermal:
                0.20,

            lubrication:
                0.20,

            mechanical:
                0.18,

            combustion:
                0.18,

            fuelInjection:
                0.14,

            electrical:
                0.10

        };

        let score = 0;

        Object.keys(
            weights
        )
        .forEach(

            key => {

                score +=

                    number(
                        subsystems[key]
                            ?.degradation
                    )

                    *

                    weights[key];

            }

        );

        return clamp(score);

    }

    function findDominantSubsystem(
        subsystems
    ) {

        return Object.entries(
            subsystems
        )
        .sort(

            (
                [, a],
                [, b]
            ) =>

                b.degradation -
                a.degradation

        )[0] || null;

    }

    function evaluate(
        input
    ) {

        if (!running) {

            return latestResult;

        }

        const sample =
            normalizeTelemetry(
                input
            );

        const faultAnalysis =
            getFaultAnalysis();

        const anomalyAnalysis =
            getAnomalyAnalysis();

        const classification =
            getClassification();

        const evidence = {

            thermal:
                thermalEvidence(
                    sample,
                    faultAnalysis
                ),

            lubrication:
                lubricationEvidence(
                    sample,
                    faultAnalysis
                ),

            mechanical:
                mechanicalEvidence(
                    sample,
                    faultAnalysis
                ),

            combustion:
                combustionEvidence(
                    sample,
                    faultAnalysis
                ),

            fuelInjection:
                fuelInjectionEvidence(
                    sample,
                    faultAnalysis
                ),

            electrical:
                electricalEvidence(
                    sample,
                    faultAnalysis
                )

        };

        const subsystems = {};

        Object.entries(
            evidence
        )
        .forEach(

            (
                [
                    subsystem,
                    score
                ]
            ) => {

                subsystems[subsystem] =
                    updateSubsystem(
                        subsystem,
                        score
                    );

                subsystems[
                    subsystem
                ].healthIndex =
                    calculateHealthIndex(

                        subsystems[
                            subsystem
                        ].degradation

                    );

            }

        );

        const overallDegradation =
            calculateOverall(
                subsystems
            );

        const overallHealth =
            calculateHealthIndex(
                overallDegradation
            );

        const dominant =
            findDominantSubsystem(
                subsystems
            );

        latestResult = {

            timestamp:
                Date.now(),

            sampleCount:
                history.length + 1,

            overallDegradation:
                Number(
                    overallDegradation
                        .toFixed(2)
                ),

            overallHealth,

            level:
                degradationLevel(
                    overallDegradation
                ),

            dominantSubsystem:

                dominant

                    ? {

                        name:
                            dominant[0],

                        ...dominant[1]

                    }

                    : null,

            subsystems,

            anomalyScore:
                number(
                    anomalyAnalysis
                        ?.anomalyScore
                ),

            probableFault:
                classification
                    ?.primaryFault
                    ?.label ||
                null,

            telemetry:
                sample

        };

        history.push({

            timestamp:
                latestResult.timestamp,

            overallDegradation:
                latestResult
                    .overallDegradation,

            overallHealth:
                latestResult
                    .overallHealth,

            subsystems:
                JSON.parse(
                    JSON.stringify(
                        subsystems
                    )
                )

        });

        while (
            history.length >
            CONFIG.historyLength
        ) {

            history.shift();

        }

        publish(
            latestResult
        );

        return latestResult;

    }

    function publish(result) {

        window.dispatchEvent(

            new CustomEvent(
                "pratirup:degradation-analysis",
                {

                    detail:
                        result

                }
            )

        );

        updateDashboard(
            result
        );

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

    function updateDashboard(
        result
    ) {

        if (!result) {

            return;

        }

        setText(
            "overallDegradation",

            `${result.overallDegradation.toFixed(1)}%`
        );

        setText(
            "overallHealthIndex",

            `${result.overallHealth.toFixed(1)}%`
        );

        setText(
            "degradationLevel",

            result.level
        );

        if (
            result.dominantSubsystem
        ) {

            setText(
                "dominantDegradation",

                result
                    .dominantSubsystem
                    .name
                    .toUpperCase()
            );

        }

        const mapping = {

            thermal:
                "thermalDegradation",

            lubrication:
                "lubricationDegradation",

            mechanical:
                "mechanicalDegradation",

            combustion:
                "combustionDegradation",

            fuelInjection:
                "fuelDegradation",

            electrical:
                "electricalDegradation"

        };

        Object.entries(
            mapping
        )
        .forEach(

            (
                [
                    subsystem,
                    elementId
                ]
            ) => {

                const data =
                    result
                        .subsystems[
                            subsystem
                        ];

                if (!data) {

                    return;

                }

                setText(
                    elementId,

                    `${data.degradation.toFixed(1)}%`
                );

            }

        );

    }

    function processState(
        input
    ) {

        const now =
            performance.now();

        if (
            now -
            lastProcessedTime <
            30
        ) {

            return;

        }

        lastProcessedTime =
            now;

        evaluate(
            input
        );

    }

    [

        "pratirup:twin-state",

        "pratirup:engine-state",

        "pratirup:telemetry"

    ]
    .forEach(

        eventName => {

            window.addEventListener(

                eventName,

                event => {

                    if (
                        event.detail
                    ) {

                        processState(
                            event.detail
                        );

                    }

                }

            );

        }

    );

    window.addEventListener(

        "pratirup:fault-classification",

        () => {

        }

    );

    window.PratirupDegradationTracker = {

        version:
            VERSION,

        evaluate,

        getLatest() {

            return latestResult;

        },

        getOverallDegradation() {

            return latestResult
                ? latestResult
                    .overallDegradation
                : 0;

        },

        getOverallHealth() {

            return latestResult
                ? latestResult
                    .overallHealth
                : 100;

        },

        getSubsystem(
            name
        ) {

            return latestResult
                ?.subsystems
                ?.[name] ||
                null;

        },

        getHistory() {

            return [
                ...history
            ];

        },

        start() {

            running = true;

        },

        stop() {

            running = false;

        },

        isRunning() {

            return running;

        },

        reset() {

            history.length = 0;

            latestResult = null;

            Object.keys(
                subsystemState
            )
            .forEach(

                key => {

                    subsystemState[key] =
                        createSubsystem();

                }

            );

        },

        config:
            CONFIG

    };

    function initialize() {

        console.info(
            `[PRATIRUP] Degradation Tracker ${VERSION} ready.`
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
                once: true
            }
        );

    }

    else {

        initialize();

    }

})();
