(function () {

    "use strict";

    const VERSION = "1.0.0";

    const CONFIG = {

        priorityThresholds: {

            critical: 85,

            high: 65,

            medium: 40,

            low: 20

        },

        rulThresholds: {

            critical: 25,

            urgent: 75,

            plan: 150,

            monitor: 250

        },

        anomalyThresholds: {

            critical: 80,

            high: 60,

            caution: 40,

            watch: 25

        },

        degradationThresholds: {

            critical: 90,

            severe: 75,

            degraded: 50,

            caution: 30

        }

    };

    let latestResult = null;

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

        if (
            !Number.isFinite(value)
        ) {

            return 0;

        }

        return Number(
            value.toFixed(digits)
        );

    }

    function getRUL() {

        const module =
            window.PratirupRULEngine;

        if (
            !module ||
            typeof module.getLatest !==
            "function"
        ) {

            return null;

        }

        return module.getLatest();

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

    function calculateRULRisk(
        rulHours
    ) {

        if (
            rulHours <=
            CONFIG.rulThresholds.critical
        ) {

            return 100;

        }

        if (
            rulHours <=
            CONFIG.rulThresholds.urgent
        ) {

            return 80;

        }

        if (
            rulHours <=
            CONFIG.rulThresholds.plan
        ) {

            return 60;

        }

        if (
            rulHours <=
            CONFIG.rulThresholds.monitor
        ) {

            return 35;

        }

        return 10;

    }

    function calculateFaultRisk(
        classification
    ) {

        const primary =
            classification
                ?.primaryFault;

        if (!primary) {

            return 0;

        }

        return clamp(
            number(
                primary.confidence
            )
        );

    }

    function calculateMaintenanceRisk(
        rul,
        degradation,
        anomaly,
        classification
    ) {

        const rulRisk =
            calculateRULRisk(

                number(
                    rul?.overallRULHours,
                    999
                )

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

        const faultRisk =
            calculateFaultRisk(
                classification
            );

        const risk =

            rulRisk * 0.35 +

            degradationRisk * 0.30 +

            anomalyRisk * 0.15 +

            faultRisk * 0.20;

        return {

            total:
                round(
                    clamp(risk),
                    1
                ),

            rulRisk:
                round(rulRisk),

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
                    faultRisk
                )

        };

    }

    function classifyPriority(
        risk
    ) {

        if (
            risk >=
            CONFIG.priorityThresholds.critical
        ) {

            return "CRITICAL";

        }

        if (
            risk >=
            CONFIG.priorityThresholds.high
        ) {

            return "HIGH";

        }

        if (
            risk >=
            CONFIG.priorityThresholds.medium
        ) {

            return "MEDIUM";

        }

        if (
            risk >=
            CONFIG.priorityThresholds.low
        ) {

            return "LOW";

        }

        return "ROUTINE";

    }

    function calculateServiceWindow(
        priority,
        rulHours
    ) {

        switch (priority) {

            case "CRITICAL":

                return {
                    code:
                        "IMMEDIATE",

                    label:
                        "Immediate inspection required",

                    targetHours:
                        0
                };

            case "HIGH":

                return {
                    code:
                        "BEFORE_NEXT_MISSION",

                    label:
                        "Inspect before next mission",

                    targetHours:
                        Math.min(
                            10,
                            rulHours
                        )
                };

            case "MEDIUM":

                return {
                    code:
                        "SCHEDULE_SOON",

                    label:
                        "Schedule maintenance soon",

                    targetHours:
                        Math.min(
                            50,
                            rulHours
                        )
                };

            case "LOW":

                return {
                    code:
                        "PLANNED",

                    label:
                        "Include in planned maintenance",

                    targetHours:
                        Math.min(
                            100,
                            rulHours
                        )
                };

            default:

                return {
                    code:
                        "ROUTINE",

                    label:
                        "Continue routine monitoring",

                    targetHours:
                        null
                };

        }

    }

    function determineMissionRestriction(
        priority
    ) {

        switch (priority) {

            case "CRITICAL":

                return {

                    level:
                        "NO-GO",

                    advisory:
                        "Do not recommend a new mission until the detected condition is inspected."

                };

            case "HIGH":

                return {

                    level:
                        "CAUTION",

                    advisory:
                        "Maintenance inspection is recommended before the next mission."

                };

            case "MEDIUM":

                return {

                    level:
                        "MONITOR",

                    advisory:
                        "Mission planning should consider the degrading subsystem and predicted service window."

                };

            case "LOW":

                return {

                    level:
                        "MONITOR",

                    advisory:
                        "Continue enhanced monitoring during subsequent operation."

                };

            default:

                return {

                    level:
                        "GO",

                    advisory:
                        "No significant maintenance restriction indicated by the prototype model."

                };

        }

    }

    const KNOWLEDGE_BASE = {

        misfire: {

            inspection:
                "Inspect cylinder combustion behaviour, ignition inputs and fuel delivery consistency.",

            action:
                "Verify ignition/fuel delivery and compare cylinder EGT/CHT behaviour before further diagnosis."

        },

        injector: {

            inspection:
                "Inspect injector response, fuel delivery balance and injection timing.",

            action:
                "Verify injector performance and compare commanded versus observed fuel/temperature behaviour."

        },

        cooling: {

            inspection:
                "Inspect cooling airflow, cylinder thermal distribution and temperature sensor validity.",

            action:
                "Investigate the source of increasing cylinder-head temperature before extended operation."

        },

        lubrication: {

            inspection:
                "Inspect oil pressure, oil temperature, lubrication circuit and related sensor readings.",

            action:
                "Investigate low-pressure or high-temperature lubrication behaviour before continued high-load operation."

        },

        "sensor-drift": {

            inspection:
                "Cross-check the suspected sensor against redundant or physically related measurements.",

            action:
                "Validate sensor calibration, wiring/data integrity and plausibility before using the signal for maintenance decisions."

        },

        "combustion-instability": {

            inspection:
                "Inspect cylinder-to-cylinder combustion balance using EGT, CHT, vibration and fuel-related evidence.",

            action:
                "Investigate combustion imbalance and identify the cylinder or subsystem producing unstable behaviour."

        },

        overheating: {

            inspection:
                "Inspect thermal loading, cooling performance, operating condition and temperature sensing.",

            action:
                "Reduce thermal stress in the simulation/operation and diagnose the cause of the sustained temperature rise."

        },

        vibration: {

            inspection:
                "Inspect vibration trend and correlate it with RPM, load and combustion behaviour.",

            action:
                "Identify whether the vibration originates from combustion imbalance or a mechanical rotating/reciprocating source."

        },

        electrical: {

            inspection:
                "Inspect battery voltage, alternator output and electrical supply stability.",

            action:
                "Verify charging-system performance and electrical measurements."

        }

    };

    function getRecommendation(
        classification
    ) {

        const fault =
            classification
                ?.primaryFault;

        if (!fault) {

            return {

                fault:
                    null,

                subsystem:
                    null,

                component:
                    null,

                inspection:
                    "Continue monitoring engine health indicators and degradation trends.",

                action:
                    "No fault-specific maintenance action is currently recommended."

            };

        }

        const recommendation =

            KNOWLEDGE_BASE[
                fault.id
            ] ||

            {

                inspection:
                    "Inspect the affected subsystem using available telemetry and maintenance procedures.",

                action:
                    "Perform additional diagnostic verification before maintenance action."

            };

        return {

            fault:
                fault.label,

            faultId:
                fault.id,

            subsystem:
                fault.subsystem,

            component:
                fault.component,

            confidence:
                fault.confidence,

            inspection:
                recommendation.inspection,

            action:
                recommendation.action

        };

    }

    function calculateConfidence(
        rul,
        classification
    ) {

        const rulConfidence =
            number(
                rul?.confidence
            );

        const faultConfidence =
            number(
                classification
                    ?.primaryFault
                    ?.confidence
            );

        if (
            !classification
                ?.primaryFault
        ) {

            return round(
                rulConfidence,
                1
            );

        }

        return round(

            rulConfidence * 0.60 +

            faultConfidence * 0.40,

            1

        );

    }

    function generateAdvisory(
        priority,
        recommendation,
        serviceWindow,
        missionRestriction,
        rul
    ) {

        const rulHours =
            number(
                rul?.overallRULHours
            );

        if (
            priority ===
            "CRITICAL"
        ) {

            return (
                `Critical maintenance condition detected. ` +
                `${recommendation.inspection} ` +
                `Prototype minimum subsystem RUL is approximately ` +
                `${rulHours.toFixed(1)} hours. ` +
                `${missionRestriction.advisory}`
            );

        }

        if (
            priority ===
            "HIGH"
        ) {

            return (
                `High-priority maintenance advisory. ` +
                `${recommendation.fault || "A degrading condition"} ` +
                `requires inspection before the next mission. ` +
                `${recommendation.action}`
            );

        }

        if (
            priority ===
            "MEDIUM"
        ) {

            return (
                `A persistent degradation trend has been detected. ` +
                `${serviceWindow.label}. ` +
                `${recommendation.inspection}`
            );

        }

        if (
            priority ===
            "LOW"
        ) {

            return (
                `Minor degradation is present. Continue enhanced monitoring ` +
                `and include the affected subsystem in planned maintenance.`
            );

        }

        return (
            "No significant predictive-maintenance action is currently indicated. " +
            "Continue routine health monitoring."
        );

    }

    function evaluate(
        rulInput = null
    ) {

        if (!running) {

            return latestResult;

        }

        const rul =
            rulInput ||
            getRUL();

        if (!rul) {

            return null;

        }

        const degradation =
            getDegradation();

        const anomaly =
            getAnomaly();

        const classification =
            getClassification();

        const risk =
            calculateMaintenanceRisk(
                rul,
                degradation,
                anomaly,
                classification
            );

        const priority =
            classifyPriority(
                risk.total
            );

        const recommendation =
            getRecommendation(
                classification
            );

        const serviceWindow =
            calculateServiceWindow(

                priority,

                number(
                    rul.overallRULHours
                )

            );

        const missionRestriction =
            determineMissionRestriction(
                priority
            );

        const confidence =
            calculateConfidence(
                rul,
                classification
            );

        latestResult = {

            timestamp:
                Date.now(),

            priority,

            maintenanceRisk:
                risk.total,

            confidence,

            riskBreakdown:
                risk,

            affectedSubsystem:
                recommendation.subsystem ||
                rul
                    ?.criticalSubsystem
                    ?.name ||
                null,

            affectedComponent:
                recommendation.component ||
                null,

            probableFault:
                recommendation.fault ||
                null,

            inspection:
                recommendation.inspection,

            recommendedAction:
                recommendation.action,

            serviceWindow,

            missionRestriction,

            overallRULHours:
                number(
                    rul.overallRULHours
                ),

            criticalSubsystem:
                rul.criticalSubsystem ||
                null,

            overallDegradation:
                number(
                    degradation
                        ?.overallDegradation
                ),

            anomalyScore:
                number(
                    anomaly
                        ?.anomalyScore
                ),

            advisory:
                null,

            prototypeAdvisory:
                true,

            validatedMaintenanceDecision:
                false

        };

        latestResult.advisory =
            generateAdvisory(

                priority,

                recommendation,

                serviceWindow,

                missionRestriction,

                rul

            );

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
                "pratirup:maintenance-advisory",
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
            "maintenancePriority",

            result.priority
        );

        setText(
            "maintenanceRisk",

            `${result.maintenanceRisk.toFixed(1)}%`
        );

        setText(
            "maintenanceConfidence",

            `${result.confidence.toFixed(1)}%`
        );

        setText(
            "maintenanceSubsystem",

            result.affectedSubsystem
                ? String(
                    result.affectedSubsystem
                ).toUpperCase()
                : "--"
        );

        setText(
            "maintenanceComponent",

            result.affectedComponent ||
            "--"
        );

        setText(
            "maintenanceFault",

            result.probableFault ||
            "NONE"
        );

        setText(
            "maintenanceInspection",

            result.inspection
        );

        setText(
            "maintenanceAction",

            result.recommendedAction
        );

        setText(
            "maintenanceServiceWindow",

            result
                .serviceWindow
                .label
        );

        setText(
            "maintenanceMissionStatus",

            result
                .missionRestriction
                .level
        );

        setText(
            "maintenanceAdvisory",

            result.advisory
        );

        setText(
            "overviewMaintenance",

            result.priority
        );

        setText(
            "missionReadiness",

            result
                .missionRestriction
                .level
        );

    }

    window.addEventListener(

        "pratirup:rul-analysis",

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

    window.PratirupPredictiveMaintenance = {

        version:
            VERSION,

        evaluate,

        getLatest() {

            return latestResult;

        },

        getPriority() {

            return latestResult
                ?.priority ||
                "UNKNOWN";

        },

        getMissionRestriction() {

            return latestResult
                ?.missionRestriction ||
                null;

        },

        getRecommendedAction() {

            return latestResult
                ?.recommendedAction ||
                null;

        },

        getServiceWindow() {

            return latestResult
                ?.serviceWindow ||
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

        },

        config:
            CONFIG

    };

    function initialize() {

        console.info(
            `[PRATIRUP] Predictive Maintenance Engine ${VERSION} ready.`
        );

        const existing =
            getRUL();

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
