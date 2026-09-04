(function () {

    "use strict";

    const CONFIG = {

        historyLength: 180,

        minimumSamples: 10,

        weights: {

            thermal: 0.22,

            vibration: 0.18,

            lubrication: 0.15,

            combustion: 0.15,

            electrical: 0.08,

            dynamic: 0.07,

            faultEvidence: 0.15

        },

        thresholds: {

            normal: 25,

            watch: 40,

            caution: 60,

            high: 80

        }

    };

    const history = [];

    let latestResult = null;

    let running = true;

    let lastProcessedTime = 0;

    function num(value, fallback = 0) {

        const n = Number(value);

        return Number.isFinite(n)
            ? n
            : fallback;

    }

    function clamp(value, min = 0, max = 1) {

        return Math.max(
            min,
            Math.min(max, value)
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
            (sum, value) => sum + value,
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

    function risk(
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
            return 1;
        }

        return clamp(
            (value - warning) /
            (critical - warning)
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
            return 1;
        }

        return clamp(
            (warning - value) /
            (warning - critical)
        );

    }

    function classify(score) {

        if (
            score >=
            CONFIG.thresholds.high
        ) {

            return "CRITICAL";

        }

        if (
            score >=
            CONFIG.thresholds.caution
        ) {

            return "HIGH";

        }

        if (
            score >=
            CONFIG.thresholds.watch
        ) {

            return "CAUTION";

        }

        if (
            score >=
            CONFIG.thresholds.normal
        ) {

            return "WATCH";

        }

        return "NORMAL";

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
                        Number(source[key]);

                    if (
                        Number.isFinite(result)
                    ) {

                        return result;

                    }

                }

            }

            return 0;

        }

        function cylinderValues(prefix) {

            const direct =
                source[prefix];

            if (
                Array.isArray(direct)
            ) {

                return direct
                    .map(Number)
                    .filter(Number.isFinite);

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

            torque:
                value(
                    "torque",
                    "torqueNm"
                ),

            cht:
                cylinderValues(
                    "cht"
                ),

            egt:
                cylinderValues(
                    "egt"
                ),

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
                )

        };

    }

    function pushHistory(sample) {

        history.push(sample);

        while (
            history.length >
            CONFIG.historyLength
        ) {

            history.shift();

        }

    }

    function thermalScore(sample) {

        const avgCHT =
            average(sample.cht);

        const avgEGT =
            average(sample.egt);

        const chtSpread =
            spread(sample.cht);

        const egtSpread =
            spread(sample.egt);

        const chtTemperatureRisk =
            risk(
                avgCHT,
                220,
                250
            );

        const egtTemperatureRisk =
            risk(
                avgEGT,
                780,
                850
            );

        const chtImbalanceRisk =
            risk(
                chtSpread,
                25,
                50
            );

        const egtImbalanceRisk =
            risk(
                egtSpread,
                55,
                100
            );

        return clamp(

            chtTemperatureRisk * 0.30 +

            egtTemperatureRisk * 0.25 +

            chtImbalanceRisk * 0.20 +

            egtImbalanceRisk * 0.25

        );

    }

    function vibrationScore(sample) {

        return risk(
            sample.vibration,
            1.4,
            2.6
        );

    }

    function lubricationScore(sample) {

        const pressureRisk =
            inverseRisk(
                sample.oilPressure,
                180,
                110
            );

        const temperatureRisk =
            risk(
                sample.oilTemperature,
                115,
                140
            );

        return clamp(

            pressureRisk * 0.65 +

            temperatureRisk * 0.35

        );

    }

    function combustionScore(sample) {

        const egtImbalance =
            risk(
                spread(sample.egt),
                50,
                100
            );

        const chtImbalance =
            risk(
                spread(sample.cht),
                25,
                50
            );

        const vibration =
            risk(
                sample.vibration,
                1.3,
                2.5
            );

        return clamp(

            egtImbalance * 0.45 +

            chtImbalance * 0.25 +

            vibration * 0.30

        );

    }

    function electricalScore(sample) {

        const battery =
            inverseRisk(
                sample.batteryVoltage,
                11.5,
                9.5
            );

        const alternator =
            inverseRisk(
                sample.alternatorVoltage,
                12.5,
                10.5
            );

        return Math.max(
            battery,
            alternator
        );

    }

    function dynamicScore(sample) {

        if (
            history.length < 2
        ) {

            return 0;

        }

        const previous =
            history[
                history.length - 2
            ];

        const rpmDelta =
            Math.abs(
                sample.rpm -
                previous.rpm
            );

        const oilDelta =
            Math.abs(
                sample.oilPressure -
                previous.oilPressure
            );

        const vibrationDelta =
            Math.abs(
                sample.vibration -
                previous.vibration
            );

        const rpmRisk =
            risk(
                rpmDelta,
                600,
                1800
            );

        const oilRisk =
            risk(
                oilDelta,
                40,
                150
            );

        const vibrationRisk =
            risk(
                vibrationDelta,
                0.4,
                1.5
            );

        return Math.max(

            rpmRisk,

            oilRisk,

            vibrationRisk

        );

    }

    function faultEvidenceScore() {

        const engine =
            window.PratirupFaultDetection;

        if (
            !engine ||
            typeof engine.getLatest !==
            "function"
        ) {

            return 0;

        }

        const result =
            engine.getLatest();

        if (!result) {

            return 0;

        }

        return clamp(
            num(
                result.overallRisk
            )
        );

    }

    function physicsResidualScore(input) {

        const residuals =

            input?.residuals ||

            input?.physicsResiduals ||

            input?.comparison?.residuals ||

            null;

        if (!residuals) {

            return 0;

        }

        const values =
            Object.values(
                residuals
            )
            .map(value => {

                if (
                    typeof value ===
                    "object"
                ) {

                    return Number(
                        value.normalized ??
                        value.score ??
                        value.residual
                    );

                }

                return Number(value);

            })
            .filter(Number.isFinite)
            .map(Math.abs);

        if (!values.length) {

            return 0;

        }

        return clamp(
            average(values)
        );

    }

    function evaluate(input) {

        if (!running) {

            return latestResult;

        }

        const sample =
            normalizeTelemetry(
                input
            );

        pushHistory(
            sample
        );

        const scores = {

            thermal:
                thermalScore(sample),

            vibration:
                vibrationScore(sample),

            lubrication:
                lubricationScore(sample),

            combustion:
                combustionScore(sample),

            electrical:
                electricalScore(sample),

            dynamic:
                dynamicScore(sample),

            faultEvidence:
                faultEvidenceScore(),

            physicsResidual:
                physicsResidualScore(input)

        };

        let weightedScore =

            scores.thermal *
            CONFIG.weights.thermal +

            scores.vibration *
            CONFIG.weights.vibration +

            scores.lubrication *
            CONFIG.weights.lubrication +

            scores.combustion *
            CONFIG.weights.combustion +

            scores.electrical *
            CONFIG.weights.electrical +

            scores.dynamic *
            CONFIG.weights.dynamic +

            scores.faultEvidence *
            CONFIG.weights.faultEvidence;

        if (
            scores.physicsResidual > 0
        ) {

            weightedScore =
                weightedScore * 0.80 +

                scores.physicsResidual *
                0.20;

        }

        weightedScore =
            clamp(
                weightedScore
            );

        const anomalyScore =
            Number(
                (
                    weightedScore *
                    100
                ).toFixed(1)
            );

        latestResult = {

            timestamp:
                Date.now(),

            anomalyScore,

            normalizedScore:
                weightedScore,

            status:
                classify(
                    anomalyScore
                ),

            sampleCount:
                history.length,

            scores: {

                thermal:
                    Number(
                        (
                            scores.thermal *
                            100
                        ).toFixed(1)
                    ),

                vibration:
                    Number(
                        (
                            scores.vibration *
                            100
                        ).toFixed(1)
                    ),

                lubrication:
                    Number(
                        (
                            scores.lubrication *
                            100
                        ).toFixed(1)
                    ),

                combustion:
                    Number(
                        (
                            scores.combustion *
                            100
                        ).toFixed(1)
                    ),

                electrical:
                    Number(
                        (
                            scores.electrical *
                            100
                        ).toFixed(1)
                    ),

                dynamic:
                    Number(
                        (
                            scores.dynamic *
                            100
                        ).toFixed(1)
                    ),

                faultEvidence:
                    Number(
                        (
                            scores.faultEvidence *
                            100
                        ).toFixed(1)
                    ),

                physicsResidual:
                    Number(
                        (
                            scores.physicsResidual *
                            100
                        ).toFixed(1)
                    )

            },

            telemetry:
                sample

        };

        publish(
            latestResult
        );

        return latestResult;

    }

    function publish(result) {

        window.dispatchEvent(

            new CustomEvent(
                "pratirup:anomaly-analysis",
                {
                    detail:
                        result
                }
            )

        );

        if (
            typeof
            window.onPratirupAnomalyAnalysis
            ===
            "function"
        ) {

            try {

                window.onPratirupAnomalyAnalysis(
                    result
                );

            }

            catch (error) {

                console.error(
                    "[PRATIRUP Anomaly Engine]",
                    error
                );

            }

        }

    }

    const EVENTS = [

        "pratirup:twin-state",

        "pratirup:engine-state",

        "pratirup:telemetry"

    ];

    EVENTS.forEach(

        eventName => {

            window.addEventListener(

                eventName,

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
                        25
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

        }

    );

    window.addEventListener(

        "pratirup:fault-analysis",

        event => {

            if (
                !event.detail?.telemetry
            ) {

                return;

            }

            const now =
                performance.now();

            if (
                now -
                lastProcessedTime <
                25
            ) {

                return;

            }

            lastProcessedTime =
                now;

            evaluate(
                {
                    telemetry:
                        event.detail.telemetry
                }
            );

        }

    );

    window.PratirupAnomalyDetection = {

        evaluate,

        getLatest() {

            return latestResult;

        },

        getScore() {

            return latestResult
                ? latestResult.anomalyScore
                : 0;

        },

        getStatus() {

            return latestResult
                ? latestResult.status
                : "UNKNOWN";

        },

        getHistory() {

            return [
                ...history
            ];

        },

        clearHistory() {

            history.length = 0;

            latestResult = null;

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

        config:
            CONFIG

    };

    function initialize() {

        console.info(
            "[PRATIRUP] Anomaly Detection Engine ready."
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
