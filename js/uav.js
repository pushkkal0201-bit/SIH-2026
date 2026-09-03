import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const VERSION = "3.2.0";

const CONFIG = Object.freeze({
    hostId: "uavMissionCanvasHost",
    pixelRatioCap: 2,

    world: {
        width: 5200,
        depth: 3000,
        terrainSegmentsX: 180,
        terrainSegmentsZ: 110,
        seaLevel: -18,
        runwayHeight: 2
    },

    mission: {
        expectedDurationSec: 760,
        altitudeScale: 0.045,
        maximumVisualAltitude: 300
    },

    aircraft: {
        scale: 0.82,
        minimumPropellerRPM: 20
    },

    motion: {
        maximumFrameDeltaSec: 0.05,
        maximumPredictionLeadSec: 2.25,
        maximumProgressRatePerSec: 0.08,

        teleportThreshold: 0.12,
        backwardsResetThreshold: 0.015,

        progressHalfLifeSec: 0.085,
        velocityHalfLifeSec: 0.22,
        altitudeHalfLifeSec: 0.16,
        attitudeHalfLifeSec: 0.075,
        bankHalfLifeSec: 0.12,
        pitchHalfLifeSec: 0.12,
        propellerHalfLifeSec: 0.08,

        cameraPositionHalfLifeSec: 0.14,
        cameraTargetHalfLifeSec: 0.10,

        sampleBufferSize: 12
    },

    camera: {
        defaultMode: "FOLLOW",
        near: 0.1,
        far: 14000,
        fov: 48
    }
});

const CAMERA_MODES = Object.freeze([
    "FOLLOW",
    "TOP",
    "SIDE",
    "FRONT",
    "REAR",
    "COCKPIT",
    "ORBIT"
]);

const PHASES = Object.freeze([
    "ENGINE_START",
    "WARMUP",
    "TAKEOFF",
    "CLIMB",
    "CRUISE",
    "HIGH_ALTITUDE",
    "DESCENT",
    "LANDING",
    "ENGINE_SHUTDOWN"
]);

const PHASE_LABELS = Object.freeze({
    ENGINE_START: "ENGINE START",
    WARMUP: "WARMUP",
    TAKEOFF: "TAKEOFF",
    CLIMB: "CLIMB",
    CRUISE: "CRUISE",
    HIGH_ALTITUDE: "HIGH ALTITUDE",
    DESCENT: "DESCENT",
    LANDING: "LANDING",
    ENGINE_SHUTDOWN: "ENGINE SHUTDOWN"
});

const runtime = {
    initialized: false,
    running: false,
    disposed: false,

    host: null,
    scene: null,
    renderer: null,
    camera: null,
    controls: null,
    clock: null,
    resizeObserver: null,
    animationFrame: null,

    world: null,
    aircraftRoot: null,
    aircraftModel: null,
    propeller: null,
    landingGear: null,
    navigationLights: null,
    engineBeacon: null,

    routeCurve: null,
    routeLine: null,
    clouds: [],
    hud: null,

    cameraMode: CONFIG.camera.defaultMode,
    backendConnected: false,

    mission: {
        state: "IDLE",
        phase: "ENGINE_START",
        elapsedTimeSec: 0,
        totalTimeSec: CONFIG.mission.expectedDurationSec,
        progress: 0,
        simulationSpeed: 1,

        altitudeM: null,
        rpm: null,
        loadPercent: null,
        throttlePercent: null,
        ambientTemperatureC: null,

        activeFaultCount: 0,
        activeFaults: []
    },

    visual: {
        routeProgress: 0,
        targetRouteProgress: 0,

        altitude: 0,
        targetAltitude: 0,

        propellerRPM: 0,
        targetPropellerRPM: 0,

        bank: 0,
        targetBank: 0,

        pitch: 0,
        targetPitch: 0
    },

    motion: {
        progressSamples: [],
        estimatedProgressRate: 0,
        lastAuthoritativeProgress: 0,
        lastSampleTimeMs: 0,
        predictedProgress: 0,
        correctionError: 0,
        hardSyncs: 0,
        softCorrections: 0
    },

    stats: {
        frames: 0,
        backendUpdates: 0,
        telemetryUpdates: 0,
        startedAt: null,
        lastBackendUpdateAt: null
    }
};


const LOCAL_FORWARD = new THREE.Vector3(1, 0, 0);
const LOCAL_UP = new THREE.Vector3(0, 1, 0);
const LOCAL_RIGHT = new THREE.Vector3(0, 0, 1);

const routeTangent = new THREE.Vector3();
const flightQuaternion = new THREE.Quaternion();

const worldForward = new THREE.Vector3();
const worldRight = new THREE.Vector3();
const worldUp = new THREE.Vector3();

const cameraDesiredPosition = new THREE.Vector3();
const cameraDesiredTarget = new THREE.Vector3();

const tempQuaternion = new THREE.Quaternion();
const bankQuaternion = new THREE.Quaternion();
const pitchQuaternion = new THREE.Quaternion();

const predictedRoutePosition = new THREE.Vector3();
const predictedRouteTangent = new THREE.Vector3();

function finiteNumber(value) {
    if (
        value === null ||
        value === undefined ||
        typeof value === "boolean"
    ) {
        return null;
    }

    const number = Number(value);
    return Number.isFinite(number) ? number : null;
}

function clamp(value, minimum, maximum) {
    return Math.min(maximum, Math.max(minimum, value));
}

function lerp(start, end, amount) {
    return start + (end - start) * amount;
}

function smoothstep(value) {
    const x = clamp(value, 0, 1);
    return x * x * (3 - 2 * x);
}

/*
 * Frame-rate-independent exponential smoothing.
 * It feels the same at 30, 60, 120 or 144 FPS.
 */
function smoothingAlpha(
    deltaSec,
    halfLifeSec
) {
    if (halfLifeSec <= 0) {
        return 1;
    }

    return 1 -
        Math.pow(
            2,
            -deltaSec / halfLifeSec
        );
}

function damp(
    current,
    target,
    deltaSec,
    halfLifeSec
) {
    return lerp(
        current,
        target,
        smoothingAlpha(
            deltaSec,
            halfLifeSec
        )
    );
}

function missionIsAdvancing() {
    const state =
        String(
            runtime.mission.state ??
            ""
        )
            .trim()
            .toUpperCase();

    if (
        [
            "RUNNING",
            "PLAYING",
            "ACTIVE",
            "STARTED",
            "RESUMED"
        ].includes(state)
    ) {
        return true;
    }

    if (
        [
            "IDLE",
            "PAUSED",
            "STOPPED",
            "COMPLETE",
            "COMPLETED",
            "FINISHED",
            "ERROR",
            "FAILED"
        ].includes(state)
    ) {
        return false;
    }

    return Math.abs(
        runtime.motion.estimatedProgressRate
    ) > 0.0000005;
}

function nominalProgressRate() {
    const total =
        finiteNumber(
            runtime.mission.totalTimeSec
        );

    const speed =
        finiteNumber(
            runtime.mission.simulationSpeed
        );

    if (
        total === null ||
        total <= 0 ||
        speed === null ||
        speed <= 0
    ) {
        return 0;
    }

    return clamp(
        speed / total,
        0,
        CONFIG.motion
            .maximumProgressRatePerSec
    );
}

function hardSyncProgress(
    progress,
    timeMs = performance.now()
) {
    const value =
        clamp(
            progress,
            0,
            1
        );

    runtime.motion.progressSamples.length =
        0;

    runtime.motion.progressSamples.push({
        progress: value,
        timeMs
    });

    runtime.motion.estimatedProgressRate =
        missionIsAdvancing()
            ? nominalProgressRate()
            : 0;

    runtime.motion.lastAuthoritativeProgress =
        value;

    runtime.motion.lastSampleTimeMs =
        timeMs;

    runtime.motion.predictedProgress =
        value;

    runtime.motion.correctionError =
        0;

    runtime.visual.routeProgress =
        value;

    runtime.visual.targetRouteProgress =
        value;

    runtime.motion.hardSyncs++;
}

function recordProgressSample(
    progress,
    timeMs = performance.now()
) {
    const value =
        clamp(
            progress,
            0,
            1
        );

    const samples =
        runtime.motion.progressSamples;

    const previous =
        samples.length
            ? samples[
                samples.length - 1
            ]
            : null;

    if (!previous) {
        hardSyncProgress(
            value,
            timeMs
        );
        return;
    }

    const deltaProgress =
        value -
        previous.progress;

    const deltaTimeSec =
        Math.max(
            0,
            (
                timeMs -
                previous.timeMs
            ) /
                1000
        );

    const isRestart =
        deltaProgress <
        -CONFIG.motion
            .backwardsResetThreshold;

    const isTeleport =
        Math.abs(
            deltaProgress
        ) >
        CONFIG.motion
            .teleportThreshold;

    /*
     * Deliberate mission reset / scrub:
     * perform one clean sync rather than visually flying through half
     * the mission to catch up.
     */
    if (
        isRestart ||
        isTeleport
    ) {
        hardSyncProgress(
            value,
            timeMs
        );
        return;
    }

    if (deltaTimeSec > 0.001) {
        const measuredRate =
            clamp(
                deltaProgress /
                    deltaTimeSec,
                -CONFIG.motion
                    .maximumProgressRatePerSec,
                CONFIG.motion
                    .maximumProgressRatePerSec
            );

        runtime.motion
            .estimatedProgressRate =
            lerp(
                runtime.motion
                    .estimatedProgressRate,
                measuredRate,
                smoothingAlpha(
                    deltaTimeSec,
                    CONFIG.motion
                        .velocityHalfLifeSec
                )
            );

        if (
            deltaProgress > 0 &&
            missionIsAdvancing()
        ) {
            runtime.motion
                .estimatedProgressRate =
                Math.max(
                    runtime.motion
                        .estimatedProgressRate,
                    nominalProgressRate() *
                        0.35
                );
        }
    }

    samples.push({
        progress: value,
        timeMs
    });

    while (
        samples.length >
        CONFIG.motion.sampleBufferSize
    ) {
        samples.shift();
    }

    runtime.motion.lastAuthoritativeProgress =
        value;

    runtime.motion.lastSampleTimeMs =
        timeMs;

    runtime.visual.targetRouteProgress =
        value;
}

