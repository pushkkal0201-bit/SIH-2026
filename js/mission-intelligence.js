(function () {

    "use strict";

    const VERSION = "1.0.0";

    const CONFIG = {

        riskThresholds: {

            noGo: 75,

            caution: 40

        },

        altitude: {

            normal: 11000,

            elevated: 15000,

            extreme: 17664

        },

        temperature: {

            hot: 40,

            extreme: 50

        },

        load: {

            high: 80,

            extreme: 95

        },

        rulSafetyFactor: 1.5,

        minimumMissionReserveHours: 5

    };

    let latestResult = null;

    const history = [];

    let running = true;

    let missionConfiguration = {

        missionId: null,

        profile: "ENDURANCE",

        durationHours: 4,

        altitudeFt: 10000,

        ambientTemperatureC: 25,

        expectedLoadPercent: 65

    };

    function number(value, fallback = 0) {

        const n = Number(value);

        return Number.isFinite(n)
            ? n
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

    function getRUL() {

        return (
            window.PratirupRULEngine
                ?.getLatest?.()
            || null
        );

    }

    function getMaintenance() {

        return (
            window.PratirupPredictiveMaintenance
                ?.getLatest?.()
            || null
        );

    }

    function getDegradation() {

        return (
            window.PratirupDegradationTracker
                ?.getLatest?.()
            || null
        );

    }

    function getAnomaly() {

        return (
            window.PratirupAnomalyDetection
                ?.getLatest?.()
            || null
        );

    }

    function getFaultClassification() {

        return (
            window.PratirupFaultClassifier
                ?.getLatest?.()
            || null
        );

    }

    function calculateAltitudeRisk(
        altitude
    ) {

        if (
            altitude <=
            CONFIG.altitude.normal
        ) {

            return 0;
        }

        if (
            altitude >=
            CONFIG.altitude.extreme
        ) {

            return 100;
        }

        if (
            altitude >=
            CONFIG.altitude.elevated
        ) {

            return 70;
        }

        return clamp(

            (
                altitude -
                CONFIG.altitude.normal
            )

            /

            (
                CONFIG.altitude.elevated -
                CONFIG.altitude.normal
            )

            * 70

        );

    }

    function calculateTemperatureRisk(
        temperature
    ) {

        if (
            temperature <=
            CONFIG.temperature.hot
        ) {

            return 0;
        }

        if (
            temperature >=
            CONFIG.temperature.extreme
        ) {

            return 100;
        }

        return clamp(

            (
                temperature -
                CONFIG.temperature.hot
            )

            /

            (
                CONFIG.temperature.extreme -
                CONFIG.temperature.hot
            )

            * 100

        );

    }

    function calculateLoadRisk(
        load
    ) {

        if (
            load <=
            CONFIG.load.high
        ) {

            return 0;
        }

        if (
            load >=
            CONFIG.load.extreme
        ) {

            return 100;
        }

        return clamp(

            (
                load -
                CONFIG.load.high
            )

            /

            (
                CONFIG.load.extreme -
                CONFIG.load.high
            )

            * 100

        );

    }

    function calculateRULMargin(
        rulHours,
        missionHours
    ) {

        const requiredHours =

            missionHours *
            CONFIG.rulSafetyFactor

            +

            CONFIG.minimumMissionReserveHours;

        const margin =

            rulHours -
            requiredHours;

        let risk = 0;

        if (margin <= 0) {

            risk = 100;

        }

        else if (
            margin < missionHours
        ) {

            risk = 75;

        }

        else if (
            margin <
            missionHours * 2
        ) {

            risk = 45;

        }

        else {

            risk = 10;

        }

        return {

            availableRULHours:
                round(rulHours),

            requiredRULHours:
                round(requiredHours),

            marginHours:
                round(margin),

            risk

        };

    }

    function maintenanceRisk(
        maintenance
    ) {

        if (!maintenance) {

            return 0;

        }

        switch (
            maintenance.priority
        ) {

            case "CRITICAL":
                return 100;

            case "HIGH":
                return 80;

            case "MEDIUM":
                return 55;

            case "LOW":
                return 25;

            default:
                return 0;

        }

    }

    function faultRisk(
        classification
    ) {

        if (
            !classification
                ?.primaryFault
        ) {

            return 0;

        }

        return clamp(

            number(
                classification
                    .primaryFault
                    .confidence
            )

        );

    }

    function missionProfileRisk(
        profile
    ) {

        switch (
            String(profile)
                .toUpperCase()
        ) {

            case "HIGH_ALTITUDE":
                return 30;

            case "HOT_WEATHER":
                return 30;

            case "RAPID_THROTTLE":
                return 35;

            case "MAX_ENDURANCE":
                return 25;

            case "ENDURANCE":
                return 15;

            case "ISR":
                return 15;

            default:
                return 10;

        }

    }

    function buildReasons(
        data
    ) {

        const reasons = [];

        if (
            data.rulMargin.risk >= 75
        ) {

            reasons.push(
                "Available prototype RUL margin is insufficient for the selected mission."
            );

        }

        if (
            data.degradationRisk >= 50
        ) {

            reasons.push(
                "Persistent engine degradation is present."
            );

        }

        if (
            data.anomalyRisk >= 60
        ) {

            reasons.push(
                "High anomaly activity is currently detected."
            );

        }

        if (
            data.faultRisk >= 60
        ) {

            reasons.push(
                "A probable engine fault has been identified with significant confidence."
            );

        }

        if (
            data.altitudeRisk >= 70
        ) {

            reasons.push(
                "Selected mission altitude introduces elevated propulsion stress."
            );

        }

        if (
            data.temperatureRisk >= 70
        ) {

            reasons.push(
                "Hot-weather operation increases thermal risk."
            );

        }

        if (
            data.loadRisk >= 70
        ) {

            reasons.push(
                "Expected engine load is close to the high-load operating region."
            );

        }

        if (
            data.maintenanceRisk >= 80
        ) {

            reasons.push(
                "Predictive-maintenance assessment recommends inspection before continued mission operation."
            );

        }

        if (!reasons.length) {

            reasons.push(
                "No major propulsion-health restriction is currently identified by the prototype model."
            );

        }

        return reasons;

    }

    function classifyReadiness(
        score,
        maintenance,
        rulMargin
    ) {

        if (
            maintenance
                ?.priority ===
            "CRITICAL"
        ) {

            return "NO-GO";

        }

        if (
            rulMargin.risk >= 100
        ) {

            return "NO-GO";

        }

        if (
            score >=
            CONFIG.riskThresholds.noGo
        ) {

            return "NO-GO";

        }

        if (
            score >=
            CONFIG.riskThresholds.caution
        ) {

            return "CAUTION";

        }

        return "GO";

    }

    function buildRecommendation(
        readiness,
        criticalSubsystem
    ) {

        const subsystem =

            criticalSubsystem
                ?.name
                ?.toUpperCase()

            || "ENGINE";

        switch (
            readiness
        ) {

            case "NO-GO":

                return (
                    `Prototype assessment recommends inspection of the ${subsystem} ` +
                    `condition before committing to the selected mission profile.`
                );

            case "CAUTION":

                return (
                    `Mission may require additional engineering review and enhanced ` +
                    `${subsystem} monitoring because the propulsion risk margin is reduced.`
                );

            default:

                return (
                    "Current prototype health and prognostic indicators show adequate " +
                    "margin for the configured mission. Continue real-time monitoring."
                );

        }

    }

    function evaluate(
        configuration = null
    ) {

        if (!running) {

            return latestResult;

        }

        if (configuration) {

            missionConfiguration = {

                ...missionConfiguration,

                ...configuration

            };

        }

        const rul =
            getRUL();

        const maintenance =
            getMaintenance();

        const degradation =
            getDegradation();

        const anomaly =
            getAnomaly();

        const classification =
            getFaultClassification();

        if (!rul) {

            return null;

        }

        const missionHours =

            Math.max(
                0.1,
                number(
                    missionConfiguration
                        .durationHours,
                    4
                )
            );

        const altitude =

            number(
                missionConfiguration
                    .altitudeFt,
                10000
            );

        const temperature =

            number(
                missionConfiguration
                    .ambientTemperatureC,
                25
            );

        const load =

            number(
                missionConfiguration
                    .expectedLoadPercent,
                65
            );

        const rulMargin =
            calculateRULMargin(

                number(
                    rul.overallRULHours
                ),

                missionHours

            );

        const altitudeRisk =
            calculateAltitudeRisk(
                altitude
            );

        const temperatureRisk =
            calculateTemperatureRisk(
                temperature
            );

        const loadRisk =
            calculateLoadRisk(
                load
            );

        const degradationRisk =

            clamp(
                number(
                    degradation
                        ?.overallDegradation
                )
            );

        const anomalyRisk =

            clamp(
                number(
                    anomaly
                        ?.anomalyScore
                )
            );

        const diagnosedFaultRisk =
            faultRisk(
                classification
            );

        const predictedMaintenanceRisk =
            maintenanceRisk(
                maintenance
            );

        const profileRisk =
            missionProfileRisk(
                missionConfiguration
                    .profile
            );

        const propulsionHealthRisk =

            degradationRisk * 0.30 +

            anomalyRisk * 0.20 +

            diagnosedFaultRisk * 0.20 +

            predictedMaintenanceRisk * 0.30;

        const environmentalRisk =

            altitudeRisk * 0.40 +

            temperatureRisk * 0.30 +

            loadRisk * 0.20 +

            profileRisk * 0.10;

        const missionRisk =

            rulMargin.risk * 0.35 +

            propulsionHealthRisk * 0.40 +

            environmentalRisk * 0.25;

        const boundedRisk =
            round(
                clamp(
                    missionRisk
                ),
                1
            );

        const readiness =
            classifyReadiness(

                boundedRisk,

                maintenance,

                rulMargin

            );

        const riskData = {

            rulMargin,

            degradationRisk:
                round(
                    degradationRisk
                ),

            anomalyRisk:
                round(
                    anomalyRisk
                ),

            faultRisk:
                round(
                    diagnosedFaultRisk
                ),

            maintenanceRisk:
                round(
                    predictedMaintenanceRisk
                ),

            altitudeRisk:
                round(
                    altitudeRisk
                ),

            temperatureRisk:
                round(
                    temperatureRisk
                ),

            loadRisk:
                round(
                    loadRisk
                ),

            profileRisk:
                round(
                    profileRisk
                )

        };

        const reasons =
            buildReasons(
                riskData
            );

        latestResult = {

            timestamp:
                Date.now(),

            missionId:
                missionConfiguration
                    .missionId,

            configuration: {

                ...missionConfiguration

            },

            readiness,

            missionRisk:
                boundedRisk,

            propulsionHealthRisk:
                round(
                    propulsionHealthRisk
                ),

            environmentalRisk:
                round(
                    environmentalRisk
                ),

            rulMargin,

            reasons,

            criticalSubsystem:
                rul
                    .criticalSubsystem ||
                null,

            probableFault:
                classification
                    ?.primaryFault
                    ?.label ||
                null,

            maintenancePriority:
                maintenance
                    ?.priority ||
                "UNKNOWN",

            overallRULHours:
                number(
                    rul.overallRULHours
                ),

            overallDegradation:
                degradationRisk,

            anomalyScore:
                anomalyRisk,

            recommendation:
                buildRecommendation(

                    readiness,

                    rul
                        .criticalSubsystem

                ),

            prototypeDecisionSupport:
                true,

            flightAuthorization:
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
            history.length >
            300
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
                "pratirup:mission-intelligence",
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
            "missionReadiness",

            result.readiness
        );

        setText(
            "overviewMissionReadiness",

            result.readiness
        );

        setText(
            "missionRisk",

            `${result.missionRisk.toFixed(1)}%`
        );

        setText(
            "missionPropulsionRisk",

            `${result.propulsionHealthRisk.toFixed(1)}%`
        );

        setText(
            "missionEnvironmentalRisk",

            `${result.environmentalRisk.toFixed(1)}%`
        );

        setText(
            "missionRulMargin",

            `${result.rulMargin.marginHours.toFixed(1)} h`
        );

        setText(
            "missionAvailableRul",

            `${result.overallRULHours.toFixed(1)} h`
        );

        setText(
            "missionRecommendation",

            result.recommendation
        );

        setText(
            "missionPrimaryReason",

            result.reasons[0] ||
            "--"
        );

        setText(
            "missionFault",

            result.probableFault ||
            "NONE"
        );

        setText(
            "missionMaintenancePriority",

            result.maintenancePriority
        );

    }

    window.addEventListener(

        "pratirup:maintenance-advisory",

        () => {

            evaluate();

        }

    );

    window.addEventListener(

        "pratirup:mission-config",

        event => {

            if (
                event.detail
            ) {

                evaluate(
                    event.detail
                );

            }

        }

    );

    window.PratirupMissionIntelligence = {

        version:
            VERSION,

        evaluate,

        configure(
            configuration
        ) {

            missionConfiguration = {

                ...missionConfiguration,

                ...configuration

            };

            return evaluate();

        },

        getConfiguration() {

            return {

                ...missionConfiguration

            };

        },

        getLatest() {

            return latestResult;

        },

        getReadiness() {

            return latestResult
                ?.readiness ||
                "UNKNOWN";

        },

        getMissionRisk() {

            return latestResult
                ?.missionRisk ??
                null;

        },

        getReasons() {

            return latestResult
                ?.reasons
                ? [
                    ...latestResult.reasons
                ]
                : [];

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

        reset() {

            latestResult = null;

            history.length = 0;

        },

        config:
            CONFIG

    };

    function initialize() {

        console.info(
            `[PRATIRUP] Mission Intelligence ${VERSION} ready.`
        );

        if (
            getRUL()
        ) {

            evaluate();

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
