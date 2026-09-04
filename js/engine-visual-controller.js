(() => {

    "use strict";

    const VERSION =
        "1.1.1";

    const SERVICE =
        "engine_visual_controller";

    const STAGE =
        "D5_REPLAY_3D_SYNCHRONIZATION";

    const CONFIG = Object.freeze({

        simulationWaitTimeoutMs:
            15000,

        simulationWaitIntervalMs:
            100,

        telemetryStaleMs:
            5000,

        maximumDeltaSec:
            0.05,

        response:
            8,

        enforceCanonicalSource:
            true,

        vibration: {

            enabled:
                true,

            positionGain:
                0.018,

            rotationGain:
                0.006,

            maximumPositionAmplitude:
                0.12,

            maximumRotationAmplitude:
                0.045,

            baseFrequencyHz:
                18,

            frequencyGain:
                8,

            decayResponse:
                5

        },

        thermal: {

            enabled:
                true,

            chtColdC:
                80,

            chtWarmC:
                150,

            chtHotC:
                220,

            chtCriticalC:
                260,

            maximumEmissiveIntensity:
                1.6

        },

        fuel: {

            minimumVisibleFlow:
                0.001

        }

    });

    const runtime = {

        initialized:
            false,

        disposed:
            false,

        simulationReady:
            false,

        simulation:
            null,

        engine:
            null,

        groups:
            null,

        animationFrame:
            null,

        lastFrameTime:
            null,

        lastTelemetryAt:
            null,

        telemetryReceived:
            0,

        lastFrameIdentity:
            null,

        source: {

            active:
                null,

            original:
                null,

            replay:
                false,

            sequence:
                null,

            missionId:
                null,

            timestamp:
                null,

            lastAcceptedSource:
                null,

            lastRejectedSource:
                null

        },

        telemetry: {

            rpm:
                null,

            loadPercent:
                null,

            throttlePercent:
                null,

            vibrationG:
                null,

            cht:
                [],

            egt:
                [],

            oilPressureKpa:
                null,

            oilTemperatureC:
                null,

            fuelPressureKpa:
                null,

            fuelFlow:
                null,

            powerKw:
                null,

            torqueNm:
                null,

            altitudeM:
                null

        },

        visual: {

            rpm:
                null,

            vibrationG:
                0,

            targetVibrationG:
                null,

            loadPercent:
                null,

            throttlePercent:
                null

        },

        baseEngineTransform: {

            position:
                null,

            rotation:
                null

        },

        cylinderMaterials:
            [],

        originalCylinderMaterials:
            [],

        diagnostics: {

            overallState:
                null,

            faults:
                []

        },

        stats: {

            canonicalTelemetryEvents:
                0,

            acceptedTelemetryEvents:
                0,

            rejectedTelemetryEvents:
                0,

            duplicateFrames:
                0,

            replayFrames:
                0,

            simulationFrames:
                0,

            liveFrames:
                0,

            unknownSourceFrames:
                0,

            diagnosticEvents:
                0,

            frames:
                0,

            rpmUpdates:
                0,

            vibrationUpdates:
                0,

            thermalUpdates:
                0,

            fuelUpdates:
                0

        }

    };

    function isObject(
        value
    ) {

        return (

            value !== null &&

            typeof value ===
                "object" &&

            !Array.isArray(
                value
            )

        );

    }

    function finiteNumber(
        value
    ) {

        if (
            value === null ||
            value === undefined ||
            value === "" ||
            typeof value ===
                "boolean"
        ) {

            return null;

        }

        const number =
            Number(
                value
            );

        return Number.isFinite(
            number
        )
            ? number
            : null;

    }

    function firstFinite(
        ...values
    ) {

        for (
            const value
            of values
        ) {

            const parsed =
                finiteNumber(
                    value
                );

            if (
                parsed !== null
            ) {

                return parsed;

            }

        }

        return null;

    }

    function firstDefined(
        ...values
    ) {

        for (
            const value
            of values
        ) {

            if (
                value !== null &&
                value !== undefined
            ) {

                return value;

            }

        }

        return null;

    }

    function firstObject(
        ...values
    ) {

        for (
            const value
            of values
        ) {

            if (
                isObject(
                    value
                )
            ) {

                return value;

            }

        }

        return null;

    }

    function finiteNumberArray(
        value
    ) {

        if (
            !Array.isArray(
                value
            )
        ) {

            return [];

        }

        return value.map(
            item =>
                finiteNumber(
                    item
                )
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

    function smoothValue(
        current,
        target,
        response,
        delta
    ) {

        if (
            target === null
        ) {

            return current;

        }

        if (
            current === null
        ) {

            return target;

        }

        const factor =

            1 -

            Math.exp(
                -response *
                delta
            );

        return (

            current +

            (
                target -
                current
            )

            *

            factor

        );

    }

    function normalizeSource(
        value
    ) {

        if (
            value === null ||
            value === undefined ||
            value === ""
        ) {

            return null;

        }

        const source =
            String(
                value
            )
                .trim()
                .toUpperCase();

        if (
            source === "CAN" ||
            source === "FADEC" ||
            source === "CAN_FADEC" ||
            source === "CAN-FADEC" ||
            source === "LIVE-CAN"
        ) {

            return "LIVE";

        }

        if (
            source ===
            "BACKEND"
        ) {

            return "SIMULATION";

        }

        return source;

    }

    function getBridge() {

        return (
            window.PRATIRUP_BRIDGE ||
            null
        );

    }

    function getArbitrationStatus() {

        const bridge =
            getBridge();

        if (
            !bridge
        ) {

            return null;

        }

        try {

            if (
                typeof bridge
                    .getSourceArbitrationStatus ===
                "function"
            ) {

                return (
                    bridge
                        .getSourceArbitrationStatus() ||
                    null
                );

            }

            if (
                typeof bridge
                    .getSourceMode ===
                "function"
            ) {

                return {

                    mode:
                        bridge
                            .getSourceMode()

                };

            }

        }

        catch (
            error
        ) {

            console.warn(
                "[PRATIRUP D5] Unable to read source arbitration status.",
                error
            );

        }

        return null;

    }

    function getRequiredSource() {

        const status =
            getArbitrationStatus();

        if (
            !status
        ) {

            return null;

        }

        const mode =
            normalizeSource(

                firstDefined(

                    status.mode,

                    status.sourceMode,

                    status.source_mode

                )

            );

        if (
            !mode ||
            mode ===
                "AUTO"
        ) {

            return null;

        }

        if (
            mode ===
                "REPLAY"
        ) {

            return "REPLAY";

        }

        if (
            mode ===
                "SIMULATION"
        ) {

            return "SIMULATION";

        }

        if (
            mode ===
                "LIVE"
        ) {

            return "LIVE";

        }

        return null;

    }

    function resolveTelemetryPayload(
        payload
    ) {

        if (
            !isObject(
                payload
            )
        ) {

            return null;

        }

        return firstObject(

            payload.telemetry,

            payload.frame,

            payload.observed,

            payload.observed_state?.state,

            payload.estimated_state?.state,

            payload.state?.telemetry,

            payload.data?.telemetry,

            payload.data?.frame,

            payload.data?.observed,

            payload.data,

            payload

        );

    }

    function extractSourceMetadata(
        payload
    ) {

        const telemetry =
            resolveTelemetryPayload(
                payload
            );

        if (
            !telemetry
        ) {

            return {

                source:
                    null,

                originalSource:
                    null,

                replay:
                    false,

                sequence:
                    null,

                missionId:
                    null,

                timestamp:
                    null

            };

        }

        const meta =
            firstObject(

                telemetry.meta,

                payload?.meta,

                {}

            );

        const source =
            normalizeSource(

                firstDefined(

                    meta?.source,

                    telemetry.source,

                    payload?.source

                )

            );

        const originalSource =
            normalizeSource(

                firstDefined(

                    meta?.original_source,

                    meta?.originalSource,

                    telemetry.original_source,

                    telemetry.originalSource,

                    payload?.original_source,

                    payload?.originalSource

                )

            );

        const replay =

            firstDefined(

                meta?.replay,

                telemetry.replay,

                payload?.replay

            ) === true;

        const sequence =
            firstDefined(

                meta?.sequence,

                telemetry.sequence,

                telemetry.sequence_number,

                payload?.sequence

            );

        const missionId =
            firstDefined(

                meta?.mission_id,

                meta?.missionId,

                telemetry.mission_id,

                telemetry.mission?.id,

                payload?.mission_id

            );

        const timestamp =
            firstDefined(

                meta?.timestamp,

                telemetry.timestamp,

                telemetry.recorded_at,

                payload?.timestamp

            );

        return {

            source,

            originalSource,

            replay,

            sequence,

            missionId,

            timestamp

        };

    }

    function buildFrameIdentity(
        metadata
    ) {

        if (
            !metadata
        ) {

            return null;

        }

        if (
            metadata.sequence ===
                null &&
            metadata.timestamp ===
                null
        ) {

            return null;

        }

        return [

            metadata.source ??
                "",

            metadata.missionId ??
                "",

            metadata.sequence ??
                "",

            metadata.timestamp ??
                ""

        ].join(
            "|"
        );

    }

    function validateCanonicalSource(
        metadata
    ) {

        if (
            !CONFIG
                .enforceCanonicalSource
        ) {

            return true;

        }

        const requiredSource =
            getRequiredSource();

        if (
            requiredSource ===
                null
        ) {

            return true;

        }

        if (
            requiredSource ===
                "REPLAY"
        ) {

            return (

                metadata.source ===
                    "REPLAY" &&

                metadata.replay ===
                    true

            );

        }

        return (
            metadata.source ===
            requiredSource
        );

    }

    function extractTelemetry(
        payload
    ) {

        const telemetry =
            resolveTelemetryPayload(
                payload
            );

        if (
            !telemetry
        ) {

            return null;

        }

        const engine =
            firstObject(

                telemetry.engine,

                telemetry.state?.engine,

                {}

            );

        const vibration =
            firstObject(

                telemetry.vibration,

                telemetry.state?.vibration,

                {}

            );

        const oil =
            firstObject(

                telemetry.oil,

                telemetry.lubrication,

                telemetry.state?.oil,

                {}

            );

        const fuel =
            firstObject(

                telemetry.fuel,

                telemetry.state?.fuel,

                {}

            );

        const performance =
            firstObject(

                telemetry.performance,

                telemetry.state?.performance,

                {}

            );

        const environment =
            firstObject(

                telemetry.environment,

                telemetry.state?.environment,

                {}

            );

        const rpm =
            firstFinite(

                engine?.rpm,

                engine?.engine_rpm,

                telemetry.engine_rpm,

                telemetry.rpm

            );

        const loadPercent =
            firstFinite(

                engine?.load_percent,

                engine?.loadPercent,

                engine?.load_pct,

                engine?.engine_load_pct,

                telemetry.load_percent,

                telemetry.loadPercent,

                telemetry.load_pct,

                telemetry.engine_load_pct

            );

        const throttlePercent =
            firstFinite(

                engine?.throttle_percent,

                engine?.throttlePercent,

                engine?.throttle_pct,

                telemetry.throttle_percent,

                telemetry.throttlePercent,

                telemetry.throttle_pct

            );

        const vibrationG =
            firstFinite(

                vibration?.overall_g,

                vibration?.overallG,

                vibration?.rms_g,

                vibration?.rmsG,

                vibration?.level,

                vibration?.value,

                telemetry.vibration_g,

                telemetry.vibrationG,

                typeof telemetry.vibration ===
                    "number"
                    ? telemetry.vibration
                    : null

            );

        let cht =
            [];

        const chtCandidate =

            telemetry.cht ??

            telemetry.cylinder_head_temperature ??

            telemetry.cylinder_head_temperatures;

        if (
            Array.isArray(
                chtCandidate
            )
        ) {

            cht =
                finiteNumberArray(
                    chtCandidate
                );

        }

        else if (
            isObject(
                chtCandidate
            )
        ) {

            const cylinders =
                finiteNumberArray([

                    chtCandidate.cylinder_1 ??
                    chtCandidate.cylinder1_c ??
                    chtCandidate.c1,

                    chtCandidate.cylinder_2 ??
                    chtCandidate.cylinder2_c ??
                    chtCandidate.c2,

                    chtCandidate.cylinder_3 ??
                    chtCandidate.cylinder3_c ??
                    chtCandidate.c3,

                    chtCandidate.cylinder_4 ??
                    chtCandidate.cylinder4_c ??
                    chtCandidate.c4

                ]);

            if (
                cylinders.some(
                    value =>
                        value !== null
                )
            ) {

                cht =
                    cylinders;

            }

            else {

                const mean =
                    firstFinite(

                        chtCandidate.mean_c,

                        chtCandidate.average_c,

                        chtCandidate.value_c

                    );

                if (
                    mean !== null
                ) {

                    cht = [

                        mean,
                        mean,
                        mean,
                        mean

                    ];

                }

            }

        }

        else {

            const direct =
                firstFinite(

                    telemetry.cht_c,

                    engine?.cht_c

                );

            if (
                direct !== null
            ) {

                cht = [

                    direct,
                    direct,
                    direct,
                    direct

                ];

            }

        }

        let egt =
            [];

        const egtCandidate =

            telemetry.egt ??

            telemetry.exhaust_gas_temperature ??

            telemetry.exhaust_gas_temperatures;

        if (
            Array.isArray(
                egtCandidate
            )
        ) {

            egt =
                finiteNumberArray(
                    egtCandidate
                );

        }

        else if (
            isObject(
                egtCandidate
            )
        ) {

            const cylinders =
                finiteNumberArray([

                    egtCandidate.cylinder_1 ??
                    egtCandidate.cylinder1_c ??
                    egtCandidate.c1,

                    egtCandidate.cylinder_2 ??
                    egtCandidate.cylinder2_c ??
                    egtCandidate.c2,

                    egtCandidate.cylinder_3 ??
                    egtCandidate.cylinder3_c ??
                    egtCandidate.c3,

                    egtCandidate.cylinder_4 ??
                    egtCandidate.cylinder4_c ??
                    egtCandidate.c4

                ]);

            if (
                cylinders.some(
                    value =>
                        value !== null
                )
            ) {

                egt =
                    cylinders;

            }

            else {

                const mean =
                    firstFinite(

                        egtCandidate.mean_c,

                        egtCandidate.average_c,

                        egtCandidate.value_c

                    );

                if (
                    mean !== null
                ) {

                    egt = [

                        mean,
                        mean,
                        mean,
                        mean

                    ];

                }

            }

        }

        else {

            const direct =
                firstFinite(

                    telemetry.egt_c,

                    engine?.egt_c

                );

            if (
                direct !== null
            ) {

                egt = [

                    direct,
                    direct,
                    direct,
                    direct

                ];

            }

        }

        const oilPressureKpa =
            firstFinite(

                oil?.pressure_kpa,

                oil?.pressureKpa,

                telemetry.oil_pressure_kpa

            );

        const oilTemperatureC =
            firstFinite(

                oil?.temperature_c,

                oil?.temperatureC,

                telemetry.oil_temperature_c

            );

        const fuelPressureKpa =
            firstFinite(

                fuel?.pressure_kpa,

                fuel?.pressureKpa,

                telemetry.fuel_pressure_kpa

            );

        const fuelFlow =
            firstFinite(

                fuel?.flow,

                fuel?.flow_rate,

                fuel?.flow_rate_kg_h,

                fuel?.flow_kg_h,

                fuel?.mass_flow_kg_h,

                fuel?.flow_kg_s,

                fuel?.mass_flow_kg_s,

                telemetry.fuel_flow,

                telemetry.fuel_flow_kg_s,

                telemetry.fuel_flow_kg_h

            );

        const powerKw =
            firstFinite(

                engine?.power_kw,

                performance?.power_kw,

                telemetry.power_kw

            );

        const torqueNm =
            firstFinite(

                engine?.torque_nm,

                performance?.torque_nm,

                telemetry.torque_nm

            );

        const altitudeM =
            firstFinite(

                environment?.altitude_m,

                telemetry.altitude_m,

                telemetry.mission?.altitude_m

            );

        return {

            rpm,

            loadPercent,

            throttlePercent,

            vibrationG,

            cht,

            egt,

            oilPressureKpa,

            oilTemperatureC,

            fuelPressureKpa,

            fuelFlow,

            powerKw,

            torqueNm,

            altitudeM

        };

    }

    function getSimulationAPI() {

        const simulation =
            window.PRATIRUP_SIMULATION;

        if (
            !simulation ||
            !simulation.engine ||
            !simulation.groups
        ) {

            return null;

        }

        return simulation;

    }

    function waitForSimulation() {

        return new Promise(
            (
                resolve,
                reject
            ) => {

                const started =
                    performance.now();

                function check() {

                    const simulation =
                        getSimulationAPI();

                    if (
                        simulation
                    ) {

                        resolve(
                            simulation
                        );

                        return;

                    }

                    if (
                        performance.now() -
                        started >
                        CONFIG
                            .simulationWaitTimeoutMs
                    ) {

                        reject(

                            new Error(
                                "PRATIRUP_SIMULATION API was not available before timeout."
                            )

                        );

                        return;

                    }

                    setTimeout(

                        check,

                        CONFIG
                            .simulationWaitIntervalMs

                    );

                }

                check();

            }
        );

    }

    function collectMeshMaterials(
        object
    ) {

        const result =
            [];

        if (
            !object ||
            typeof object.traverse !==
                "function"
        ) {

            return result;

        }

        object.traverse(
            child => {

                if (
                    !child.isMesh ||
                    !child.material
                ) {

                    return;

                }

                const materials =
                    Array.isArray(
                        child.material
                    )
                        ? child.material
                        : [
                            child.material
                        ];

                materials.forEach(
                    material => {

                        if (
                            material
                        ) {

                            result.push(
                                material
                            );

                        }

                    }
                );

            }
        );

        return result;

    }

    function prepareCylinderMaterials() {

        runtime.cylinderMaterials =
            [];

        runtime.originalCylinderMaterials =
            [];

        const cylinders =
            runtime.groups?.cylinders;

        if (
            !Array.isArray(
                cylinders
            )
        ) {

            return;

        }

        cylinders.forEach(
            (
                cylinder,
                index
            ) => {

                const materials =
                    collectMeshMaterials(
                        cylinder
                    );

                runtime.cylinderMaterials[
                    index
                ] =
                    materials;

                runtime.originalCylinderMaterials[
                    index
                ] =
                    materials.map(
                        material => ({

                            color:
                                material.color &&
                                typeof material.color
                                    .clone ===
                                "function"

                                    ? material.color
                                        .clone()

                                    : null,

                            emissive:
                                material.emissive &&
                                typeof material.emissive
                                    .clone ===
                                "function"

                                    ? material.emissive
                                        .clone()

                                    : null,

                            emissiveIntensity:
                                finiteNumber(
                                    material
                                        .emissiveIntensity
                                )

                        })
                    );

            }
        );

    }

    function captureBaseTransform() {

        if (
            !runtime.engine
        ) {

            return;

        }

        if (
            runtime.engine.position &&
            typeof runtime.engine.position
                .clone ===
            "function"
        ) {

            runtime
                .baseEngineTransform
                .position =
                runtime.engine
                    .position
                    .clone();

        }

        if (
            runtime.engine.rotation &&
            typeof runtime.engine.rotation
                .clone ===
            "function"
        ) {

            runtime
                .baseEngineTransform
                .rotation =
                runtime.engine
                    .rotation
                    .clone();

        }

    }

    function applyRPM() {

        const rpm =
            runtime.telemetry
                .rpm;

        if (
            rpm === null
        ) {

            return;

        }

        const boundedRPM =
            clamp(
                rpm,
                0,
                4500
            );

        runtime.visual.rpm =
            boundedRPM;

        if (
            typeof runtime.simulation
                ?.setRPM ===
            "function"
        ) {

            runtime.simulation
                .setRPM(
                    boundedRPM
                );

            runtime.stats
                .rpmUpdates +=
                1;

        }

        if (
            boundedRPM ===
                0
        ) {

            if (
                typeof runtime.simulation
                    ?.stop ===
                "function"
            ) {

                runtime.simulation
                    .stop();

            }

        }

        else {

            if (
                typeof runtime.simulation
                    ?.run ===
                "function"
            ) {

                runtime.simulation
                    .run();

            }

        }

    }

    function updateVibration(
        delta
    ) {

        if (
            !CONFIG.vibration.enabled ||
            !runtime.engine
        ) {

            return;

        }

        const target =
            runtime.visual
                .targetVibrationG;

        if (
            target === null
        ) {

            const factor =

                1 -

                Math.exp(

                    -CONFIG
                        .vibration
                        .decayResponse *

                    delta

                );

            runtime.visual
                .vibrationG +=

                (
                    0 -
                    runtime.visual
                        .vibrationG
                )

                *

                factor;

        }

        else {

            runtime.visual
                .vibrationG =
                smoothValue(

                    runtime.visual
                        .vibrationG,

                    Math.max(
                        0,
                        target
                    ),

                    CONFIG.response,

                    delta

                );

        }

        const vibrationG =
            runtime.visual
                .vibrationG;

        const amplitude =
            clamp(

                vibrationG *

                CONFIG
                    .vibration
                    .positionGain,

                0,

                CONFIG
                    .vibration
                    .maximumPositionAmplitude

            );

        const rotationAmplitude =
            clamp(

                vibrationG *

                CONFIG
                    .vibration
                    .rotationGain,

                0,

                CONFIG
                    .vibration
                    .maximumRotationAmplitude

            );

        const frequency =

            CONFIG
                .vibration
                .baseFrequencyHz

            +

            vibrationG *

            CONFIG
                .vibration
                .frequencyGain;

        const time =
            performance.now() *
            0.001;

        const basePosition =
            runtime
                .baseEngineTransform
                .position;

        const baseRotation =
            runtime
                .baseEngineTransform
                .rotation;

        if (
            !basePosition ||
            !baseRotation
        ) {

            return;

        }

        runtime.engine
            .position
            .set(

                basePosition.x +

                Math.sin(
                    time *
                    frequency
                ) *
                amplitude,

                basePosition.y +

                Math.sin(
                    time *
                    frequency *
                    1.17
                ) *
                amplitude *
                0.62,

                basePosition.z +

                Math.cos(
                    time *
                    frequency *
                    0.91
                ) *
                amplitude *
                0.48

            );

        runtime.engine
            .rotation
            .set(

                baseRotation.x +

                Math.sin(
                    time *
                    frequency *
                    0.73
                ) *
                rotationAmplitude *
                0.35,

                baseRotation.y +

                Math.cos(
                    time *
                    frequency *
                    0.61
                ) *
                rotationAmplitude *
                0.22,

                baseRotation.z +

                Math.sin(
                    time *
                    frequency *
                    0.82
                ) *
                rotationAmplitude

            );

        runtime.stats
            .vibrationUpdates +=
            1;

    }

    function temperatureColor(
        value,
        warm,
        hot,
        critical
    ) {

        if (
            value < warm
        ) {

            return {

                r:
                    0.05,

                g:
                    0.10,

                b:
                    0.14

            };

        }

        if (
            value < hot
        ) {

            const t =
                clamp(

                    (
                        value -
                        warm
                    ) /

                    (
                        hot -
                        warm
                    ),

                    0,

                    1

                );

            return {

                r:
                    0.15 +
                    0.55 * t,

                g:
                    0.10 +
                    0.18 * t,

                b:
                    0.03

            };

        }

        const denominator =
            critical -
            hot;

        const t =
            denominator > 0

                ? clamp(

                    (
                        value -
                        hot
                    ) /
                    denominator,

                    0,

                    1

                )

                : 1;

        return {

            r:
                0.70 +
                0.30 * t,

            g:
                0.15 +
                0.15 * t,

            b:
                0.03

        };

    }

    function updateCylinderThermalVisuals() {

        if (
            !CONFIG.thermal.enabled
        ) {

            return;

        }

        const cht =
            runtime.telemetry
                .cht;

        if (
            !Array.isArray(
                cht
            ) ||
            cht.length ===
                0
        ) {

            return;

        }

        cht.forEach(
            (
                temperature,
                cylinderIndex
            ) => {

                if (
                    temperature ===
                        null
                ) {

                    return;

                }

                const materials =
                    runtime
                        .cylinderMaterials[
                            cylinderIndex
                        ];

                if (
                    !Array.isArray(
                        materials
                    )
                ) {

                    return;

                }

                const heatColor =
                    temperatureColor(

                        temperature,

                        CONFIG
                            .thermal
                            .chtWarmC,

                        CONFIG
                            .thermal
                            .chtHotC,

                        CONFIG
                            .thermal
                            .chtCriticalC

                    );

                const normalized =
                    clamp(

                        (
                            temperature -

                            CONFIG
                                .thermal
                                .chtColdC
                        )

                        /

                        (
                            CONFIG
                                .thermal
                                .chtCriticalC -

                            CONFIG
                                .thermal
                                .chtColdC
                        ),

                        0,

                        1

                    );

                materials.forEach(
                    material => {

                        if (
                            material.emissive &&
                            typeof material
                                .emissive
                                .setRGB ===
                            "function"
                        ) {

                            material
                                .emissive
                                .setRGB(

                                    heatColor.r,

                                    heatColor.g,

                                    heatColor.b

                                );

                            if (
                                "emissiveIntensity"
                                in material
                            ) {

                                material
                                    .emissiveIntensity =

                                    normalized *

                                    CONFIG
                                        .thermal
                                        .maximumEmissiveIntensity;

                            }

                        }

                    }
                );

                runtime.stats
                    .thermalUpdates +=
                    1;

            }
        );

    }

    function updateFuelVisual() {

        const fuelGroup =
            runtime.groups
                ?.fuelFlow;

        if (
            !fuelGroup
        ) {

            return;

        }

        const flow =
            runtime.telemetry
                .fuelFlow;

        if (
            flow === null
        ) {

            return;

        }

        fuelGroup.visible =

            flow >

            CONFIG
                .fuel
                .minimumVisibleFlow;

        runtime.stats
            .fuelUpdates +=
            1;

    }

    function resolveFaultPayload(
        payload
    ) {

        if (
            !isObject(
                payload
            )
        ) {

            return null;

        }

        return firstObject(

            payload.fault_detection,

            payload.faults,

            payload.diagnostics,

            payload.pipeline
                ?.fault_detection,

            payload.data
                ?.fault_detection,

            payload

        );

    }

    function applyDiagnostics(
        payload
    ) {

        const faultPayload =
            resolveFaultPayload(
                payload
            );

        if (
            !faultPayload
        ) {

            return false;

        }

        const overallState =
            firstDefined(

                faultPayload
                    .overall_state,

                faultPayload
                    .state

            );

        runtime
            .diagnostics
            .overallState =

            overallState ===
                null

                ? null

                : String(
                    overallState
                )
                    .toUpperCase();

        const faults =
            firstDefined(

                faultPayload
                    .detected_faults,

                faultPayload
                    .active_faults,

                faultPayload
                    .faults

            );

        runtime
            .diagnostics
            .faults =

            Array.isArray(
                faults
            )

                ? faults

                : [];

        runtime.stats
            .diagnosticEvents +=
            1;

        return true;

    }

    function applyTelemetry(
        payload,
        options = {}
    ) {

        const metadata =
            extractSourceMetadata(
                payload
            );

        if (
            options
                .skipSourceValidation !==
                true &&

            !validateCanonicalSource(
                metadata
            )
        ) {

            runtime.stats
                .rejectedTelemetryEvents +=
                1;

            runtime.source
                .lastRejectedSource =
                metadata.source;

            return false;

        }

        if (
            metadata.source ===
                "REPLAY" &&

            metadata.replay !==
                true
        ) {

            runtime.stats
                .rejectedTelemetryEvents +=
                1;

            runtime.source
                .lastRejectedSource =
                metadata.source;

            return false;

        }

        const identity =
            buildFrameIdentity(
                metadata
            );

        if (
            identity !== null &&
            identity ===
                runtime
                    .lastFrameIdentity
        ) {

            runtime.stats
                .duplicateFrames +=
                1;

            return false;

        }

        const extracted =
            extractTelemetry(
                payload
            );

        if (
            !extracted
        ) {

            runtime.stats
                .rejectedTelemetryEvents +=
                1;

            return false;

        }

        if (
            identity !==
                null
        ) {

            runtime.lastFrameIdentity =
                identity;

        }

        runtime.lastTelemetryAt =
            Date.now();

        runtime.telemetryReceived +=
            1;

        runtime.stats
            .acceptedTelemetryEvents +=
            1;

        runtime.source.active =
            metadata.source;

        runtime.source.original =
            metadata.originalSource;

        runtime.source.replay =
            metadata.replay;

        runtime.source.sequence =
            metadata.sequence;

        runtime.source.missionId =
            metadata.missionId;

        runtime.source.timestamp =
            metadata.timestamp;

        runtime.source
            .lastAcceptedSource =
            metadata.source;

        runtime.source
            .lastRejectedSource =
            null;

        if (
            metadata.source ===
                "REPLAY"
        ) {

            runtime.stats
                .replayFrames +=
                1;

        }

        else if (
            metadata.source ===
                "SIMULATION"
        ) {

            runtime.stats
                .simulationFrames +=
                1;

        }

        else if (
            metadata.source ===
                "LIVE"
        ) {

            runtime.stats
                .liveFrames +=
                1;

        }

        else {

            runtime.stats
                .unknownSourceFrames +=
                1;

        }

        runtime.telemetry.rpm =
            extracted.rpm;

        runtime.telemetry
            .loadPercent =
            extracted.loadPercent;

        runtime.telemetry
            .throttlePercent =
            extracted.throttlePercent;

        runtime.telemetry
            .vibrationG =
            extracted.vibrationG;

        runtime.telemetry.cht =
            extracted.cht;

        runtime.telemetry.egt =
            extracted.egt;

        runtime.telemetry
            .oilPressureKpa =
            extracted.oilPressureKpa;

        runtime.telemetry
            .oilTemperatureC =
            extracted.oilTemperatureC;

        runtime.telemetry
            .fuelPressureKpa =
            extracted.fuelPressureKpa;

        runtime.telemetry
            .fuelFlow =
            extracted.fuelFlow;

        runtime.telemetry
            .powerKw =
            extracted.powerKw;

        runtime.telemetry
            .torqueNm =
            extracted.torqueNm;

        runtime.telemetry
            .altitudeM =
            extracted.altitudeM;

        runtime.visual
            .targetVibrationG =
            extracted.vibrationG;

        runtime.visual
            .loadPercent =
            extracted.loadPercent;

        runtime.visual
            .throttlePercent =
            extracted.throttlePercent;

        applyRPM();

        updateCylinderThermalVisuals();

        updateFuelVisual();

        applyDiagnostics(
            payload
        );

        window.dispatchEvent(

            new CustomEvent(

                "pratirup:engine-visual-frame-applied",

                {

                    detail: {

                        service:
                            SERVICE,

                        version:
                            VERSION,

                        source:
                            metadata.source,

                        original_source:
                            metadata
                                .originalSource,

                        replay:
                            metadata.replay,

                        sequence:
                            metadata.sequence,

                        mission_id:
                            metadata.missionId,

                        timestamp:
                            metadata.timestamp,

                        rpm:
                            extracted.rpm,

                        vibration_g:
                            extracted
                                .vibrationG,

                        oil_pressure_kpa:
                            extracted
                                .oilPressureKpa,

                        power_kw:
                            extracted.powerKw,

                        torque_nm:
                            extracted.torqueNm,

                        altitude_m:
                            extracted.altitudeM

                    }

                }

            )

        );

        return true;

    }

    function canonicalTelemetryEventHandler(
        event
    ) {

        runtime.stats
            .canonicalTelemetryEvents +=
            1;

        if (
            !event ||
            !event.detail
        ) {

            return;

        }

        applyTelemetry(
            event.detail
        );

    }

    function diagnosticEventHandler(
        event
    ) {

        if (
            event?.detail
        ) {

            applyDiagnostics(
                event.detail
            );

        }

    }

    function sourceModeEventHandler() {

        runtime.lastFrameIdentity =
            null;

    }

    function installListeners() {

        window.addEventListener(

            "pratirup:telemetry",

            canonicalTelemetryEventHandler

        );

        [

            "pratirup:diagnostics",

            "pratirup:fault-detection",

            "pratirup:fault",

            "pratirup:pipeline"

        ]
        .forEach(
            eventName => {

                window.addEventListener(

                    eventName,

                    diagnosticEventHandler

                );

            }
        );

        window.addEventListener(

            "pratirup:telemetry-source-mode",

            sourceModeEventHandler

        );

        window.addEventListener(

            "pratirup:telemetry-source-change",

            sourceModeEventHandler

        );

    }

    function removeListeners() {

        window.removeEventListener(

            "pratirup:telemetry",

            canonicalTelemetryEventHandler

        );

        [

            "pratirup:diagnostics",

            "pratirup:fault-detection",

            "pratirup:fault",

            "pratirup:pipeline"

        ]
        .forEach(
            eventName => {

                window.removeEventListener(

                    eventName,

                    diagnosticEventHandler

                );

            }
        );

        window.removeEventListener(

            "pratirup:telemetry-source-mode",

            sourceModeEventHandler

        );

        window.removeEventListener(

            "pratirup:telemetry-source-change",

            sourceModeEventHandler

        );

    }

    function animate(
        timestamp
    ) {

        if (
            runtime.disposed
        ) {

            return;

        }

        runtime.animationFrame =
            requestAnimationFrame(
                animate
            );

        if (
            runtime.lastFrameTime ===
                null
        ) {

            runtime.lastFrameTime =
                timestamp;

            return;

        }

        const delta =
            Math.min(

                (
                    timestamp -
                    runtime.lastFrameTime
                ) /
                1000,

                CONFIG
                    .maximumDeltaSec

            );

        runtime.lastFrameTime =
            timestamp;

        runtime.stats.frames +=
            1;

        updateVibration(
            delta
        );

    }

    async function initialize() {

        if (
            runtime.initialized
        ) {

            return true;

        }

        runtime.disposed =
            false;

        try {

            runtime.simulation =
                await waitForSimulation();

            runtime.engine =
                runtime.simulation
                    .engine;

            runtime.groups =
                runtime.simulation
                    .groups;

            runtime.simulationReady =
                true;

            captureBaseTransform();

            prepareCylinderMaterials();

            installListeners();

            runtime.lastFrameTime =
                null;

            runtime.animationFrame =
                requestAnimationFrame(
                    animate
                );

            runtime.initialized =
                true;

            console.info(

                `[PRATIRUP Engine Visual Controller] v${VERSION} initialized — D5 canonical replay synchronization enabled.`

            );

            window.dispatchEvent(

                new CustomEvent(

                    "pratirup:engine-visual-controller-ready",

                    {

                        detail: {

                            service:
                                SERVICE,

                            version:
                                VERSION,

                            stage:
                                STAGE,

                            canonical_only:
                                true,

                            replay_ready:
                                true,

                            global_three_dependency:
                                false

                        }

                    }

                )

            );

            return true;

        }

        catch (
            error
        ) {

            console.error(

                "[PRATIRUP Engine Visual Controller] initialization failed:",

                error

            );

            runtime.simulationReady =
                false;

            return false;

        }

    }

    function resetEngineTransform() {

        if (
            !runtime.engine
        ) {

            return;

        }

        const position =
            runtime
                .baseEngineTransform
                .position;

        const rotation =
            runtime
                .baseEngineTransform
                .rotation;

        if (
            position &&
            runtime.engine.position &&
            typeof runtime.engine
                .position
                .copy ===
            "function"
        ) {

            runtime.engine
                .position
                .copy(
                    position
                );

        }

        if (
            rotation &&
            runtime.engine.rotation &&
            typeof runtime.engine
                .rotation
                .copy ===
            "function"
        ) {

            runtime.engine
                .rotation
                .copy(
                    rotation
                );

        }

    }

    function resetCylinderMaterials() {

        runtime
            .cylinderMaterials
            .forEach(
                (
                    materials,
                    cylinderIndex
                ) => {

                    if (
                        !Array.isArray(
                            materials
                        )
                    ) {

                        return;

                    }

                    const originals =
                        runtime
                            .originalCylinderMaterials[
                                cylinderIndex
                            ];

                    materials.forEach(
                        (
                            material,
                            materialIndex
                        ) => {

                            const original =
                                originals?.[
                                    materialIndex
                                ];

                            if (
                                !original
                            ) {

                                return;

                            }

                            if (
                                material.color &&
                                original.color &&
                                typeof material.color
                                    .copy ===
                                "function"
                            ) {

                                material.color
                                    .copy(
                                        original.color
                                    );

                            }

                            if (
                                material.emissive &&
                                original.emissive &&
                                typeof material.emissive
                                    .copy ===
                                "function"
                            ) {

                                material.emissive
                                    .copy(
                                        original.emissive
                                    );

                            }

                            if (
                                original
                                    .emissiveIntensity !==
                                null &&
                                "emissiveIntensity"
                                in material
                            ) {

                                material
                                    .emissiveIntensity =
                                    original
                                        .emissiveIntensity;

                            }

                        }
                    );

                }
            );

    }

    function reset() {

        runtime.telemetry = {

            rpm:
                null,

            loadPercent:
                null,

            throttlePercent:
                null,

            vibrationG:
                null,

            cht:
                [],

            egt:
                [],

            oilPressureKpa:
                null,

            oilTemperatureC:
                null,

            fuelPressureKpa:
                null,

            fuelFlow:
                null,

            powerKw:
                null,

            torqueNm:
                null,

            altitudeM:
                null

        };

        runtime.visual = {

            rpm:
                null,

            vibrationG:
                0,

            targetVibrationG:
                null,

            loadPercent:
                null,

            throttlePercent:
                null

        };

        runtime.source = {

            active:
                null,

            original:
                null,

            replay:
                false,

            sequence:
                null,

            missionId:
                null,

            timestamp:
                null,

            lastAcceptedSource:
                null,

            lastRejectedSource:
                null

        };

        runtime.diagnostics = {

            overallState:
                null,

            faults:
                []

        };

        runtime.lastFrameIdentity =
            null;

        runtime.lastTelemetryAt =
            null;

        resetEngineTransform();

        resetCylinderMaterials();

        return true;

    }

    function dispose() {

        if (
            runtime.disposed
        ) {

            return true;

        }

        runtime.disposed =
            true;

        removeListeners();

        if (
            runtime.animationFrame !==
                null
        ) {

            cancelAnimationFrame(
                runtime.animationFrame
            );

            runtime.animationFrame =
                null;

        }

        resetEngineTransform();

        resetCylinderMaterials();

        runtime.initialized =
            false;

        runtime.simulationReady =
            false;

        console.info(

            `[PRATIRUP Engine Visual Controller] v${VERSION} disposed.`

        );

        return true;

    }

    function getStatus() {

        const stale =

            runtime.lastTelemetryAt ===
                null

                ? true

                :

            Date.now() -
            runtime.lastTelemetryAt >

            CONFIG
                .telemetryStaleMs;

        const arbitration =
            getArbitrationStatus();

        return {

            service:
                SERVICE,

            version:
                VERSION,

            stage:
                STAGE,

            initialized:
                runtime.initialized,

            simulation_ready:
                runtime.simulationReady,

            canonical_telemetry_only:
                true,

            global_three_dependency:
                false,

            telemetry_received:
                runtime.telemetryReceived,

            telemetry_stale:
                stale,

            last_telemetry_at:
                runtime.lastTelemetryAt,

            source: {

                active:
                    runtime.source
                        .active,

                original:
                    runtime.source
                        .original,

                replay:
                    runtime.source
                        .replay,

                sequence:
                    runtime.source
                        .sequence,

                mission_id:
                    runtime.source
                        .missionId,

                timestamp:
                    runtime.source
                        .timestamp,

                last_accepted:
                    runtime.source
                        .lastAcceptedSource,

                last_rejected:
                    runtime.source
                        .lastRejectedSource

            },

            arbitration:
                arbitration
                    ? {

                        mode:
                            firstDefined(

                                arbitration.mode,

                                arbitration
                                    .sourceMode,

                                arbitration
                                    .source_mode

                            ),

                        replay_active:
                            arbitration
                                .replayActive ===
                            true

                    }
                    : null,

            telemetry: {

                rpm:
                    runtime.telemetry
                        .rpm,

                load_percent:
                    runtime.telemetry
                        .loadPercent,

                throttle_percent:
                    runtime.telemetry
                        .throttlePercent,

                vibration_g:
                    runtime.telemetry
                        .vibrationG,

                cht:
                    [
                        ...runtime.telemetry
                            .cht
                    ],

                egt:
                    [
                        ...runtime.telemetry
                            .egt
                    ],

                oil_pressure_kpa:
                    runtime.telemetry
                        .oilPressureKpa,

                oil_temperature_c:
                    runtime.telemetry
                        .oilTemperatureC,

                fuel_pressure_kpa:
                    runtime.telemetry
                        .fuelPressureKpa,

                fuel_flow:
                    runtime.telemetry
                        .fuelFlow,

                power_kw:
                    runtime.telemetry
                        .powerKw,

                torque_nm:
                    runtime.telemetry
                        .torqueNm,

                altitude_m:
                    runtime.telemetry
                        .altitudeM

            },

            visual: {

                rpm:
                    runtime.visual
                        .rpm,

                vibration_g:
                    runtime.visual
                        .vibrationG,

                target_vibration_g:
                    runtime.visual
                        .targetVibrationG,

                load_percent:
                    runtime.visual
                        .loadPercent,

                throttle_percent:
                    runtime.visual
                        .throttlePercent

            },

            diagnostics: {

                overall_state:
                    runtime
                        .diagnostics
                        .overallState,

                fault_count:
                    runtime
                        .diagnostics
                        .faults
                        .length

            },

            stats: {

                ...runtime.stats

            },

            semantics: {

                zero:
                    "valid_numeric_zero",

                null:
                    "unavailable"

            },

            isolation: {

                consumes_raw_backend_telemetry:
                    false,

                consumes_raw_replay_telemetry:
                    false,

                consumes_canonical_telemetry:
                    true,

                posts_api_telemetry:
                    false,

                writes_database:
                    false,

                creates_replay_timer:
                    false,

                reruns_models:
                    false

            },

            scope: {

                calculates_health:
                    false,

                calculates_faults:
                    false,

                calculates_rul:
                    false,

                calculates_maintenance:
                    false,

                calculates_physics:
                    false,

                modifies_can_fadec:
                    false,

                modifies_source_arbitration:
                    false

            }

        };

    }

    function testVibration(
        vibrationG = 1
    ) {

        const value =
            finiteNumber(
                vibrationG
            );

        if (
            value ===
                null
        ) {

            return false;

        }

        runtime.visual
            .targetVibrationG =
            Math.max(
                0,
                value
            );

        runtime.telemetry
            .vibrationG =
            Math.max(
                0,
                value
            );

        return true;

    }

    function testCanonicalFrame(
        frame
    ) {

        return applyTelemetry(

            frame,

            {

                skipSourceValidation:
                    true

            }

        );

    }

    window.PRATIRUPEngineVisualController = {

        VERSION,

        SERVICE,

        STAGE,

        initialize,

        applyTelemetry,

        applyDiagnostics,

        getStatus,

        testVibration,

        testCanonicalFrame,

        reset,

        dispose

    };

    window.addEventListener(

        "pratirup:simulation-ready",

        () => {

            initialize();

        },

        {
            once:
                true
        }

    );

    if (
        window.PRATIRUP_SIMULATION
    ) {

        initialize();

    }

})();