function predictedMissionProgress(
    nowMs = performance.now()
) {
    const samples =
        runtime.motion.progressSamples;

    const latest =
        samples.length
            ? samples[
                samples.length - 1
            ]
            : null;

    if (!latest) {
        return clamp(
            runtime.mission.progress,
            0,
            1
        );
    }

    if (
        !missionIsAdvancing() ||
        latest.progress >= 1
    ) {
        runtime.motion.predictedProgress =
            latest.progress;

        return latest.progress;
    }

    const sampleAgeSec =
        clamp(
            (
                nowMs -
                latest.timeMs
            ) /
                1000,
            0,
            CONFIG.motion
                .maximumPredictionLeadSec
        );

    let rate =
        runtime.motion
            .estimatedProgressRate;

    if (
        !Number.isFinite(rate) ||
        rate <= 0.0000005
    ) {
        rate =
            nominalProgressRate();
    }

    rate =
        clamp(
            rate,
            0,
            CONFIG.motion
                .maximumProgressRatePerSec
        );

    const predicted =
        clamp(
            latest.progress +
                rate *
                sampleAgeSec,
            latest.progress,
            1
        );

    runtime.motion.predictedProgress =
        predicted;

    return predicted;
}

function normalizeProgress(value) {
    const number = finiteNumber(value);

    if (number === null) {
        return null;
    }

    return clamp(
        number <= 1 ? number : number / 100,
        0,
        1
    );
}

function normalizePhase(value) {
    const normalized = String(value ?? "")
        .trim()
        .toUpperCase();

    return PHASES.includes(normalized)
        ? normalized
        : runtime.mission.phase;
}

function terrainNoise(x, z) {
    return (
        Math.sin(x * 0.009) *
            Math.cos(z * 0.012) *
            0.45 +

        Math.sin(
            x * 0.021 +
            z * 0.017
        ) *
            0.30 +

        Math.cos(
            x * 0.004 -
            z * 0.024
        ) *
            0.18 +

        Math.sin(
            (x + z) * 0.033
        ) *
            0.07
    );
}

function mountainMask(
    x,
    z,
    centerX,
    centerZ,
    width,
    depth
) {
    const dx = (x - centerX) / width;
    const dz = (z - centerZ) / depth;

    return clamp(
        1 - Math.sqrt(dx * dx + dz * dz),
        0,
        1
    );
}

function terrainHeight(x, z) {
    let height =
        -4 +
        terrainNoise(x, z) * 16;

    // Airfield Alpha flat region.
    if (x < -1750) {
        height = lerp(height, 0, 0.84);
    }

    // Lower hills.
    const hill = mountainMask(
        x,
        z,
        -1150,
        -160,
        800,
        600
    );

    height +=
        hill *
        hill *
        (
            65 +
            Math.abs(
                terrainNoise(
                    x * 1.7,
                    z * 1.7
                )
            ) *
                55
        );

    // Main mountain range.
    const mountain = mountainMask(
        x,
        z,
        -350,
        180,
        1050,
        720
    );

    height +=
        mountain *
        mountain *
        (
            150 +
            Math.abs(
                terrainNoise(
                    x * 2.3,
                    z * 2.1
                )
            ) *
                135
        );

    // Secondary ridge.
    const ridge = mountainMask(
        x,
        z,
        450,
        -270,
        700,
        480
    );

    height +=
        ridge *
        ridge *
        (
            80 +
            Math.abs(
                terrainNoise(
                    x * 2.7,
                    z * 2.4
                )
            ) *
                70
        );

    // Sea basin.
    if (x > 650 && x < 1600) {
        const entry = smoothstep(
            (x - 650) / 260
        );

        const exit =
            1 -
            smoothstep(
                (x - 1350) / 250
            );

        const seaWeight =
            Math.min(
                entry,
                exit
            );

        height = lerp(
            height,
            CONFIG.world.seaLevel - 24,
            seaWeight
        );
    }

    // Destination mainland.
    if (x > 1550) {
        const destinationBlend =
            smoothstep(
                (x - 1550) / 380
            );

        const destinationHeight =
            -1 +
            terrainNoise(x, z) * 7;

        height = lerp(
            height,
            destinationHeight,
            destinationBlend
        );
    }

    // Airfield Bravo flat region.
    if (x > 1980) {
        height = lerp(
            height,
            0,
            0.89
        );
    }

    return height;
}

function createTerrain() {
    const geometry =
        new THREE.PlaneGeometry(
            CONFIG.world.width,
            CONFIG.world.depth,
            CONFIG.world.terrainSegmentsX,
            CONFIG.world.terrainSegmentsZ
        );

    geometry.rotateX(
        -Math.PI / 2
    );

    const positions =
        geometry.getAttribute(
            "position"
        );

    const colors = [];

    for (
        let index = 0;
        index < positions.count;
        index++
    ) {
        const x =
            positions.getX(index);

        const z =
            positions.getZ(index);

        const height =
            terrainHeight(
                x,
                z
            );

        positions.setY(
            index,
            height
        );

        const color =
            new THREE.Color();

        if (
            height <
            CONFIG.world.seaLevel + 3
        ) {
            color.setHex(
                0x40533b
            );
        } else if (height < 20) {
            color.setHex(
                0x3d683d
            );
        } else if (height < 70) {
            color.setHex(
                0x547746
            );
        } else if (height < 135) {
            color.setHex(
                0x667354
            );
        } else if (height < 205) {
            color.setHex(
                0x736d62
            );
        } else {
            color.setHex(
                0xc7c9c5
            );
        }

        colors.push(
            color.r,
            color.g,
            color.b
        );
    }

    geometry.setAttribute(
        "color",
        new THREE.Float32BufferAttribute(
            colors,
            3
        )
    );

    geometry.computeVertexNormals();

    const material =
        new THREE.MeshStandardMaterial({
            vertexColors: true,
            roughness: 0.94,
            metalness: 0
        });

    const terrain =
        new THREE.Mesh(
            geometry,
            material
        );

    terrain.receiveShadow = true;

    return terrain;
}

function createSea() {
    const geometry =
        new THREE.PlaneGeometry(
            1150,
            2300,
            28,
            28
        );

    const material =
        new THREE.MeshPhysicalMaterial({
            color: 0x17658a,
            roughness: 0.18,
            metalness: 0.05,
            transparent: true,
            opacity: 0.92,
            clearcoat: 0.75,
            clearcoatRoughness: 0.15
        });

    const sea =
        new THREE.Mesh(
            geometry,
            material
        );

    sea.rotation.x =
        -Math.PI / 2;

    sea.position.set(
        1100,
        CONFIG.world.seaLevel,
        0
    );

    return sea;
}

function createSky() {
    const geometry =
        new THREE.SphereGeometry(
            7000,
            48,
            28
        );

    const material =
        new THREE.ShaderMaterial({
            side: THREE.BackSide,

            uniforms: {
                topColor: {
                    value:
                        new THREE.Color(
                            0x135e9e
                        )
                },

                middleColor: {
                    value:
                        new THREE.Color(
                            0x6eb9e5
                        )
                },

                horizonColor: {
                    value:
                        new THREE.Color(
                            0xd5ecf8
                        )
                }
            },

            vertexShader: `
                varying vec3 vWorldPosition;

                void main() {
                    vec4 worldPosition =
                        modelMatrix *
                        vec4(position, 1.0);

                    vWorldPosition =
                        worldPosition.xyz;

                    gl_Position =
                        projectionMatrix *
                        modelViewMatrix *
                        vec4(position, 1.0);
                }
            `,

            fragmentShader: `
                uniform vec3 topColor;
                uniform vec3 middleColor;
                uniform vec3 horizonColor;

                varying vec3 vWorldPosition;

                void main() {
                    float h =
                        normalize(
                            vWorldPosition
                        ).y;

                    float upper =
                        smoothstep(
                            0.15,
                            0.90,
                            h
                        );

                    float middle =
                        smoothstep(
                            -0.05,
                            0.35,
                            h
                        );

                    vec3 baseColor =
                        mix(
                            horizonColor,
                            middleColor,
                            middle
                        );

                    vec3 finalColor =
                        mix(
                            baseColor,
                            topColor,
                            upper
                        );

                    gl_FragColor =
                        vec4(
                            finalColor,
                            1.0
                        );
                }
            `
        });

    return new THREE.Mesh(
        geometry,
        material
    );
}

function createCloud(
    x,
    y,
    z,
    scale
) {
    const root =
        new THREE.Group();

    const material =
        new THREE.MeshStandardMaterial({
            color: 0xffffff,
            roughness: 1,
            transparent: true,
            opacity: 0.67,
            depthWrite: false
        });

    const pieces = [
        [0, 0, 0, 22],
        [17, 2, 2, 17],
        [-18, 2, 1, 16],
        [4, 8, -5, 19],
        [-8, 7, 7, 16]
    ];

    for (const piece of pieces) {
        const mesh =
            new THREE.Mesh(
                new THREE.SphereGeometry(
                    piece[3],
                    16,
                    10
                ),
                material
            );

        mesh.position.set(
            piece[0],
            piece[1],
            piece[2]
        );

        root.add(mesh);
    }

    root.position.set(
        x,
        y,
        z
    );

    root.scale.setScalar(
        scale
    );
    return root;
}

