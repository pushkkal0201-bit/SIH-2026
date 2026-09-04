(function () {

    "use strict";

    const VERSION =
        "1.0.0";

    const CONFIG = {

        minimumConfidenceForFault:
            30,

        confirmedConfidence:
            70,

        highConfidence:
            85,

        anomalyInfluence:
            0.25,

        diagnosticInfluence:
            0.75

    };

    let latestFaultAnalysis =
        null;

    let latestAnomalyAnalysis =
        null;

    let latestClassification =
        null;

    let enabled =
        true;

    function num(
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
        minimum = 0,
        maximum = 100
    ) {

        return Math.min(
            maximum,
            Math.max(
                minimum,
                value
            )
        );

    }

    const FAULT_METADATA = {

        "misfire": {

            label:
                "Misfire Condition",

            subsystem:
                "Combustion",

            component:
                "Cylinder / Ignition / Injection",

            recommendation:
                "Inspect cylinder combustion, ignition and injector behaviour."

        },

        "injector": {

            label:
                "Injector Abnormality",

            subsystem:
                "Fuel / Injection",

            component:
                "Fuel Injector",

            recommendation:
                "Inspect injector pulse, fuel delivery and cylinder temperature imbalance."

        },

        "cooling": {

            label:
                "Cooling Degradation",

            subsystem:
                "Thermal",

            component:
                "Cylinder Cooling System",

            recommendation:
                "Inspect cooling effectiveness and sustained CHT behaviour."

        },

        "lubrication": {

            label:
                "Lubrication Issue",

            subsystem:
                "Lubrication",

            component:
                "Oil System",

            recommendation:
                "Inspect oil pressure, temperature, pump condition and lubrication circuit."

        },

        "sensor-drift": {

            label:
                "Sensor Drift / Failure",

            subsystem:
                "Instrumentation",

            component:
                "Engine Sensor",

            recommendation:
                "Validate sensor plausibility, wiring and calibration."

        },

        "combustion-instability": {

            label:
                "Combustion Instability",

            subsystem:
                "Combustion",

            component:
                "Cylinder / Combustion System",

            recommendation:
                "Inspect mixture quality, injection consistency and cylinder imbalance."

        },

        "overheating": {

            label:
                "Overheating Trend",

            subsystem:
                "Thermal",

            component:
                "Engine Thermal System",

            recommendation:
                "Investigate increasing CHT/EGT and cooling effectiveness."

        },

        "vibration": {

            label:
                "Abnormal Vibration",

            subsystem:
                "Mechanical",

            component:
                "Rotating / Reciprocating Assembly",

            recommendation:
                "Inspect mechanical balance, mounts and rotating components."

        },

        "electrical": {

            label:
                "Electrical Health Issue",

            subsystem:
                "Electrical",

            component:
                "Battery / Alternator",

            recommendation:
                "Inspect charging system, alternator and battery condition."

        }

    };

    function getFaultResult() {

        if (
            latestFaultAnalysis
        ) {

            return latestFaultAnalysis;

        }

        return window
            .PratirupFaultDetection
            ?.getLatest?.() ||
            null;

    }

    function getAnomalyResult() {

        if (
            latestAnomalyAnalysis
        ) {

            return latestAnomalyAnalysis;

        }

        return window
            .PratirupAnomalyDetection
            ?.getLatest?.() ||
            null;

    }

    function normalizeFaultScore(
        fault
    ) {

        if (!fault) {

            return 0;

        }

        const rawScore =
            num(
                fault.score
            );

        if (
            rawScore <= 1
        ) {

            return clamp(
                rawScore *
                100
            );

        }

        return clamp(
            rawScore
        );

    }

    function calculateConfidence(
        faultScore,
        anomalyScore
    ) {

        return clamp(

            faultScore *
            CONFIG
                .diagnosticInfluence +

            anomalyScore *
            CONFIG
                .anomalyInfluence

        );

    }

    function confidenceBand(
        confidence
    ) {

        if (
            confidence >=
            CONFIG.highConfidence
        ) {

            return "HIGH";

        }

        if (
            confidence >=
            CONFIG.confirmedConfidence
        ) {

            return "MODERATE";

        }

        if (
            confidence >=
            CONFIG.minimumConfidenceForFault
        ) {

            return "LOW";

        }

        return "INSUFFICIENT";

    }

    function buildExplanation(
        classification
    ) {

        if (
            !classification ||
            !classification.detected
        ) {

            return (
                "No significant fault pattern is currently supported " +
                "by the available diagnostic and anomaly evidence."
            );

        }

        const evidence =
            classification
                .evidence ||
            [];

        let explanation =

            `${classification.faultName} is currently the highest-ranked diagnostic condition ` +

            `with ${classification.confidence.toFixed(1)}% confidence.`;

        if (
            evidence.length
        ) {

            explanation +=

                " Supporting evidence includes " +

                evidence
                    .slice(
                        0,
                        3
                    )
                    .join(
                        "; "
                    ) +

                ".";

        }

        explanation +=

            ` The affected subsystem is identified as ${classification.subsystem}.`;

        return explanation;

    }

    function rankFaults(
        faultAnalysis,
        anomalyAnalysis
    ) {

        const faults =
            Array.isArray(
                faultAnalysis
                    ?.faults
            )

                ? faultAnalysis.faults

                : [];

        const anomalyScore =
            num(
                anomalyAnalysis
                    ?.anomalyScore
            );

        return faults
            .map(
                fault => {

                    const faultScore =
                        normalizeFaultScore(
                            fault
                        );

                    const confidence =
                        calculateConfidence(
                            faultScore,
                            anomalyScore
                        );

                    const metadata =

                        FAULT_METADATA[
                            fault.id
                        ] ||

                        {

                            label:
                                fault.name ||
                                fault.id ||
                                "Unknown Fault",

                            subsystem:
                                fault.subsystem ||
                                "Unknown",

                            component:
                                "Unknown",

                            recommendation:
                                "Further diagnostic investigation required."

                        };

                    return {

                        id:
                            fault.id,

                        name:
                            metadata.label,

                        subsystem:
                            metadata.subsystem,

                        component:
                            metadata.component,

                        diagnosticScore:
                            Number(
                                faultScore
                                    .toFixed(1)
                            ),

                        anomalyScore:
                            Number(
                                anomalyScore
                                    .toFixed(1)
                            ),

                        confidence:
                            Number(
                                confidence
                                    .toFixed(1)
                            ),

                        confidenceBand:
                            confidenceBand(
                                confidence
                            ),

                        severity:
                            fault.severity ||
                            "UNKNOWN",

                        evidence:
                            Array.isArray(
                                fault.evidence
                            )

                                ? [
                                    ...fault.evidence
                                  ]

                                : [],

                        recommendation:
                            metadata
                                .recommendation

                    };

                }
            )
            .sort(
                (
                    a,
                    b
                ) =>

                    b.confidence -
                    a.confidence

            );

    }

    function classify() {

        if (
            !enabled
        ) {

            return latestClassification;

        }

        const faultAnalysis =
            getFaultResult();

        const anomalyAnalysis =
            getAnomalyResult();

        if (
            !faultAnalysis &&
            !anomalyAnalysis
        ) {

            latestClassification = {

                timestamp:
                    Date.now(),

                detected:
                    false,

                status:
                    "WAITING_FOR_DATA",

                faultId:
                    null,

                faultName:
                    null,

                confidence:
                    0,

                confidenceBand:
                    "INSUFFICIENT",

                rankedFaults:
                    [],

                explanation:
                    "Waiting for diagnostic and anomaly data."

            };

            publish(
                latestClassification
            );

            return latestClassification;

        }

        const rankedFaults =
            rankFaults(
                faultAnalysis,
                anomalyAnalysis
            );

        const best =
            rankedFaults[0] ||
            null;

        const detected =

            Boolean(best) &&

            best.confidence >=
            CONFIG
                .minimumConfidenceForFault;

        const classification = {

            timestamp:
                Date.now(),

            detected,

            status:

                detected

                    ? "FAULT_PATTERN_DETECTED"

                    : "NO_SIGNIFICANT_FAULT",

            faultId:

                detected
                    ? best.id
                    : null,

            faultName:

                detected
                    ? best.name
                    : "No Significant Fault",

            subsystem:

                detected
                    ? best.subsystem
                    : null,

            affectedComponent:

                detected
                    ? best.component
                    : null,

            confidence:

                detected
                    ? best.confidence
                    : 0,

            confidenceBand:

                detected
                    ? best.confidenceBand
                    : "INSUFFICIENT",

            severity:

                detected
                    ? best.severity
                    : "NORMAL",

            anomalyScore:
                num(
                    anomalyAnalysis
                        ?.anomalyScore
                ),

            evidence:

                detected
                    ? best.evidence
                    : [],

            recommendation:

                detected
                    ? best.recommendation
                    : "Continue monitoring.",

            rankedFaults

        };

        classification.explanation =
            buildExplanation(
                classification
            );

        latestClassification =
            classification;

        publish(
            classification
        );

        return classification;

    }

    function publish(
        result
    ) {

        window.dispatchEvent(

            new CustomEvent(
                "pratirup:fault-classification",
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

        if (
            element
        ) {

            element.textContent =
                value;

        }

    }

    function updateDashboard(
        result
    ) {

        if (
            !result
        ) {

            return;

        }

        setText(
            "aiLikelyFault",
            result.faultName ||
            "NO SIGNIFICANT FAULT"
        );

        setText(
            "aiAffectedComponent",
            result.affectedComponent ||
            "--"
        );

        setText(
            "aiFaultConfidence",

            result.detected

                ? `${result.confidence.toFixed(1)}%`

                : "--"
        );

        setText(
            "aiExplanation",
            result.explanation
        );

        setText(
            "overviewLikelyFault",

            result.detected

                ? result.faultName

                : "NONE"
        );

        setText(
            "overviewAiConfidence",

            result.detected

                ? `${result.confidence.toFixed(1)}%`

                : "--"
        );

        const evidence =
            result.evidence ||
            [];

        setText(
            "aiEvidence1",
            evidence[0] ||
            "--"
        );

        setText(
            "aiEvidence2",
            evidence[1] ||
            "--"
        );

        setText(
            "aiEvidence3",
            evidence[2] ||
            "--"
        );

        const map = {

            misfire:
                "probMisfire",

            injector:
                "probInjector",

            lubrication:
                "probLubrication",

            cooling:
                "probCooling",

            "sensor-drift":
                "probSensorDrift"

        };

        Object.entries(
            map
        )
        .forEach(
            (
                [
                    faultId,
                    elementId
                ]
            ) => {

                const fault =
                    result.rankedFaults
                        ?.find(
                            item =>
                                item.id ===
                                faultId
                        );

                setText(

                    elementId,

                    fault

                        ? `${fault.confidence.toFixed(1)}%`

                        : "--"

                );

            }
        );

        setText(
            "aiModelStatus",
            "PROTOTYPE ACTIVE"
        );

    }

    window.addEventListener(

        "pratirup:fault-analysis",

        event => {

            latestFaultAnalysis =
                event.detail ||
                null;

            classify();

        }

    );

    window.addEventListener(

        "pratirup:anomaly-analysis",

        event => {

            latestAnomalyAnalysis =
                event.detail ||
                null;

            classify();

        }

    );

    window.PratirupFaultClassifier = {

        version:
            VERSION,

        classify,

        getLatest() {

            return latestClassification;

        },

        getRankedFaults() {

            return latestClassification
                ?.rankedFaults

                ? [
                    ...latestClassification
                        .rankedFaults
                  ]

                : [];

        },

        getMostLikelyFault() {

            return latestClassification
                ?.detected

                ? {

                    id:
                        latestClassification
                            .faultId,

                    name:
                        latestClassification
                            .faultName,

                    confidence:
                        latestClassification
                            .confidence,

                    subsystem:
                        latestClassification
                            .subsystem

                  }

                : null;

        },

        enable() {

            enabled =
                true;

        },

        disable() {

            enabled =
                false;

        },

        isEnabled() {

            return enabled;

        },

        reset() {

            latestFaultAnalysis =
                null;

            latestAnomalyAnalysis =
                null;

            latestClassification =
                null;

        },

        config:
            CONFIG

    };

    console.info(
        `[PRATIRUP] Fault Classifier ${VERSION} ready.`
    );

})();
