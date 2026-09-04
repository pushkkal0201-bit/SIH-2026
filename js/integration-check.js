"use strict";

const INTEGRATION_CHECK_VERSION =
  "1.0.0";

const integrationState = {

  ready: false,

  passed: 0,

  failed: 0,

  warnings: 0,

  checks: []

};

function recordCheck(
  name,
  condition,
  type = "required",
  message = ""
) {

  const passed =
    Boolean(condition);

  const result = {

    name,

    passed,

    type,

    message

  };

  integrationState
    .checks
    .push(result);

  if (passed) {

    integrationState.passed++;

    console.log(
      `%c[PASS] ${name}`,
      "color:#3ad699"
    );

  }

  else if (
    type === "warning"
  ) {

    integrationState.warnings++;

    console.warn(
      `[WARNING] ${name}`,
      message
    );

  }

  else {

    integrationState.failed++;

    console.error(
      `[FAIL] ${name}`,
      message
    );

  }

  return passed;

}

function checkModules() {

  console.group(
    "PRATIRUP — MODULE CHECK"
  );

  recordCheck(
    "Telemetry Schema",
    window.PRATIRUP_TELEMETRY_SCHEMA,
    "required",
    "telemetry-schema.js is missing or failed to load."
  );

  recordCheck(
    "Telemetry Bridge",
    window.PRATIRUP_BRIDGE,
    "required",
    "telemetry-bridge.js is unavailable."
  );

  recordCheck(
    "Digital Twin Core",
    window.PRATIRUP_TWIN,
    "required",
    "digital-twin-core.js is unavailable."
  );

  recordCheck(
    "Physics Interface",
    window.PRATIRUP_PHYSICS,
    "required",
    "physics-model-interface.js is unavailable."
  );

  recordCheck(
    "Engine Physics Model",
    window.PRATIRUP_ENGINE_MODEL,
    "required",
    "engine-physics-model.js is unavailable."
  );

  recordCheck(
    "Simulation Adapter",
    window.PRATIRUP_SIMULATION_ADAPTER,
    "required",
    "simulation-adapter.js is unavailable."
  );

  recordCheck(
    "Simulation Controls",
    window.PRATIRUP_SIMULATION_CONTROLS,
    "required",
    "simulation-controls.js is unavailable."
  );

  recordCheck(
    "Physics Dashboard",
    window.PRATIRUP_PHYSICS_DASHBOARD,
    "required",
    "physics-dashboard.js is unavailable."
  );

  recordCheck(
    "Three.js Engine Simulation",
    window.PRATIRUP_SIMULATION,
    "required",
    "simulation.js did not expose PRATIRUP_SIMULATION."
  );

  recordCheck(
    "Component Inspector",
    window.PRATIRUP_INSPECTOR,
    "warning",
    "component-inspector.js is unavailable."
  );

  console.groupEnd();

}

const REQUIRED_DOM_IDS = [

  "simulationStage",
  "engineCanvasHost",

  "runEngineButton",
  "rpmSlider",
  "rpmDisplay",

  "explodeButton",
  "wireframeButton",
  "labelsButton",
  "coverButton",
  "detailsButton",
  "resetViewButton",
  "expandViewButton",

  "focusComponentButton",
  "isolateComponentButton",
  "clearComponentButton",
  "selectedComponentName",

  "simThrottle",
  "simThrottleValue",

  "simLoad",
  "simLoadValue",

  "simAltitude",
  "simAltitudeValue",

  "simTemperature",
  "simTemperatureValue",

  "simMissionMode",
  "simMissionModeValue",

  "simMissionButton",
  "simResetButton",

  "telemetryRpm",
  "telemetryPower",
  "telemetryTorque",
  "telemetryFuelFlow",

  "telemetryCht1",
  "telemetryCht2",
  "telemetryCht3",
  "telemetryCht4",
  "telemetryChtAverage",

  "telemetryEgt1",
  "telemetryEgt2",
  "telemetryEgt3",
  "telemetryEgt4",
  "telemetryEgtAverage",

  "telemetryOilPressure",
  "telemetryOilPressureDetail",
  "telemetryOilTemperature",

  "telemetryAltitude",
  "telemetryAmbientTemp",
  "telemetryAmbientPressure",
  "telemetryAirDensity",

  "twinSource",
  "twinSourceDetail",
  "twinSyncStatus",
  "twinSynchronization",
  "twinModelConfidence",

  "physicsModelState",

  "healthIndex",
  "activeFaultCount",
  "estimatedRul"

];