function createLabel(text) {
    const canvas =
        document.createElement(
            "canvas"
        );

    canvas.width = 512;
    canvas.height = 128;

    const context =
        canvas.getContext(
            "2d"
        );

    context.fillStyle =
        "rgba(5, 16, 26, 0.82)";

    context.fillRect(
        0,
        0,
        512,
        128
    );

    context.strokeStyle =
        "#00d9ff";

    context.lineWidth = 4;

    context.strokeRect(
        2,
        2,
        508,
        124
    );

    context.fillStyle =
        "#ffffff";

    context.font =
        "bold 39px Arial";

    context.textAlign =
        "center";

    context.textBaseline =
        "middle";

    context.fillText(
        text,
        256,
        64
    );

    const texture =
        new THREE.CanvasTexture(
            canvas
        );

    texture.colorSpace =
        THREE.SRGBColorSpace;

    return new THREE.Sprite(
        new THREE.SpriteMaterial({
            map: texture,
            transparent: true,
            depthWrite: false
        })
    );
}


function createAirfield(
    name,
    worldX
) {
    const root =
        new THREE.Group();

    root.name = name;

    root.position.set(
        worldX,
        CONFIG.world.runwayHeight,
        0
    );

    const runway =
        new THREE.Mesh(
            new THREE.PlaneGeometry(
                520,
                38
            ),
            new THREE.MeshStandardMaterial({
                color: 0x282d30,
                roughness: 0.96
            })
        );

    runway.rotation.x =
        -Math.PI / 2;

    runway.receiveShadow = true;
    root.add(runway);

    const white =
        new THREE.MeshBasicMaterial({
            color: 0xe7ecee
        });

    // Runway edges.
    for (const z of [-17.5, 17.5]) {
        const edge =
            new THREE.Mesh(
                new THREE.PlaneGeometry(
                    500,
                    0.55
                ),
                white
            );

        edge.rotation.x =
            -Math.PI / 2;

        edge.position.set(
            0,
            0.04,
            z
        );

        root.add(edge);
    }

    // Centerline.
    for (
        let x = -220;
        x <= 220;
        x += 30
    ) {
        const line =
            new THREE.Mesh(
                new THREE.PlaneGeometry(
                    14,
                    0.8
                ),
                white
            );

        line.rotation.x =
            -Math.PI / 2;

        line.position.set(
            x,
            0.05,
            0
        );

        root.add(line);
    }

    // Threshold markings.
    for (const thresholdX of [-225, 225]) {
        for (
            let z = -12;
            z <= 12;
            z += 4
        ) {
            const stripe =
                new THREE.Mesh(
                    new THREE.PlaneGeometry(
                        14,
                        2
                    ),
                    white
                );

            stripe.rotation.x =
                -Math.PI / 2;

            stripe.position.set(
                thresholdX,
                0.055,
                z
            );

            root.add(stripe);
        }
    }

    // Taxiway.
    const taxiway =
        new THREE.Mesh(
            new THREE.PlaneGeometry(
                200,
                17
            ),
            new THREE.MeshStandardMaterial({
                color: 0x3b4144,
                roughness: 0.93
            })
        );

    taxiway.rotation.x =
        -Math.PI / 2;

    taxiway.rotation.z =
        THREE.MathUtils.degToRad(
            32
        );

    taxiway.position.set(
        -105,
        0.01,
        72
    );

    root.add(taxiway);

    // Apron.
    const apron =
        new THREE.Mesh(
            new THREE.PlaneGeometry(
                160,
                105
            ),
            new THREE.MeshStandardMaterial({
                color: 0x555a5c,
                roughness: 0.96
            })
        );

    apron.rotation.x =
        -Math.PI / 2;

    apron.position.set(
        -170,
        0,
        145
    );

    root.add(apron);

    // Hangars.
    for (
        let index = 0;
        index < 3;
        index++
    ) {
        const hangar =
            new THREE.Mesh(
                new THREE.BoxGeometry(
                    52,
                    24,
                    45
                ),
                new THREE.MeshStandardMaterial({
                    color: 0x7d8587,
                    roughness: 0.82
                })
            );

        hangar.position.set(
            -195 + index * 62,
            12,
            210
        );

        hangar.castShadow = true;
        root.add(hangar);
    }

    // Control tower.
    const tower =
        new THREE.Group();

    const towerShaft =
        new THREE.Mesh(
            new THREE.BoxGeometry(
                13,
                48,
                13
            ),
            new THREE.MeshStandardMaterial({
                color: 0x8f989b
            })
        );

    towerShaft.position.y = 24;
    tower.add(towerShaft);

    const cabin =
        new THREE.Mesh(
            new THREE.BoxGeometry(
                27,
                9,
                27
            ),
            new THREE.MeshPhysicalMaterial({
                color: 0x244653,
                transparent: true,
                opacity: 0.83,
                roughness: 0.25
            })
        );

    cabin.position.y = 52;
    tower.add(cabin);

    tower.position.set(
        70,
        0,
        135
    );

    root.add(tower);

    // Runway lights.
    const lampGeometry =
        new THREE.SphereGeometry(
            0.42,
            8,
            6
        );

    for (
        let x = -240;
        x <= 240;
        x += 24
    ) {
        for (const z of [-20, 20]) {
            const lamp =
                new THREE.Mesh(
                    lampGeometry,
                    new THREE.MeshBasicMaterial({
                        color: 0xdff8ff
                    })
                );

            lamp.position.set(
                x,
                0.8,
                z
            );

            root.add(lamp);
        }
    }

    const label =
        createLabel(name);

    label.position.set(
        0,
        65,
        0
    );

    label.scale.set(
        70,
        18,
        1
    );

    root.add(label);

    return root;
}

function createUAV() {
    /*
     * CRITICAL ORIENTATION RULE:
     *
     * The nose is at +X.
     * The rear engine / pusher propeller is at -X.
     *
     * Do not rotate the whole model by PI.
     * Do not use root.lookAt().
     */
    const aircraftRoot =
        new THREE.Group();

    aircraftRoot.name =
        "PRATIRUP_UAV_ROOT";

    const model =
        new THREE.Group();

    model.name =
        "PRATIRUP_INDIGENOUS_MALE_UAV_MODEL";

    aircraftRoot.add(model);

    const bodyMaterial =
        new THREE.MeshStandardMaterial({
            color: 0xaeb8bd,
            metalness: 0.38,
            roughness: 0.47
        });

    const darkMaterial =
        new THREE.MeshStandardMaterial({
            color: 0x151c21,
            metalness: 0.32,
            roughness: 0.46
        });

    // Fuselage along X.
    const fuselageGeometry =
        new THREE.CylinderGeometry(
            2.75,
            1.75,
            35,
            40
        );

    fuselageGeometry.rotateZ(
        Math.PI / 2
    );

    const fuselage =
        new THREE.Mesh(
            fuselageGeometry,
            bodyMaterial
        );

    fuselage.scale.z = 0.84;
    fuselage.castShadow = true;
    model.add(fuselage);

    // Nose is explicitly at +X.
    const nose =
        new THREE.Mesh(
            new THREE.SphereGeometry(
                2.72,
                32,
                18
            ),
            bodyMaterial
        );

    nose.scale.set(
        1.85,
        1,
        0.84
    );

    nose.position.x = 18;
    nose.castShadow = true;
    model.add(nose);

    // EO/IR visual sensor.
    const sensorBall =
        new THREE.Mesh(
            new THREE.SphereGeometry(
                1.2,
                24,
                18
            ),
            new THREE.MeshStandardMaterial({
                color: 0x10191f,
                metalness: 0.25,
                roughness: 0.25
            })
        );

    sensorBall.position.set(
        10,
        -2.8,
        0
    );

    model.add(sensorBall);

    // Wings extend along +/- Z.
    const wingGeometry =
        new THREE.BoxGeometry(
            11,
            0.65,
            76
        );

    const mainWing =
        new THREE.Mesh(
            wingGeometry,
            bodyMaterial
        );

    mainWing.position.set(
        0,
        0.1,
        0
    );

    mainWing.castShadow = true;
    model.add(mainWing);

    // Slightly tapered wing-tip panels.
    for (const z of [-39, 39]) {
        const tip =
            new THREE.Mesh(
                new THREE.BoxGeometry(
                    5.5,
                    0.48,
                    7
                ),
                bodyMaterial
            );

        tip.position.set(
            -1.5,
            0.25,
            z
        );

        model.add(tip);
    }

    // Twin booms.
    for (const z of [-6.2, 6.2]) {
        const boomGeometry =
            new THREE.CylinderGeometry(
                0.72,
                0.45,
                24,
                20
            );

        boomGeometry.rotateZ(
            Math.PI / 2
        );

        const boom =
            new THREE.Mesh(
                boomGeometry,
                bodyMaterial
            );

        boom.position.set(
            -10,
            0.4,
            z
        );

        model.add(boom);

        const fin =
            new THREE.Mesh(
                new THREE.BoxGeometry(
                    4.8,
                    8.2,
                    0.55
                ),
                bodyMaterial
            );

        fin.position.set(
            -22,
            4,
            z
        );

        fin.rotation.z =
            THREE.MathUtils.degToRad(
                -8
            );

        model.add(fin);
    }

    // Horizontal stabilizer.
    const stabilizer =
        new THREE.Mesh(
            new THREE.BoxGeometry(
                5,
                0.48,
                17
            ),
            bodyMaterial
        );

    stabilizer.position.set(
        -21,
        1,
        0
    );

    model.add(stabilizer);

    // Rear engine cowl.
    const cowlGeometry =
        new THREE.CylinderGeometry(
            2,
            1.65,
            5,
            30
        );

    cowlGeometry.rotateZ(
        Math.PI / 2
    );

    const cowl =
        new THREE.Mesh(
            cowlGeometry,
            darkMaterial
        );

    cowl.position.x = -17.5;
    model.add(cowl);

    // Pusher propeller at the rear (-X).
    const propeller =
        new THREE.Group();

    propeller.name =
        "UAV_PUSHER_PROPELLER";

    propeller.position.x =
        -20.5;

    const hub =
        new THREE.Mesh(
            new THREE.SphereGeometry(
                0.76,
                18,
                14
            ),
            darkMaterial
        );

    propeller.add(hub);

    const bladeMaterial =
        new THREE.MeshStandardMaterial({
            color: 0x101518,
            metalness: 0.32,
            roughness: 0.40
        });

    for (
        let index = 0;
        index < 3;
        index++
    ) {
        const pivot =
            new THREE.Group();

        pivot.rotation.x =
            index *
            Math.PI *
            2 /
            3;

        const blade =
            new THREE.Mesh(
                new THREE.BoxGeometry(
                    0.28,
                    11.5,
                    0.95
                ),
                bladeMaterial
            );

        blade.position.y = 5.6;

        blade.rotation.z =
            THREE.MathUtils.degToRad(
                7
            );

        pivot.add(blade);
        propeller.add(pivot);
    }

    model.add(propeller);

    // Landing gear.
    const landingGear =
        new THREE.Group();

    landingGear.name =
        "UAV_LANDING_GEAR";

    const strutMaterial =
        new THREE.MeshStandardMaterial({
            color: 0x596267,
            metalness: 0.78,
            roughness: 0.30
        });

    const tyreMaterial =
        new THREE.MeshStandardMaterial({
            color: 0x0b0e10,
            roughness: 0.92
        });

    function addGear(
        x,
        z,
        radius = 0.78
    ) {
        const strut =
            new THREE.Mesh(
                new THREE.CylinderGeometry(
                    0.12,
                    0.12,
                    4.6,
                    10
                ),
                strutMaterial
            );

        strut.position.set(
            x,
            -3,
            z
        );

        landingGear.add(strut);

        const wheel =
            new THREE.Mesh(
                new THREE.TorusGeometry(
                    radius,
                    radius * 0.33,
                    10,
                    22
                ),
                tyreMaterial
            );

        wheel.rotation.y =
            Math.PI / 2;

        wheel.position.set(
            x,
            -5.2,
            z
        );

        landingGear.add(wheel);
    }

    addGear(
        4.5,
        5.2
    );

    addGear(
        4.5,
        -5.2
    );

    addGear(
        13,
        0,
        0.62
    );

    model.add(landingGear);

    // Navigation lights.
    const navigationLights =
        new THREE.Group();

    const leftNav =
        new THREE.Mesh(
            new THREE.SphereGeometry(
                0.38,
                12,
                8
            ),
            new THREE.MeshBasicMaterial({
                color: 0xff3535
            })
        );

    leftNav.position.set(
        0,
        0.7,
        38
    );

    navigationLights.add(
        leftNav
    );

    const rightNav =
        new THREE.Mesh(
            new THREE.SphereGeometry(
                0.38,
                12,
                8
            ),
            new THREE.MeshBasicMaterial({
                color: 0x46ff84
            })
        );

    rightNav.position.set(
        0,
        0.7,
        -38
    );

    navigationLights.add(
        rightNav
    );

    model.add(navigationLights);

    // Engine status beacon.
    const engineBeacon =
        new THREE.Mesh(
            new THREE.SphereGeometry(
                0.34,
                14,
                10
            ),
            new THREE.MeshStandardMaterial({
                color: 0x38dc78,
                emissive: 0x38dc78,
                emissiveIntensity: 1
            })
        );

    engineBeacon.position.set(
        -15,
        2.4,
        -1.4
    );

    model.add(engineBeacon);

    aircraftRoot.scale.setScalar(
        CONFIG.aircraft.scale
    );

    return {
        root: aircraftRoot,
        model,
        propeller,
        landingGear,
        navigationLights,
        engineBeacon
    };
}

