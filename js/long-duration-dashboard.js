"use strict";

(function () {

    const VERSION = "1.0.0";

    const GLOBAL_NAME =
        "PRATIRUPLongDurationDashboard";

    const CONFIG = Object.freeze({

        referenceLifeHours: 1000,

        chartPadding: {
            top: 18,
            right: 18,
            bottom: 30,
            left: 48
        },

        degradationMaxPercent: 100,

        rulMaxHours: 1000

    });

    const state = {

        initialized: false,

        latest: null,

        history: [],

        maintenanceEvents: []

    };

    const dom = {};

    function bindDOM() {

        dom.panel =
            document.getElementById(
                "longDurationPanel"
            );

        dom.engineHours =
            document.getElementById(
                "lifeStudyEngineHours"
            );

        dom.degradation =
            document.getElementById(
                "lifeStudyDegradation"
            );

        dom.rul =
            document.getElementById(
                "lifeStudyRul"
            );

        dom.lifeState =
            document.getElementById(
                "lifeStudyState"
            );

        dom.maintenance =
            document.getElementById(
                "lifeStudyMaintenance"
            );

        dom.progressFill =
            document.getElementById(
                "engineLifeProgressFill"
            );

        dom.degradationChart =
            document.getElementById(
                "degradationLifeChart"
            );

        dom.rulChart =
            document.getElementById(
                "rulLifeChart"
            );

        dom.maintenanceTimeline =
            document.getElementById(
                "longDurationMaintenanceTimeline"
            );

        dom.wear = {

            thermal: {
                value:
                    document.getElementById(
                        "wearThermalValue"
                    ),

                fill:
                    document.getElementById(
                        "wearThermalFill"
                    )
            },

            lubrication: {
                value:
                    document.getElementById(
                        "wearLubricationValue"
                    ),

                fill:
                    document.getElementById(
                        "wearLubricationFill"
                    )
            },

            vibration_growth: {
                value:
                    document.getElementById(
                        "wearVibrationValue"
                    ),

                fill:
                    document.getElementById(
                        "wearVibrationFill"
                    )
            },

            efficiency_loss: {
                value:
                    document.getElementById(
                        "wearEfficiencyValue"
                    ),

                fill:
                    document.getElementById(
                        "wearEfficiencyFill"
                    )
            },

            combustion: {
                value:
                    document.getElementById(
                        "wearCombustionValue"
                    ),

                fill:
                    document.getElementById(
                        "wearCombustionFill"
                    )
            }

        };

    }

    function isFiniteNumber(value) {

        return (
            typeof value === "number" &&
            Number.isFinite(value)
        );

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

    function percentageFromFraction(
        value
    ) {

        if (!isFiniteNumber(value)) {
            return null;
        }

        return (
            clamp(
                value,
                0,
                1
            ) * 100
        );

    }

    function formatNumber(
        value,
        digits = 2
    ) {

        if (!isFiniteNumber(value)) {
            return "--";
        }

        return value.toFixed(
            digits
        );

    }

    function formatHours(
        value
    ) {

        if (!isFiniteNumber(value)) {
            return "--";
        }

        return (
            value.toFixed(1) +
            " h"
        );

    }

    function formatPercent(
        value
    ) {

        if (!isFiniteNumber(value)) {
            return "--";
        }

        return (
            value.toFixed(2) +
            "%"
        );

    }

    function normalizeWear(
        wear
    ) {

        const source =
            wear &&
            typeof wear === "object"
                ? wear
                : {};

        return {

            thermal:
                isFiniteNumber(
                    source.thermal
                )
                    ? clamp(
                        source.thermal,
                        0,
                        1
                    )
                    : null,

            lubrication:
                isFiniteNumber(
                    source.lubrication
                )
                    ? clamp(
                        source.lubrication,
                        0,
                        1
                    )
                    : null,

            vibration_growth:
                isFiniteNumber(
                    source.vibration_growth
                )
                    ? clamp(
                        source.vibration_growth,
                        0,
                        1
                    )
                    : null,

            efficiency_loss:
                isFiniteNumber(
                    source.efficiency_loss
                )
                    ? clamp(
                        source.efficiency_loss,
                        0,
                        1
                    )
                    : null,

            combustion:
                isFiniteNumber(
                    source.combustion
                )
                    ? clamp(
                        source.combustion,
                        0,
                        1
                    )
                    : null

        };

    }

    function normalizeStudyPoint(
        input
    ) {

        if (
            !input ||
            typeof input !== "object"
        ) {
            return null;
        }

        const engineHours =
            isFiniteNumber(
                input.engine_hours
            )
                ? Math.max(
                    0,
                    input.engine_hours
                )
                : null;

        const degradationIndex =
            isFiniteNumber(
                input.degradation_index
            )
                ? clamp(
                    input.degradation_index,
                    0,
                    1
                )
                : null;

        const rulHours =
            isFiniteNumber(
                input.projected_remaining_hours
            )
                ? Math.max(
                    0,
                    input.projected_remaining_hours
                )
                : null;

        const lifeState =
            typeof input.life_state ===
                "string"
                ? input.life_state
                : (
                    typeof input.rul_state ===
                        "string"
                        ? input.rul_state
                        : null
                );

        return {

            engine_hours:
                engineHours,

            degradation_index:
                degradationIndex,

            projected_remaining_hours:
                rulHours,

            life_state:
                lifeState,

            wear:
                normalizeWear(
                    input.wear
                ),

            synthetic:
                input.synthetic !== false

        };

    }

    function normalizeMaintenanceEvent(
        event
    ) {

        if (
            !event ||
            typeof event !== "object"
        ) {
            return null;
        }

        const engineHours =
            isFiniteNumber(
                event.engine_hours
            )
                ? Math.max(
                    0,
                    event.engine_hours
                )
                : null;

        const type =
            typeof event.maintenance_type ===
                "string"
                ? event.maintenance_type
                : "UNKNOWN";

        const before =
            isFiniteNumber(
                event.degradation_before
            )
                ? clamp(
                    event.degradation_before,
                    0,
                    1
                )
                : null;

        const after =
            isFiniteNumber(
                event.degradation_after
            )
                ? clamp(
                    event.degradation_after,
                    0,
                    1
                )
                : null;

        return {

            event_id:
                event.event_id ?? null,

            engine_hours:
                engineHours,

            maintenance_type:
                type,

            degradation_before:
                before,

            degradation_after:
                after,

            synthetic:
                event.synthetic !== false

        };

    }

    function applyValueClass(
        element,
        fraction
    ) {

        if (!element) {
            return;
        }

        element.classList.remove(
            "long-duration-value-low",
            "long-duration-value-moderate",
            "long-duration-value-high",
            "long-duration-value-unavailable"
        );

        if (!isFiniteNumber(fraction)) {

            element.classList.add(
                "long-duration-value-unavailable"
            );

            return;

        }

        if (fraction < 0.35) {

            element.classList.add(
                "long-duration-value-low"
            );

        } else if (
            fraction < 0.70
        ) {

            element.classList.add(
                "long-duration-value-moderate"
            );

        } else {

            element.classList.add(
                "long-duration-value-high"
            );

        }

    }

    function renderSummary(
        point
    ) {

        if (!point) {
            return;
        }

        if (dom.engineHours) {

            dom.engineHours.textContent =
                formatHours(
                    point.engine_hours
                );

        }

        if (dom.degradation) {

            const percent =
                percentageFromFraction(
                    point.degradation_index
                );

            dom.degradation.textContent =
                formatPercent(
                    percent
                );

            applyValueClass(
                dom.degradation,
                point.degradation_index
            );

        }

        if (dom.rul) {

            dom.rul.textContent =
                formatHours(
                    point.projected_remaining_hours
                );

        }

        if (dom.lifeState) {

            dom.lifeState.textContent =
                point.life_state ??
                "--";

        }

        renderProgress(
            point.engine_hours
        );

    }

    function renderProgress(
        engineHours
    ) {

        if (!dom.progressFill) {
            return;
        }

        if (!isFiniteNumber(engineHours)) {

            dom.progressFill.style.width =
                "0%";

            return;

        }

        const progress =
            clamp(
                (
                    engineHours /
                    CONFIG.referenceLifeHours
                ) * 100,
                0,
                100
            );

        dom.progressFill.style.width =
            progress.toFixed(2) +
            "%";

    }

    function renderWear(
        wear
    ) {

        const normalized =
            normalizeWear(
                wear
            );

        Object.keys(
            dom.wear
        ).forEach(
            key => {

                const reference =
                    dom.wear[key];

                const value =
                    normalized[key];

                const percent =
                    percentageFromFraction(
                        value
                    );

                if (
                    reference.value
                ) {

                    reference.value.textContent =
                        formatPercent(
                            percent
                        );

                    applyValueClass(
                        reference.value,
                        value
                    );

                }

                if (
                    reference.fill
                ) {

                    reference.fill.style.width =
                        isFiniteNumber(percent)
                            ? (
                                clamp(
                                    percent,
                                    0,
                                    100
                                )
                                .toFixed(2) +
                                "%"
                            )
                            : "0%";

                }

            }
        );

    }

    function prepareCanvas(
        canvas
    ) {

        if (!canvas) {
            return null;
        }

        const rect =
            canvas.getBoundingClientRect();

        const cssWidth =
            Math.max(
                300,
                rect.width || 640
            );

        const cssHeight =
            Math.max(
                180,
                rect.height || 220
            );

        const ratio =
            window.devicePixelRatio ||
            1;

        canvas.width =
            Math.round(
                cssWidth * ratio
            );

        canvas.height =
            Math.round(
                cssHeight * ratio
            );

        const context =
            canvas.getContext(
                "2d"
            );

        if (!context) {
            return null;
        }

        context.setTransform(
            ratio,
            0,
            0,
            ratio,
            0,
            0
        );

        return {

            context,

            width:
                cssWidth,

            height:
                cssHeight

        };

    }

    function drawChartGrid(
        context,
        width,
        height,
        yLabels
    ) {

        const padding =
            CONFIG.chartPadding;

        const plotWidth =
            width -
            padding.left -
            padding.right;

        const plotHeight =
            height -
            padding.top -
            padding.bottom;

        context.clearRect(
            0,
            0,
            width,
            height
        );

        context.font =
            "9px sans-serif";

        context.lineWidth =
            1;

        for (
            let index = 0;
            index <= 4;
            index += 1
        ) {

            const ratio =
                index / 4;

            const y =
                padding.top +
                plotHeight * ratio;

            context.beginPath();

            context.strokeStyle =
                "rgba(145,164,197,0.12)";

            context.moveTo(
                padding.left,
                y
            );

            context.lineTo(
                padding.left +
                plotWidth,
                y
            );

            context.stroke();

            if (
                Array.isArray(
                    yLabels
                ) &&
                yLabels[index] !==
                    undefined
            ) {

                context.fillStyle =
                    "#91A4C5";

                context.textAlign =
                    "right";

                context.fillText(
                    String(
                        yLabels[index]
                    ),
                    padding.left - 7,
                    y + 3
                );

            }

        }

        const hourLabels =
            [
                0,
                250,
                500,
                750,
                1000
            ];

        hourLabels.forEach(
            hour => {

                const ratio =
                    hour /
                    CONFIG.referenceLifeHours;

                const x =
                    padding.left +
                    plotWidth *
                    ratio;

                context.beginPath();

                context.strokeStyle =
                    "rgba(145,164,197,0.08)";

                context.moveTo(
                    x,
                    padding.top
                );

                context.lineTo(
                    x,
                    padding.top +
                    plotHeight
                );

                context.stroke();

                context.fillStyle =
                    "#91A4C5";

                context.textAlign =
                    "center";

                context.fillText(
                    `${hour}h`,
                    x,
                    height - 10
                );

            }
        );

    }

    function drawSeries(
        canvas,
        points,
        valueAccessor,
        maxValue,
        strokeColor,
        yLabels
    ) {

        const prepared =
            prepareCanvas(
                canvas
            );

        if (!prepared) {
            return;
        }

        const {
            context,
            width,
            height
        } = prepared;

        drawChartGrid(
            context,
            width,
            height,
            yLabels
        );

        const valid =
            points.filter(
                point => {

                    return (
                        isFiniteNumber(
                            point.engine_hours
                        ) &&
                        isFiniteNumber(
                            valueAccessor(
                                point
                            )
                        )
                    );

                }
            );

        if (
            valid.length === 0
        ) {

            context.fillStyle =
                "#91A4C5";

            context.font =
                "11px sans-serif";

            context.textAlign =
                "center";

            context.fillText(
                "NO SYNTHETIC LIFE-STUDY DATA",
                width / 2,
                height / 2
            );

            return;

        }

        const padding =
            CONFIG.chartPadding;

        const plotWidth =
            width -
            padding.left -
            padding.right;

        const plotHeight =
            height -
            padding.top -
            padding.bottom;

        context.beginPath();

        context.lineWidth =
            2;

        context.strokeStyle =
            strokeColor;

        valid.forEach(
            (point, index) => {

                const hourRatio =
                    clamp(
                        point.engine_hours /
                        CONFIG.referenceLifeHours,
                        0,
                        1
                    );

                const value =
                    valueAccessor(
                        point
                    );

                const valueRatio =
                    clamp(
                        value /
                        maxValue,
                        0,
                        1
                    );

                const x =
                    padding.left +
                    plotWidth *
                    hourRatio;

                const y =
                    padding.top +
                    plotHeight *
                    (
                        1 -
                        valueRatio
                    );

                if (index === 0) {

                    context.moveTo(
                        x,
                        y
                    );

                } else {

                    context.lineTo(
                        x,
                        y
                    );

                }

            }
        );

        context.stroke();

        valid.forEach(
            point => {

                const value =
                    valueAccessor(
                        point
                    );

                const hourRatio =
                    clamp(
                        point.engine_hours /
                        CONFIG.referenceLifeHours,
                        0,
                        1
                    );

                const valueRatio =
                    clamp(
                        value /
                        maxValue,
                        0,
                        1
                    );

                const x =
                    padding.left +
                    plotWidth *
                    hourRatio;

                const y =
                    padding.top +
                    plotHeight *
                    (
                        1 -
                        valueRatio
                    );

                context.beginPath();

                context.fillStyle =
                    strokeColor;

                context.arc(
                    x,
                    y,
                    3,
                    0,
                    Math.PI * 2
                );

                context.fill();

            }
        );

    }

    function renderCharts() {

        drawSeries(

            dom.degradationChart,

            state.history,

            point => {

                const fraction =
                    point.degradation_index;

                return (
                    isFiniteNumber(
                        fraction
                    )
                        ? fraction * 100
                        : null
                );

            },

            CONFIG.degradationMaxPercent,

            "#D946EF",

            [
                "100%",
                "75%",
                "50%",
                "25%",
                "0%"
            ]

        );

        drawSeries(

            dom.rulChart,

            state.history,

            point =>
                point.projected_remaining_hours,

            CONFIG.rulMaxHours,

            "#8B5CF6",

            [
                "1000h",
                "750h",
                "500h",
                "250h",
                "0h"
            ]

        );

    }

    function renderMaintenance() {

        if (
            !dom.maintenanceTimeline
        ) {
            return;
        }

        dom.maintenanceTimeline
            .replaceChildren();

        if (
            state.maintenanceEvents
                .length === 0
        ) {

            const empty =
                document.createElement(
                    "div"
                );

            empty.className =
                "long-duration-maintenance-empty";

            empty.textContent =
                "No synthetic maintenance events recorded.";

            dom.maintenanceTimeline
                .appendChild(
                    empty
                );

            if (dom.maintenance) {

                dom.maintenance.textContent =
                    "NONE";

            }

            return;

        }

        state.maintenanceEvents
            .forEach(
                event => {

                    const row =
                        document.createElement(
                            "div"
                        );

                    row.className =
                        "long-duration-maintenance-event";

                    const hour =
                        document.createElement(
                            "div"
                        );

                    hour.className =
                        "long-duration-maintenance-hour";

                    hour.textContent =
                        formatHours(
                            event.engine_hours
                        );

                    const type =
                        document.createElement(
                            "div"
                        );

                    type.className =
                        "long-duration-maintenance-type";

                    type.textContent =
                        event.maintenance_type;

                    const change =
                        document.createElement(
                            "div"
                        );

                    change.className =
                        "long-duration-maintenance-change";

                    if (
                        isFiniteNumber(
                            event.degradation_before
                        ) &&
                        isFiniteNumber(
                            event.degradation_after
                        )
                    ) {

                        change.textContent =
                            (
                                (
                                    event.degradation_before *
                                    100
                                ).toFixed(2)
                            ) +
                            "% → " +
                            (
                                (
                                    event.degradation_after *
                                    100
                                ).toFixed(2)
                            ) +
                            "%";

                    } else {

                        change.textContent =
                            "--";

                    }

                    row.append(
                        hour,
                        type,
                        change
                    );

                    dom.maintenanceTimeline
                        .appendChild(
                            row
                        );

                }
            );

        const latest =
            state.maintenanceEvents[
                state.maintenanceEvents.length -
                1
            ];

        if (dom.maintenance) {

            dom.maintenance.textContent =
                latest.maintenance_type;

        }

    }

    function renderLatest() {

        if (!state.latest) {

            renderCharts();
            renderMaintenance();

            return;

        }

        renderSummary(
            state.latest
        );

        renderWear(
            state.latest.wear
        );

        renderCharts();

        renderMaintenance();

    }

    function setStudyData(
        payload
    ) {

        if (
            !payload ||
            typeof payload !== "object"
        ) {

            return false;

        }

        const rawHistory =
            Array.isArray(
                payload.history
            )
                ? payload.history
                : [];

        const normalizedHistory =
            rawHistory
                .map(
                    normalizeStudyPoint
                )
                .filter(Boolean)
                .sort(
                    (a, b) => {

                        const left =
                            isFiniteNumber(
                                a.engine_hours
                            )
                                ? a.engine_hours
                                : Infinity;

                        const right =
                            isFiniteNumber(
                                b.engine_hours
                            )
                                ? b.engine_hours
                                : Infinity;

                        return (
                            left -
                            right
                        );

                    }
                );

        state.history =
            normalizedHistory;

        if (payload.latest) {

            state.latest =
                normalizeStudyPoint(
                    payload.latest
                );

        } else if (
            normalizedHistory.length > 0
        ) {

            state.latest =
                normalizedHistory[
                    normalizedHistory.length -
                    1
                ];

        } else {

            state.latest = null;

        }

        const rawEvents =
            Array.isArray(
                payload.maintenance_events
            )
                ? payload.maintenance_events
                : [];

        state.maintenanceEvents =
            rawEvents
                .map(
                    normalizeMaintenanceEvent
                )
                .filter(Boolean)
                .sort(
                    (a, b) => {

                        const left =
                            isFiniteNumber(
                                a.engine_hours
                            )
                                ? a.engine_hours
                                : Infinity;

                        const right =
                            isFiniteNumber(
                                b.engine_hours
                            )
                                ? b.engine_hours
                                : Infinity;

                        return (
                            left -
                            right
                        );

                    }
                );

        renderLatest();

        window.dispatchEvent(

            new CustomEvent(
                "pratirup:long-duration-rendered",
                {
                    detail: {
                        synthetic: true,
                        presentationOnly: true,
                        databaseWrites: false,
                        readinessCalculation: false,
                        flightAuthorization: false
                    }
                }
            )

        );

        return true;

    }

    function loadDemonstrationData() {

        return setStudyData({

            history: [

                {
                    engine_hours: 0,
                    degradation_index: 0,
                    projected_remaining_hours: 1000,
                    life_state: "EARLY_LIFE",

                    wear: {
                        thermal: 0,
                        lubrication: 0,
                        vibration_growth: 0,
                        efficiency_loss: 0,
                        combustion: 0
                    },

                    synthetic: true
                },

                {
                    engine_hours: 10,
                    degradation_index: 0.001023,
                    projected_remaining_hours: 998.98,
                    life_state: "EARLY_LIFE",

                    wear: {
                        thermal: 0.001,
                        lubrication: 0.001,
                        vibration_growth: 0.001,
                        efficiency_loss: 0.001,
                        combustion: 0.001
                    },

                    synthetic: true
                },

                {
                    engine_hours: 100,
                    degradation_index: 0.030282,
                    projected_remaining_hours: 969.72,
                    life_state: "EARLY_LIFE",

                    wear: {
                        thermal: 0.0447,
                        lubrication: 0.0282,
                        vibration_growth: 0.0158,
                        efficiency_loss: 0.0304,
                        combustion: 0.0224
                    },

                    synthetic: true
                },

                {
                    engine_hours: 250,
                    degradation_index: 0.1200,
                    projected_remaining_hours: 879.97,
                    life_state: "NOMINAL",

                    wear: {
                        thermal: 0.145,
                        lubrication: 0.128,
                        vibration_growth: 0.085,
                        efficiency_loss: 0.112,
                        combustion: 0.119
                    },

                    synthetic: true
                },

                {
                    engine_hours: 500,
                    degradation_index: 0.344476,
                    projected_remaining_hours: 655.52,
                    life_state: "NOMINAL",

                    wear: {
                        thermal: 0.3923,
                        lubrication: 0.3552,
                        vibration_growth: 0.2872,
                        efficiency_loss: 0.3645,
                        combustion: 0.3186
                    },

                    synthetic: true
                },

                {
                    engine_hours: 800,
                    degradation_index: 0.708669,
                    projected_remaining_hours: 291.33,
                    life_state: "DECLINING",

                    wear: {
                        thermal: 0.7399,
                        lubrication: 0.7163,
                        vibration_growth: 0.6692,
                        efficiency_loss: 0.7064,
                        combustion: 0.6927
                    },

                    synthetic: true
                }

            ],

            latest: {

                engine_hours: 800,

                degradation_index:
                    0.708669,

                projected_remaining_hours:
                    291.33,

                life_state:
                    "DECLINING",

                wear: {

                    thermal:
                        0.7399,

                    lubrication:
                        0.7163,

                    vibration_growth:
                        0.6692,

                    efficiency_loss:
                        0.7064,

                    combustion:
                        0.6927

                },

                synthetic: true

            },

            maintenance_events: [

                {
                    event_id: 1,

                    engine_hours: 500,

                    maintenance_type:
                        "MAJOR_SERVICE",

                    degradation_before:
                        0.344476,

                    degradation_after:
                        0.215177,

                    synthetic: true
                }

            ]

        });

    }

    function getStatus() {

        return {

            service:
                "long_duration_dashboard",

            version:
                VERSION,

            initialized:
                state.initialized,

            synthetic:
                true,

            presentationOnly:
                true,

            historyPoints:
                state.history.length,

            maintenanceEvents:
                state.maintenanceEvents.length,

            latestEngineHours:
                state.latest
                    ?.engine_hours ??
                    null,

            latestDegradation:
                state.latest
                    ?.degradation_index ??
                    null,

            latestProjectedRul:
                state.latest
                    ?.projected_remaining_hours ??
                    null,

            semantics: {

                zero:
                    "GENUINE_NUMERIC_ZERO",

                null:
                    "UNAVAILABLE",

                measuredEngineHours:
                    false,

                officialLifeLimit:
                    false,

                authoritativeRul:
                    false

            },

            isolation: {

                telemetryGeneration:
                    false,

                websocketOwner:
                    false,

                canonicalTelemetryMutation:
                    false,

                digitalTwinExecution:
                    false,

                authoritativeDegradation:
                    false,

                authoritativeRul:
                    false,

                authoritativeMaintenance:
                    false,

                readinessCalculation:
                    false,

                databaseWrites:
                    false,

                flightAuthorization:
                    false

            }

        };

    }

    let resizeTimer = null;

    function handleResize() {

        if (resizeTimer) {

            window.clearTimeout(
                resizeTimer
            );

        }

        resizeTimer =
            window.setTimeout(
                () => {

                    renderCharts();

                },
                120
            );

    }

    function initialize() {

        if (state.initialized) {
            return true;
        }

        bindDOM();

        if (!dom.panel) {

            console.warn(
                "[PRATIRUP D9-H] " +
                "Long-duration panel not found."
            );

            return false;

        }

        state.initialized = true;

        window.addEventListener(
            "resize",
            handleResize
        );

        renderLatest();

        console.info(
            "[PRATIRUP D9-H] " +
            "Long-duration dashboard initialized."
        );

        return true;

    }

    const api = Object.freeze({

        version:
            VERSION,

        initialize,

        setStudyData,

        loadDemonstrationData,

        getStatus,

        render:
            renderLatest

    });

    window[
        GLOBAL_NAME
    ] = api;

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

    } else {

        initialize();

    }

})();
