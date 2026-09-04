(function () {

    "use strict";

    const VERSION = "1.0.0";

    const CONFIG = {

        maximumRULHours: {

            thermal: 500,

            lubrication: 400,

            mechanical: 450,

            combustion: 350,

            fuelInjection: 400,

            electrical: 300

        },

        failureThreshold: 90,

        minimumRate: 0.02,

        smoothingFactor: 0.18,

        minimumSamplesForConfidence: 20,

        maximumRate: 5,

        levels: {

            healthy: 250,

            planMaintenance: 150,

            maintenanceSoon: 75,

            urgent: 25

        }

    };

    let latestResult = null;

    const subsystemRULState = {};

    const history = [];

    let running = true;

    let lastProcessedTime = 0;

    function number(
        value,
        fallback = 0
    ) {

        const result =
            Number(value);

        return Number.isFinite(result)
            ? result
            : fallback;

    }

    function clamp(
        value,
        minimum,
        maximum
    ) {

        return Math.max(
            minimum,
            Math.min(
                maximum,
                value
            )
        );

    }

    function round(
        value,
        digits = 1
    ) {

        if (!Number.isFinite(value)) {

            return 0;

        }

        return Number(
            value.toFixed(digits)
        );

    }

    function getDegradation() {

        const module =
            window.PratirupDegradationTracker;

        if (
            !module ||
            typeof module.getLatest !==
            "function"
        ) {

            return null;

        }

        return module.getLatest();

    }

    function getAnomaly() {

        const module =
            window.PratirupAnomalyDetection;

        if (
            !module ||
            typeof module.getLatest !==
            "function"
        ) {

            return null;

        }

        return module.getLatest();

    }

    function getClassification() {

        const module =
            window.PratirupFaultClassifier;

        if (
            !module ||
            typeof module.getLatest !==
            "function"
        ) {

            return null;

        }

        return module.getLatest();

    }

    function calculateBaselineRUL(
        subsystem,
        degradation
    ) {

        const maximumHours =

            CONFIG.maximumRULHours[
                subsystem
            ] || 300;

        const threshold =
            CONFIG.failureThreshold;

        if (
            degradation >= threshold
        ) {

            return 0;

        }

        const remainingFraction =

            (
                threshold -
                degradation
            )

            /

            threshold;

        return (

            maximumHours *
            remainingFraction

        );

    }

    function calculateTrendRUL(
        subsystem,
        degradation,
        degradationRate
    ) {

        const maximumHours =

            CONFIG.maximumRULHours[
                subsystem
            ] || 300;

        if (
            degradationRate <=
            CONFIG.minimumRate
        ) {

            return maximumHours;

        }

        const safeRate =
            clamp(
                degradationRate,
                CONFIG.minimumRate,
                CONFIG.maximumRate
            );

        const remainingDegradation =

            Math.max(
                0,
                CONFIG.failureThreshold -
                degradation
            );

        const estimatedSamples =

            remainingDegradation /
            safeRate;

        const normalized =

            clamp(
                estimatedSamples / 250,
                0,
                1
            );

        return (

            maximumHours *
            normalized

        );

    }

    function persistenceFactor(
        persistence
    ) {

        const normalized =

            clamp(
                persistence / 100,
                0,
                1
            );

        return (

            1 -
            normalized * 0.25

        );

    }

    function anomalyFactor(
        anomalyScore
    ) {

        const normalized =

            clamp(
                anomalyScore / 100,
                0,
                1
            );

        return (

            1 -
            normalized * 0.20

        );

    }

    function faultFactor(
        subsystem,
        classification
    ) {

        const primary =
            classification
                ?.primaryFault;

        if (!primary) {

            return 1;

        }

        const confidence =

            clamp(
                number(
                    primary.confidence
                ) / 100,
                0,
                1
            );

        const faultSubsystem =

            String(
                primary.subsystem ||
                ""
            )
            .toLowerCase();

        const mapping = {

            thermal:
                [
                    "thermal"
                ],

            lubrication:
                [
                    "lubrication"
                ],

            mechanical:
                [
                    "mechanical"
                ],

            combustion:
                [
                    "combustion"
                ],

            fuelInjection:
                [
                    "fuel",
                    "injection"
                ],

            electrical:
                [
                    "electrical"
                ]

        };

        const keywords =
            mapping[subsystem] ||
            [];

        const matches =
            keywords.some(
                keyword =>
                    faultSubsystem.includes(
                        keyword
                    )
            );

        if (!matches) {

            return 1;

        }

        return (

            1 -
            confidence * 0.25

        );

    }

    function calculateConfidence(
        subsystemData,
        anomalyScore
    ) {

        const samples =
            number(
                subsystemData.samples
            );

        const persistence =
            number(
                subsystemData.persistence
            );

        const degradation =
            number(
                subsystemData.degradation
            );

        const sampleConfidence =

            clamp(

                samples /
                CONFIG.minimumSamplesForConfidence,

                0,

                1

            );

        const persistenceConfidence =

            clamp(
                persistence / 100,
                0,
                1
            );

        const degradationConfidence =

            clamp(
                degradation / 50,
                0,
                1
            );

        const anomalyConfidence =

            clamp(
                anomalyScore / 100,
                0,
                1
            );

        const confidence =

            sampleConfidence * 0.45 +

            persistenceConfidence * 0.25 +

            degradationConfidence * 0.20 +

            anomalyConfidence * 0.10;

        return round(
            confidence * 100,
            1
        );

    }

    function classifyRUL(
        hours
    ) {

        if (
            hours <=
            CONFIG.levels.urgent
        ) {

            return "URGENT";

        }

        if (
            hours <=
            CONFIG.levels.maintenanceSoon
        ) {

            return "MAINTENANCE_SOON";

        }

        if (
            hours <=
            CONFIG.levels.planMaintenance
        ) {

            return "PLAN_MAINTENANCE";

        }

        if (
            hours <=
            CONFIG.levels.healthy
        ) {

            return "MONITOR";

        }

        return "HEALTHY";

    }

    function classifyRULTrend(
        current,
        previous
    ) {

        if (
            !Number.isFinite(previous)
        ) {

            return "STABLE";

        }

        const difference =
            current -
            previous;

        if (
            difference < -10
        ) {

            return "RAPIDLY_DECREASING";

        }

        if (
            difference < -2
        ) {

            return "DECREASING";

        }

        if (
            difference > 5
        ) {

            return "RECOVERING";

        }

        return "STABLE";

    }

    function calculateSubsystemRUL(
        subsystem,
        data,
        anomalyScore,
        classification
    ) {

        const degradation =
            number(
                data.degradation
            );

        const degradationRate =
            number(
                data.degradationRate
            );

        const persistence =
            number(
                data.persistence
            );

        const baselineRUL =
            calculateBaselineRUL(
                subsystem,
                degradation
            );

        const trendRUL =
            calculateTrendRUL(
                subsystem,
                degradation,
                degradationRate
            );

        let estimatedRUL =

            baselineRUL * 0.60 +

            trendRUL * 0.40;

        estimatedRUL *=

            persistenceFactor(
                persistence
            );

        estimatedRUL *=

            anomalyFactor(
                anomalyScore
            );

        estimatedRUL *=

            faultFactor(
                subsystem,
                classification
            );

        const maximumHours =

            CONFIG.maximumRULHours[
                subsystem
            ] || 300;

        estimatedRUL =
            clamp(
                estimatedRUL,
                0,
                maximumHours
            );

        const previous =

            subsystemRULState[
                subsystem
            ];

        let smoothedRUL =
            estimatedRUL;

        if (
            previous &&
            Number.isFinite(
                previous.rulHours
            )
        ) {

            smoothedRUL =

                previous.rulHours *

                (
                    1 -
                    CONFIG.smoothingFactor
                )

                +

                estimatedRUL *

                CONFIG.smoothingFactor;

        }

        const result = {

            subsystem,

            rulHours:
                round(
                    smoothedRUL,
                    1
                ),

            rawRULHours:
                round(
                    estimatedRUL,
                    1
                ),

            maximumHorizonHours:
                maximumHours,

            remainingLifePercent:
                round(

                    (
                        smoothedRUL /
                        maximumHours
                    ) * 100,

                    1

                ),

            degradation:
                round(
                    degradation,
                    1
                ),

            degradationRate:
                round(
                    degradationRate,
                    3
                ),

            persistence:
                round(
                    persistence,
                    1
                ),

            confidence:
                calculateConfidence(
                    data,
                    anomalyScore
                ),

            status:
                classifyRUL(
                    smoothedRUL
                ),

            trend:
                classifyRULTrend(

                    smoothedRUL,

                    previous
                        ?.rulHours

                )

        };

        subsystemRULState[
            subsystem
        ] = result;

        return result;

    }

    function findCriticalSubsystem(
        subsystems
    ) {

        const entries =
            Object.entries(
                subsystems
            );

        if (!entries.length) {

            return null;

        }

        entries.sort(

            (
                [, a],
                [, b]
            ) =>

                a.rulHours -
                b.rulHours

        );

        const [
            name,
            data
        ] = entries[0];

        return {

            name,

            ...data

        };

    }

    function calculateOverallRUL(
        subsystems
    ) {

        const values =
            Object.values(
                subsystems
            )
            .map(
                item =>
                    item.rulHours
            )
            .filter(
                Number.isFinite
            );

        if (!values.length) {

            return 0;

        }

        return Math.min(
            ...values
        );

    }

    function calculateOverallConfidence(
        subsystems
    ) {

        const values =
            Object.values(
                subsystems
            )
            .map(
                item =>
                    item.confidence
            )
            .filter(
                Number.isFinite
            );

        if (!values.length) {

            return 0;

        }

        return round(

            values.reduce(
                (
                    total,
                    value
                ) =>
                    total + value,
                0
            )

            /

            values.length,

            1

        );

    }

    function evaluate(
        degradationInput = null
    ) {

        if (!running) {

            return latestResult;

        }

        const degradation =

            degradationInput ||
            getDegradation();

        if (
            !degradation ||
            !degradation.subsystems
        ) {

            return null;

        }

        const anomaly =
            getAnomaly();

        const classification =
            getClassification();

        const anomalyScore =
            number(
                anomaly?.anomalyScore
            );

        const subsystemResults =
            {};

        Object.entries(
            degradation.subsystems
        )
        .forEach(

            (
                [
                    subsystem,
                    data
                ]
            ) => {

                subsystemResults[
                    subsystem
                ] =
                    calculateSubsystemRUL(

                        subsystem,

                        data,

                        anomalyScore,

                        classification

                    );

            }

        );

        const overallRUL =
            calculateOverallRUL(
                subsystemResults
            );

        const criticalSubsystem =
            findCriticalSubsystem(
                subsystemResults
            );

        const overallConfidence =
            calculateOverallConfidence(
                subsystemResults
            );

        latestResult = {

            timestamp:
                Date.now(),

            overallRULHours:
                round(
                    overallRUL,
                    1
                ),

            status:
                classifyRUL(
                    overallRUL
                ),

            confidence:
                overallConfidence,

            criticalSubsystem,

            subsystems:
                subsystemResults,

            anomalyScore,

            probableFault:

                classification
                    ?.primaryFault
                    ?.label ||

                null,

            degradationLevel:
                degradation.level ||
                "UNKNOWN",

            prototypeEstimate:
                true,

            validatedRUL:
                false

        };

        history.push(
            JSON.parse(
                JSON.stringify(
                    latestResult
                )
            )
        );

        while (
            history.length > 300
        ) {

            history.shift();

        }

        publish(
            latestResult
        );

        return latestResult;

    }

    function publish(
        result
    ) {

        window.dispatchEvent(

            new CustomEvent(
                "pratirup:rul-analysis",
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
            "rulHours",

            `${result.overallRULHours.toFixed(1)} h`
        );

        setText(
            "overviewRul",

            `${result.overallRULHours.toFixed(1)} h`
        );

        setText(
            "rulStatus",

            result.status
        );

        setText(
            "rulConfidence",

            `${result.confidence.toFixed(1)}%`
        );

        if (
            result.criticalSubsystem
        ) {

            setText(
                "rulCriticalSubsystem",

                result
                    .criticalSubsystem
                    .name
                    .toUpperCase()
            );

        }

        const mapping = {

            thermal:
                "rulThermal",

            lubrication:
                "rulLubrication",

            mechanical:
                "rulMechanical",

            combustion:
                "rulCombustion",

            fuelInjection:
                "rulFuel",

            electrical:
                "rulElectrical"

        };

        Object.entries(
            mapping
        )
        .forEach(

            (
                [
                    subsystem,
                    id
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
                    id,

                    `${data.rulHours.toFixed(1)} h`
                );

            }

        );

    }

    window.addEventListener(

        "pratirup:degradation-analysis",

        event => {

            if (
                !event.detail
            ) {

                return;

            }

            const now =
                performance.now();

            if (
                now -
                lastProcessedTime <
                20
            ) {

                return;

            }

            lastProcessedTime =
                now;

            evaluate(
                event.detail
            );

        }

    );

    window.PratirupRULEngine = {

        version:
            VERSION,

        evaluate,

        getLatest() {

            return latestResult;

        },

        getOverallRUL() {

            return latestResult
                ?.overallRULHours ??
                null;

        },

        getSubsystemRUL(
            subsystem
        ) {

            return latestResult
                ?.subsystems
                ?.[subsystem] ||
                null;

        },

        getCriticalSubsystem() {

            return latestResult
                ?.criticalSubsystem ||
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

            latestResult = null;

            history.length = 0;

            Object.keys(
                subsystemRULState
            )
            .forEach(
                key =>
                    delete subsystemRULState[
                        key
                    ]
            );

        },

        config:
            CONFIG

    };

    function initialize() {

        console.info(
            `[PRATIRUP] RUL Engine ${VERSION} ready.`
        );

        const existing =
            getDegradation();

        if (existing) {

            evaluate(
                existing
            );

        }

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