function createMissionRoute() {
    const runwayY =
        CONFIG.world.runwayHeight +
        5;

    /*
     * Route moves mainly from negative X to positive X.
     * Since UAV nose is +X, quaternion alignment below makes it
     * physically point in the direction of travel.
     */
    return new THREE.CatmullRomCurve3(
        [
            // Alpha apron/taxi.
            new THREE.Vector3(
                -2350,
                runwayY,
                120
            ),

            new THREE.Vector3(
                -2250,
                runwayY,
                70
            ),

            new THREE.Vector3(
                -2110,
                runwayY,
                10
            ),

            // Runway acceleration.
            new THREE.Vector3(
                -1920,
                runwayY,
                0
            ),

            // Takeoff/climb.
            new THREE.Vector3(
                -1650,
                35,
                -15
            ),

            new THREE.Vector3(
                -1420,
                90,
                -35
            ),

            new THREE.Vector3(
                -1150,
                155,
                -70
            ),

            new THREE.Vector3(
                -850,
                215,
                15
            ),

            // Mountains.
            new THREE.Vector3(
                -500,
                285,
                120
            ),

            new THREE.Vector3(
                -100,
                320,
                30
            ),

            new THREE.Vector3(
                300,
                330,
                -110
            ),

            // Coast / sea.
            new THREE.Vector3(
                650,
                325,
                -150
            ),

            new THREE.Vector3(
                980,
                330,
                -70
            ),

            new THREE.Vector3(
                1320,
                325,
                80
            ),

            // Destination.
            new THREE.Vector3(
                1630,
                285,
                80
            ),

            new THREE.Vector3(
                1860,
                210,
                30
            ),

            new THREE.Vector3(
                2050,
                135,
                0
            ),

            new THREE.Vector3(
                2190,
                70,
                0
            ),

            new THREE.Vector3(
                2320,
                28,
                0
            ),

            // Touchdown and rollout.
            new THREE.Vector3(
                2440,
                runwayY,
                0
            ),

            new THREE.Vector3(
                2620,
                runwayY,
                0
            )
        ],
        false,
        "catmullrom",
        0.10
    );
}

function createRouteLine(curve) {
    const geometry =
        new THREE.BufferGeometry()
            .setFromPoints(
                curve.getPoints(
                    400
                )
            );

    const material =
        new THREE.LineDashedMaterial({
            color: 0x48ff7b,
            transparent: true,
            opacity: 0.55,
            dashSize: 15,
            gapSize: 9
        });

    const line =
        new THREE.Line(
            geometry,
            material
        );

    line.computeLineDistances();

    return line;
}

function createWorld() {
    const root =
        new THREE.Group();

    root.name =
        "PRATIRUP_EARTH_ENVIRONMENT";

    root.add(
        createTerrain()
    );

    root.add(
        createSea()
    );

    root.add(
        createAirfield(
            "AIRFIELD ALPHA",
            -2110
        )
    );

    root.add(
        createAirfield(
            "AIRFIELD BRAVO",
            2440
        )
    );

    const cloudDefinitions = [
        [-1600, 155, -330, 1.1],
        [-1250, 190, 310, 1.25],
        [-800, 250, -350, 1.35],
        [-350, 300, 350, 1.2],
        [180, 285, -380, 1.4],
        [720, 245, 370, 1.25],
        [1100, 280, -350, 1.45],
        [1500, 255, 300, 1.15],
        [1900, 190, -300, 1.2]
    ];

    for (const definition of cloudDefinitions) {
        const cloud =
            createCloud(
                ...definition
            );

        runtime.clouds.push(
            cloud
        );

        root.add(cloud);
    }

    return root;
}


function extractBackendStatus(status) {
    if (
        !status ||
        typeof status !== "object"
    ) {
        return;
    }

    const player =
        status.simulation_player ??
        {};

    const scenario =
        status.scenario ??
        {};

    const faults =
        status.fault_injection ??
        {};

    const stateValue =
        player.state ??
        scenario.state;

    if (stateValue !== undefined) {
        runtime.mission.state =
            String(
                stateValue
            ).toUpperCase();
    }

    const phaseValue =
        scenario.phase ??
        player.phase;

    if (phaseValue !== undefined) {
        runtime.mission.phase =
            normalizePhase(
                phaseValue
            );
    }

    const progress =
        normalizeProgress(
            scenario.progress ??
            player.progress
        );

    if (progress !== null) {
        runtime.mission.progress =
            progress;

        recordProgressSample(
            progress
        );
    }

    const elapsed =
        finiteNumber(
            scenario.elapsed_time_sec ??
            player.elapsed_time_sec
        );

    if (elapsed !== null) {
        runtime.mission.elapsedTimeSec =
            elapsed;
    }

    const total =
        finiteNumber(
            scenario.total_duration_sec ??
            player.total_duration_sec ??
            player.duration_sec
        );

    if (total !== null) {
        runtime.mission.totalTimeSec =
            total;
    }

    const speed =
        finiteNumber(
            scenario.simulation_speed ??
            player.speed
        );

    if (speed !== null) {
        runtime.mission.simulationSpeed =
            speed;
    }

    const altitude =
        finiteNumber(
            scenario
                ?.targets
                ?.environment
                ?.altitude_m ??

            scenario
                ?.environment
                ?.altitude_m ??

            scenario.altitude_m
        );

    if (altitude !== null) {
        runtime.mission.altitudeM =
            altitude;
    }

    const rpm =
        finiteNumber(
            scenario
                ?.targets
                ?.engine
                ?.rpm ??

            scenario
                ?.engine
                ?.rpm ??

            scenario.rpm
        );

    if (rpm !== null) {
        runtime.mission.rpm =
            rpm;
    }

    const load =
        finiteNumber(
            scenario
                ?.targets
                ?.engine
                ?.load_percent ??

            scenario
                ?.targets
                ?.engine
                ?.loadPercent ??

            scenario
                ?.engine
                ?.load_percent ??

            scenario.load_percent
        );

    if (load !== null) {
        runtime.mission.loadPercent =
            load;
    }

    const throttle =
        finiteNumber(
            scenario
                ?.targets
                ?.engine
                ?.throttle_percent ??

            scenario
                ?.targets
                ?.engine
                ?.throttlePercent ??

            scenario.throttle_percent
        );

    if (throttle !== null) {
        runtime.mission.throttlePercent =
            throttle;
    }

    runtime.mission.activeFaultCount =
        finiteNumber(
            faults.active_fault_count
        ) ??
        0;

    runtime.mission.activeFaults =
        Array.isArray(
            faults.active_faults
        )
            ? faults.active_faults
            : [];

    runtime.backendConnected = true;

    runtime.stats.backendUpdates++;

    runtime.stats.lastBackendUpdateAt =
        new Date().toISOString();

    updateVisualTargets();
    updateHUD();
}