function checkDom() {

  console.group(
    "PRATIRUP — DOM CHECK"
  );

  REQUIRED_DOM_IDS.forEach(
    id => {

      const element =
        document.getElementById(id);

      recordCheck(
        `DOM #${id}`,
        Boolean(element),
        "required",
        `Missing HTML element with id="${id}".`
      );

    }
  );

  console.groupEnd();

}

function checkTelemetrySchema() {

  const schema =
    window.PRATIRUP_TELEMETRY_SCHEMA;

  if (!schema) {
    return;
  }

  console.group(
    "PRATIRUP — TELEMETRY CHECK"
  );

  let frame = null;

  try {

    frame =
      schema.create(
        schema.DATA_SOURCES
          ?.SIMULATION
      );

    recordCheck(
      "Create telemetry frame",
      Boolean(frame),
      "required"
    );

    if (frame) {

      const validation =
        schema.validate(frame);

      recordCheck(
        "Telemetry frame validation",
        validation?.valid === true,
        "required",
        validation?.errors?.join(", ")
      );

    }

  }

  catch (error) {

    recordCheck(
      "Telemetry schema execution",
      false,
      "required",
      error.message
    );

  }

  console.groupEnd();

}

function checkDigitalTwin() {

  const twin =
    window.PRATIRUP_TWIN;

  if (!twin) {
    return;
  }

  console.group(
    "PRATIRUP — DIGITAL TWIN CHECK"
  );

  try {

    const state =
      twin.getState?.();

    recordCheck(
      "Digital Twin state accessible",
      Boolean(state),
      "required"
    );

    recordCheck(
      "Twin synchronization field",
      typeof state?.synchronized ===
        "boolean",
      "required"
    );

    recordCheck(
      "Twin source tracking",
      "activeSource" in
        (state || {}),
      "required"
    );

  }

  catch (error) {

    recordCheck(
      "Digital Twin execution",
      false,
      "required",
      error.message
    );

  }

  console.groupEnd();

}

function checkPhysics() {

  const physics =
    window.PRATIRUP_PHYSICS;

  if (!physics) {
    return;
  }

  console.group(
    "PRATIRUP — PHYSICS CHECK"
  );

  try {

    const status =
      physics.getStatus?.();

    recordCheck(
      "Physics interface status",
      Boolean(status),
      "required"
    );

    recordCheck(
      "Engine model registered",
      status?.modelRegistered ===
        true,
      "required",
      "engine-physics-model.js must register itself."
    );

    recordCheck(
      "Physics interface enabled",
      status?.enabled === true,
      "warning",
      "Physics interface is currently disabled."
    );

  }

  catch (error) {

    recordCheck(
      "Physics system execution",
      false,
      "required",
      error.message
    );

  }

  console.groupEnd();

}

function checkSimulationAdapter() {

  const adapter =
    window
      .PRATIRUP_SIMULATION_ADAPTER;

  if (!adapter) {
    return;
  }

  console.group(
    "PRATIRUP — SIMULATION ADAPTER CHECK"
  );

  try {

    const state =
      adapter.getState?.();

    recordCheck(
      "Simulation adapter state",
      Boolean(state),
      "required"
    );

    const frame =
      adapter.getFrame?.();

    recordCheck(
      "Simulation adapter frame",
      Boolean(frame),
      "required"
    );

    recordCheck(
      "Simulation telemetry source",
      frame?.meta?.source ===
        "simulation",
      "required"
    );

  }

  catch (error) {

    recordCheck(
      "Simulation adapter execution",
      false,
      "required",
      error.message
    );

  }

  console.groupEnd();

}