function extractTelemetry(payload) {
    if (
        !payload ||
        typeof payload !== "object"
    ) {
        return;
    }

    const telemetry =
        payload.telemetry ??
        payload.data ??
        payload.frame ??
        payload;

    const engine =
        telemetry.engine ??
        {};

    const environment =
        telemetry.environment ??
        {};

    const rpm =
        finiteNumber(
            engine.rpm
        );

    if (rpm !== null) {
        runtime.mission.rpm =
            rpm;
    }

    const load =
        finiteNumber(
            engine.load_percent ??
            engine.loadPercent
        );

    if (load !== null) {
        runtime.mission.loadPercent =
            load;
    }

    const throttle =
        finiteNumber(
            engine.throttle_percent ??
            engine.throttlePercent
        );

    if (throttle !== null) {
        runtime.mission.throttlePercent =
            throttle;
    }

    const altitude =
        finiteNumber(
            environment.altitude_m ??
            environment.altitude
        );

    if (altitude !== null) {
        runtime.mission.altitudeM =
            altitude;
    }

    runtime.stats.telemetryUpdates++;

    updateVisualTargets();
    updateHUD();
}

function updateVisualTargets() {
    /*
     * Route movement is handled by recordProgressSample() and
     * predictedMissionProgress(). This fallback is only for the state
     * before the first backend progress packet arrives.
     */
    if (
        runtime.motion.progressSamples
            .length === 0
    ) {
        runtime.visual.targetRouteProgress =
            runtime.mission.progress;
    }

    if (
        runtime.mission.altitudeM !==
        null
    ) {
        runtime.visual.targetAltitude =
            clamp(
                runtime.mission.altitudeM *
                    CONFIG.mission.altitudeScale,
                0,
                CONFIG.mission.maximumVisualAltitude
            );
    }

    /*
     * 0 RPM is real and stops the propeller.
     * null means unavailable and therefore does not fabricate 0 RPM.
     */
    if (runtime.mission.rpm !== null) {
        runtime.visual.targetPropellerRPM =
            Math.max(
                0,
                runtime.mission.rpm
            );
    }

    switch (runtime.mission.phase) {
        case "TAKEOFF":
            runtime.visual.targetPitch =
                THREE.MathUtils.degToRad(
                    7
                );
            break;

        case "CLIMB":
            runtime.visual.targetPitch =
                THREE.MathUtils.degToRad(
                    4
                );
            break;

        case "DESCENT":
            runtime.visual.targetPitch =
                THREE.MathUtils.degToRad(
                    -3
                );
            break;

        case "LANDING":
            runtime.visual.targetPitch =
                THREE.MathUtils.degToRad(
                    -1
                );
            break;

        default:
            runtime.visual.targetPitch = 0;
            break;
    }

    if (runtime.landingGear) {
        runtime.landingGear.visible = [
            "ENGINE_START",
            "WARMUP",
            "TAKEOFF",
            "LANDING",
            "ENGINE_SHUTDOWN"
        ].includes(
            runtime.mission.phase
        );
    }

    if (
        runtime.mission.phase ===
        "ENGINE_SHUTDOWN"
    ) {
        runtime.visual.targetPropellerRPM = 0;
    }

    updateEngineBeacon();
}

function updateEngineBeacon() {
    if (!runtime.engineBeacon) {
        return;
    }

    const faultActive =
        runtime.mission.activeFaultCount >
        0;

    const color =
        faultActive
            ? 0xff4343
            : 0x38dc78;

    runtime.engineBeacon.material.color.setHex(
        color
    );

    runtime.engineBeacon.material.emissive.setHex(
        color
    );

    runtime.engineBeacon.material.emissiveIntensity =
        faultActive
            ? 2.3
            : 1;
}

function orientAircraftToRoute(
    tangent,
    delta
) {
    routeTangent
        .copy(tangent)
        .normalize();

    flightQuaternion.setFromUnitVectors(
        LOCAL_FORWARD,
        routeTangent
    );

    runtime.aircraftRoot.quaternion.slerp(
        flightQuaternion,
        smoothingAlpha(
            delta,
            CONFIG.motion
                .attitudeHalfLifeSec
        )
    );

    const horizontalHeading =
        Math.atan2(
            routeTangent.z,
            routeTangent.x
        );

    runtime.visual.targetBank =
        clamp(
            -Math.sin(
                horizontalHeading
            ) *
                0.08,
            -0.10,
            0.10
        );

    runtime.visual.bank =
        damp(
            runtime.visual.bank,
            runtime.visual.targetBank,
            delta,
            CONFIG.motion
                .bankHalfLifeSec
        );

    runtime.visual.pitch =
        damp(
            runtime.visual.pitch,
            runtime.visual.targetPitch,
            delta,
            CONFIG.motion
                .pitchHalfLifeSec
        );

    bankQuaternion.setFromAxisAngle(
        LOCAL_FORWARD,
        runtime.visual.bank
    );

    pitchQuaternion.setFromAxisAngle(
        LOCAL_RIGHT,
        -runtime.visual.pitch
    );

    tempQuaternion.copy(
        bankQuaternion
    );

    tempQuaternion.multiply(
        pitchQuaternion
    );

    runtime.aircraftModel.quaternion.copy(
        tempQuaternion
    );
}

function updateAircraft(
    delta,
    nowMs = performance.now()
) {
    if (
        !runtime.aircraftRoot ||
        !runtime.aircraftModel ||
        !runtime.routeCurve
    ) {
        return;
    }

    /*
     * Continuously predict a small amount between backend packets.
     * The prediction itself changes every render frame, eliminating the
     * visible "patch-to-patch" movement caused by discrete progress data.
     */
    const predictedProgress =
        predictedMissionProgress(
            nowMs
        );

    runtime.visual.targetRouteProgress =
        predictedProgress;

    const previousProgress =
        runtime.visual.routeProgress;

    runtime.visual.routeProgress =
        damp(
            runtime.visual.routeProgress,
            predictedProgress,
            delta,
            CONFIG.motion
                .progressHalfLifeSec
        );

    /*
     * Network timing can make a correction target land microscopically
     * behind the already-rendered position. During active forward flight,
     * never show that tiny backwards tick.
     */
    if (
        missionIsAdvancing() &&
        runtime.visual.routeProgress <
            previousProgress
    ) {
        runtime.visual.routeProgress =
            previousProgress;
    }

    const progress =
        clamp(
            runtime.visual.routeProgress,
            0,
            0.999999
        );

    predictedRoutePosition.copy(
        runtime.routeCurve.getPointAt(
            progress
        )
    );

    predictedRouteTangent.copy(
        runtime.routeCurve.getTangentAt(
            progress
        )
    );

    const phase =
        runtime.mission.phase;

    /*
     * Smooth altitude separately.
     * In v3.1 targetAltitude was applied directly to position.y, which
     * could cause a vertical hop on every altitude packet.
     */
    runtime.visual.altitude =
        damp(
            runtime.visual.altitude,
            runtime.visual.targetAltitude,
            delta,
            CONFIG.motion
                .altitudeHalfLifeSec
        );

    if (
        runtime.mission.altitudeM !==
            null &&
        ![
            "ENGINE_START",
            "WARMUP",
            "TAKEOFF",
            "LANDING",
            "ENGINE_SHUTDOWN"
        ].includes(phase)
    ) {
        const terrainClearance =
            terrainHeight(
                predictedRoutePosition.x,
                predictedRoutePosition.z
            ) +
            35;

        predictedRoutePosition.y =
            Math.max(
                terrainClearance,
                runtime.visual.altitude
            );
    }

    runtime.aircraftRoot.position.copy(
        predictedRoutePosition
    );

    orientAircraftToRoute(
        predictedRouteTangent,
        delta
    );

    runtime.visual.propellerRPM =
        damp(
            runtime.visual.propellerRPM,
            runtime.visual.targetPropellerRPM,
            delta,
            CONFIG.motion
                .propellerHalfLifeSec
        );

    if (
        runtime.propeller &&
        runtime.visual.propellerRPM >
            CONFIG.aircraft.minimumPropellerRPM
    ) {
        const revolutionsPerSecond =
            runtime.visual.propellerRPM /
            60;

        runtime.propeller.rotation.x +=
            revolutionsPerSecond *
            Math.PI *
            2 *
            delta;
    }

    if (
        runtime.engineBeacon &&
        runtime.mission.activeFaultCount >
            0
    ) {
        const pulse =
            1 +
            Math.sin(
                nowMs *
                    0.01
            ) *
                0.2;

        runtime.engineBeacon.scale.setScalar(
            pulse
        );
    } else if (runtime.engineBeacon) {
        runtime.engineBeacon.scale.setScalar(
            1
        );
    }

    runtime.motion.correctionError =
        runtime.mission.progress -
        runtime.visual.routeProgress;

    if (
        Math.abs(
            runtime.motion.correctionError
        ) > 0.000001
    ) {
        runtime.motion.softCorrections++;
    }
}

function updateClouds(delta) {
    runtime.clouds.forEach(
        (
            cloud,
            index
        ) => {
            cloud.position.x +=
                (
                    2.2 +
                    index *
                        0.05
                ) *
                delta;

            if (
                cloud.position.x >
                2800
            ) {
                cloud.position.x =
                    -2800;
            }
        }
    );
}

function updateCamera(delta) {
    if (
        !runtime.aircraftRoot ||
        !runtime.camera ||
        !runtime.controls
    ) {
        return;
    }

    const positionAlpha =
        smoothingAlpha(
            delta,
            CONFIG.motion
                .cameraPositionHalfLifeSec
        );

    const targetAlpha =
        smoothingAlpha(
            delta,
            CONFIG.motion
                .cameraTargetHalfLifeSec
        );

    const aircraftPosition =
        runtime.aircraftRoot.position;

    /*
     * Camera reference axes use exactly the same aircraft convention:
     * local +X = forward, local +Z = right.
     */
    worldForward
        .copy(LOCAL_FORWARD)
        .applyQuaternion(
            runtime.aircraftRoot.quaternion
        )
        .normalize();

    worldRight
        .copy(LOCAL_RIGHT)
        .applyQuaternion(
            runtime.aircraftRoot.quaternion
        )
        .normalize();

    worldUp
        .copy(LOCAL_UP)
        .applyQuaternion(
            runtime.aircraftRoot.quaternion
        )
        .normalize();

    switch (runtime.cameraMode) {
        case "FOLLOW":
            cameraDesiredPosition
                .copy(
                    aircraftPosition
                )
                .addScaledVector(
                    worldForward,
                    -70
                )
                .addScaledVector(
                    worldRight,
                    30
                )
                .addScaledVector(
                    worldUp,
                    24
                );

            cameraDesiredTarget
                .copy(
                    aircraftPosition
                )
                .addScaledVector(
                    worldForward,
                    18
                );

            runtime.controls.enabled =
                false;
            break;

        case "TOP":
            cameraDesiredPosition
                .copy(
                    aircraftPosition
                );

            cameraDesiredPosition.y +=
                155;

            cameraDesiredTarget.copy(
                aircraftPosition
            );

            runtime.controls.enabled =
                false;
            break;

        case "SIDE":
            cameraDesiredPosition
                .copy(
                    aircraftPosition
                )
                .addScaledVector(
                    worldRight,
                    105
                )
                .addScaledVector(
                    worldUp,
                    12
                );

            cameraDesiredTarget.copy(
                aircraftPosition
            );

            runtime.controls.enabled =
                false;
            break;

        case "FRONT":
            /*
             * Camera is ahead of the nose, looking BACK at the UAV.
             */
            cameraDesiredPosition
                .copy(
                    aircraftPosition
                )
                .addScaledVector(
                    worldForward,
                    92
                )
                .addScaledVector(
                    worldUp,
                    10
                );

            cameraDesiredTarget.copy(
                aircraftPosition
            );

            runtime.controls.enabled =
                false;
            break;

        case "REAR":
            cameraDesiredPosition
                .copy(
                    aircraftPosition
                )
                .addScaledVector(
                    worldForward,
                    -92
                )
                .addScaledVector(
                    worldUp,
                    12
                );

            cameraDesiredTarget
                .copy(
                    aircraftPosition
                )
                .addScaledVector(
                    worldForward,
                    20
                );

            runtime.controls.enabled =
                false;
            break;

        case "COCKPIT":
            /*
             * Conceptual forward-view camera near the nose.
             */
            cameraDesiredPosition
                .copy(
                    aircraftPosition
                )
                .addScaledVector(
                    worldForward,
                    12
                )
                .addScaledVector(
                    worldUp,
                    2.8
                );

            cameraDesiredTarget
                .copy(
                    aircraftPosition
                )
                .addScaledVector(
                    worldForward,
                    180
                )
                .addScaledVector(
                    worldUp,
                    4
                );

            runtime.controls.enabled =
                false;
            break;

        case "ORBIT":
            runtime.controls.enabled =
                true;

            runtime.controls.target.lerp(
                aircraftPosition,
                targetAlpha
            );

            runtime.controls.update();
            return;
    }

    runtime.camera.position.lerp(
        cameraDesiredPosition,
        positionAlpha
    );

    runtime.controls.target.lerp(
        cameraDesiredTarget,
        targetAlpha
    );

    runtime.camera.lookAt(
        runtime.controls.target
    );
}
function createHUD() {
    const hud =
        document.createElement(
            "div"
        );

    hud.className =
        "pratirup-uav-mission-hud";

    hud.innerHTML = `
        <div class="puav-header">
            <div>
                <small>PRATIRUP DIGITAL TWIN</small>
                <strong>INDIGENOUS MALE UAV MISSION VIEW</strong>
            </div>

            <div
                class="puav-backend"
                data-uav-backend
            >
                BACKEND: WAITING
            </div>
        </div>

        <div class="puav-phase">
            <span>MISSION PHASE</span>
            <strong data-uav-phase>
                ENGINE START
            </strong>
        </div>

        <div class="puav-telemetry">
            <div>
                <span>ALTITUDE</span>
                <strong data-uav-altitude>--</strong>
                <small>m</small>
            </div>

            <div>
                <span>ENGINE RPM</span>
                <strong data-uav-rpm>--</strong>
                <small>RPM</small>
            </div>

            <div>
                <span>LOAD</span>
                <strong data-uav-load>--</strong>
                <small>%</small>
            </div>

            <div>
                <span>THROTTLE</span>
                <strong data-uav-throttle>--</strong>
                <small>%</small>
            </div>

            <div>
                <span>MISSION</span>
                <strong data-uav-progress>0.0</strong>
                <small>%</small>
            </div>
        </div>

        <div class="puav-camera-panel">
            <span>CAMERA</span>

            <div>
                <button data-uav-camera="FOLLOW">FOLLOW</button>
                <button data-uav-camera="TOP">TOP</button>
                <button data-uav-camera="SIDE">SIDE</button>
                <button data-uav-camera="FRONT">FRONT</button>
                <button data-uav-camera="REAR">REAR</button>
                <button data-uav-camera="COCKPIT">COCKPIT</button>
                <button data-uav-camera="ORBIT">ORBIT</button>
            </div>
        </div>

        <div class="puav-progress">
            <div>
                <span>AIRFIELD ALPHA</span>
                <span>MOUNTAINS</span>
                <span>SEA</span>
                <span>AIRFIELD BRAVO</span>
            </div>

            <div class="puav-progress-track">
                <div
                    class="puav-progress-fill"
                    data-uav-progress-fill
                ></div>
            </div>
        </div>

        <div
            class="puav-fault"
            data-uav-fault
        >
            NO ACTIVE SIMULATION FAULT
        </div>

        <div class="puav-orientation">
            ORIENTATION: +X NOSE / ROUTE-TANGENT ALIGNED
        </div>

        <div class="puav-disclaimer">
            PRATIRUP engineering-demonstrator visualization.
            Conceptual indigenous UAV geometry.
            Not operational CAD or a certified flight simulator.
        </div>
    `;

    runtime.host.appendChild(
        hud
    );

    hud.querySelectorAll(
        "[data-uav-camera]"
    ).forEach(
        button => {
            button.addEventListener(
                "click",
                () => {
                    setCameraMode(
                        button.dataset.uavCamera
                    );
                }
            );
        }
    );

    return hud;
}