function checkCanvas() {

  console.group(
    "PRATIRUP — THREE.JS CHECK"
  );

  const simulation =
    window.PRATIRUP_SIMULATION;

  if (!simulation) {

    recordCheck(
      "Three.js simulation API",
      false,
      "required"
    );

    console.groupEnd();

    return;

  }

  recordCheck(
    "Three.js renderer",
    Boolean(
      simulation.renderer
    ),
    "required"
  );

  recordCheck(
    "Three.js scene",
    Boolean(
      simulation.scene
    ),
    "required"
  );

  recordCheck(
    "Three.js camera",
    Boolean(
      simulation.camera
    ),
    "required"
  );

  recordCheck(
    "Engine group",
    Boolean(
      simulation.engine
    ),
    "required"
  );

  const canvas =
    simulation.renderer
      ?.domElement;

  recordCheck(
    "Renderer canvas attached",
    Boolean(
      canvas &&
      canvas.isConnected
    ),
    "required"
  );

  console.groupEnd();

}

function checkEventFlow() {

  console.group(
    "PRATIRUP — EVENT PIPELINE"
  );

  let received =
    false;

  const handler =
    () => {

      received =
        true;

    };

  window.addEventListener(
    "pratirup:simulation-controls",
    handler,
    {
      once: true
    }
  );

  const controls =
    window
      .PRATIRUP_SIMULATION_CONTROLS;

  const state =
    controls?.getState?.();

  if (
    controls &&
    state
  ) {

    controls.setThrottle(
      state.throttlePercent
    );

  }

  window.setTimeout(
    () => {

      recordCheck(
        "Simulation controls event",
        received,
        "required",
        "Simulation control event was not detected."
      );

      console.groupEnd();

      finalizeIntegrationCheck();

    },
    100
  );

}

function finalizeIntegrationCheck() {

  integrationState.ready =
    true;

  const success =
    integrationState.failed ===
    0;

  console.log(
    "==============================================="
  );

  console.log(
    "PRATIRUP INTEGRATION REPORT"
  );

  console.log(
    "==============================================="
  );

  console.log(
    "Passed:",
    integrationState.passed
  );

  console.log(
    "Warnings:",
    integrationState.warnings
  );

  console.log(
    "Failed:",
    integrationState.failed
  );

  if (success) {

    console.log(
      "%cPRATIRUP CORE PIPELINE READY",
      "color:#3ad699;font-weight:bold;font-size:14px"
    );

  }

  else {

    console.error(
      "PRATIRUP integration contains errors."
    );

  }

  console.log(
    "==============================================="
  );

  window.dispatchEvent(

    new CustomEvent(
      "pratirup:integration-result",
      {

        detail: {

          success,

          passed:
            integrationState.passed,

          failed:
            integrationState.failed,

          warnings:
            integrationState.warnings,

          checks:
            [...integrationState.checks]

        }

      }
    )

  );

}

function runIntegrationCheck() {

  integrationState.passed =
    0;

  integrationState.failed =
    0;

  integrationState.warnings =
    0;

  integrationState.checks =
    [];

  console.log(
    "[PRATIRUP] Starting integration check..."
  );

  checkModules();

  checkDom();

  checkTelemetrySchema();

  checkDigitalTwin();

  checkPhysics();

  checkSimulationAdapter();

  checkCanvas();

  checkEventFlow();

}

window.PRATIRUP_INTEGRATION_CHECK = {

  version:
    INTEGRATION_CHECK_VERSION,

  run:
    runIntegrationCheck,

  getState() {

    return {

      ...integrationState,

      checks:
        [...integrationState.checks]

    };

  }

};

window.addEventListener(
  "load",
  () => {

    window.setTimeout(
      runIntegrationCheck,
      500
    );

  },
  {
    once: true
  }
);