function injectStyles() {
    const style =
        document.createElement(
            "style"
        );

    style.textContent = `
        #${CONFIG.hostId} {
            position: relative;
            width: 100%;
            height: 720px;
            min-height: 560px;
            overflow: hidden;
            border-radius: 16px;
            background: #07131e;
        }

        #${CONFIG.hostId} canvas {
            display: block;
            width: 100%;
            height: 100%;
        }

        .pratirup-uav-mission-hud {
            position: absolute;
            inset: 0;
            pointer-events: none;
            color: #f3fbff;
            font-family:
                Inter,
                system-ui,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                sans-serif;
        }

        .puav-header {
            position: absolute;
            top: 16px;
            left: 16px;
            right: 16px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }

        .puav-header > div:first-child {
            display: flex;
            flex-direction: column;
            gap: 4px;
            padding: 11px 13px;
            border: 1px solid rgba(255,255,255,.14);
            border-radius: 9px;
            background: rgba(4,15,24,.70);
            backdrop-filter: blur(10px);
        }

        .puav-header small {
            color: #65eaff;
            font-size: 9px;
            letter-spacing: .14em;
        }

        .puav-header strong {
            font-size: 15px;
            letter-spacing: .04em;
        }

        .puav-backend {
            padding: 9px 11px;
            border: 1px solid rgba(255,255,255,.15);
            border-radius: 8px;
            background: rgba(4,15,24,.70);
            font-size: 9px;
            letter-spacing: .09em;
        }

        .puav-backend.connected {
            color: #65ff8d;
            border-color: rgba(101,255,141,.45);
        }

        .puav-phase {
            position: absolute;
            left: 16px;
            top: 95px;
            min-width: 150px;
            padding: 10px 12px;
            border: 1px solid rgba(72,255,123,.42);
            border-radius: 8px;
            background: rgba(4,19,14,.72);
        }

        .puav-phase span {
            display: block;
            margin-bottom: 4px;
            font-size: 8px;
            letter-spacing: .12em;
            opacity: .58;
        }

        .puav-phase strong {
            color: #48ff7b;
            font-size: 13px;
        }

        .puav-camera-panel {
            position: absolute;
            top: 88px;
            right: 16px;
            width: 260px;
            padding: 10px;
            border: 1px solid rgba(255,255,255,.13);
            border-radius: 10px;
            background: rgba(4,15,24,.74);
            backdrop-filter: blur(10px);
            pointer-events: auto;
        }

        .puav-camera-panel > span {
            display: block;
            margin-bottom: 7px;
            font-size: 8px;
            letter-spacing: .12em;
            opacity: .58;
        }

        .puav-camera-panel > div {
            display: grid;
            grid-template-columns: repeat(3,1fr);
            gap: 5px;
// PRATIRUP UAV Mission Visualization v3.2.0
// PART 4 OF 4
// Original line range: 3496-4659
// Paste this immediately after Part 3.

        }

        .puav-camera-panel button {
            padding: 7px 4px;
            border: 1px solid rgba(255,255,255,.14);
            border-radius: 6px;
            background: rgba(255,255,255,.03);
            color: #eafbff;
            font-size: 8px;
            cursor: pointer;
        }

        .puav-camera-panel button:hover,
        .puav-camera-panel button.active {
            border-color: #00d9ff;
        }

        .puav-camera-panel button.active {
            color: #67f3ff;
            background: rgba(0,217,255,.10);
        }

        .puav-telemetry {
            position: absolute;
            left: 16px;
            bottom: 95px;
            display: grid;
            grid-template-columns:
                repeat(5,minmax(82px,1fr));
            gap: 7px;
        }

        .puav-telemetry > div {
            min-width: 90px;
            padding: 9px;
            border: 1px solid rgba(255,255,255,.13);
            border-radius: 8px;
            background: rgba(4,15,24,.72);
            backdrop-filter: blur(9px);
        }

        .puav-telemetry span {
            display: block;
            margin-bottom: 4px;
            font-size: 8px;
            letter-spacing: .08em;
            opacity: .56;
        }

        .puav-telemetry strong {
            font-size: 15px;
        }

        .puav-telemetry small {
            margin-left: 3px;
            font-size: 8px;
            opacity: .5;
        }

        .puav-progress {
            position: absolute;
            left: 16px;
            right: 16px;
            bottom: 49px;
        }

        .puav-progress > div:first-child {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
            font-size: 8px;
            letter-spacing: .06em;
            opacity: .67;
        }

        .puav-progress-track {
            height: 5px;
            overflow: hidden;
            border-radius: 5px;
            background: rgba(255,255,255,.12);
        }

        .puav-progress-fill {
            width: 0%;
            height: 100%;
            background:
                linear-gradient(
                    90deg,
                    #00d9ff,
                    #48ff7b
                );
        }

        .puav-fault {
            position: absolute;
            right: 16px;
            bottom: 93px;
            padding: 8px 10px;
            border: 1px solid rgba(72,255,123,.35);
            border-radius: 7px;
            background: rgba(4,18,13,.70);
            color: #63ff8f;
            font-size: 8px;
            letter-spacing: .06em;
        }

        .puav-fault.active {
            color: #ff6969;
            border-color: rgba(255,85,85,.50);
            background: rgba(35,7,7,.72);
        }

        .puav-orientation {
            position: absolute;
            top: 16px;
            left: 50%;
            transform: translateX(-50%);
            padding: 7px 9px;
            border: 1px solid rgba(0,217,255,.20);
            border-radius: 7px;
            background: rgba(4,15,24,.56);
            color: rgba(230,251,255,.60);
            font-size: 8px;
            letter-spacing: .08em;
        }

        .puav-disclaimer {
            position: absolute;
            left: 50%;
            bottom: 13px;
            transform: translateX(-50%);
            max-width: 80%;
            text-align: center;
            font-size: 8px;
            color: rgba(255,255,255,.46);
        }

        @media (max-width: 900px) {
            #${CONFIG.hostId} {
                height: 620px;
            }

            .puav-telemetry {
                grid-template-columns:
                    repeat(3,minmax(80px,1fr));
                right: 16px;
            }

            .puav-camera-panel {
                width: 220px;
            }

            .puav-orientation {
                display: none;
            }
        }
    `;

    document.head.appendChild(
        style
    );
}

function updateHUD() {
    if (!runtime.hud) {
        return;
    }

    const query =
        selector =>
            runtime.hud.querySelector(
                selector
            );

    query(
        "[data-uav-phase]"
    ).textContent =
        PHASE_LABELS[
            runtime.mission.phase
        ] ??
        runtime.mission.phase;

    query(
        "[data-uav-altitude]"
    ).textContent =
        runtime.mission.altitudeM ===
        null
            ? "--"
            : runtime.mission.altitudeM.toFixed(
                0
            );

    query(
        "[data-uav-rpm]"
    ).textContent =
        runtime.mission.rpm ===
        null
            ? "--"
            : runtime.mission.rpm.toFixed(
                0
            );

    query(
        "[data-uav-load]"
    ).textContent =
        runtime.mission.loadPercent ===
        null
            ? "--"
            : runtime.mission.loadPercent.toFixed(
                1
            );

    query(
        "[data-uav-throttle]"
    ).textContent =
        runtime.mission.throttlePercent ===
        null
            ? "--"
            : runtime.mission.throttlePercent.toFixed(
                1
            );

    const percentage =
        runtime.mission.progress *
        100;

    query(
        "[data-uav-progress]"
    ).textContent =
        percentage.toFixed(
            1
        );

    query(
        "[data-uav-progress-fill]"
    ).style.width =
        `${percentage}%`;

    const backend =
        query(
            "[data-uav-backend]"
        );

    backend.textContent =
        runtime.backendConnected
            ? "BACKEND: CONNECTED"
            : "BACKEND: WAITING";

    backend.classList.toggle(
        "connected",
        runtime.backendConnected
    );

    const fault =
        query(
            "[data-uav-fault]"
        );

    if (
        runtime.mission.activeFaultCount >
        0
    ) {
        const firstFault =
            runtime.mission.activeFaults[
                0
            ];

        fault.textContent =
            `SIMULATION FAULT: ${
                firstFault?.fault_type ??
                firstFault?.type ??
                "ACTIVE"
            }`;

        fault.classList.add(
            "active"
        );
    } else {
        fault.textContent =
            "NO ACTIVE SIMULATION FAULT";

        fault.classList.remove(
            "active"
        );
    }

    runtime.hud.querySelectorAll(
        "[data-uav-camera]"
    ).forEach(
        button => {
            button.classList.toggle(
                "active",
                button.dataset.uavCamera ===
                    runtime.cameraMode
            );
        }
    );
}

function setCameraMode(mode) {
    const normalized =
        String(
            mode ??
            ""
        )
            .trim()
            .toUpperCase();

    if (
        !CAMERA_MODES.includes(
            normalized
        )
    ) {
        console.warn(
            `[PRATIRUP UAV] Unsupported camera mode: ${normalized}`
        );

        return false;
    }

    runtime.cameraMode =
        normalized;

    if (runtime.controls) {
        runtime.controls.enabled =
            normalized === "ORBIT";
    }

    updateHUD();

    return true;
}

function resize() {
    if (
        !runtime.host ||
        !runtime.camera ||
        !runtime.renderer
    ) {
        return;
    }

    const rect =
        runtime.host.getBoundingClientRect();

    const width =
        Math.max(
            1,
            rect.width
        );

    const height =
        Math.max(
            1,
            rect.height
        );

    runtime.camera.aspect =
        width / height;

    runtime.camera.updateProjectionMatrix();

    runtime.renderer.setSize(
        width,
        height,
        false
    );

    runtime.renderer.setPixelRatio(
        Math.min(
            window.devicePixelRatio ||
                1,
            CONFIG.pixelRatioCap
        )
    );
}
function missionStatusHandler(event) {
    extractBackendStatus(
        event.detail
    );
}

function telemetryHandler(event) {
    extractTelemetry(
        event.detail
    );
}

async function requestInitialBackendStatus() {
    const controller =
        window.PRATIRUPMissionControl;

    if (
        !controller ||
        typeof controller.getStatus !==
            "function"
    ) {
        return;
    }

    try {
        const status =
            await controller.getStatus();

        extractBackendStatus(
            status
        );
    } catch (error) {
        console.warn(
            "[PRATIRUP UAV] Initial mission status request failed.",
            error
        );
    }
}

function animate(nowMs) {
    if (
        !runtime.running ||
        runtime.disposed
    ) {
        return;
    }

    runtime.animationFrame =
        requestAnimationFrame(
            animate
        );

    const delta =
        Math.min(
            runtime.clock.getDelta(),
            CONFIG.motion
                .maximumFrameDeltaSec
        );

    const frameTimeMs =
        Number.isFinite(nowMs)
            ? nowMs
            : performance.now();

    updateAircraft(
        delta,
        frameTimeMs
    );

    updateClouds(delta);
    updateCamera(delta);

    runtime.renderer.render(
        runtime.scene,
        runtime.camera
    );

    runtime.stats.frames++;
}

function start() {
    if (!runtime.initialized) {
        return initialize();
    }

    if (runtime.running) {
        return getStatus();
    }

    runtime.running = true;
    runtime.clock.start();
    animate();

    return getStatus();
}

function stop() {
    runtime.running = false;

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

    return getStatus();
}

function initialize() {
    if (runtime.initialized) {
        return getStatus();
    }

    const host =
        document.getElementById(
            CONFIG.hostId
        );

    if (!host) {
        console.warn(
            `[PRATIRUP UAV] #${CONFIG.hostId} was not found.`
        );

        return {
            success: false,
            reason: "HOST_NOT_FOUND"
        };
    }

    runtime.host = host;
    runtime.disposed = false;

    host.innerHTML = "";

    runtime.scene =
        new THREE.Scene();

    runtime.scene.fog =
        new THREE.FogExp2(
            0x9bc9df,
            0.00020
        );

    runtime.camera =
        new THREE.PerspectiveCamera(
            CONFIG.camera.fov,
            1,
            CONFIG.camera.near,
            CONFIG.camera.far
        );

    runtime.camera.position.set(
        -2300,
        80,
        145
    );

    runtime.renderer =
        new THREE.WebGLRenderer({
            antialias: true,
            powerPreference:
                "high-performance"
        });

    runtime.renderer.outputColorSpace =
        THREE.SRGBColorSpace;

    runtime.renderer.shadowMap.enabled =
        true;

    runtime.renderer.shadowMap.type =
        THREE.PCFSoftShadowMap;

    host.appendChild(
        runtime.renderer.domElement
    );

    runtime.controls =
        new OrbitControls(
            runtime.camera,
            runtime.renderer.domElement
        );

    runtime.controls.enableDamping =
        true;

    runtime.controls.dampingFactor =
        0.055;

    runtime.controls.minDistance =
        14;

    runtime.controls.maxDistance =
        650;

    runtime.controls.enabled =
        false;

    runtime.clock =
        new THREE.Clock();

    runtime.scene.add(
        createSky()
    );

    runtime.scene.add(
        new THREE.HemisphereLight(
            0xd2efff,
            0x34452f,
            2.2
        )
    );

    const sun =
        new THREE.DirectionalLight(
            0xfff3dc,
            3.1
        );

    sun.position.set(
        -1300,
        1900,
        -800
    );

    sun.castShadow = true;

    sun.shadow.mapSize.set(
        2048,
        2048
    );

    runtime.scene.add(sun);

    runtime.world =
        createWorld();

    runtime.scene.add(
        runtime.world
    );

    runtime.routeCurve =
        createMissionRoute();

    runtime.routeLine =
        createRouteLine(
            runtime.routeCurve
        );

    runtime.scene.add(
        runtime.routeLine
    );

    const aircraft =
        createUAV();

    runtime.aircraftRoot =
        aircraft.root;

    runtime.aircraftModel =
        aircraft.model;

    runtime.propeller =
        aircraft.propeller;

    runtime.landingGear =
        aircraft.landingGear;

    runtime.navigationLights =
        aircraft.navigationLights;

    runtime.engineBeacon =
        aircraft.engineBeacon;

    const initialPosition =
        runtime.routeCurve.getPointAt(
            0
        );

    runtime.aircraftRoot.position.copy(
        initialPosition
    );

    runtime.visual.routeProgress = 0;
    runtime.visual.targetRouteProgress = 0;
    runtime.visual.altitude =
        initialPosition.y;

    runtime.motion.progressSamples.length =
        0;

    runtime.motion.estimatedProgressRate =
        0;

    runtime.motion.lastAuthoritativeProgress =
        0;

    runtime.motion.lastSampleTimeMs =
        0;

    runtime.motion.predictedProgress =
        0;

    runtime.motion.correctionError =
        0;

    /*
     * Initialize orientation immediately so first frame is also correct.
     */
    const initialTangent =
        runtime.routeCurve.getTangentAt(
            0
        );

    flightQuaternion.setFromUnitVectors(
        LOCAL_FORWARD,
        initialTangent.normalize()
    );

    runtime.aircraftRoot.quaternion.copy(
        flightQuaternion
    );

    runtime.scene.add(
        runtime.aircraftRoot
    );

    injectStyles();

    runtime.hud =
        createHUD();

    runtime.resizeObserver =
        new ResizeObserver(
            resize
        );

    runtime.resizeObserver.observe(
        host
    );

    resize();

    window.addEventListener(
        "pratirup:mission-status",
        missionStatusHandler
    );

    window.addEventListener(
        "pratirup:telemetry",
        telemetryHandler
    );

    window.addEventListener(
        "pratirup:telemetry-update",
        telemetryHandler
    );

    window.addEventListener(
        "pratirup:backend-telemetry",
        telemetryHandler
    );

    runtime.initialized = true;

    runtime.stats.startedAt =
        new Date().toISOString();

    updateVisualTargets();
    updateHUD();

    start();
    requestInitialBackendStatus();

    console.log(
        `[PRATIRUP] UAV Mission Visualization v${VERSION} READY`
    );

    console.log(
        "[PRATIRUP UAV] Orientation convention: local +X = nose/forward."
    );

    return getStatus();
}

function getStatus() {
    return {
        service:
            "uav_mission_visualization",

        version: VERSION,

        initialized:
            runtime.initialized,

        running:
            runtime.running,

        backend_connected:
            runtime.backendConnected,

        camera_mode:
            runtime.cameraMode,

        supported_camera_modes:
            [...CAMERA_MODES],

        orientation: {
            model_forward_axis:
                "+X",
            route_alignment:
                "Quaternion.setFromUnitVectors(+X, route_tangent)",
            uses_object3d_lookat_for_aircraft:
                false,
            permanent_pi_model_flip:
                false
        },

        mission: {
            state:
                runtime.mission.state,

            phase:
                runtime.mission.phase,

            elapsed_time_sec:
                runtime.mission.elapsedTimeSec,

            total_time_sec:
                runtime.mission.totalTimeSec,

            progress:
                runtime.mission.progress,

            simulation_speed:
                runtime.mission.simulationSpeed,

            altitude_m:
                runtime.mission.altitudeM,

            rpm:
                runtime.mission.rpm,

            load_percent:
                runtime.mission.loadPercent,

            throttle_percent:
                runtime.mission.throttlePercent,

            active_fault_count:
                runtime.mission.activeFaultCount
        },

        motion: {
            mode:
                "AUTHORITATIVE_SAMPLE_PREDICTION",

            authoritative_progress:
                runtime.mission.progress,

            rendered_progress:
                runtime.visual.routeProgress,

            predicted_progress:
                runtime.motion.predictedProgress,

            estimated_progress_rate_per_sec:
                runtime.motion.estimatedProgressRate,

            correction_error:
                runtime.motion.correctionError,

            buffered_samples:
                runtime.motion.progressSamples.length,

            maximum_prediction_lead_sec:
                CONFIG.motion.maximumPredictionLeadSec,

            hard_syncs:
                runtime.motion.hardSyncs
        },

        propeller: {
            backend_rpm_driven:
                true,

            target_rpm:
                runtime.visual.targetPropellerRPM,

            visual_rpm:
                runtime.visual.propellerRPM,

            stops_at_zero_rpm:
                true
        },

        environment: {
            terrain: true,
            mountains: true,
            sea: true,
            coastline: true,
            clouds: true,
            atmospheric_sky: true,
            start_airfield:
                "AIRFIELD ALPHA",
            destination_airfield:
                "AIRFIELD BRAVO"
        },

        semantics: {
            zero_is_valid: true,
            none_means_unavailable:
                true,
            frontend_calculates_engine_physics:
                false,
            frontend_calculates_diagnostics:
                false,
            frontend_controls_can_fadec:
                false
        },

        runtime: {
            frames:
                runtime.stats.frames,

            backend_updates:
                runtime.stats.backendUpdates,

            telemetry_updates:
                runtime.stats.telemetryUpdates,

            started_at:
                runtime.stats.startedAt,

            last_backend_update_at:
                runtime.stats.lastBackendUpdateAt
        }
    };
}

function debugMotion() {
    const result = {
        mission_state:
            runtime.mission.state,

        authoritative_progress:
            runtime.mission.progress,

        rendered_progress:
            runtime.visual.routeProgress,

        predicted_progress:
            runtime.motion.predictedProgress,

        estimated_progress_rate_per_sec:
            runtime.motion.estimatedProgressRate,

        correction_error:
            runtime.motion.correctionError,

        buffered_samples:
            runtime.motion.progressSamples.length,

        last_sample_age_ms:
            runtime.motion.lastSampleTimeMs
                ? performance.now() -
                    runtime.motion.lastSampleTimeMs
                : null,

        advancing:
            missionIsAdvancing()
    };

    console.table(result);
    return result;
}


function debugOrientation() {
    if (
        !runtime.aircraftRoot ||
        !runtime.routeCurve
    ) {
        return null;
    }

    const progress =
        clamp(
            runtime.visual.routeProgress,
            0,
            0.9999
        );

    const tangent =
        runtime.routeCurve
            .getTangentAt(progress)
            .normalize();

    const actualForward =
        LOCAL_FORWARD
            .clone()
            .applyQuaternion(
                runtime.aircraftRoot.quaternion
            )
            .normalize();

    const alignment =
        actualForward.dot(
            tangent
        );

    const result = {
        progress,
        route_tangent:
            tangent.toArray(),
        aircraft_forward:
            actualForward.toArray(),
        dot_alignment:
            alignment,
        expected:
            "Near +1.0 means the nose points along the route."
    };

    console.table(result);
    return result;
}

function dispose() {
    if (
        !runtime.initialized ||
        runtime.disposed
    ) {
        return;
    }

    stop();

    window.removeEventListener(
        "pratirup:mission-status",
        missionStatusHandler
    );

    window.removeEventListener(
        "pratirup:telemetry",
        telemetryHandler
    );

    window.removeEventListener(
        "pratirup:telemetry-update",
        telemetryHandler
    );

    window.removeEventListener(
        "pratirup:backend-telemetry",
        telemetryHandler
    );

    runtime.resizeObserver?.disconnect();
    runtime.controls?.dispose();

    runtime.scene?.traverse(
        object => {
            object.geometry?.dispose?.();

            if (object.material) {
                const materials =
                    Array.isArray(
                        object.material
                    )
                        ? object.material
                        : [object.material];

                for (const material of materials) {
                    material.map?.dispose?.();
                    material.dispose?.();
                }
            }
        }
    );

    runtime.renderer?.dispose();
    runtime.renderer?.domElement?.remove();
    runtime.hud?.remove();

    runtime.motion.progressSamples.length =
        0;

    runtime.motion.estimatedProgressRate =
        0;

    runtime.motion.lastSampleTimeMs =
        0;

    runtime.disposed = true;
    runtime.initialized = false;
}

const API = Object.freeze({
    VERSION,
    initialize,
    start,
    stop,
    setCameraMode,
    getStatus,
    debugMotion,
    debugOrientation,
    dispose
});

window.PRATIRUPUAVMissionVisualization =
    API;

document.addEventListener(
    "DOMContentLoaded",
    () => {
        if (
            document.getElementById(
                CONFIG.hostId
            )
        ) {
            initialize();
        }
    }
);

export {
    VERSION,
    initialize,
    start,
    stop,
    setCameraMode,
    getStatus,
    debugMotion,
    debugOrientation,
    dispose
};

export default API;
